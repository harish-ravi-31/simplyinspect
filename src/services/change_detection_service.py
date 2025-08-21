"""
Permission Change Detection Service

Monitors SharePoint permissions for changes against established baselines.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.db.db_handler import DatabaseHandler
from src.services.baseline_service import BaselineService
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class ChangeDetectionService:
    """Service for detecting and tracking permission changes"""
    
    def __init__(self, db_handler: DatabaseHandler):
        self.db = db_handler
        self.baseline_service = BaselineService(db_handler)
        self.notification_service = NotificationService(db_handler)
    
    async def detect_changes_for_site(
        self,
        site_id: str,
        notify: bool = True
    ) -> Dict[str, Any]:
        """
        Detect permission changes for a site against its active baseline
        
        Args:
            site_id: SharePoint site ID
            notify: Whether to send notifications for detected changes
            
        Returns:
            Detection results including changes found
        """
        try:
            logger.info(f"Starting change detection for site {site_id}")
            
            # Get active baseline for the site
            baseline_query = """
                SELECT * FROM permission_baselines
                WHERE site_id = $1 AND is_active = true
                LIMIT 1
            """
            
            baseline = await self.db.fetch_one(baseline_query, site_id)
            
            if not baseline:
                logger.warning(f"No active baseline found for site {site_id}")
                return {
                    "status": "no_baseline",
                    "message": f"No active baseline found for site {site_id}",
                    "site_id": site_id
                }
            
            # Compare baseline with current permissions
            comparison = await self.baseline_service.compare_with_current(baseline['id'])
            
            # Process detected changes
            changes = comparison.get('changes', {})
            summary = changes.get('summary', {})
            
            if summary.get('added_count', 0) == 0 and \
               summary.get('removed_count', 0) == 0 and \
               summary.get('modified_count', 0) == 0:
                logger.info(f"No changes detected for site {site_id}")
                return {
                    "status": "no_changes",
                    "message": "No permission changes detected",
                    "site_id": site_id,
                    "baseline_id": baseline['id'],
                    "baseline_name": baseline['baseline_name']
                }
            
            # Record changes in the database
            await self._record_changes(
                baseline['id'],
                site_id,
                changes
            )
            
            # Send notifications if requested
            notification_result = None
            if notify:
                notification_result = await self._notify_changes(
                    site_id,
                    baseline,
                    changes
                )
            
            logger.info(f"Change detection completed for site {site_id}: "
                       f"{summary.get('added_count', 0)} added, "
                       f"{summary.get('removed_count', 0)} removed, "
                       f"{summary.get('modified_count', 0)} modified")
            
            return {
                "status": "changes_detected",
                "site_id": site_id,
                "baseline_id": baseline['id'],
                "baseline_name": baseline['baseline_name'],
                "detection_time": datetime.utcnow().isoformat(),
                "changes": changes,
                "notification_sent": notification_result is not None,
                "notification_result": notification_result
            }
            
        except Exception as e:
            logger.error(f"Error detecting changes for site {site_id}: {e}")
            raise
    
    async def detect_all_sites(self, notify: bool = True) -> List[Dict[str, Any]]:
        """
        Detect changes for all sites with active baselines
        
        Args:
            notify: Whether to send notifications
            
        Returns:
            List of detection results for each site
        """
        try:
            logger.info("Starting change detection for all sites")
            
            # Get all sites with active baselines
            sites_query = """
                SELECT DISTINCT site_id, site_url, baseline_name
                FROM permission_baselines
                WHERE is_active = true
            """
            
            sites = await self.db.fetch_all(sites_query)
            
            if not sites:
                logger.info("No sites with active baselines found")
                return []
            
            results = []
            for site in sites:
                try:
                    result = await self.detect_changes_for_site(
                        site['site_id'],
                        notify=notify
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error detecting changes for site {site['site_id']}: {e}")
                    results.append({
                        "status": "error",
                        "site_id": site['site_id'],
                        "error": str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Error in detect_all_sites: {e}")
            raise
    
    async def _record_changes(
        self,
        baseline_id: int,
        site_id: str,
        changes: Dict[str, Any]
    ) -> None:
        """Record detected changes in the database"""
        try:
            # Record added permissions
            for perm in changes.get('added_permissions', []):
                await self._insert_change_record(
                    baseline_id,
                    site_id,
                    'added',
                    None,  # No old permission
                    perm
                )
            
            # Record removed permissions
            for perm in changes.get('removed_permissions', []):
                await self._insert_change_record(
                    baseline_id,
                    site_id,
                    'removed',
                    perm,
                    None  # No new permission
                )
            
            # Record modified permissions
            for mod in changes.get('modified_permissions', []):
                change_type = 'modified'
                
                # Check if inheritance changed
                if mod.get('old_inheritance') != mod.get('new_inheritance'):
                    if mod.get('new_inheritance'):
                        change_type = 'inheritance_broken'
                    else:
                        change_type = 'inheritance_restored'
                
                await self._insert_change_record(
                    baseline_id,
                    site_id,
                    change_type,
                    {
                        'permission_level': mod.get('old_permission_level'),
                        'has_broken_inheritance': mod.get('old_inheritance')
                    },
                    {
                        'permission_level': mod.get('new_permission_level'),
                        'has_broken_inheritance': mod.get('new_inheritance')
                    },
                    resource_id=mod.get('resource_id'),
                    resource_name=mod.get('resource_name'),
                    principal_id=mod.get('principal_id'),
                    principal_name=mod.get('principal_name')
                )
            
        except Exception as e:
            logger.error(f"Error recording changes: {e}")
            raise
    
    async def _insert_change_record(
        self,
        baseline_id: int,
        site_id: str,
        change_type: str,
        old_permission: Optional[Dict[str, Any]],
        new_permission: Optional[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Insert a single change record"""
        try:
            # Extract details from permissions or kwargs
            if new_permission:
                resource_id = new_permission.get('resource_id')
                resource_name = new_permission.get('resource_name')
                resource_type = new_permission.get('resource_type')
                principal_id = new_permission.get('principal_id')
                principal_name = new_permission.get('principal_name')
                principal_email = new_permission.get('principal_email')
                principal_type = new_permission.get('principal_type')
            elif old_permission:
                resource_id = old_permission.get('resource_id')
                resource_name = old_permission.get('resource_name')
                resource_type = old_permission.get('resource_type')
                principal_id = old_permission.get('principal_id')
                principal_name = old_permission.get('principal_name')
                principal_email = old_permission.get('principal_email')
                principal_type = old_permission.get('principal_type')
            else:
                resource_id = kwargs.get('resource_id')
                resource_name = kwargs.get('resource_name')
                resource_type = kwargs.get('resource_type')
                principal_id = kwargs.get('principal_id')
                principal_name = kwargs.get('principal_name')
                principal_email = kwargs.get('principal_email')
                principal_type = kwargs.get('principal_type')
            
            query = """
                INSERT INTO permission_changes (
                    baseline_id,
                    site_id,
                    change_type,
                    resource_id,
                    resource_name,
                    resource_type,
                    principal_id,
                    principal_name,
                    principal_email,
                    principal_type,
                    old_permission,
                    new_permission
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """
            
            await self.db.execute(
                query,
                baseline_id,
                site_id,
                change_type,
                resource_id,
                resource_name,
                resource_type,
                principal_id,
                principal_name,
                principal_email,
                principal_type,
                json.dumps(old_permission) if old_permission else None,
                json.dumps(new_permission) if new_permission else None
            )
            
        except Exception as e:
            logger.error(f"Error inserting change record: {e}")
            # Don't raise - continue processing other changes
    
    async def _notify_changes(
        self,
        site_id: str,
        baseline: Dict[str, Any],
        changes: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Send notifications for detected changes"""
        try:
            # Get notification recipients for this site
            recipients_query = """
                SELECT recipient_email, recipient_name
                FROM notification_recipients
                WHERE (site_id = $1 OR site_id IS NULL)
                AND is_active = true
                AND 'permission_change' = ANY(notification_types)
            """
            
            recipients = await self.db.fetch_all(recipients_query, site_id)
            
            if not recipients:
                logger.info(f"No active notification recipients for site {site_id}")
                return None
            
            # Prepare notification content
            summary = changes.get('summary', {})
            subject = f"Permission Changes Detected - {baseline.get('site_url', site_id)}"
            
            # Create notification for each recipient
            notifications_sent = []
            for recipient in recipients:
                notification = await self.notification_service.create_notification(
                    recipient_email=recipient['recipient_email'],
                    recipient_name=recipient.get('recipient_name'),
                    subject=subject,
                    notification_type='permission_change',
                    site_id=site_id,
                    baseline_id=baseline['id'],
                    change_summary=summary,
                    changes_detail=changes
                )
                notifications_sent.append(notification)
            
            # Mark changes as notification sent
            await self._mark_changes_notified(baseline['id'])
            
            return {
                "recipients_count": len(recipients),
                "notifications_created": len(notifications_sent)
            }
            
        except Exception as e:
            logger.error(f"Error sending notifications: {e}")
            return None
    
    async def _mark_changes_notified(self, baseline_id: int) -> None:
        """Mark changes as having notifications sent"""
        try:
            query = """
                UPDATE permission_changes
                SET notification_sent = true
                WHERE baseline_id = $1
                AND notification_sent = false
            """
            
            await self.db.execute(query, baseline_id)
            
        except Exception as e:
            logger.warning(f"Failed to mark changes as notified: {e}")
    
    async def get_recent_changes(
        self,
        site_id: Optional[str] = None,
        days: int = 7,
        reviewed: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent permission changes
        
        Args:
            site_id: Optional site ID filter
            days: Number of days to look back
            reviewed: Optional filter for reviewed status
            
        Returns:
            List of recent changes
        """
        try:
            query = """
                SELECT 
                    pc.*,
                    pb.baseline_name,
                    pb.site_url
                FROM permission_changes pc
                JOIN permission_baselines pb ON pc.baseline_id = pb.id
                WHERE pc.detected_at >= $1
            """
            
            params = [datetime.utcnow() - timedelta(days=days)]
            param_counter = 2
            
            if site_id:
                query += f" AND pc.site_id = ${param_counter}"
                params.append(site_id)
                param_counter += 1
            
            if reviewed is not None:
                query += f" AND pc.reviewed = ${param_counter}"
                params.append(reviewed)
                param_counter += 1
            
            query += " ORDER BY pc.detected_at DESC"
            
            changes = await self.db.fetch_all(query, *params)
            
            # Parse JSON fields
            for change in changes:
                if change.get('old_permission'):
                    change['old_permission'] = json.loads(change['old_permission']) if isinstance(change['old_permission'], str) else change['old_permission']
                if change.get('new_permission'):
                    change['new_permission'] = json.loads(change['new_permission']) if isinstance(change['new_permission'], str) else change['new_permission']
            
            return changes
            
        except Exception as e:
            logger.error(f"Error fetching recent changes: {e}")
            raise
    
    async def mark_changes_reviewed(
        self,
        change_ids: List[int],
        reviewed_by: str,
        review_notes: Optional[str] = None
    ) -> int:
        """
        Mark changes as reviewed
        
        Args:
            change_ids: List of change IDs to mark as reviewed
            reviewed_by: User who reviewed the changes
            review_notes: Optional review notes
            
        Returns:
            Number of changes marked as reviewed
        """
        try:
            if not change_ids:
                return 0
            
            # Build the IN clause safely
            placeholders = ','.join([f'${i+1}' for i in range(len(change_ids))])
            
            query = f"""
                UPDATE permission_changes
                SET 
                    reviewed = true,
                    reviewed_by = ${len(change_ids) + 1},
                    reviewed_at = CURRENT_TIMESTAMP,
                    review_notes = ${len(change_ids) + 2}
                WHERE id IN ({placeholders})
                AND reviewed = false
            """
            
            params = change_ids + [reviewed_by, review_notes]
            result = await self.db.execute(query, *params)
            
            # Extract affected rows count from result if available
            affected = len(change_ids)  # Assume all were updated
            
            logger.info(f"Marked {affected} changes as reviewed by {reviewed_by}")
            return affected
            
        except Exception as e:
            logger.error(f"Error marking changes as reviewed: {e}")
            raise