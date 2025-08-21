"""
Identity Management Routes for SimplyInspect
Handles user and group identity synchronization
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from src.db.db_handler import get_db
from src.services.identity_sync_service import IdentitySyncService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Identity Management"])

@router.post("/identities/sync")
async def sync_all_identities(db_handler = Depends(get_db)):
    """Sync all groups and members from Entra ID"""
    try:
        sync_service = IdentitySyncService(db_handler)
        result = await sync_service.sync_all_groups_and_members()
        return result
    except Exception as e:
        logger.error(f"Failed to sync identities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/identities/groups/{group_id}/members")
async def get_group_members(
    group_id: str,
    db_handler = Depends(get_db)
):
    """Get cached group members"""
    try:
        sync_service = IdentitySyncService(db_handler)
        result = await sync_service.get_group_members_from_cache(group_id)
        return result
    except Exception as e:
        logger.error(f"Failed to get group members: {e}")
        raise HTTPException(status_code=500, detail=str(e))