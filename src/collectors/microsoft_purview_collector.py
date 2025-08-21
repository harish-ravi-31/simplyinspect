"""
Microsoft Purview Audit Log Collector
Collects audit logs from Microsoft Purview via Office 365 Management Activity API
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import aiohttp
from msal import ConfidentialClientApplication

from ..external_audit_logs import AuditLogEvent

logger = logging.getLogger(__name__)

# Utility: Recursively extract first occurrence of a field from nested dict/list

def extract_field_recursive(data, field_names):
    if isinstance(field_names, str):
        field_names = [field_names]
    if isinstance(data, dict):
        for field in field_names:
            if field in data and data[field]:
                return data[field]
        for value in data.values():
            result = extract_field_recursive(value, field_names)
            if result:
                return result
    elif isinstance(data, list):
        for item in data:
            result = extract_field_recursive(item, field_names)
            if result:
                return result
    return None

class MicrosoftPurviewCollector:
    """Collector for Microsoft Purview audit logs"""
    
    def __init__(self, source_config: Dict[str, Any]):
        self.source_config = source_config
        self.config = source_config.get('Configuration', {})
        self.tenant_id = self.config.get('tenant_id')
        self.client_id = self.config.get('client_id')
        self.client_secret = self.config.get('client_secret')
        self.content_types = self.config.get('content_types', ['Audit.Exchange', 'Audit.SharePoint', 'Audit.General'])
        
        # MSAL application for authentication
        self.msal_app = ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )
        
        # API endpoints
        self.base_url = "https://manage.office.com/api/v1.0"
        self.audit_log_url = urljoin(self.base_url, f"{self.tenant_id}/activity/feed/subscriptions/content")
    
    async def collect_logs(self) -> List[AuditLogEvent]:
        """Collect audit logs from Microsoft Purview"""
        events = []
        
        try:
            # Get access token
            access_token = await self._get_access_token()
            if not access_token:
                logger.error("Failed to obtain access token for Microsoft Purview")
                return events
            
            # Collect logs for each content type
            for content_type in self.content_types:
                try:
                    content_events = await self._collect_content_type_logs(access_token, content_type)
                    events.extend(content_events)
                    logger.info(f"Collected {len(content_events)} events from {content_type}")
                except Exception as e:
                    logger.error(f"Failed to collect logs from {content_type}: {e}")
            
            logger.info(f"Total collected events: {len(events)}")
            return events
            
        except Exception as e:
            logger.error(f"Failed to collect Microsoft Purview logs: {e}")
            return events
    
    async def _get_access_token(self) -> Optional[str]:
        """Get access token for Office 365 Management API"""
        try:
            # Get token for Office 365 Management API
            scopes = ["https://manage.office.com/.default"]
            result = self.msal_app.acquire_token_for_client(scopes=scopes)
            
            if "access_token" in result:
                logger.debug("Successfully obtained access token")
                return result["access_token"]
            else:
                logger.error(f"Failed to get access token: {result.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting access token: {e}")
            return None
    
    async def _collect_content_type_logs(self, access_token: str, content_type: str) -> List[AuditLogEvent]:
        """Collect logs for a specific content type"""
        events = []
        
        # Calculate time range (last 24 hours by default)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        params = {
            "contentType": content_type,
            "startTime": start_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "endTime": end_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.audit_log_url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        events = await self._parse_audit_logs(data, content_type)
                    else:
                        logger.error(f"Failed to get audit logs: {response.status} - {await response.text()}")
                        
        except Exception as e:
            logger.error(f"Error collecting {content_type} logs: {e}")
        
        return events
    
    async def _parse_audit_logs(self, data: Dict[str, Any], content_type: str) -> List[AuditLogEvent]:
        """Parse audit log data into AuditLogEvent objects"""
        events = []
        
        try:
            # Handle different response formats
            if isinstance(data, list):
                audit_records = data
            elif isinstance(data, dict) and 'value' in data:
                audit_records = data['value']
            else:
                logger.warning(f"Unexpected data format for {content_type}")
                return events
            
            for record in audit_records:
                try:
                    event = await self._parse_audit_record(record, content_type)
                    if event:
                        events.append(event)
                except Exception as e:
                    logger.error(f"Failed to parse audit record: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing audit logs: {e}")
        
        return events
    
    async def _parse_audit_record(self, record: Dict[str, Any], content_type: str) -> Optional[AuditLogEvent]:
        """Parse a single audit record into an AuditLogEvent with comprehensive data extraction"""
        try:
            # Extract common fields with better fallbacks
            event_id = record.get('Id') or record.get('RecordId') or str(record.get('CreationTime', '')) + '_' + str(record.get('UserKey', ''))
            # Use Operation as EventType where available (as suggested by user)
            event_type = record.get('Operation') or record.get('RecordType') or 'Unknown'
            
            # Parse timestamp with better error handling
            timestamp_str = record.get('CreationTime') or record.get('TimeStamp')
            if timestamp_str:
                try:
                    # Handle different timestamp formats
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1] + '+00:00'
                    event_timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    event_timestamp = datetime.now(timezone.utc)
            else:
                event_timestamp = datetime.now(timezone.utc)
            
            # Enhanced actor information extraction
            actor_id = record.get('UserKey') or record.get('UserId') or record.get('ActorId')
            # Use UserId as ActorName (as suggested by user)
            actor_name = record.get('UserId') or record.get('UserPrincipalName') or record.get('ActorName') or record.get('UserType')
            actor_type = self._determine_actor_type(record)
            actor_ip = record.get('ClientIPAddress') or record.get('ClientIP') or record.get('IPAddress')
            
            # Enhanced target information extraction
            target_id = record.get('ObjectId') or record.get('TargetId') or record.get('ItemType')
            target_name = record.get('ObjectName') or record.get('TargetName') or record.get('ItemType')
            target_type = self._determine_target_type(record, content_type)
            target_path = record.get('SiteUrl') or record.get('SourceFileName') or record.get('FolderPath')
            
            # Enhanced action information extraction
            action = record.get('Operation') or record.get('Action') or 'Unknown'
            action_result = 'success' if record.get('ResultStatus') == 'Succeeded' else 'failure'
            action_reason = record.get('ActionReason') or record.get('Reason')
            
            # Comprehensive field extraction using recursive search
            internet_message_id = extract_field_recursive(record, ['InternetMessageId', 'MessageId'])
            email_subject = extract_field_recursive(record, ['Subject', 'EmailSubject'])
            sender = extract_field_recursive(record, ['Sender', 'From', 'FromAddress'])
            recipients = extract_field_recursive(record, ['Recipients', 'To', 'ToAddress'])
            
            # Enhanced Microsoft Purview specific fields
            source_folder = extract_field_recursive(record, ['SourceFolder', 'FolderPath', 'ParentFolder'])
            destination_folder = extract_field_recursive(record, ['DestinationFolder', 'DestFolder'])
            operation = record.get('Operation') or record.get('Action')
            result_status = record.get('ResultStatus') or record.get('Status')
            client_process_name = record.get('ClientProcessName') or record.get('ApplicationName')
            client_version = record.get('ClientVersion') or record.get('AppVersion')
            session_id = record.get('SessionId') or record.get('CorrelationId')
            mailbox_guid = record.get('MailboxGuid') or record.get('MailboxId')
            organization_name = record.get('OrganizationName') or record.get('TenantName')
            cross_mailbox_operation = record.get('CrossMailboxOperation', False)
            
            # Additional fields from sample JSON
            client_ip_address = record.get('ClientIPAddress') or record.get('ClientIP') or record.get('IPAddress')
            workload = record.get('Workload')
            record_type = record.get('RecordType')
            organization_id = record.get('OrganizationId')
            mailbox_owner_upn = record.get('MailboxOwnerUPN')
            originating_server = record.get('OriginatingServer')
            
            # Extract from AffectedItems if available
            if 'AffectedItems' in record and isinstance(record['AffectedItems'], list):
                for item in record['AffectedItems']:
                    if isinstance(item, dict):
                        if not internet_message_id and 'InternetMessageId' in item:
                            internet_message_id = item['InternetMessageId']
                        if not email_subject and 'Subject' in item:
                            email_subject = item['Subject']
                        if not source_folder and 'ParentFolder' in item:
                            parent_folder = item['ParentFolder']
                            if isinstance(parent_folder, dict) and 'Path' in parent_folder:
                                source_folder = parent_folder['Path']
            
            # Extract from FolderItems if available (handle nested structure)
            if 'Folders' in record and isinstance(record['Folders'], list):
                for folder in record['Folders']:
                    if isinstance(folder, dict) and 'FolderItems' in folder and isinstance(folder['FolderItems'], list):
                        for item in folder['FolderItems']:
                            if isinstance(item, dict):
                                if not internet_message_id and 'InternetMessageId' in item:
                                    internet_message_id = item['InternetMessageId']
                                if not email_subject and 'Subject' in item:
                                    email_subject = item['Subject']
            
            # Also check direct FolderItems (fallback)
            if 'FolderItems' in record and isinstance(record['FolderItems'], list):
                for item in record['FolderItems']:
                    if isinstance(item, dict):
                        if not internet_message_id and 'InternetMessageId' in item:
                            internet_message_id = item['InternetMessageId']
                        if not email_subject and 'Subject' in item:
                            email_subject = item['Subject']
            
            # Extract from Folders if available (handle nested structure)
            if 'Folders' in record and isinstance(record['Folders'], list):
                for folder in record['Folders']:
                    if isinstance(folder, dict):
                        if not source_folder and 'Path' in folder:
                            source_folder = folder['Path']
                        # Also check for folder ID as fallback
                        if not source_folder and 'Id' in folder:
                            source_folder = folder['Id']
            
            # Enhanced processed data with comprehensive extraction
            processed_data = {
                'application': record.get('ApplicationId') or record.get('ApplicationName'),
                'client_ip': client_ip_address or actor_ip,
                'user_agent': record.get('UserAgent') or record.get('ClientUserAgent'),
                'workload': workload or record.get('Service'),
                'organization_id': organization_id or record.get('TenantId'),
                'record_type': record_type or record.get('EventType'),
                'result_status': result_status,
                'correlation_id': record.get('CorrelationId') or record.get('SessionId'),
                'internet_message_id': internet_message_id,
                'subject': email_subject,
                'sender': sender,
                'recipients': recipients,
                'source_folder': source_folder,
                'destination_folder': destination_folder,
                'operation': operation,
                'client_process_name': client_process_name,
                'client_version': client_version,
                'session_id': session_id,
                'mailbox_guid': mailbox_guid,
                'organization_name': organization_name,
                'cross_mailbox_operation': cross_mailbox_operation,
                'action_reason': action_reason,
                'mailbox_owner_upn': mailbox_owner_upn,
                'originating_server': originating_server,
                'external_access': record.get('ExternalAccess'),
                'operation_count': record.get('OperationCount'),
                'logon_type': record.get('LogonType'),
                'internal_logon_type': record.get('InternalLogonType')
            }
            
            # Content-type specific processing
            if content_type == 'Audit.Exchange':
                processed_data.update({
                    'mailbox_guid': mailbox_guid,
                    'item_type': record.get('ItemType') or record.get('ObjectType'),
                    'folder_path': source_folder,
                    'message_size': record.get('MessageSize') or record.get('Size'),
                    'has_attachments': record.get('HasAttachments', False),
                    'attachment_count': record.get('AttachmentCount'),
                    'is_read': record.get('IsRead'),
                    'is_draft': record.get('IsDraft'),
                    'importance': record.get('Importance'),
                    'sensitivity': record.get('Sensitivity')
                })
            elif content_type == 'Audit.SharePoint':
                processed_data.update({
                    'site_url': record.get('SiteUrl') or record.get('WebUrl'),
                    'source_file_name': record.get('SourceFileName') or record.get('FileName'),
                    'source_relative_url': record.get('SourceRelativeUrl') or record.get('RelativeUrl'),
                    'list_id': record.get('ListId'),
                    'list_item_unique_id': record.get('ListItemUniqueId'),
                    'web_id': record.get('WebId'),
                    'file_size': record.get('FileSize') or record.get('Size'),
                    'file_type': record.get('FileType') or record.get('Extension'),
                    'is_folder': record.get('IsFolder', False)
                })
            elif content_type == 'Audit.AzureActiveDirectory':
                processed_data.update({
                    'app_id': record.get('AppId') or record.get('ApplicationId'),
                    'resource_id': record.get('ResourceId') or record.get('TargetResourceId'),
                    'ip_address': actor_ip,
                    'location': record.get('Location') or record.get('GeoLocation'),
                    'device_info': record.get('DeviceInfo'),
                    'risk_level': record.get('RiskLevel'),
                    'authentication_method': record.get('AuthenticationMethod')
                })
            
            # Enhanced metadata with comprehensive information
            metadata = {
                'content_type': content_type,
                'parsed_at': datetime.now(timezone.utc).isoformat(),
                'original_record_keys': list(record.keys()),
                'extraction_version': '2.0',
                'has_affected_items': 'AffectedItems' in record,
                'has_folder_items': 'FolderItems' in record,
                'has_folders': 'Folders' in record,
                'record_completeness': self._assess_record_completeness(record)
            }
            
            # Return comprehensive AuditLogEvent
            return AuditLogEvent(
                source_system=self.source_config.get('SourceSystem', 'microsoft_purview'),
                event_id=event_id,
                event_type=event_type,
                event_timestamp=event_timestamp,
                source_instance=record.get('OrganizationId') or record.get('TenantId'),
                source_version=record.get('ApiVersion') or 'v1.0',
                actor_id=actor_id,
                actor_name=actor_name,
                actor_type=actor_type,
                actor_ip_address=actor_ip,
                actor_location=record.get('Location') or record.get('GeoLocation'),
                target_id=target_id,
                target_name=target_name,
                target_type=target_type,
                target_path=target_path,
                action=action,
                action_result=action_result,
                action_reason=action_reason,
                raw_data=record,
                processed_data=processed_data,
                metadata=metadata,
                internet_message_id=internet_message_id,
                email_subject=email_subject,
                source_folder=source_folder,
                destination_folder=destination_folder,
                operation=operation,
                result_status=result_status,
                client_process_name=client_process_name,
                client_version=client_version,
                session_id=session_id,
                mailbox_guid=mailbox_guid,
                organization_name=organization_name,
                cross_mailbox_operation=cross_mailbox_operation
            )
            
        except Exception as e:
            logger.error(f"Error parsing audit record: {e}")
            return None
    
    def _determine_actor_type(self, record: Dict[str, Any]) -> str:
        """Determine the type of actor from the audit record"""
        user_type = record.get('UserType', '').lower()
        
        if 'admin' in user_type or 'administrator' in user_type:
            return 'administrator'
        elif 'service' in user_type or 'application' in user_type:
            return 'service_principal'
        elif 'system' in user_type:
            return 'system'
        else:
            return 'user'
    
    def _determine_target_type(self, record: Dict[str, Any], content_type: str) -> str:
        """Determine the type of target from the audit record"""
        if content_type == 'Audit.Exchange':
            item_type = record.get('ItemType', '').lower()
            if 'message' in item_type or 'email' in item_type:
                return 'email'
            elif 'calendar' in item_type:
                return 'calendar'
            elif 'contact' in item_type:
                return 'contact'
            elif 'task' in item_type:
                return 'task'
            else:
                return 'mailbox_item'
        
        elif content_type == 'Audit.SharePoint':
            source_file = record.get('SourceFileName', '').lower()
            if source_file.endswith(('.doc', '.docx')):
                return 'document'
            elif source_file.endswith(('.xls', '.xlsx')):
                return 'spreadsheet'
            elif source_file.endswith(('.ppt', '.pptx')):
                return 'presentation'
            elif source_file.endswith(('.pdf')):
                return 'pdf'
            elif source_file.endswith(('.txt', '.rtf')):
                return 'text'
            else:
                return 'file'
        
        else:
            return 'unknown'
    
    def _assess_record_completeness(self, record: Dict[str, Any]) -> str:
        """Assess how complete the record is based on available fields"""
        required_fields = ['Id', 'CreationTime', 'Operation', 'UserKey']
        optional_fields = ['ClientIP', 'ApplicationId', 'Workload', 'ResultStatus', 'AffectedItems', 'FolderItems']
        
        required_count = sum(1 for field in required_fields if field in record and record[field])
        optional_count = sum(1 for field in optional_fields if field in record and record[field])
        
        if required_count == len(required_fields) and optional_count >= 3:
            return 'complete'
        elif required_count >= 3 and optional_count >= 1:
            return 'partial'
        else:
            return 'minimal'
    
    async def test_connection(self) -> bool:
        """Test the connection to Microsoft Purview API"""
        try:
            access_token = await self._get_access_token()
            if not access_token:
                return False
            
            # Try to get a small sample of logs
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {
                "contentType": "Audit.General",
                "startTime": (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "endTime": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.audit_log_url, headers=headers, params=params) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False 