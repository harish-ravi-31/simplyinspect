"""
One-time sync script to populate sharepoint_libraries from existing sharepoint_permissions data
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from src.db.db_handler import get_db
from src.routes.auth_routes import require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Sync"])

@router.post("/sync-sharepoint-libraries", dependencies=[Depends(require_admin)])
async def sync_sharepoint_libraries_from_permissions(
    db_handler = Depends(get_db)
):
    """
    Sync SharePoint libraries from existing sharepoint_permissions table
    to the new sharepoint_libraries table for assignment purposes
    """
    try:
        # Get all sites as assignable libraries - this matches what users see in SharePoint Permissions
        libraries_query = """
        SELECT DISTINCT
            site_id,
            resource_name as site_name,
            resource_id as library_id,
            resource_name as library_name,
            resource_url as library_url,
            site_url,
            COUNT(DISTINCT principal_id) as permission_count
        FROM sharepoint_permissions
        WHERE resource_type = 'site'
            AND site_id IS NOT NULL
            AND resource_name IS NOT NULL
        GROUP BY site_id, resource_name, resource_id, resource_url, site_url
        ORDER BY resource_name
        """
        
        raw_libraries = await db_handler.fetch_all(libraries_query)
        
        # Convert to the format expected by the assignment system
        libraries = []
        for lib in raw_libraries:
            libraries.append({
                'site_id': lib['site_id'],
                'site_name': lib['site_name'],
                'library_id': lib['library_id'],
                'library_name': lib['library_name'],
                'library_url': lib['library_url'] or lib['site_url'],
                'resource_type': 'site',
                'permission_count': lib['permission_count']
            })
        
        synced_count = 0
        for lib in libraries:
            try:
                # Insert or update in sharepoint_libraries table
                await db_handler.execute("""
                    INSERT INTO sharepoint_libraries 
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
                """, 
                lib['site_id'], 
                lib['site_name'] or 'Unknown Site', 
                lib['library_id'], 
                lib['library_name'] or 'Unknown Library', 
                lib['library_url'], 
                lib['permission_count'])
                
                synced_count += 1
            except Exception as e:
                logger.warning(f"Failed to sync library {lib.get('library_name')}: {e}")
                continue
        
        logger.info(f"Synced {synced_count} SharePoint libraries")
        
        # Return summary
        total_libraries = await db_handler.fetch_value(
            "SELECT COUNT(*) FROM sharepoint_libraries"
        )
        
        return {
            "status": "success",
            "synced_count": synced_count,
            "total_libraries": total_libraries,
            "message": f"Successfully synced {synced_count} libraries from SharePoint permissions"
        }
        
    except Exception as e:
        logger.error(f"Failed to sync SharePoint libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))