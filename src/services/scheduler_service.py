"""
Scheduler Service for Automated Tasks

Handles scheduled jobs like permission change detection.
"""

import logging
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from src.db.db_handler import get_db_handler
from src.services.change_detection_service import ChangeDetectionService
from src.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class SchedulerService:
    """Service for managing scheduled tasks"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db_handler = None
        
        # Get configuration from environment
        self.change_detection_enabled = os.getenv('CHANGE_DETECTION_ENABLED', 'true').lower() == 'true'
        self.change_detection_interval = int(os.getenv('CHANGE_DETECTION_INTERVAL', '3600'))  # seconds
        self.change_detection_cron = os.getenv('CHANGE_DETECTION_CRON', '')  # Optional cron expression
        self.notification_check_interval = int(os.getenv('NOTIFICATION_CHECK_INTERVAL', '300'))  # 5 minutes
        
    async def initialize(self):
        """Initialize the scheduler and database connection"""
        try:
            # Get database handler
            self.db_handler = get_db_handler()
            
            # Schedule change detection
            if self.change_detection_enabled:
                if self.change_detection_cron:
                    # Use cron expression if provided
                    self.scheduler.add_job(
                        self.run_change_detection,
                        CronTrigger.from_crontab(self.change_detection_cron),
                        id='change_detection_cron',
                        name='Change Detection (Cron)',
                        replace_existing=True
                    )
                    logger.info(f"Scheduled change detection with cron: {self.change_detection_cron}")
                else:
                    # Use interval trigger
                    self.scheduler.add_job(
                        self.run_change_detection,
                        IntervalTrigger(seconds=self.change_detection_interval),
                        id='change_detection_interval',
                        name='Change Detection (Interval)',
                        replace_existing=True
                    )
                    logger.info(f"Scheduled change detection every {self.change_detection_interval} seconds")
            
            # Schedule notification processing
            self.scheduler.add_job(
                self.process_notifications,
                IntervalTrigger(seconds=self.notification_check_interval),
                id='notification_processing',
                name='Notification Processing',
                replace_existing=True
            )
            logger.info(f"Scheduled notification processing every {self.notification_check_interval} seconds")
            
            # Schedule daily baseline comparison summary (at 8 AM)
            self.scheduler.add_job(
                self.generate_daily_summary,
                CronTrigger(hour=8, minute=0),
                id='daily_summary',
                name='Daily Summary',
                replace_existing=True
            )
            logger.info("Scheduled daily summary at 8:00 AM")
            
            # Start the scheduler
            self.scheduler.start()
            logger.info("Scheduler service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            raise
    
    async def run_change_detection(self):
        """Run change detection for all sites with active baselines"""
        try:
            logger.info("Starting scheduled change detection")
            
            if not self.db_handler:
                logger.error("Database handler not initialized")
                return
            
            change_service = ChangeDetectionService(self.db_handler)
            results = await change_service.detect_all_sites(notify=True)
            
            # Log summary
            total_sites = len(results)
            sites_with_changes = sum(1 for r in results if r.get('status') == 'changes_detected')
            total_changes = sum(
                r.get('changes', {}).get('summary', {}).get('added_count', 0) +
                r.get('changes', {}).get('summary', {}).get('removed_count', 0) +
                r.get('changes', {}).get('summary', {}).get('modified_count', 0)
                for r in results if r.get('status') == 'changes_detected'
            )
            
            logger.info(f"Change detection completed: {total_sites} sites checked, "
                       f"{sites_with_changes} with changes, {total_changes} total changes detected")
            
            # Store run statistics
            await self._store_run_statistics('change_detection', {
                'sites_checked': total_sites,
                'sites_with_changes': sites_with_changes,
                'total_changes': total_changes,
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error in scheduled change detection: {e}")
            await self._store_run_statistics('change_detection', {
                'error': str(e),
                'status': 'failed'
            })
    
    async def process_notifications(self):
        """Process pending email notifications"""
        try:
            logger.debug("Processing pending notifications")
            
            if not self.db_handler:
                logger.error("Database handler not initialized")
                return
            
            notification_service = NotificationService(self.db_handler)
            sent_count = await notification_service.send_pending_notifications(max_notifications=10)
            
            if sent_count > 0:
                logger.info(f"Sent {sent_count} notifications")
            
        except Exception as e:
            logger.error(f"Error processing notifications: {e}")
    
    async def generate_daily_summary(self):
        """Generate and send daily summary of permission changes"""
        try:
            logger.info("Generating daily summary")
            
            if not self.db_handler:
                logger.error("Database handler not initialized")
                return
            
            # Get yesterday's changes
            query = """
                SELECT 
                    COUNT(*) as total_changes,
                    COUNT(DISTINCT site_id) as affected_sites,
                    COUNT(DISTINCT baseline_id) as affected_baselines,
                    SUM(CASE WHEN change_type = 'added' THEN 1 ELSE 0 END) as added,
                    SUM(CASE WHEN change_type = 'removed' THEN 1 ELSE 0 END) as removed,
                    SUM(CASE WHEN change_type = 'modified' THEN 1 ELSE 0 END) as modified,
                    SUM(CASE WHEN reviewed = false THEN 1 ELSE 0 END) as unreviewed
                FROM permission_changes
                WHERE detected_at >= CURRENT_DATE - INTERVAL '1 day'
                AND detected_at < CURRENT_DATE
            """
            
            summary = await self.db_handler.fetch_one(query)
            
            if summary and summary['total_changes'] > 0:
                # Get recipients configured for daily summaries
                recipients_query = """
                    SELECT recipient_email, recipient_name
                    FROM notification_recipients
                    WHERE is_active = true
                    AND frequency = 'daily'
                    AND 'permission_change' = ANY(notification_types)
                """
                
                recipients = await self.db_handler.fetch_all(recipients_query)
                
                if recipients:
                    notification_service = NotificationService(self.db_handler)
                    
                    for recipient in recipients:
                        await notification_service.create_notification(
                            recipient_email=recipient['recipient_email'],
                            recipient_name=recipient.get('recipient_name'),
                            subject="Daily Permission Changes Summary",
                            notification_type='daily_summary',
                            change_summary=summary,
                            priority=7  # Lower priority than immediate notifications
                        )
                    
                    logger.info(f"Created daily summary notifications for {len(recipients)} recipients")
            
            await self._store_run_statistics('daily_summary', summary)
            
        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")
    
    async def _store_run_statistics(self, job_type: str, statistics: dict):
        """Store job run statistics for monitoring"""
        try:
            # This could be extended to store in a dedicated table for monitoring
            logger.info(f"Job {job_type} statistics: {statistics}")
            
            # Optional: Store in database for historical tracking
            # query = """
            #     INSERT INTO scheduler_run_history (job_type, run_time, statistics)
            #     VALUES ($1, $2, $3)
            # """
            # await self.db_handler.execute(query, job_type, datetime.utcnow(), json.dumps(statistics))
            
        except Exception as e:
            logger.warning(f"Failed to store run statistics: {e}")
    
    def get_scheduled_jobs(self):
        """Get list of scheduled jobs and their status"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs
    
    async def trigger_job(self, job_id: str):
        """Manually trigger a scheduled job"""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.func()
                logger.info(f"Manually triggered job: {job_id}")
                return True
            else:
                logger.warning(f"Job not found: {job_id}")
                return False
        except Exception as e:
            logger.error(f"Error triggering job {job_id}: {e}")
            return False
    
    def pause_job(self, job_id: str):
        """Pause a scheduled job"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Paused job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {e}")
            return False
    
    def resume_job(self, job_id: str):
        """Resume a paused job"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Resumed job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the scheduler gracefully"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("Scheduler service shut down")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")

# Global scheduler instance
scheduler_service = None

def get_scheduler_service():
    """Get or create the global scheduler service instance"""
    global scheduler_service
    if scheduler_service is None:
        scheduler_service = SchedulerService()
    return scheduler_service