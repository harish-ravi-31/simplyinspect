"""
Microsoft Purview Collector
Integrates with Office 365 Management Activity API to collect audit logs
"""

import asyncio
import logging
import json
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import aiohttp
import msal

# Removed circular import - this collector doesn't need to import the service

logger = logging.getLogger(__name__)

class MicrosoftPurviewCollector:
    """Collector for Microsoft Purview audit logs via Office 365 Management Activity API"""
    
    def __init__(self, source_config: Dict[str, Any]):
        self.source_config = source_config
        self.source_system = source_config.get('source_system') or source_config.get('SourceSystem')
        
        # Parse configuration from JSON string if needed
        config_raw = source_config.get('configuration') or source_config.get('Configuration')
        if isinstance(config_raw, str):
            import json
            self.config = json.loads(config_raw)
        else:
            self.config = config_raw or {}
        
        # MSAL application for authentication
        self.app = msal.ConfidentialClientApplication(
            client_id=self.config['client_id'],
            client_credential=self.config['client_secret'],
            authority=f"https://login.microsoftonline.com/{self.config['tenant_id']}"
        )
        
        # API endpoints
        self.base_url = "https://manage.office.com/api/v1.0"
        self.content_types = self.config.get('content_types', [
            'Audit.AzureActiveDirectory',
            'Audit.Exchange',
            'Audit.SharePoint',
            'Audit.General',
            'DLP.All'
        ])
        
        # Rate limiting
        self.rate_limit_delay = 1.0  # seconds between requests
        self.max_retries = 3
        
    async def test_connection(self, config: dict = None) -> bool:
        """Test connection to Microsoft Purview API"""
        try:
            # Use provided config or fall back to instance config
            test_config = config or self.config
            
            # Extract required parameters
            tenant_id = test_config.get('tenant_id')
            client_id = test_config.get('client_id')
            client_secret = test_config.get('client_secret')
            
            if not all([tenant_id, client_id, client_secret]):
                logger.error("Missing required configuration parameters")
                return False
            
            # Create temporary MSAL app for testing
            test_app = msal.ConfidentialClientApplication(
                client_id=client_id,
                client_credential=client_secret,
                authority=f"https://login.microsoftonline.com/{tenant_id}"
            )
            
            # Get access token
            scopes = ['https://manage.office.com/.default']
            result = test_app.acquire_token_for_client(scopes=scopes)
            
            if 'access_token' not in result:
                logger.error(f"Failed to get access token: {result.get('error_description', 'Unknown error')}")
                return False
            
            token = result['access_token']
            
            # Test API endpoint
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession() as session:
                # Test with a simple subscription list request
                url = f"https://manage.office.com/api/v1.0/{tenant_id}/activity/feed/subscriptions/list"
                async with session.get(url, headers=headers) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Connection test failed for Microsoft Purview: {e}")
            return False
    
    async def collect_logs(self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Collect audit logs from Microsoft Purview"""
        try:
            # Get access token
            token = await self._get_access_token()
            if not token:
                raise Exception("Failed to obtain access token")
            
            # Set default time range if not provided
            if not end_time:
                end_time = datetime.now(timezone.utc)
            if not start_time:
                start_time = end_time - timedelta(hours=1)  # Default to last hour
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            all_logs = []
            
            # Collect from each content type
            for content_type in self.content_types:
                try:
                    logs = await self._collect_content_type(
                        content_type, start_time, end_time, headers
                    )
                    all_logs.extend(logs)
                    
                    # Rate limiting
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except Exception as e:
                    logger.error(f"Error collecting {content_type} logs: {e}")
                    continue
            
            logger.info(f"Collected {len(all_logs)} logs from {self.source_system}")
            return all_logs
            
        except Exception as e:
            logger.error(f"Error collecting logs from {self.source_system}: {e}")
            raise
    
    async def _get_access_token(self) -> Optional[str]:
        """Get access token using MSAL"""
        try:
            # Get token for Office 365 Management API
            scopes = ['https://manage.office.com/.default']
            
            result = self.app.acquire_token_for_client(scopes=scopes)
            
            if 'access_token' in result:
                return result['access_token']
            else:
                logger.error(f"Failed to get access token: {result.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    async def _collect_content_type(self, content_type: str, start_time: datetime, end_time: datetime, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Collect logs for a specific content type"""
        logs = []
        
        # Format timestamps for API
        start_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
        end_str = end_time.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Get available content
        url = f"{self.base_url}/{self.config['tenant_id']}/activity/feed/subscriptions/content"
        params = {
            'contentType': content_type,
            'startTime': start_str,
            'endTime': end_str
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status != 200:
                    logger.error(f"Failed to get content for {content_type}: {response.status}")
                    return logs
                
                content_data = await response.json()
                
                # Process each content URL
                for content_item in content_data:
                    try:
                        # Extract the actual URL from the content item
                        if isinstance(content_item, dict):
                            content_url = content_item.get('contentUri')
                        else:
                            content_url = content_item
                            
                        if not content_url:
                            logger.warning(f"No contentUri found in content item: {content_item}")
                            continue
                            
                        content_logs = await self._fetch_content_logs(content_url, headers)
                        logs.extend(content_logs)
                        
                        # Rate limiting
                        await asyncio.sleep(self.rate_limit_delay)
                        
                    except Exception as e:
                        logger.error(f"Error fetching content from {content_item}: {e}")
                        continue
        
        return logs
    
    async def _fetch_content_logs(self, content_url: str, headers: Dict[str, str]) -> List[Dict[str, Any]]:
        """Fetch logs from a content URL"""
        logs = []
        
        async with aiohttp.ClientSession() as session:
            async with session.get(content_url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch content from {content_url}: {response.status}")
                    return logs
                
                # Parse the content (usually JSON lines format)
                content = await response.text()
                
                # Debug: Log the first few lines to understand the format
                lines = content.strip().split('\n')
                if lines:
                    logger.debug(f"First line format: {type(json.loads(lines[0]))} - {lines[0][:200]}...")
                
                for line in lines:
                    if line.strip():
                        try:
                            log_entry = json.loads(line)
                            
                            # Handle different response formats
                            if isinstance(log_entry, list):
                                # If the response is a list of log entries
                                for entry in log_entry:
                                    if isinstance(entry, dict):
                                        parsed_logs = self._parse_log_entry(entry)
                                        if parsed_logs:
                                            logs.extend(parsed_logs)  # Extend with list of entries
                            elif isinstance(log_entry, dict):
                                # If the response is a single log entry
                                parsed_logs = self._parse_log_entry(log_entry)
                                if parsed_logs:
                                    logs.extend(parsed_logs)  # Extend with list of entries
                            else:
                                logger.warning(f"Unexpected log entry format: {type(log_entry)}")
                                
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse log line: {e}")
                            continue
        
        return logs
    
    def _parse_log_entry(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse a Microsoft Purview log entry into our agnostic schema
        Returns a list of audit log entries - one for each email message involved"""
        
        try:
            # Extract basic fields
            event_id = log_entry.get('Id', '')
            event_type = log_entry.get('RecordType', '')
            event_timestamp = log_entry.get('CreationTime', '')

            # Parse timestamp
            try:
                if event_timestamp:
                    # Handle different timestamp formats
                    if 'T' in event_timestamp and 'Z' in event_timestamp:
                        # ISO format with Z
                        parsed_timestamp = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                    elif 'T' in event_timestamp:
                        # ISO format without Z
                        parsed_timestamp = datetime.fromisoformat(event_timestamp)
                    else:
                        # Try parsing as other formats
                        parsed_timestamp = datetime.strptime(event_timestamp, '%Y-%m-%d %H:%M:%S')
                else:
                    parsed_timestamp = datetime.now(timezone.utc)
            except Exception:
                parsed_timestamp = datetime.now(timezone.utc)

            # Extract actor information
            actor_name = log_entry.get('UserId', log_entry.get('Actor', ''))  # UserId is typically the email/username
            actor_id = log_entry.get('UserKey', log_entry.get('ActorName', ''))  # UserKey is typically the internal ID

            # Extract target information
            target_id = log_entry.get('ObjectId', log_entry.get('TargetId', ''))
            target_name = log_entry.get('ObjectName', log_entry.get('TargetName', ''))

            # Extract action
            action = log_entry.get('Operation', log_entry.get('Action', ''))

            # Extract IP and location
            ip_address = log_entry.get('ClientIP') or None  # Use None instead of empty string for INET column
            location = log_entry.get('Location') or None

            # Extract enhanced Microsoft Purview fields
            operation = log_entry.get('Operation', '')
            result_status = log_entry.get('ResultStatus', '')
            client_process_name = log_entry.get('ClientProcessName', '')
            client_version = log_entry.get('ClientVersion', '')
            session_id = log_entry.get('SessionId', '')
            mailbox_guid = log_entry.get('MailboxGuid', '')
            organization_name = log_entry.get('OrganizationName', '')
            cross_mailbox_operation = log_entry.get('CrossMailboxOperation', False)

            # Extract folder information
            source_folder = None
            destination_folder = None
            if 'Folder' in log_entry and isinstance(log_entry['Folder'], dict):
                source_folder = log_entry['Folder'].get('Path', '')

            if 'DestFolder' in log_entry and isinstance(log_entry['DestFolder'], dict):
                destination_folder = log_entry['DestFolder'].get('Path', '')

            # Extract additional context
            additional_data = {}
            for key, value in log_entry.items():
                if key not in ['Id', 'RecordType', 'CreationTime', 'UserId', 'UserKey', 'ObjectId', 'ObjectName', 'Operation', 'ClientIP', 'Location']:
                    additional_data[key] = value

            # Map event type to our schema
            mapped_event_type = self._map_event_type(event_type)

            # Determine relevance flags
            security_relevant = self._is_security_relevant(event_type, action, additional_data)
            legal_hold_relevant = self._is_legal_hold_relevant(event_type, action, additional_data)
            retention_relevant = self._is_retention_relevant(event_type, action, additional_data)

            # Extract all email messages from the log entry
            email_messages = self._extract_email_messages(log_entry)
            
            # If no specific email messages found, create one entry with the general event
            if not email_messages:
                # Generate unique ID for the general event
                unique_id = hashlib.sha256(
                    f"{event_id}{event_timestamp}{actor_id}{target_id}".encode()
                ).hexdigest()
                
                return [{
                    'source_system': 'microsoft_purview',
                    'event_id': unique_id,
                    'event_type': mapped_event_type,
                    'event_timestamp': parsed_timestamp,
                    'actor_id': actor_id,
                    'actor_name': actor_name,
                    'actor_type': 'user',
                    'ip_address': ip_address,
                    'location': location,
                    'target_id': target_id,
                    'target_name': target_name,
                    'target_type': log_entry.get('Workload', ''),
                    'action': action,
                    'action_result': result_status,
                    'raw_data': log_entry,
                    'processed_data': additional_data,
                    'security_relevant': security_relevant,
                    'legal_hold_relevant': legal_hold_relevant,
                    'retention_relevant': retention_relevant,
                    'compliance_tags': self._generate_compliance_tags(event_type, action, additional_data),
                    'operation': operation,
                    'result_status': result_status,
                    'client_process_name': client_process_name,
                    'client_version': client_version,
                    'session_id': session_id,
                    'mailbox_guid': mailbox_guid,
                    'organization_name': organization_name,
                    'cross_mailbox_operation': cross_mailbox_operation,
                    'source_folder': source_folder,
                    'destination_folder': destination_folder
                }]
            
            # Create separate audit log entries for each email message
            audit_entries = []
            for i, email_msg in enumerate(email_messages):
                # Generate unique ID for each email-specific event
                unique_id = hashlib.sha256(
                    f"{event_id}{event_timestamp}{actor_id}{email_msg.get('internet_message_id', '')}{i}".encode()
                ).hexdigest()
                
                # Extract email-specific information
                internet_message_id = email_msg.get('internet_message_id', '')
                email_subject = email_msg.get('subject', '')
                email_folder = email_msg.get('folder_path', source_folder)
                email_size = email_msg.get('size_in_bytes')
                
                # Create email-specific additional data
                email_additional_data = additional_data.copy()
                email_additional_data.update({
                    'InternetMessageId': internet_message_id,
                    'EmailSubject': email_subject,
                    'EmailSize': email_size,
                    'EmailFolder': email_folder,
                    'EmailIndex': i,
                    'TotalEmailsInEvent': len(email_messages)
                })
                
                audit_entries.append({
                    'source_system': 'microsoft_purview',
                    'event_id': unique_id,
                    'event_type': mapped_event_type,
                    'event_timestamp': parsed_timestamp,
                    'actor_id': actor_id,
                    'actor_name': actor_name,
                    'actor_type': 'user',
                    'ip_address': ip_address,
                    'location': location,
                    'target_id': target_id,
                    'target_name': target_name,
                    'target_type': log_entry.get('Workload', ''),
                    'action': action,
                    'action_result': result_status,
                    'raw_data': log_entry,
                    'processed_data': email_additional_data,
                    'security_relevant': security_relevant,
                    'legal_hold_relevant': legal_hold_relevant,
                    'retention_relevant': retention_relevant,
                    'compliance_tags': self._generate_compliance_tags(event_type, action, additional_data),
                    'operation': operation,
                    'result_status': result_status,
                    'client_process_name': client_process_name,
                    'client_version': client_version,
                    'session_id': session_id,
                    'mailbox_guid': mailbox_guid,
                    'organization_name': organization_name,
                    'cross_mailbox_operation': cross_mailbox_operation,
                    'source_folder': email_folder,
                    'destination_folder': destination_folder,
                    'internet_message_id': internet_message_id,
                    'email_subject': email_subject
                })
            
            return audit_entries
            
        except Exception as e:
            logger.error(f"Error parsing log entry: {e}")
            return []

    def _extract_email_messages(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all email messages from a Microsoft Purview log entry
        Handles complex folder structures with multiple emails per folder"""
        
        email_messages = []
        
        # Method 1: Extract from Folders structure (like in your example)
        if 'Folders' in log_entry and isinstance(log_entry['Folders'], list):
            for folder in log_entry['Folders']:
                if isinstance(folder, dict):
                    folder_path = folder.get('Path', '')
                    folder_items = folder.get('FolderItems', [])
                    
                    if isinstance(folder_items, list):
                        for item in folder_items:
                            if isinstance(item, dict):
                                internet_message_id = item.get('InternetMessageId', '')
                                if internet_message_id:  # Only add if we have a message ID
                                    email_messages.append({
                                        'internet_message_id': internet_message_id,
                                        'subject': item.get('Subject', ''),  # May not be present
                                        'folder_path': folder_path,
                                        'size_in_bytes': item.get('SizeInBytes'),
                                        'item_id': item.get('Id', ''),
                                        'immutable_id': item.get('ImmutableId', ''),
                                        'client_request_id': item.get('ClientRequestId', '')
                                    })
        
        # Method 2: Extract from AffectedItems (older format)
        if not email_messages and 'AffectedItems' in log_entry and isinstance(log_entry['AffectedItems'], list):
            for item in log_entry['AffectedItems']:
                if isinstance(item, dict):
                    internet_message_id = item.get('InternetMessageId', '')
                    if internet_message_id:
                        email_messages.append({
                            'internet_message_id': internet_message_id,
                            'subject': item.get('Subject', ''),
                            'folder_path': item.get('ParentFolder', {}).get('Path', '') if isinstance(item.get('ParentFolder'), dict) else '',
                            'size_in_bytes': item.get('SizeInBytes'),
                            'item_id': item.get('Id', ''),
                            'immutable_id': item.get('ImmutableId', ''),
                            'client_request_id': item.get('ClientRequestId', '')
                        })
        
        # Method 3: Extract from direct fields (single email events)
        if not email_messages:
            internet_message_id = (
                log_entry.get('InternetMessageId') or 
                log_entry.get('MessageId') or 
                log_entry.get('EmailId')
            )
            if internet_message_id:
                email_messages.append({
                    'internet_message_id': internet_message_id,
                    'subject': (
                        log_entry.get('Subject') or 
                        log_entry.get('EmailSubject') or 
                        log_entry.get('MessageSubject')
                    ),
                    'folder_path': (
                        log_entry.get('Folder', {}).get('Path', '') if isinstance(log_entry.get('Folder'), dict) else ''
                    ),
                    'size_in_bytes': log_entry.get('SizeInBytes'),
                    'item_id': log_entry.get('Id', ''),
                    'immutable_id': log_entry.get('ImmutableId', ''),
                    'client_request_id': log_entry.get('ClientRequestId', '')
                })
        
        return email_messages
    
    def _map_event_type(self, source_event_type: str) -> str:
        """Map Microsoft Purview event types to our agnostic schema"""
        event_mapping = {
            # Azure Active Directory events
            'UserLoggedIn': 'authentication.login',
            'UserLogoff': 'authentication.logout',
            'UserPasswordChanged': 'authentication.password_change',
            'UserPasswordReset': 'authentication.password_reset',
            'UserAccountCreated': 'user.creation',
            'UserAccountDeleted': 'user.deletion',
            'UserAccountModified': 'user.modification',
            
            # Exchange events
            'MailItemsAccessed': 'email.access',
            'MailItemsCreated': 'email.creation',
            'MailItemsDeleted': 'email.deletion',
            'MailItemsModified': 'email.modification',
            'MailItemsMoved': 'email.movement',
            
            # SharePoint events
            'FileAccessed': 'file.access',
            'FileCreated': 'file.creation',
            'FileDeleted': 'file.deletion',
            'FileModified': 'file.modification',
            'FileDownloaded': 'file.download',
            'FileUploaded': 'file.upload',
            'FileShared': 'file.sharing',
            
            # General events
            'AdminAction': 'admin.action',
            'SystemAction': 'system.action',
            'SecurityEvent': 'security.event',
            
            # DLP events
            'DLPIncident': 'dlp.incident',
            'DLPPolicyMatch': 'dlp.policy_match',
            'DLPContentProcessed': 'dlp.content_processed'
        }
        
        return event_mapping.get(source_event_type, 'unknown')
    
    def _is_security_relevant(self, event_type: str, action: str, additional_data: Dict[str, Any]) -> bool:
        """Determine if an event is security relevant"""
        security_keywords = [
            'login', 'logout', 'password', 'authentication', 'authorization',
            'access', 'permission', 'role', 'admin', 'security', 'dlp',
            'incident', 'threat', 'malware', 'phishing', 'breach'
        ]
        
        # Convert to strings and handle None values
        event_str = str(event_type) if event_type is not None else ''
        action_str = str(action) if action is not None else ''
        
        event_lower = event_str.lower()
        action_lower = action_str.lower()
        
        return any(keyword in event_lower or keyword in action_lower for keyword in security_keywords)
    
    def _is_legal_hold_relevant(self, event_type: str, action: str, additional_data: Dict[str, Any]) -> bool:
        """Determine if an event is legal hold relevant"""
        legal_hold_keywords = [
            'delete', 'deletion', 'remove', 'purge', 'retention',
            'legal', 'hold', 'litigation', 'discovery', 'compliance'
        ]
        
        # Convert to strings and handle None values
        event_str = str(event_type) if event_type is not None else ''
        action_str = str(action) if action is not None else ''
        
        event_lower = event_str.lower()
        action_lower = action_str.lower()
        
        return any(keyword in event_lower or keyword in action_lower for keyword in legal_hold_keywords)
    
    def _is_retention_relevant(self, event_type: str, action: str, additional_data: Dict[str, Any]) -> bool:
        """Determine if an event is retention relevant"""
        retention_keywords = [
            'retention', 'archive', 'backup', 'restore', 'expiration',
            'policy', 'compliance', 'governance', 'lifecycle'
        ]
        
        # Convert to strings and handle None values
        event_str = str(event_type) if event_type is not None else ''
        action_str = str(action) if action is not None else ''
        
        event_lower = event_str.lower()
        action_lower = action_str.lower()
        
        return any(keyword in event_lower or keyword in action_lower for keyword in retention_keywords)
    
    def _generate_compliance_tags(self, event_type: str, action: str, additional_data: Dict[str, Any]) -> List[str]:
        """Generate compliance tags based on event characteristics"""
        tags = []
        
        # Convert to strings and handle None values
        event_str = str(event_type) if event_type is not None else ''
        action_str = str(action) if action is not None else ''
        
        event_lower = event_str.lower()
        action_lower = action_str.lower()
        
        # GDPR tags
        if any(keyword in event_lower or keyword in action_lower 
               for keyword in ['personal', 'data', 'privacy', 'consent', 'right']):
            tags.append('gdpr')
        
        # SOX tags
        if any(keyword in event_lower or keyword in action_lower 
               for keyword in ['financial', 'audit', 'control', 'sox', 'sarbanes']):
            tags.append('sox')
        
        # HIPAA tags
        if any(keyword in event_lower or keyword in action_lower 
               for keyword in ['health', 'medical', 'phi', 'hipaa', 'patient']):
            tags.append('hipaa')
        
        # ISO 27001 tags
        if any(keyword in event_lower or keyword in action_lower 
               for keyword in ['security', 'iso', '27001', 'information']):
            tags.append('iso27001')
        
        return tags 