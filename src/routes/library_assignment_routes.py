"""
SharePoint Library Assignment Routes
Manages assignment of SharePoint libraries to reviewer users
"""

import json
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from src.db.db_handler import get_db
from src.routes.auth_routes import get_current_user, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/library-assignments", tags=["Library Assignments"])

# Pydantic models
class SharePointLibrary(BaseModel):
    site_id: str
    site_name: str
    library_id: str
    library_name: str
    library_url: Optional[str] = None
    item_count: Optional[int] = 0

class LibraryAssignment(BaseModel):
    user_id: int
    library_ids: List[str]  # Changed to strings since we're using SharePoint resource IDs
    permissions: Optional[dict] = Field(default={"can_view": True, "can_export": False, "can_analyze": True})
    notes: Optional[str] = None

class UserLibraryResponse(BaseModel):
    assignment_id: int
    library_id: int
    site_id: str
    site_name: str
    library_name: str
    library_url: Optional[str]
    permissions: dict
    assigned_at: datetime

@router.post("/sync-libraries", dependencies=[Depends(require_admin)])
async def sync_sharepoint_libraries(
    libraries: List[SharePointLibrary],
    db_handler = Depends(get_db)
):
    """Sync SharePoint libraries from the main app (admin only)"""
    try:
        synced_count = 0
        for library in libraries:
            # Upsert library
            result = await db_handler.fetch_one("""
                INSERT INTO public.sharepoint_libraries 
                (site_id, site_name, library_id, library_name, library_url, item_count, last_synced)
                VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                ON CONFLICT (site_id, library_id) 
                DO UPDATE SET
                    site_name = EXCLUDED.site_name,
                    library_name = EXCLUDED.library_name,
                    library_url = EXCLUDED.library_url,
                    item_count = EXCLUDED.item_count,
                    last_synced = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, library.site_id, library.site_name, library.library_id, 
                library.library_name, library.library_url, library.item_count)
            
            if result:
                synced_count += 1
        
        logger.info(f"Synced {synced_count} SharePoint libraries")
        return {"status": "success", "synced_count": synced_count}
        
    except Exception as e:
        logger.error(f"Failed to sync SharePoint libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/libraries")
async def get_all_libraries(
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Get all available SharePoint libraries (admin) or assigned libraries (reviewer)"""
    try:
        if current_user["role"] == "administrator":
            # Admins see all libraries
            libraries = await db_handler.fetch_all("""
                SELECT 
                    id, site_id, site_name, library_id, library_name, 
                    library_url, item_count, last_synced
                FROM public.sharepoint_libraries
                ORDER BY site_name, library_name
            """)
        else:
            # Reviewers see only assigned libraries
            libraries = await db_handler.fetch_all("""
                SELECT DISTINCT
                    sl.id, sl.site_id, sl.site_name, sl.library_id, 
                    sl.library_name, sl.library_url, sl.item_count, 
                    sl.last_synced, rla.permissions
                FROM public.sharepoint_libraries sl
                INNER JOIN public.reviewer_library_assignments rla 
                    ON sl.id = rla.library_id
                WHERE rla.user_id = $1 AND rla.is_active = true
                ORDER BY sl.site_name, sl.library_name
            """, current_user["id"])
        
        return {"libraries": libraries}
        
    except Exception as e:
        logger.error(f"Failed to get libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/{user_id}/libraries", dependencies=[Depends(require_admin)])
async def get_user_library_assignments(
    user_id: int,
    db_handler = Depends(get_db)
):
    """Get library assignments for a specific user (admin only)"""
    try:
        assignments = await db_handler.fetch_all("""
            SELECT 
                rla.id as assignment_id,
                sl.id as library_id,
                sl.site_id,
                sl.site_name,
                sl.library_id as sp_library_id,
                sl.library_name,
                sl.library_url,
                rla.permissions,
                rla.assigned_at,
                rla.notes,
                rla.is_active
            FROM public.reviewer_library_assignments rla
            JOIN public.sharepoint_libraries sl ON rla.library_id = sl.id
            WHERE rla.user_id = $1
            ORDER BY sl.site_name, sl.library_name
        """, user_id)
        
        return {"assignments": assignments}
        
    except Exception as e:
        logger.error(f"Failed to get user library assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/assign")
async def assign_libraries_to_user(
    assignment: LibraryAssignment,
    request: Request,
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Assign libraries to a reviewer user (admin only)"""
    try:
        # Verify the target user is a reviewer
        target_user = await db_handler.fetch_one("""
            SELECT id, role, full_name FROM public.users 
            WHERE id = $1 AND is_active = true
        """, assignment.user_id)
        
        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if target_user["role"] == "administrator":
            raise HTTPException(
                status_code=400, 
                detail="Cannot assign libraries to administrators - they have access to all libraries"
            )
        
        # Remove existing assignments for this user
        await db_handler.execute("""
            UPDATE public.reviewer_library_assignments 
            SET is_active = false 
            WHERE user_id = $1
        """, assignment.user_id)
        
        # Add new assignments
        assigned_count = 0
        for library_id in assignment.library_ids:
            # First ensure the library exists in sharepoint_libraries table
            await db_handler.execute("""
                INSERT INTO sharepoint_libraries 
                (site_id, site_name, library_id, library_name, last_synced)
                SELECT site_id, resource_name, resource_id, resource_name, CURRENT_TIMESTAMP
                FROM sharepoint_permissions 
                WHERE resource_id = $1 AND resource_type = 'site'
                ON CONFLICT (site_id, library_id) DO NOTHING
            """, library_id)
            
            # Get the internal ID for the assignment
            lib_record = await db_handler.fetch_one("""
                SELECT id FROM sharepoint_libraries 
                WHERE library_id = $1
            """, library_id)
            
            if not lib_record:
                logger.warning(f"Could not find library record for {library_id}")
                continue
            
            result = await db_handler.fetch_one("""
                INSERT INTO public.reviewer_library_assignments 
                (user_id, library_id, assigned_by, permissions, notes, is_active)
                VALUES ($1, $2, $3, $4::jsonb, $5, true)
                ON CONFLICT (user_id, library_id) 
                DO UPDATE SET
                    is_active = true,
                    assigned_by = $3,
                    assigned_at = CURRENT_TIMESTAMP,
                    permissions = $4::jsonb,
                    notes = $5
                RETURNING id
            """, assignment.user_id, lib_record["id"], current_user["id"], 
                json.dumps(assignment.permissions), assignment.notes)
            
            if result:
                assigned_count += 1
        
        # Log the action
        await db_handler.execute("""
            INSERT INTO public.user_audit_log 
            (user_id, action, details, ip_address, created_at)
            VALUES ($1, $2, $3::jsonb, $4, CURRENT_TIMESTAMP)
        """, current_user["id"], "assign_libraries", 
            json.dumps({"target_user": assignment.user_id, "library_count": assigned_count}),
            request.client.host)
        
        logger.info(f"Assigned {assigned_count} libraries to user {assignment.user_id}")
        return {
            "status": "success", 
            "message": f"Assigned {assigned_count} libraries to {target_user['full_name']}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to assign libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/users/{user_id}/libraries/{library_id}")
async def remove_library_assignment(
    user_id: int,
    library_id: int,
    request: Request,
    current_user: dict = Depends(require_admin),
    db_handler = Depends(get_db)
):
    """Remove a library assignment from a user (admin only)"""
    try:
        result = await db_handler.execute("""
            UPDATE public.reviewer_library_assignments 
            SET is_active = false 
            WHERE user_id = $1 AND library_id = $2 AND is_active = true
        """, user_id, library_id)
        
        # Log the action
        await db_handler.execute("""
            INSERT INTO public.user_audit_log 
            (user_id, action, details, ip_address, created_at)
            VALUES ($1, $2, $3::jsonb, $4, CURRENT_TIMESTAMP)
        """, current_user["id"], "remove_library_assignment", 
            json.dumps({"target_user": user_id, "library_id": library_id}),
            request.client.host)
        
        return {"status": "success", "message": "Library assignment removed"}
        
    except Exception as e:
        logger.error(f"Failed to remove library assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-libraries")
async def get_my_assigned_libraries(
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Get libraries assigned to the current user (for reviewers)"""
    try:
        if current_user["role"] == "administrator":
            # Admins have access to all libraries
            libraries = await db_handler.fetch_all("""
                SELECT 
                    id as library_id, site_id, site_name, 
                    library_id as sp_library_id, library_name, 
                    library_url, item_count,
                    '{"can_view": true, "can_export": true, "can_analyze": true}'::jsonb as permissions
                FROM public.sharepoint_libraries
                ORDER BY site_name, library_name
            """)
        else:
            # Get assigned libraries for reviewer
            libraries = await db_handler.fetch_all("""
                SELECT 
                    rla.id as assignment_id,
                    sl.id as library_id,
                    sl.site_id,
                    sl.site_name,
                    sl.library_id as sp_library_id,
                    sl.library_name,
                    sl.library_url,
                    sl.item_count,
                    rla.permissions,
                    rla.assigned_at
                FROM public.reviewer_library_assignments rla
                JOIN public.sharepoint_libraries sl ON rla.library_id = sl.id
                WHERE rla.user_id = $1 AND rla.is_active = true
                ORDER BY sl.site_name, sl.library_name
            """, current_user["id"])
        
        return {
            "role": current_user["role"],
            "libraries": libraries,
            "total_count": len(libraries)
        }
        
    except Exception as e:
        logger.error(f"Failed to get assigned libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))