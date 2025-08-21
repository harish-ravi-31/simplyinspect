"""
Permission Baseline API Routes

Endpoints for managing permission baselines and change detection.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Body
from src.db.db_handler import get_db
from src.services.baseline_service import BaselineService
from src.services.change_detection_service import ChangeDetectionService
from src.services.notification_service import NotificationService
from src.routes.auth_routes import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/baselines/create")
async def create_baseline(
    site_id: str = Body(..., description="SharePoint site ID"),
    site_url: str = Body(..., description="SharePoint site URL"),
    baseline_name: str = Body(..., description="Name for the baseline"),
    baseline_description: Optional[str] = Body(None, description="Description of the baseline"),
    set_as_active: bool = Body(True, description="Set as active baseline"),
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Create a new permission baseline for a site (admin only)"""
    try:
        # Check admin permission
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Only administrators can create baselines")
        
        logger.info(f"Creating baseline '{baseline_name}' for site {site_id} by user {current_user['username']}")
        
        baseline_service = BaselineService(db_handler)
        baseline = await baseline_service.create_baseline(
            site_id=site_id,
            site_url=site_url,
            baseline_name=baseline_name,
            created_by=current_user["username"],
            created_by_email=current_user.get("email", current_user["username"]),
            baseline_description=baseline_description,
            set_as_active=set_as_active
        )
        
        return {
            "status": "success",
            "message": f"Baseline '{baseline_name}' created successfully",
            "baseline": baseline
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating baseline: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/baselines")
async def get_baselines(
    site_id: Optional[str] = Query(None, description="Filter by site ID"),
    include_inactive: bool = Query(True, description="Include inactive baselines"),
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Get list of baselines"""
    try:
        baseline_service = BaselineService(db_handler)
        
        # Reviewers can only see baselines for their assigned sites
        if current_user["role"] == "reviewer":
            # Get assigned libraries for the reviewer
            query = """
                SELECT DISTINCT sl.site_id
                FROM reviewer_library_assignments rla
                JOIN sharepoint_libraries sl ON rla.library_id = sl.id
                WHERE rla.user_id = $1 AND rla.is_active = true
            """
            assigned_sites = await db_handler.fetch_all(query, current_user["id"])
            
            if not assigned_sites:
                return {"baselines": [], "total": 0}
            
            # If site_id is specified, check if it's in assigned sites
            if site_id:
                site_ids = [s['site_id'] for s in assigned_sites]
                if site_id not in site_ids:
                    return {"baselines": [], "total": 0}
            
        baselines = await baseline_service.get_baselines(
            site_id=site_id,
            include_inactive=include_inactive
        )
        
        return {
            "baselines": baselines,
            "total": len(baselines)
        }
        
    except Exception as e:
        logger.error(f"Error fetching baselines: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/baselines/{baseline_id}")
async def get_baseline_detail(
    baseline_id: int,
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Get detailed information about a specific baseline"""
    try:
        baseline_service = BaselineService(db_handler)
        baseline = await baseline_service.get_baseline_by_id(baseline_id)
        
        if not baseline:
            raise HTTPException(status_code=404, detail="Baseline not found")
        
        # Check access for reviewers
        if current_user["role"] == "reviewer":
            query = """
                SELECT 1 FROM reviewer_library_assignments rla
                JOIN sharepoint_libraries sl ON rla.library_id = sl.id
                WHERE rla.user_id = $1 AND sl.site_id = $2 AND rla.is_active = true
                LIMIT 1
            """
            has_access = await db_handler.fetch_one(query, current_user["id"], baseline['site_id'])
            
            if not has_access:
                raise HTTPException(status_code=403, detail="Access denied to this baseline")
        
        return baseline
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching baseline {baseline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/baselines/{baseline_id}/activate")
async def activate_baseline(
    baseline_id: int,
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Activate a baseline (admin only)"""
    try:
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Only administrators can activate baselines")
        
        baseline_service = BaselineService(db_handler)
        baseline = await baseline_service.activate_baseline(baseline_id)
        
        return {
            "status": "success",
            "message": f"Baseline {baseline_id} activated",
            "baseline": baseline
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error activating baseline {baseline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/baselines/{baseline_id}/deactivate")
async def deactivate_baseline(
    baseline_id: int,
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Deactivate a baseline (admin only)"""
    try:
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Only administrators can deactivate baselines")
        
        baseline_service = BaselineService(db_handler)
        baseline = await baseline_service.deactivate_baseline(baseline_id)
        
        return {
            "status": "success",
            "message": f"Baseline {baseline_id} deactivated",
            "baseline": baseline
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deactivating baseline {baseline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/baselines/{baseline_id}")
async def delete_baseline(
    baseline_id: int,
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Delete a baseline (admin only)"""
    try:
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Only administrators can delete baselines")
        
        baseline_service = BaselineService(db_handler)
        success = await baseline_service.delete_baseline(baseline_id)
        
        return {
            "status": "success" if success else "failed",
            "message": f"Baseline {baseline_id} deleted" if success else "Failed to delete baseline"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting baseline {baseline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/baselines/{baseline_id}/compare")
async def compare_baseline(
    baseline_id: int,
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Compare a baseline with current permissions"""
    try:
        baseline_service = BaselineService(db_handler)
        
        # Check baseline exists and user has access
        baseline = await baseline_service.get_baseline_by_id(baseline_id)
        if not baseline:
            raise HTTPException(status_code=404, detail="Baseline not found")
        
        # Check access for reviewers
        if current_user["role"] == "reviewer":
            query = """
                SELECT 1 FROM reviewer_library_assignments rla
                JOIN sharepoint_libraries sl ON rla.library_id = sl.id
                WHERE rla.user_id = $1 AND sl.site_id = $2 AND rla.is_active = true
                LIMIT 1
            """
            has_access = await db_handler.fetch_one(query, current_user["id"], baseline['site_id'])
            
            if not has_access:
                raise HTTPException(status_code=403, detail="Access denied to this baseline")
        
        comparison = await baseline_service.compare_with_current(baseline_id)
        
        return comparison
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing baseline {baseline_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change-detection/detect-site")
async def detect_changes_for_site(
    site_id: str = Body(..., description="Site ID to check for changes"),
    notify: bool = Body(True, description="Send notifications for detected changes"),
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Detect permission changes for a specific site (admin only)"""
    try:
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Only administrators can trigger change detection")
        
        change_service = ChangeDetectionService(db_handler)
        result = await change_service.detect_changes_for_site(site_id, notify=notify)
        
        return result
        
    except Exception as e:
        logger.error(f"Error detecting changes for site {site_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change-detection/detect-all")
async def detect_all_changes(
    notify: bool = Body(True, description="Send notifications for detected changes"),
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Detect permission changes for all sites with active baselines (admin only)"""
    try:
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Only administrators can trigger change detection")
        
        change_service = ChangeDetectionService(db_handler)
        results = await change_service.detect_all_sites(notify=notify)
        
        return {
            "sites_checked": len(results),
            "changes_detected": sum(1 for r in results if r.get('status') == 'changes_detected'),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error detecting changes for all sites: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/change-detection/recent-changes")
async def get_recent_changes(
    site_id: Optional[str] = Query(None, description="Filter by site ID"),
    days: int = Query(7, description="Number of days to look back"),
    reviewed: Optional[bool] = Query(None, description="Filter by reviewed status"),
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Get recent permission changes"""
    try:
        change_service = ChangeDetectionService(db_handler)
        
        # Apply access control for reviewers
        if current_user["role"] == "reviewer":
            # Get assigned sites
            query = """
                SELECT DISTINCT sl.site_id
                FROM reviewer_library_assignments rla
                JOIN sharepoint_libraries sl ON rla.library_id = sl.id
                WHERE rla.user_id = $1 AND rla.is_active = true
            """
            assigned_sites = await db_handler.fetch_all(query, current_user["id"])
            
            if not assigned_sites:
                return {"changes": [], "total": 0}
            
            # If site_id specified, check access
            if site_id:
                site_ids = [s['site_id'] for s in assigned_sites]
                if site_id not in site_ids:
                    return {"changes": [], "total": 0}
        
        changes = await change_service.get_recent_changes(
            site_id=site_id,
            days=days,
            reviewed=reviewed
        )
        
        return {
            "changes": changes,
            "total": len(changes),
            "unreviewed_count": sum(1 for c in changes if not c.get('reviewed'))
        }
        
    except Exception as e:
        logger.error(f"Error fetching recent changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/change-detection/mark-reviewed")
async def mark_changes_reviewed(
    change_ids: List[int] = Body(..., description="List of change IDs to mark as reviewed"),
    review_notes: Optional[str] = Body(None, description="Optional review notes"),
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Mark permission changes as reviewed"""
    try:
        change_service = ChangeDetectionService(db_handler)
        
        # Verify user has access to these changes (especially for reviewers)
        if current_user["role"] == "reviewer":
            # Check that all changes belong to sites the reviewer has access to
            query = """
                SELECT DISTINCT pc.id
                FROM permission_changes pc
                JOIN permission_baselines pb ON pc.baseline_id = pb.id
                JOIN sharepoint_libraries sl ON pb.site_id = sl.site_id
                JOIN reviewer_library_assignments rla ON sl.id = rla.library_id
                WHERE pc.id = ANY($1)
                AND rla.user_id = $2
                AND rla.is_active = true
            """
            accessible_changes = await db_handler.fetch_all(query, change_ids, current_user["id"])
            accessible_ids = [c['id'] for c in accessible_changes]
            
            # Filter to only accessible changes
            change_ids = [cid for cid in change_ids if cid in accessible_ids]
            
            if not change_ids:
                raise HTTPException(status_code=403, detail="No accessible changes to review")
        
        count = await change_service.mark_changes_reviewed(
            change_ids=change_ids,
            reviewed_by=current_user["username"],
            review_notes=review_notes
        )
        
        return {
            "status": "success",
            "reviewed_count": count,
            "message": f"Marked {count} changes as reviewed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking changes as reviewed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications/recipients")
async def get_notification_recipients(
    site_id: Optional[str] = Query(None, description="Filter by site ID"),
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Get notification recipients (admin only)"""
    try:
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Only administrators can view notification recipients")
        
        query = """
            SELECT * FROM notification_recipients
            WHERE is_active = true
        """
        params = []
        
        if site_id:
            query += " AND (site_id = $1 OR site_id IS NULL)"
            params.append(site_id)
        
        query += " ORDER BY site_id, recipient_email"
        
        recipients = await db_handler.fetch_all(query, *params)
        
        return {
            "recipients": recipients,
            "total": len(recipients)
        }
        
    except Exception as e:
        logger.error(f"Error fetching notification recipients: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/recipients/manage")
async def manage_notification_recipient(
    action: str = Body(..., description="Action: add, remove, or update"),
    email: str = Body(..., description="Recipient email"),
    name: Optional[str] = Body(None, description="Recipient name"),
    site_id: Optional[str] = Body(None, description="Site ID (None for global)"),
    notification_types: Optional[List[str]] = Body(None, description="Notification types"),
    frequency: str = Body("immediate", description="Notification frequency"),
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Manage notification recipients (admin only)"""
    try:
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Only administrators can manage notification recipients")
        
        notification_service = NotificationService(db_handler)
        result = await notification_service.manage_recipients(
            action=action,
            email=email,
            name=name,
            site_id=site_id,
            notification_types=notification_types,
            frequency=frequency
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error managing notification recipient: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications/status")
async def get_notification_status(
    recipient_email: Optional[str] = Query(None, description="Filter by recipient"),
    status: Optional[str] = Query(None, description="Filter by status"),
    days: int = Query(7, description="Number of days to look back"),
    current_user: dict = Depends(get_current_user),
    db_handler = Depends(get_db)
):
    """Get notification status (admin only)"""
    try:
        if current_user["role"] != "administrator":
            raise HTTPException(status_code=403, detail="Only administrators can view notification status")
        
        notification_service = NotificationService(db_handler)
        notifications = await notification_service.get_notification_status(
            recipient_email=recipient_email,
            status=status,
            days=days
        )
        
        # Calculate summary statistics
        status_counts = {}
        for notif in notifications:
            s = notif.get('status', 'unknown')
            status_counts[s] = status_counts.get(s, 0) + 1
        
        return {
            "notifications": notifications,
            "total": len(notifications),
            "status_summary": status_counts
        }
        
    except Exception as e:
        logger.error(f"Error fetching notification status: {e}")
        raise HTTPException(status_code=500, detail=str(e))