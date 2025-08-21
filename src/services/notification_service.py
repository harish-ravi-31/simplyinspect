"""
Email Notification Service

Handles email notifications for permission changes and other events.
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.db.db_handler import DatabaseHandler

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for managing and sending email notifications"""
    
    def __init__(self, db_handler: DatabaseHandler):
        self.db = db_handler
        
        # SMTP configuration from environment variables
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.office365.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.smtp_from = os.getenv('SMTP_FROM', self.smtp_user)
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        
        # Check if SMTP is configured
        self.smtp_configured = bool(self.smtp_user and self.smtp_password)
        
        if not self.smtp_configured:
            logger.warning("SMTP not configured. Email notifications will be queued but not sent.")
    
    async def create_notification(
        self,
        recipient_email: str,
        subject: str,
        notification_type: str = 'permission_change',
        recipient_name: Optional[str] = None,
        site_id: Optional[str] = None,
        baseline_id: Optional[int] = None,
        change_summary: Optional[Dict[str, Any]] = None,
        changes_detail: Optional[Dict[str, Any]] = None,
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        Create a notification in the queue
        
        Args:
            recipient_email: Email address to send to
            subject: Email subject
            notification_type: Type of notification
            recipient_name: Optional recipient name
            site_id: Related site ID
            baseline_id: Related baseline ID
            change_summary: Summary of changes
            changes_detail: Detailed changes
            priority: Priority (1=highest, 10=lowest)
            
        Returns:
            Created notification record
        """
        try:
            # Generate email body
            body = self._generate_email_body(
                notification_type,
                site_id,
                change_summary,
                changes_detail
            )
            
            html_body = self._generate_html_email_body(
                notification_type,
                site_id,
                change_summary,
                changes_detail
            )
            
            # Insert into queue
            query = """
                INSERT INTO notification_queue (
                    notification_type,
                    recipient_email,
                    recipient_name,
                    subject,
                    body,
                    html_body,
                    priority,
                    change_summary,
                    related_baseline_id,
                    related_site_id,
                    status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
            """
            
            notification = await self.db.fetch_one(
                query,
                notification_type,
                recipient_email,
                recipient_name,
                subject,
                body,
                html_body,
                priority,
                json.dumps(change_summary) if change_summary else None,
                baseline_id,
                site_id,
                'pending'
            )
            
            logger.info(f"Created notification {notification['id']} for {recipient_email}")
            
            # Send immediately if SMTP is configured
            if self.smtp_configured:
                await self.send_pending_notifications()
            
            return notification
            
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            raise
    
    def _generate_email_body(
        self,
        notification_type: str,
        site_id: Optional[str],
        change_summary: Optional[Dict[str, Any]],
        changes_detail: Optional[Dict[str, Any]]
    ) -> str:
        """Generate plain text email body"""
        
        if notification_type == 'permission_change':
            body = "SharePoint Permission Changes Detected\n"
            body += "=" * 40 + "\n\n"
            
            if site_id:
                body += f"Site: {site_id}\n"
            
            if change_summary:
                body += "\nSummary of Changes:\n"
                body += "-" * 20 + "\n"
                body += f"• Added permissions: {change_summary.get('added_count', 0)}\n"
                body += f"• Removed permissions: {change_summary.get('removed_count', 0)}\n"
                body += f"• Modified permissions: {change_summary.get('modified_count', 0)}\n"
                body += f"• Total current permissions: {change_summary.get('total_current', 0)}\n"
            
            if changes_detail and changes_detail.get('added_permissions'):
                body += "\nNew Permissions Added:\n"
                body += "-" * 20 + "\n"
                for perm in changes_detail['added_permissions'][:10]:  # Limit to first 10
                    body += f"• {perm.get('principal_name', 'Unknown')} - "
                    body += f"{perm.get('resource_name', 'Unknown')} "
                    body += f"({perm.get('permission_level', 'Unknown')})\n"
                
                if len(changes_detail['added_permissions']) > 10:
                    body += f"... and {len(changes_detail['added_permissions']) - 10} more\n"
            
            if changes_detail and changes_detail.get('removed_permissions'):
                body += "\nPermissions Removed:\n"
                body += "-" * 20 + "\n"
                for perm in changes_detail['removed_permissions'][:10]:
                    body += f"• {perm.get('principal_name', 'Unknown')} - "
                    body += f"{perm.get('resource_name', 'Unknown')} "
                    body += f"({perm.get('permission_level', 'Unknown')})\n"
                
                if len(changes_detail['removed_permissions']) > 10:
                    body += f"... and {len(changes_detail['removed_permissions']) - 10} more\n"
            
            body += "\n" + "-" * 40 + "\n"
            body += "Please review these changes in the SimplyInspect application.\n"
            body += f"Detection time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            
        else:
            body = f"Notification: {notification_type}\n"
            body += f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            if change_summary:
                body += f"\nDetails: {json.dumps(change_summary, indent=2)}\n"
        
        return body
    
    def _generate_html_email_body(
        self,
        notification_type: str,
        site_id: Optional[str],
        change_summary: Optional[Dict[str, Any]],
        changes_detail: Optional[Dict[str, Any]]
    ) -> str:
        """Generate HTML email body"""
        
        if notification_type == 'permission_change':
            html = """
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .header { background-color: #1976D2; color: white; padding: 20px; }
                    .content { padding: 20px; }
                    .summary { background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }
                    .changes-section { margin: 20px 0; }
                    .changes-list { list-style-type: none; padding: 0; }
                    .changes-list li { padding: 8px; margin: 5px 0; background-color: #fff; border-left: 3px solid #1976D2; }
                    .added { border-left-color: #4CAF50; }
                    .removed { border-left-color: #f44336; }
                    .modified { border-left-color: #FF9800; }
                    .footer { background-color: #f0f0f0; padding: 15px; margin-top: 30px; font-size: 0.9em; color: #666; }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>SharePoint Permission Changes Detected</h1>
                </div>
                <div class="content">
            """
            
            if site_id:
                html += f"<p><strong>Site:</strong> {site_id}</p>"
            
            if change_summary:
                html += """
                <div class="summary">
                    <h2>Summary of Changes</h2>
                    <table>
                        <tr><td><strong>Added permissions:</strong></td><td>{}</td></tr>
                        <tr><td><strong>Removed permissions:</strong></td><td>{}</td></tr>
                        <tr><td><strong>Modified permissions:</strong></td><td>{}</td></tr>
                        <tr><td><strong>Total current permissions:</strong></td><td>{}</td></tr>
                    </table>
                </div>
                """.format(
                    change_summary.get('added_count', 0),
                    change_summary.get('removed_count', 0),
                    change_summary.get('modified_count', 0),
                    change_summary.get('total_current', 0)
                )
            
            if changes_detail and changes_detail.get('added_permissions'):
                html += """
                <div class="changes-section">
                    <h3>New Permissions Added</h3>
                    <ul class="changes-list">
                """
                for perm in changes_detail['added_permissions'][:10]:
                    html += f"""
                    <li class="added">
                        <strong>{perm.get('principal_name', 'Unknown')}</strong> - 
                        {perm.get('resource_name', 'Unknown')} 
                        <em>({perm.get('permission_level', 'Unknown')})</em>
                    </li>
                    """
                
                if len(changes_detail['added_permissions']) > 10:
                    html += f"<li>... and {len(changes_detail['added_permissions']) - 10} more</li>"
                
                html += "</ul></div>"
            
            if changes_detail and changes_detail.get('removed_permissions'):
                html += """
                <div class="changes-section">
                    <h3>Permissions Removed</h3>
                    <ul class="changes-list">
                """
                for perm in changes_detail['removed_permissions'][:10]:
                    html += f"""
                    <li class="removed">
                        <strong>{perm.get('principal_name', 'Unknown')}</strong> - 
                        {perm.get('resource_name', 'Unknown')} 
                        <em>({perm.get('permission_level', 'Unknown')})</em>
                    </li>
                    """
                
                if len(changes_detail['removed_permissions']) > 10:
                    html += f"<li>... and {len(changes_detail['removed_permissions']) - 10} more</li>"
                
                html += "</ul></div>"
            
            html += f"""
                </div>
                <div class="footer">
                    <p>Please review these changes in the SimplyInspect application.</p>
                    <p>Detection time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                </div>
            </body>
            </html>
            """
            
        else:
            html = f"""
            <html>
            <body>
                <h2>Notification: {notification_type}</h2>
                <p>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                {f'<pre>{json.dumps(change_summary, indent=2)}</pre>' if change_summary else ''}
            </body>
            </html>
            """
        
        return html
    
    async def send_pending_notifications(self, max_notifications: int = 10) -> int:
        """
        Send pending notifications from the queue
        
        Args:
            max_notifications: Maximum number of notifications to send
            
        Returns:
            Number of notifications sent
        """
        if not self.smtp_configured:
            logger.warning("SMTP not configured. Cannot send notifications.")
            return 0
        
        try:
            # Get pending notifications
            query = """
                SELECT * FROM notification_queue
                WHERE status = 'pending'
                AND scheduled_for <= CURRENT_TIMESTAMP
                ORDER BY priority ASC, created_at ASC
                LIMIT $1
            """
            
            notifications = await self.db.fetch_all(query, max_notifications)
            
            if not notifications:
                logger.debug("No pending notifications to send")
                return 0
            
            sent_count = 0
            for notification in notifications:
                try:
                    await self._send_single_notification(notification)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send notification {notification['id']}: {e}")
                    await self._mark_notification_failed(notification['id'], str(e))
            
            logger.info(f"Sent {sent_count} notifications")
            return sent_count
            
        except Exception as e:
            logger.error(f"Error sending pending notifications: {e}")
            return 0
    
    async def _send_single_notification(self, notification: Dict[str, Any]) -> None:
        """Send a single email notification"""
        try:
            # Update status to sending
            await self.db.execute(
                "UPDATE notification_queue SET status = 'sending' WHERE id = $1",
                notification['id']
            )
            
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = self.smtp_from
            message['To'] = notification['recipient_email']
            message['Subject'] = notification['subject']
            
            # Add text and HTML parts
            text_part = MIMEText(notification['body'], 'plain')
            message.attach(text_part)
            
            if notification.get('html_body'):
                html_part = MIMEText(notification['html_body'], 'html')
                message.attach(html_part)
            
            # Send email
            async with aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=self.smtp_use_tls
            ) as smtp:
                await smtp.login(self.smtp_user, self.smtp_password)
                await smtp.send_message(message)
            
            # Mark as sent
            await self.db.execute(
                """
                UPDATE notification_queue 
                SET status = 'sent', sent_at = CURRENT_TIMESTAMP 
                WHERE id = $1
                """,
                notification['id']
            )
            
            logger.info(f"Successfully sent notification {notification['id']} to {notification['recipient_email']}")
            
        except Exception as e:
            logger.error(f"Error sending notification {notification['id']}: {e}")
            raise
    
    async def _mark_notification_failed(self, notification_id: int, error_message: str) -> None:
        """Mark a notification as failed"""
        try:
            await self.db.execute(
                """
                UPDATE notification_queue 
                SET 
                    status = CASE 
                        WHEN retry_count >= max_retries THEN 'failed'
                        ELSE 'pending'
                    END,
                    retry_count = retry_count + 1,
                    error_message = $2,
                    scheduled_for = CASE
                        WHEN retry_count < max_retries THEN CURRENT_TIMESTAMP + INTERVAL '5 minutes'
                        ELSE scheduled_for
                    END
                WHERE id = $1
                """,
                notification_id,
                error_message
            )
        except Exception as e:
            logger.error(f"Error marking notification as failed: {e}")
    
    async def get_notification_status(
        self,
        recipient_email: Optional[str] = None,
        status: Optional[str] = None,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get notification status
        
        Args:
            recipient_email: Optional filter by recipient
            status: Optional filter by status
            days: Number of days to look back
            
        Returns:
            List of notifications
        """
        try:
            query = """
                SELECT * FROM notification_queue
                WHERE created_at >= $1
            """
            
            params = [datetime.utcnow() - timedelta(days=days)]
            param_counter = 2
            
            if recipient_email:
                query += f" AND recipient_email = ${param_counter}"
                params.append(recipient_email)
                param_counter += 1
            
            if status:
                query += f" AND status = ${param_counter}"
                params.append(status)
                param_counter += 1
            
            query += " ORDER BY created_at DESC"
            
            notifications = await self.db.fetch_all(query, *params)
            
            # Parse JSON fields
            for notif in notifications:
                if notif.get('change_summary'):
                    notif['change_summary'] = json.loads(notif['change_summary']) if isinstance(notif['change_summary'], str) else notif['change_summary']
            
            return notifications
            
        except Exception as e:
            logger.error(f"Error fetching notification status: {e}")
            raise
    
    async def manage_recipients(
        self,
        action: str,
        email: str,
        name: Optional[str] = None,
        site_id: Optional[str] = None,
        notification_types: Optional[List[str]] = None,
        frequency: str = 'immediate'
    ) -> Dict[str, Any]:
        """
        Manage notification recipients
        
        Args:
            action: 'add', 'remove', 'update'
            email: Recipient email
            name: Recipient name
            site_id: Site ID (None for global)
            notification_types: Types of notifications to receive
            frequency: Notification frequency
            
        Returns:
            Result of the operation
        """
        try:
            if action == 'add':
                query = """
                    INSERT INTO notification_recipients (
                        site_id, recipient_email, recipient_name,
                        notification_types, frequency
                    ) VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (site_id, recipient_email) 
                    DO UPDATE SET
                        recipient_name = EXCLUDED.recipient_name,
                        notification_types = EXCLUDED.notification_types,
                        frequency = EXCLUDED.frequency,
                        is_active = true
                    RETURNING *
                """
                
                result = await self.db.fetch_one(
                    query,
                    site_id,
                    email,
                    name,
                    json.dumps(notification_types or ['permission_change']),
                    frequency
                )
                
                return {"action": "added", "recipient": result}
            
            elif action == 'remove':
                query = """
                    UPDATE notification_recipients
                    SET is_active = false
                    WHERE recipient_email = $1
                    AND (site_id = $2 OR ($2 IS NULL AND site_id IS NULL))
                """
                
                await self.db.execute(query, email, site_id)
                return {"action": "removed", "email": email, "site_id": site_id}
            
            elif action == 'update':
                updates = []
                params = []
                param_counter = 1
                
                if name is not None:
                    updates.append(f"recipient_name = ${param_counter}")
                    params.append(name)
                    param_counter += 1
                
                if notification_types is not None:
                    updates.append(f"notification_types = ${param_counter}")
                    params.append(json.dumps(notification_types))
                    param_counter += 1
                
                if frequency:
                    updates.append(f"frequency = ${param_counter}")
                    params.append(frequency)
                    param_counter += 1
                
                if updates:
                    params.extend([email, site_id])
                    query = f"""
                        UPDATE notification_recipients
                        SET {', '.join(updates)}
                        WHERE recipient_email = ${param_counter}
                        AND (site_id = ${param_counter + 1} OR (${param_counter + 1} IS NULL AND site_id IS NULL))
                        RETURNING *
                    """
                    
                    result = await self.db.fetch_one(query, *params)
                    return {"action": "updated", "recipient": result}
            
            return {"action": action, "status": "no_change"}
            
        except Exception as e:
            logger.error(f"Error managing recipients: {e}")
            raise