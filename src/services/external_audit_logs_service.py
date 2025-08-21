"""
External Audit Logs Service for Simply Archive
Handles collection, processing, and storage of external audit logs from various sources
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import asyncpg
# Optional import - croniter not critical
try:
    from croniter import croniter
except ImportError:
    croniter = None

# Simplified imports for SimplyInspect
import os

logger = logging.getLogger(__name__)

class ProcessingStatus(Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"

class JobStatus(Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class AuditLogEvent:
    """Data class for audit log events with AI-optimized fields"""
    source_system: str
    event_id: Optional[str] = None
    event_type: Optional[str] = None
    event_timestamp: Optional[datetime] = None
    source_instance: Optional[str] = None
    source_version: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    actor_type: Optional[str] = None
    actor_ip_address: Optional[str] = None
    actor_location: Optional[Dict[str, Any]] = None
    target_id: Optional[str] = None
    target_name: Optional[str] = None
    target_type: Optional[str] = None
    target_path: Optional[str] = None
    action: Optional[str] = None
    action_result: Optional[str] = None
    action_reason: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    processed_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    internet_message_id: Optional[str] = None
    email_subject: Optional[str] = None
    source_folder: Optional[str] = None
    destination_folder: Optional[str] = None
    operation: Optional[str] = None
    result_status: Optional[str] = None
    client_process_name: Optional[str] = None
    client_version: Optional[str] = None
    session_id: Optional[str] = None
    mailbox_guid: Optional[str] = None
    organization_name: Optional[str] = None
    cross_mailbox_operation: Optional[bool] = None

class ExternalAuditLogsService:
    """Service for managing external audit log collection and processing"""
    
    def __init__(self):
        self.db_handler = db_handler
        self.encryption_middleware = EncryptionMiddleware()
        self.collectors = {}
        self._register_collectors()
    
    def _register_collectors(self):
        """Register available log collectors"""
        self.collectors = {}
        
        try:
            from .collectors.microsoft_purview import MicrosoftPurviewCollector
            self.collectors['microsoft_purview'] = MicrosoftPurviewCollector
            logger.info("Microsoft Purview collector registered")
        except ImportError as e:
            logger.warning(f"Microsoft Purview collector not available: {e}")
        
        try:
            from .collectors.firewall_collector import FirewallCollector
            self.collectors['firewall_logs'] = FirewallCollector
            logger.info("Firewall collector registered")
        except ImportError as e:
            logger.warning(f"Firewall collector not available: {e}")
        
        try:
            from .collectors.e3_compliance_collector import E3ComplianceCollector
            self.collectors['e3_compliance'] = E3ComplianceCollector
            logger.info("E3 Compliance collector registered")
        except ImportError as e:
            logger.warning(f"E3 Compliance collector not available: {e}")
        
        try:
            from .collectors.e5_compliance_collector import E5ComplianceCollector
            self.collectors['e5_compliance'] = E5ComplianceCollector
            logger.info("E5 Compliance collector registered")
        except ImportError as e:
            logger.warning(f"E5 Compliance collector not available: {e}")
        
        logger.info(f"Registered {len(self.collectors)} collectors: {list(self.collectors.keys())}")
    
    async def ensure_tables(self):
        """Ensure all required tables exist"""
        await self.db_handler.connect()
        async with self.db_handler.pool.acquire() as conn:
            # Run the schema creation script
            with open('database_migrations/create_external_audit_logs_schema.sql', 'r') as f:
                schema_sql = f.read()
                await conn.execute(schema_sql)
        
        logger.info("External audit logs tables ensured")
    
    async def get_sources(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get configured audit log sources"""
        query = """
            SELECT * FROM public."AuditLogSources"
            WHERE "IsActive" = $1 OR $1 = FALSE
            ORDER BY "SourceSystem"
        """
        sources = await self.db_handler.fetch_all(query, active_only)
        return [dict(source) for source in sources]
    
    async def get_source(self, source_system: str) -> Optional[Dict[str, Any]]:
        """Get a specific audit log source configuration"""
        query = """
            SELECT * FROM public."AuditLogSources"
            WHERE "SourceSystem" = $1
        """
        source = await self.db_handler.fetch_one(query, source_system)
        return dict(source) if source else None
    
    async def update_source(self, source_system: str, updates: Dict[str, Any]) -> bool:
        """Update audit log source configuration"""
        set_clauses = []
        params = []
        param_idx = 1
        
        for key, value in updates.items():
            if key in ['Configuration', 'Schedule', 'RetentionDays', 'IsActive', 'DisplayName', 'Description']:
                set_clauses.append(f'"{key}" = ${param_idx}')
                params.append(value)
                param_idx += 1
        
        if not set_clauses:
            return False
        
        set_clauses.append(f'"UpdatedAt" = ${param_idx}')
        params.append(datetime.now(timezone.utc))
        params.append(source_system)
        
        query = f"""
            UPDATE public."AuditLogSources"
            SET {', '.join(set_clauses)}
            WHERE "SourceSystem" = ${param_idx + 1}
        """
        
        await self.db_handler.execute(query, *params)
        logger.info(f"Updated audit log source: {source_system}")
        return True
    
    async def add_source(self, source_config: Dict[str, Any]) -> bool:
        """Add a new audit log source"""
        query = """
            INSERT INTO public."AuditLogSources" (
                "SourceSystem", "DisplayName", "Description", "Configuration", 
                "Schedule", "RetentionDays", "IsActive"
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """
        
        try:
            await self.db_handler.execute(
                query,
                source_config['source_system'],
                source_config['display_name'],
                source_config.get('description'),
                json.dumps(source_config['configuration']),
                json.dumps(source_config.get('schedule')),
                source_config.get('retention_days', 2555),
                source_config.get('is_active', True)
            )
            logger.info(f"Added new audit log source: {source_config['source_system']}")
            return True
        except Exception as e:
            logger.error(f"Failed to add audit log source: {e}")
            return False
    
    async def store_audit_log(self, event: AuditLogEvent, tenant_id: str = 'default') -> int:
        """Store an audit log event in the database with simplified processing and encryption support"""
        try:
            # Initialize encryption middleware if needed
            if self.encryption_middleware.kms is None:
                await self.encryption_middleware.initialize()
            
            # Simple categorization without database queries
            event_category = self._simple_categorize_event(event.event_type)
            event_subcategory = self._simple_subcategorize_event(event.event_type)
            
            query = """
                INSERT INTO public."ExternalAuditLogs" (
                    "SourceSystem", "SourceInstance", "SourceVersion", "EventId", "EventType", 
                    "EventCategory", "EventSubcategory", "EventTimestamp", "IngestionTimestamp",
                    "ActorId", "ActorName", "ActorType", "ActorIpAddress", "ActorLocation",
                    "TargetId", "TargetName", "TargetType", "TargetPath", "InternetMessageId", 
                    "EmailSubject", "SourceFolder", "DestinationFolder", "Operation", "ResultStatus",
                    "ClientProcessName", "ClientVersion", "SessionId", "MailboxGuid", "OrganizationName",
                    "CrossMailboxOperation", "Action", "ActionResult", 
                    "ActionReason", "RawData", "ProcessedData", "Metadata", "ProcessingStatus",
                    "Tags", "PartitionDate", "TenantId", "IsEncrypted"
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, 
                    $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, 
                    $33, $34, $35, $36, $37, $38, $39, $40, $41
                ) RETURNING "Id"
            """
            
            # Prepare audit log data for potential encryption
            audit_log_data = {
                'raw_data': event.raw_data or {},
                'processed_data': event.processed_data or {},
                'metadata': event.metadata or {},
                'actor_location': event.actor_location,
                'email_subject': event.email_subject,
                'action_reason': event.action_reason
            }
            
            # Encrypt audit log data if encryption is enabled
            encrypted_audit_data = await self.encryption_middleware.encrypt_audit_log(
                audit_log_data, tenant_id
            )
            
            # Determine if data was encrypted
            is_encrypted = encrypted_audit_data.get('encrypted', False)
            
            # Prepare data for database storage
            if is_encrypted:
                # Store encrypted data package
                raw_data_json = json.dumps(encrypted_audit_data.get('data', {}))
                processed_data_json = json.dumps({})  # Empty since it's encrypted
                metadata_json = json.dumps({'encrypted': True})
                actor_location_json = json.dumps({})  # Empty since it's encrypted
                encrypted_email_subject = None  # Don't store subject separately if encrypted
                encrypted_action_reason = None  # Don't store reason separately if encrypted
            else:
                # Store unencrypted data normally
                raw_data_json = json.dumps(event.raw_data) if event.raw_data else '{}'
                processed_data_json = json.dumps(event.processed_data) if event.processed_data else '{}'
                metadata_json = json.dumps(event.metadata) if event.metadata else '{}'
                actor_location_json = json.dumps(event.actor_location) if event.actor_location else None
                encrypted_email_subject = event.email_subject
                encrypted_action_reason = event.action_reason
            
            log_id = await self.db_handler.fetchval(
                query,
                event.source_system,
                event.source_instance,
                event.source_version,
                event.event_id,
                event.event_type,
                event_category,
                event_subcategory,
                event.event_timestamp,
                datetime.now(timezone.utc),  # IngestionTimestamp
                event.actor_id,
                event.actor_name,
                event.actor_type,
                event.actor_ip_address if event.actor_ip_address else None,
                actor_location_json,
                event.target_id,
                event.target_name,
                event.target_type,
                event.target_path,
                event.internet_message_id,
                encrypted_email_subject,
                event.source_folder,
                event.destination_folder,
                event.operation,
                event.result_status,
                event.client_process_name,
                event.client_version,
                event.session_id,
                event.mailbox_guid,
                event.organization_name,
                event.cross_mailbox_operation,
                event.action or 'Unknown',
                event.action_result,
                encrypted_action_reason,
                raw_data_json,
                processed_data_json,
                metadata_json,
                ProcessingStatus.PROCESSED.value,
                [],  # Tags - will be updated later
                event.event_timestamp.date(),
                tenant_id,
                is_encrypted
            )
            
            # Store audit log encryption metadata if encryption was used
            if is_encrypted and log_id:
                await self.encryption_middleware.store_audit_encryption_metadata(
                    log_id, tenant_id, {"encryption_type": "AES-GCM-256"}
                )
            
            logger.info(f"Stored audit log event {event.event_id} with ID {log_id} (encrypted: {is_encrypted})")
            return log_id
            
        except Exception as e:
            logger.error(f"Failed to store audit log event {event.event_id}: {e}", exc_info=True)
            # Store failed event for retry
            await self._store_failed_event(event, str(e))
            raise
    
    async def store_audit_logs_batch(self, events: List[AuditLogEvent], batch_size: int = 25, fast_bulk_insert: bool = False):
        """Store a batch of audit log events in the database for scalability"""
        if not events:
            return 0
        # Prepare the insert query (same as store_audit_log, but for executemany)
        query = """
            INSERT INTO public."ExternalAuditLogs" (
                "SourceSystem", "SourceInstance", "SourceVersion", "EventId", "EventType", 
                "EventCategory", "EventSubcategory", "EventTimestamp", "IngestionTimestamp",
                "ActorId", "ActorName", "ActorType", "ActorIpAddress", "ActorLocation",
                "TargetId", "TargetName", "TargetType", "TargetPath", "InternetMessageId", 
                "EmailSubject", "SourceFolder", "DestinationFolder", "Operation", "ResultStatus",
                "ClientProcessName", "ClientVersion", "SessionId", "MailboxGuid", "OrganizationName",
                "CrossMailboxOperation", "Action", "ActionResult", 
                "ActionReason", "ComplianceTags", "LegalHoldRelevant", "RetentionRelevant", 
                "SecurityRelevant", "RawData", "ProcessedData", "Metadata", "ProcessingStatus",
                "Tags", "PartitionDate"
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, 
                $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, 
                $33, $34, $35, $36, $37, $38, $39, $40, $41, $42, $43
            )
        """
        # Prepare the parameter list for each event
        param_batches = []
        now = datetime.now(timezone.utc)
        
        for event in events:
            if fast_bulk_insert:
                # Fast path: Skip expensive processing for bulk imports
                param_batches.append([
                    event.source_system,
                    event.source_instance,
                    event.source_version,
                    event.event_id,
                    event.event_type,
                    None,  # EventCategory - will be updated later
                    None,  # EventSubcategory - will be updated later
                    event.event_timestamp,
                    now,  # IngestionTimestamp
                    event.actor_id,
                    event.actor_name,
                    event.actor_type,
                    event.actor_ip_address if event.actor_ip_address else None,
                    json.dumps(event.actor_location) if event.actor_location else None,
                    event.target_id,
                    event.target_name,
                    event.target_type,
                    event.target_path,
                    event.internet_message_id,
                    event.email_subject,
                    event.source_folder,
                    event.destination_folder,
                    event.operation,
                    event.result_status,
                    event.client_process_name,
                    event.client_version,
                    event.session_id,
                    event.mailbox_guid,
                    event.organization_name,
                    event.cross_mailbox_operation,
                    event.action or 'Unknown',
                    event.action_result,
                    event.action_reason,
                    [],  # ComplianceTags - will be updated later
                    False,  # LegalHoldRelevant - will be updated later
                    False,  # RetentionRelevant - will be updated later
                    False,  # SecurityRelevant - will be updated later
                    json.dumps(event.raw_data) if event.raw_data else {},
                    json.dumps(event.processed_data) if event.processed_data else {},
                    json.dumps({}),  # Metadata - will be updated later
                    ProcessingStatus.PENDING.value,  # Mark as pending for later processing
                    [],  # Tags - will be updated later
                    event.event_timestamp.date()
                ])
            else:
                # Full processing path (original logic)
                mapping = await self._get_event_mapping(event.source_system, event.event_type)
                event_category = mapping.get('mapped_event_category') if mapping else None
                event_subcategory = mapping.get('mapped_event_subcategory') if mapping else None
                compliance_tags = mapping.get('compliance_tags', []) if mapping else []
                legal_hold_relevant = mapping.get('is_legal_hold_relevant', False) if mapping else False
                retention_relevant = mapping.get('is_retention_relevant', False) if mapping else False
                security_relevant = mapping.get('is_security_relevant', False) if mapping else False
                ai_metadata = self._create_ai_optimized_metadata(event, mapping)
                ai_tags = self._create_ai_optimized_tags(event, mapping)
                processed_data = self._enhance_processed_data(event.processed_data, event, mapping)
                param_batches.append([
                    event.source_system,
                    event.source_instance,
                    event.source_version,
                    event.event_id,
                    event.event_type,
                    event_category,
                    event_subcategory,
                    event.event_timestamp,
                    now,  # IngestionTimestamp
                    event.actor_id,
                    event.actor_name,
                    event.actor_type,
                    event.actor_ip_address if event.actor_ip_address else None,
                    json.dumps(event.actor_location) if event.actor_location else None,
                    event.target_id,
                    event.target_name,
                    event.target_type,
                    event.target_path,
                    event.internet_message_id,
                    event.email_subject,
                    event.source_folder,
                    event.destination_folder,
                    event.operation,
                    event.result_status,
                    event.client_process_name,
                    event.client_version,
                    event.session_id,
                    event.mailbox_guid,
                    event.organization_name,
                    event.cross_mailbox_operation,
                    event.action or 'Unknown',
                    event.action_result,
                    event.action_reason,
                    compliance_tags,
                    legal_hold_relevant,
                    retention_relevant,
                    security_relevant,
                    json.dumps(event.raw_data) if event.raw_data else {},
                    json.dumps(processed_data),
                    json.dumps(ai_metadata),
                    ProcessingStatus.PROCESSED.value,
                    ai_tags,
                    event.event_timestamp.date()
                ])
        # Insert in batches
        inserted = 0
        for i in range(0, len(param_batches), batch_size):
            batch = param_batches[i:i+batch_size]
            max_retries = 3
            retry_count = 0
            batch_success = False
            
            while retry_count < max_retries:
                try:
                    await self.db_handler.executemany(query, batch)
                    inserted += len(batch)
                    logger.debug(f"Successfully inserted batch {i//batch_size + 1} with {len(batch)} records")
                    batch_success = True
                    break  # Success, exit retry loop
                except asyncio.TimeoutError as e:
                    retry_count += 1
                    logger.warning(f"Timeout on batch {i//batch_size + 1}, attempt {retry_count}/{max_retries}: {e}")
                    if retry_count < max_retries:
                        await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                    else:
                        logger.error(f"Failed to insert batch {i//batch_size + 1} after {max_retries} attempts, falling back to single-record inserts")
                except Exception as e:
                    logger.error(f"Batch insert failed: {e}", exc_info=True)
                    break  # Don't retry on non-timeout errors
            
            # Fallback to single-record inserts if batch failed
            if not batch_success:
                logger.info(f"Falling back to single-record inserts for batch {i//batch_size + 1}")
                single_inserted = 0
                for j, record_params in enumerate(batch):
                    try:
                        # Use the existing single-record insert method
                        single_query = """
                            INSERT INTO public."ExternalAuditLogs" (
                                "SourceSystem", "SourceInstance", "SourceVersion", "EventId", "EventType", 
                                "EventCategory", "EventSubcategory", "EventTimestamp", "IngestionTimestamp",
                                "ActorId", "ActorName", "ActorType", "ActorIpAddress", "ActorLocation",
                                "TargetId", "TargetName", "TargetType", "TargetPath", "InternetMessageId", 
                                "EmailSubject", "SourceFolder", "DestinationFolder", "Operation", "ResultStatus",
                                "ClientProcessName", "ClientVersion", "SessionId", "MailboxGuid", "OrganizationName",
                                "CrossMailboxOperation", "Action", "ActionResult", 
                                "ActionReason", "ComplianceTags", "LegalHoldRelevant", "RetentionRelevant", 
                                "SecurityRelevant", "RawData", "ProcessedData", "Metadata", "ProcessingStatus",
                                "Tags", "PartitionDate"
                            ) VALUES (
                                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, 
                                $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, 
                                $33, $34, $35, $36, $37, $38, $39, $40, $41, $42, $43
                            )
                        """
                        await self.db_handler.execute(single_query, *record_params)
                        single_inserted += 1
                        if (j + 1) % 10 == 0:  # Log progress every 10 records
                            logger.debug(f"Single-record insert progress: {j + 1}/{len(batch)} records")
                    except Exception as e:
                        logger.error(f"Failed to insert single record {j + 1} in batch {i//batch_size + 1}: {e}")
                        # Continue with next record instead of failing entire batch
                
                inserted += single_inserted
                logger.info(f"Single-record fallback completed: {single_inserted}/{len(batch)} records inserted for batch {i//batch_size + 1}")
        
        return inserted
    
    async def store_audit_logs_minimal(self, events: List[AuditLogEvent], batch_size: int = 10):
        """Minimal bulk insert - capture all available fields without expensive processing"""
        if not events:
            return 0
        
        logger.info(f"Starting minimal import of {len(events)} events with batch size {batch_size}")
        
        # Enhanced insert query - capture all available fields without constraints
        query = """
            INSERT INTO public."ExternalAuditLogs" (
                "SourceSystem", "SourceInstance", "SourceVersion", "EventId", "EventType", 
                "EventCategory", "EventSubcategory", "EventTimestamp", "IngestionTimestamp",
                "ActorId", "ActorName", "ActorType", "ActorIpAddress", "ActorLocation",
                "TargetId", "TargetName", "TargetType", "TargetPath", "InternetMessageId", 
                "EmailSubject", "SourceFolder", "DestinationFolder", "Operation", "ResultStatus",
                "ClientProcessName", "ClientVersion", "SessionId", "MailboxGuid", "OrganizationName",
                "CrossMailboxOperation", "Action", "ActionResult", "ActionReason",
                "RawData", "ProcessedData", "Metadata", "ProcessingStatus", "Tags", "PartitionDate"
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, 
                $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, 
                $33, $34, $35, $36, $37, $38, $39
            )
        """
        
        # Prepare batch parameters - simplified without complex processing
        param_batches = []
        for event in events:
            # Simple categorization based on event type (no database queries)
            event_category = self._simple_categorize_event(event.event_type)
            event_subcategory = self._simple_subcategorize_event(event.event_type)
            
            param_batches.append([
                event.source_system,
                event.source_instance,
                event.source_version,
                event.event_id,
                event.event_type,
                event_category,
                event_subcategory,
                event.event_timestamp,
                datetime.now(timezone.utc),
                event.actor_id,
                event.actor_name,
                event.actor_type,
                event.actor_ip_address,
                json.dumps(event.actor_location) if event.actor_location else None,
                event.target_id,
                event.target_name,
                event.target_type,
                event.target_path,
                event.internet_message_id,
                event.email_subject,
                event.source_folder,
                event.destination_folder,
                event.operation,
                event.result_status,
                event.client_process_name,
                event.client_version,
                event.session_id,
                event.mailbox_guid,
                event.organization_name,
                event.cross_mailbox_operation,
                event.action or 'Unknown',
                event.action_result,
                event.action_reason,
                json.dumps(event.raw_data) if event.raw_data else {},
                json.dumps(event.processed_data) if event.processed_data else {},
                json.dumps(event.metadata) if event.metadata else {},
                ProcessingStatus.PENDING.value,  # Mark as pending for later processing
                [],  # Tags - will be updated later
                event.event_timestamp.date()
            ])
        
        # Insert in batches
        inserted = 0
        total_batches = (len(param_batches) + batch_size - 1) // batch_size
        logger.info(f"Processing {total_batches} batches of up to {batch_size} records each")
        
        for i in range(0, len(param_batches), batch_size):
            batch = param_batches[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            try:
                logger.debug(f"Processing batch {batch_num}/{total_batches} with {len(batch)} records")
                await self.db_handler.executemany(query, batch)
                inserted += len(batch)
                logger.info(f"Successfully inserted batch {batch_num}/{total_batches} with {len(batch)} records")
            except Exception as e:
                logger.error(f"Batch {batch_num}/{total_batches} failed: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                # Try single records as fallback
                single_inserted = 0
                for j, record_params in enumerate(batch):
                    try:
                        await self.db_handler.execute(query, *record_params)
                        single_inserted += 1
                        if single_inserted % 10 == 0:  # Log progress every 10 records
                            logger.info(f"Single record fallback: {single_inserted}/{len(batch)} records inserted")
                    except Exception as single_error:
                        logger.error(f"Failed to insert single record {j + 1} in batch {batch_num}: {single_error}")
                inserted += single_inserted
                logger.info(f"Batch {batch_num} fallback completed: {single_inserted}/{len(batch)} records inserted")
        
        logger.info(f"Minimal import completed: {inserted}/{len(events)} records inserted")
        return inserted
    
    async def store_audit_logs_single(self, events: List[AuditLogEvent]):
        """Single-record insert - most reliable approach for large datasets"""
        if not events:
            return 0
        
        logger.info(f"Starting single-record import of {len(events)} events")
        
        # Simplified insert query - only essential fields
        query = """
            INSERT INTO public."ExternalAuditLogs" (
                "SourceSystem", "EventId", "EventType", "EventTimestamp", "IngestionTimestamp",
                "ActorId", "ActorName", "ActorType", "ActorIpAddress",
                "TargetId", "TargetName", "TargetType", "TargetPath",
                "Action", "ActionResult", "ActionReason",
                "RawData", "ProcessedData", "Metadata", "ProcessingStatus", "Tags", "PartitionDate"
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22
            )
        """
        
        inserted = 0
        failed = 0
        
        for i, event in enumerate(events):
            try:
                # Simple categorization
                event_category = self._simple_categorize_event(event.event_type)
                event_subcategory = self._simple_subcategorize_event(event.event_type)
                
                # Prepare parameters - no truncation, preserve all data
                params = [
                    event.source_system,                            # SourceSystem VARCHAR(100)
                    event.event_id,                                 # EventId TEXT (unlimited)
                    event.event_type,                               # EventType VARCHAR(100)
                    event.event_timestamp,
                    datetime.now(timezone.utc),
                    event.actor_id,                                 # ActorId TEXT (unlimited)
                    event.actor_name,                               # ActorName TEXT (unlimited)
                    event.actor_type,                               # ActorType VARCHAR(50)
                    event.actor_ip_address,                         # ActorIpAddress INET
                    event.target_id,                                # TargetId TEXT (unlimited)
                    event.target_name,                              # TargetName TEXT (unlimited)
                    event.target_type,                              # TargetType VARCHAR(100)
                    event.target_path,                              # TargetPath TEXT (no limit)
                    event.action or 'Unknown',                      # Action VARCHAR(100)
                    event.action_result,                            # ActionResult VARCHAR(50)
                    event.action_reason,                            # ActionReason TEXT (no limit)
                    json.dumps(event.raw_data) if event.raw_data else "{}",
                    json.dumps(event.processed_data) if event.processed_data else None,
                    json.dumps(event.metadata) if event.metadata else None,
                    ProcessingStatus.PENDING.value,
                    [],
                    event.event_timestamp.date() if event.event_timestamp else None
                ]
                
                await self.db_handler.execute(query, *params)
                inserted += 1
                
                # Log progress every 100 records
                if (i + 1) % 100 == 0:
                    logger.info(f"Progress: {i + 1}/{len(events)} records inserted ({inserted} successful, {failed} failed)")
                    
            except Exception as e:
                failed += 1
                logger.error(f"Failed to insert record {i + 1}: {str(e)}")
                if failed % 10 == 0:  # Log failures every 10
                    logger.error(f"Failure count: {failed} out of {i + 1} processed")
        
        logger.info(f"Single-record import completed: {inserted} successful, {failed} failed out of {len(events)} total")
        return inserted
    
    async def store_audit_logs_test(self, events: List[AuditLogEvent]):
        """Comprehensive test insert - map all available fields from AuditLogEvent"""
        if not events:
            return 0
        
        logger.info(f"Starting comprehensive test import of {len(events)} events")
        
        # Comprehensive insert query - map all available fields
        query = """
            INSERT INTO public."ExternalAuditLogs" (
                "SourceSystem", "EventId", "EventType", "EventTimestamp", "IngestionTimestamp",
                "ActorId", "ActorName", "ActorType", "ActorIpAddress",
                "TargetId", "TargetName", "TargetType", "TargetPath",
                "Action", "ActionResult", "ActionReason",
                "InternetMessageId", "EmailSubject", "SourceFolder", "DestinationFolder",
                "Operation", "ResultStatus", "ClientProcessName", "ClientVersion",
                "SessionId", "MailboxGuid", "OrganizationName", "CrossMailboxOperation",
                "RawData", "ProcessedData", "Metadata", "ProcessingStatus", "Tags", "PartitionDate"
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35
            )
        """
        
        inserted = 0
        failed = 0
        
        for i, event in enumerate(events):
            try:
                # Map all available fields from AuditLogEvent - no truncation
                params = [
                    event.source_system,
                    event.event_id,
                    event.event_type,
                    event.event_timestamp,
                    datetime.now(timezone.utc),
                    event.actor_id,
                    event.actor_name,
                    event.actor_type,
                    event.actor_ip_address,
                    event.target_id,
                    event.target_name,
                    event.target_type,
                    event.target_path,
                    event.action,
                    event.action_result,
                    event.action_reason,
                    event.internet_message_id,
                    event.email_subject,
                    event.source_folder,
                    event.destination_folder,
                    event.operation,
                    event.result_status,
                    event.client_process_name,
                    event.client_version,
                    event.session_id,
                    event.mailbox_guid,
                    event.organization_name,
                    event.cross_mailbox_operation,
                    json.dumps(event.raw_data) if event.raw_data else "{}",
                    json.dumps(event.processed_data) if event.processed_data else None,
                    json.dumps(event.metadata) if event.metadata else None,
                    "processed",  # ProcessingStatus
                    [],  # Tags - empty array for now
                    event.event_timestamp.date() if event.event_timestamp else None  # PartitionDate
                ]
                
                await self.db_handler.execute(query, *params)
                inserted += 1
                
                # Log progress every 50 records
                if (i + 1) % 50 == 0:
                    logger.info(f"Test progress: {i + 1}/{len(events)} records inserted ({inserted} successful, {failed} failed)")
                    
            except Exception as e:
                failed += 1
                logger.error(f"Test failed to insert record {i + 1}: {str(e)}")
                logger.error(f"Error type: {type(e).__name__}")
                if failed >= 5:  # Stop after 5 failures to avoid spam
                    logger.error("Stopping test import after 5 failures")
                    break
        
        logger.info(f"Test import completed: {inserted} successful, {failed} failed out of {len(events)} total")
        return inserted
    
    def _simple_categorize_event(self, event_type: str) -> str:
        """Simple event categorization without database queries"""
        event_type_lower = event_type.lower()
        
        # Microsoft Purview categories
        if any(keyword in event_type_lower for keyword in ['mail', 'email', 'message']):
            return 'email'
        elif any(keyword in event_type_lower for keyword in ['file', 'document', 'attachment']):
            return 'file'
        elif any(keyword in event_type_lower for keyword in ['folder', 'directory']):
            return 'folder'
        elif any(keyword in event_type_lower for keyword in ['permission', 'access', 'share']):
            return 'access'
        elif any(keyword in event_type_lower for keyword in ['delete', 'remove']):
            return 'deletion'
        elif any(keyword in event_type_lower for keyword in ['create', 'add', 'new']):
            return 'creation'
        elif any(keyword in event_type_lower for keyword in ['modify', 'update', 'change']):
            return 'modification'
        elif any(keyword in event_type_lower for keyword in ['login', 'auth', 'sign']):
            return 'authentication'
        else:
            return 'other'
    
    def _simple_subcategorize_event(self, event_type: str) -> str:
        """Simple event subcategorization without database queries"""
        event_type_lower = event_type.lower()
        
        # Microsoft Purview subcategories
        if 'move' in event_type_lower:
            return 'move'
        elif 'copy' in event_type_lower:
            return 'copy'
        elif 'send' in event_type_lower:
            return 'send'
        elif 'receive' in event_type_lower:
            return 'receive'
        elif 'delete' in event_type_lower:
            return 'delete'
        elif 'create' in event_type_lower:
            return 'create'
        elif 'modify' in event_type_lower:
            return 'modify'
        elif 'access' in event_type_lower:
            return 'access'
        else:
            return 'other'
    

    
    async def collect_logs(self, source_system: str, job_type: str = 'scheduled') -> str:
        """Collect logs from a specific source system, using batch insert for scalability"""
        job_id = str(uuid.uuid4())
        await self._create_collection_job(job_id, source_system, job_type)
        try:
            # Run database health check first
            logger.info("Running database health check before import...")
            health_ok = await self.check_database_health()
            if not health_ok:
                logger.error("Database health check failed - aborting import")
                raise Exception("Database health check failed")
            
            source_config = await self.get_source(source_system)
            if not source_config:
                raise ValueError(f"Source system {source_system} not found")
            collector_class = self.collectors.get(source_system)
            if not collector_class:
                raise ValueError(f"No collector available for source system {source_system}")
            collector = collector_class(source_config)
            events = await collector.collect_logs()
            processed_count = 0
            failed_count = 0
            skipped_count = 0
            BATCH_SIZE = 25  # Reduced from 200 to prevent timeouts
            # Convert dicts to AuditLogEvent objects if needed
            event_objs = []
            for event_data in events:
                if isinstance(event_data, dict):
                    event = AuditLogEvent(
                        source_system=event_data.get('source_system', source_system),
                        event_id=event_data.get('event_id'),
                        event_type=event_data.get('event_type'),
                        event_timestamp=event_data.get('event_timestamp', datetime.now(timezone.utc)),
                        source_instance=event_data.get('source_instance'),
                        source_version=event_data.get('source_version'),
                        actor_id=event_data.get('actor_id'),
                        actor_name=event_data.get('actor_name'),
                        actor_type=event_data.get('actor_type'),
                        actor_ip_address=event_data.get('ip_address'),
                        actor_location=event_data.get('location'),
                        target_id=event_data.get('target_id'),
                        target_name=event_data.get('target_name'),
                        target_type=event_data.get('target_type'),
                        target_path=event_data.get('target_path'),
                        action=event_data.get('action'),
                        action_result=event_data.get('action_result'),
                        action_reason=event_data.get('action_reason'),
                        raw_data=event_data.get('raw_data'),
                        processed_data=event_data.get('processed_data'),
                        metadata=event_data.get('metadata'),
                        internet_message_id=event_data.get('internet_message_id'),
                        email_subject=event_data.get('email_subject'),
                        source_folder=event_data.get('source_folder'),
                        destination_folder=event_data.get('destination_folder'),
                        operation=event_data.get('operation'),
                        result_status=event_data.get('result_status'),
                        client_process_name=event_data.get('client_process_name'),
                        client_version=event_data.get('client_version'),
                        session_id=event_data.get('session_id'),
                        mailbox_guid=event_data.get('mailbox_guid'),
                        organization_name=event_data.get('organization_name'),
                        cross_mailbox_operation=event_data.get('cross_mailbox_operation')
                    )
                    event_objs.append(event)
                else:
                    event_objs.append(event_data)
            # Use comprehensive single-record insert to populate all fields
            inserted = await self.store_audit_logs_single(event_objs)
            processed_count = inserted
            # Update job status
            await self._update_collection_job(job_id, JobStatus.COMPLETED.value, {
                'records_processed': processed_count,
                'records_failed': failed_count,
                'records_skipped': skipped_count
            })
            await self.update_source(source_system, {
                'LastCollectionTime': datetime.now(timezone.utc)
            })
            logger.info(f"Completed log collection for {source_system}: {processed_count} processed, {failed_count} failed")
            return job_id
        except Exception as e:
            logger.error(f"Failed to collect logs from {source_system}: {e}", exc_info=True)
            await self._update_collection_job(job_id, JobStatus.FAILED.value, {
                'error_details': str(e)
            })
            raise
    
    async def _create_collection_job(self, job_id: str, source_system: str, job_type: str):
        """Create a collection job record"""
        query = """
            INSERT INTO public."AuditLogCollectionJobs" (
                "SourceSystem", "JobId", "JobType", "Status", "StartTime"
            ) VALUES ($1, $2, $3, $4, $5)
        """
        await self.db_handler.execute(
            query,
            source_system,
            job_id,
            job_type,
            JobStatus.RUNNING.value,
            datetime.now(timezone.utc)
        )
    
    async def _update_collection_job(self, job_id: str, status: str, details: Dict[str, Any] = None):
        """Update collection job status"""
        query = """
            UPDATE public."AuditLogCollectionJobs"
            SET "Status" = $1, "EndTime" = $2, "RecordsProcessed" = $3,
                "RecordsFailed" = $4, "RecordsSkipped" = $5, "ErrorDetails" = $6
            WHERE "JobId" = $7
        """
        await self.db_handler.execute(
            query,
            status,
            datetime.now(timezone.utc),
            details.get('records_processed', 0) if details else 0,
            details.get('records_failed', 0) if details else 0,
            details.get('records_skipped', 0) if details else 0,
            json.dumps(details.get('error_details')) if details and 'error_details' in details else None,
            job_id
        )
    
    async def get_collection_jobs(self, source_system: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get collection job history"""
        if source_system:
            query = """
                SELECT * FROM public."AuditLogCollectionJobs"
                WHERE "SourceSystem" = $1
                ORDER BY "StartTime" DESC
                LIMIT $2
            """
            jobs = await self.db_handler.fetch_all(query, source_system, limit)
        else:
            query = """
                SELECT * FROM public."AuditLogCollectionJobs"
                ORDER BY "StartTime" DESC
                LIMIT $1
            """
            jobs = await self.db_handler.fetch_all(query, limit)
        
        return [dict(job) for job in jobs]
    
    async def search_audit_logs(self, 
                               source_system: Optional[str] = None,
                               event_type: Optional[str] = None,
                               actor_id: Optional[str] = None,
                               target_id: Optional[str] = None,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               search_term: Optional[str] = None,
                               compliance_tags: Optional[List[str]] = None,
                               security_relevant: Optional[bool] = None,
                               legal_hold_relevant: Optional[bool] = None,
                               retention_relevant: Optional[bool] = None,
                               tags: Optional[List[str]] = None,
                               risk_level: Optional[str] = None,
                               anomaly_score_min: Optional[float] = None,
                               business_hours_only: Optional[bool] = None,
                               page: int = 1,
                               page_size: int = 50,
                               sort_by: str = "EventTimestamp",
                               sort_order: str = "DESC") -> Tuple[List[Dict[str, Any]], int]:
        """Advanced search audit logs with AI-optimized filters and sorting"""
        
        where_clauses = []
        params = []
        param_idx = 1
        
        # Basic filters
        if source_system:
            where_clauses.append(f'"SourceSystem" = ${param_idx}')
            params.append(source_system)
            param_idx += 1
        
        if event_type:
            where_clauses.append(f'"EventType" = ${param_idx}')
            params.append(event_type)
            param_idx += 1
        
        if actor_id:
            where_clauses.append(f'"ActorId" = ${param_idx}')
            params.append(actor_id)
            param_idx += 1
        
        if target_id:
            where_clauses.append(f'"TargetId" = ${param_idx}')
            params.append(target_id)
            param_idx += 1
        
        # Date range filters
        if start_date:
            where_clauses.append(f'"EventTimestamp" >= ${param_idx}')
            params.append(start_date)
            param_idx += 1
        
        if end_date:
            where_clauses.append(f'"EventTimestamp" <= ${param_idx}')
            params.append(end_date)
            param_idx += 1
        
        # AI-optimized search
        if search_term:
            # Enhanced search with multiple vectors
            search_clauses = [
                f'"SearchVector" @@ plainto_tsquery(${param_idx})',
                f'"ActorName" ILIKE ${param_idx + 1}',
                f'"TargetName" ILIKE ${param_idx + 1}',
                f'"Action" ILIKE ${param_idx + 1}'
            ]
            where_clauses.append(f"({' OR '.join(search_clauses)})")
            params.extend([search_term, f'%{search_term}%'])
            param_idx += 2
        
        # Compliance and security filters
        if compliance_tags:
            where_clauses.append(f'"ComplianceTags" && ${param_idx}')
            params.append(compliance_tags)
            param_idx += 1
        
        if security_relevant is not None:
            where_clauses.append(f'"SecurityRelevant" = ${param_idx}')
            params.append(security_relevant)
            param_idx += 1
        
        if legal_hold_relevant is not None:
            where_clauses.append(f'"LegalHoldRelevant" = ${param_idx}')
            params.append(legal_hold_relevant)
            param_idx += 1
        
        if retention_relevant is not None:
            where_clauses.append(f'"RetentionRelevant" = ${param_idx}')
            params.append(retention_relevant)
            param_idx += 1
        
        # Tag-based filtering
        if tags:
            where_clauses.append(f'"Tags" && ${param_idx}')
            params.append(tags)
            param_idx += 1
        
        # AI-enhanced filters
        if risk_level:
            where_clauses.append(f'"Metadata"->\'security_context\'->\'risk_level\' = ${param_idx}')
            params.append(risk_level)
            param_idx += 1
        
        if anomaly_score_min is not None:
            where_clauses.append(f'CAST("Metadata"->\'security_context\'->\'anomaly_score\' AS FLOAT) >= ${param_idx}')
            params.append(anomaly_score_min)
            param_idx += 1
        
        if business_hours_only is not None:
            if business_hours_only:
                where_clauses.append(f'EXTRACT(HOUR FROM "EventTimestamp") BETWEEN 9 AND 17')
            else:
                where_clauses.append(f'EXTRACT(HOUR FROM "EventTimestamp") NOT BETWEEN 9 AND 17')
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Validate sort parameters
        valid_sort_fields = [
            "EventTimestamp", "IngestionTimestamp", "ActorName", "TargetName", 
            "EventType", "Action", "SecurityRelevant", "LegalHoldRelevant"
        ]
        if sort_by not in valid_sort_fields:
            sort_by = "EventTimestamp"
        
        if sort_order.upper() not in ["ASC", "DESC"]:
            sort_order = "DESC"
        
        # Count query
        count_query = f'SELECT COUNT(*) FROM public."ExternalAuditLogs" {where_sql}'
        total_count = await self.db_handler.fetchval(count_query, *params)
        
        # Data query with enhanced sorting
        offset = (page - 1) * page_size
        data_query = f'''
            SELECT 
                *,
                -- AI-enhanced relevance score
                CASE 
                    WHEN "SecurityRelevant" = TRUE THEN 100
                    WHEN "LegalHoldRelevant" = TRUE THEN 80
                    WHEN "RetentionRelevant" = TRUE THEN 60
                    ELSE 40
                END + 
                CASE 
                    WHEN "ProcessingStatus" = 'processed' THEN 10
                    ELSE 0
                END as relevance_score
            FROM public."ExternalAuditLogs"
            {where_sql}
            ORDER BY relevance_score DESC, "{sort_by}" {sort_order}
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        '''
        params.extend([page_size, offset])
        
        logs = await self.db_handler.fetch_all(data_query, *params)
        
        # Convert logs to dictionaries and handle IP address serialization
        serialized_logs = []
        for log in logs:
            log_dict = dict(log)
            
            # Convert IP address objects to strings for serialization
            if log_dict.get('ActorIpAddress') is not None:
                if hasattr(log_dict['ActorIpAddress'], 'exploded'):
                    # It's an ipaddress.IPv4Address or ipaddress.IPv6Address object
                    log_dict['ActorIpAddress'] = log_dict['ActorIpAddress'].exploded
                elif isinstance(log_dict['ActorIpAddress'], str):
                    # Already a string, keep as is
                    pass
                else:
                    # Convert to string representation
                    log_dict['ActorIpAddress'] = str(log_dict['ActorIpAddress'])
            
            serialized_logs.append(log_dict)
        
        return serialized_logs, total_count
    
    async def get_audit_log_stats(self, source_system: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive audit log statistics with AI insights"""
        since_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Build where clause and parameters
        where_conditions = ['"EventTimestamp" >= $1']
        params = [since_date]
        param_idx = 1
        
        if source_system:
            param_idx += 1
            where_conditions.append(f'"SourceSystem" = ${param_idx}')
            params.append(source_system)
        
        where_clause = ' AND '.join(where_conditions)
        
        # Basic statistics
        total_query = f'SELECT COUNT(*) FROM public."ExternalAuditLogs" WHERE {where_clause}'
        total_events = await self.db_handler.fetchval(total_query, *params)
        
        # Events by source system
        source_query = f'''
            SELECT "SourceSystem", COUNT(*) as count
            FROM public."ExternalAuditLogs"
            WHERE {where_clause}
            GROUP BY "SourceSystem"
            ORDER BY count DESC
        '''
        source_stats = await self.db_handler.fetch_all(source_query, *params)
        
        # Events by type
        type_query = f'''
            SELECT "EventType", COUNT(*) as count
            FROM public."ExternalAuditLogs"
            WHERE {where_clause}
            GROUP BY "EventType"
            ORDER BY count DESC
            LIMIT 10
        '''
        type_stats = await self.db_handler.fetch_all(type_query, *params)
        
        # Security and compliance statistics
        security_query = f'''
            SELECT COUNT(*) FROM public."ExternalAuditLogs"
            WHERE {where_clause} AND "SecurityRelevant" = TRUE
        '''
        security_events = await self.db_handler.fetchval(security_query, *params)
        
        legal_hold_query = f'''
            SELECT COUNT(*) FROM public."ExternalAuditLogs"
            WHERE {where_clause} AND "LegalHoldRelevant" = TRUE
        '''
        legal_hold_events = await self.db_handler.fetchval(legal_hold_query, *params)
        
        retention_query = f'''
            SELECT COUNT(*) FROM public."ExternalAuditLogs"
            WHERE {where_clause} AND "RetentionRelevant" = TRUE
        '''
        retention_events = await self.db_handler.fetchval(retention_query, *params)
        
        # AI-enhanced analytics
        ai_insights = await self._get_ai_insights(where_clause, params)
        
        # Temporal patterns
        temporal_patterns = await self._get_temporal_patterns(where_clause, params)
        
        # Risk analysis
        risk_analysis = await self._get_risk_analysis(where_clause, params)
        
        return {
            'total_events': total_events,
            'source_systems': [dict(stat) for stat in source_stats],
            'event_types': [dict(stat) for stat in type_stats],
            'security_events': security_events,
            'legal_hold_events': legal_hold_events,
            'retention_events': retention_events,
            'period_days': days,
            'ai_insights': ai_insights,
            'temporal_patterns': temporal_patterns,
            'risk_analysis': risk_analysis
        }
    
    async def _get_ai_insights(self, where_clause: str, params: List[Any]) -> Dict[str, Any]:
        """Get AI-powered insights from audit data"""
        insights = {}
        
        # Data quality insights
        quality_query = f'''
            SELECT 
                AVG(CAST("Metadata"->>'data_quality_score' AS FLOAT)) as avg_quality,
                COUNT(*) FILTER (WHERE CAST("Metadata"->>'data_quality_score' AS FLOAT) > 0.8) as high_quality_count,
                COUNT(*) FILTER (WHERE CAST("Metadata"->>'data_quality_score' AS FLOAT) < 0.5) as low_quality_count
            FROM public."ExternalAuditLogs"
            WHERE {where_clause}
        '''
        quality_stats = await self.db_handler.fetch_one(quality_query, *params)
        insights['data_quality'] = dict(quality_stats) if quality_stats else {}
        
        # Anomaly detection
        anomaly_query = f'''
            SELECT 
                COUNT(*) FILTER (WHERE CAST("Metadata"->'security_context'->>'anomaly_score' AS FLOAT) > 0.7) as high_anomaly_count,
                AVG(CAST("Metadata"->'security_context'->>'anomaly_score' AS FLOAT)) as avg_anomaly_score
            FROM public."ExternalAuditLogs"
            WHERE {where_clause}
        '''
        anomaly_stats = await self.db_handler.fetch_one(anomaly_query, *params)
        insights['anomaly_detection'] = dict(anomaly_stats) if anomaly_stats else {}
        
        # Compliance insights
        compliance_query = f'''
            SELECT 
                COUNT(*) FILTER (WHERE "ComplianceTags" && ARRAY['gdpr']) as gdpr_events,
                COUNT(*) FILTER (WHERE "ComplianceTags" && ARRAY['sox']) as sox_events,
                COUNT(*) FILTER (WHERE "ComplianceTags" && ARRAY['hipaa']) as hipaa_events
            FROM public."ExternalAuditLogs"
            WHERE {where_clause}
        '''
        compliance_stats = await self.db_handler.fetch_one(compliance_query, *params)
        insights['compliance'] = dict(compliance_stats) if compliance_stats else {}
        
        return insights
    
    async def _get_temporal_patterns(self, where_clause: str, params: List[Any]) -> Dict[str, Any]:
        """Analyze temporal patterns in audit data"""
        patterns = {}
        
        # Hourly distribution
        hourly_query = f'''
            SELECT 
                EXTRACT(HOUR FROM "EventTimestamp") as hour,
                COUNT(*) as count
            FROM public."ExternalAuditLogs"
            WHERE {where_clause}
            GROUP BY EXTRACT(HOUR FROM "EventTimestamp")
            ORDER BY hour
        '''
        hourly_stats = await self.db_handler.fetch_all(hourly_query, *params)
        patterns['hourly_distribution'] = [dict(stat) for stat in hourly_stats]
        
        # Day of week distribution
        dow_query = f'''
            SELECT 
                EXTRACT(DOW FROM "EventTimestamp") as day_of_week,
                COUNT(*) as count
            FROM public."ExternalAuditLogs"
            WHERE {where_clause}
            GROUP BY EXTRACT(DOW FROM "EventTimestamp")
            ORDER BY day_of_week
        '''
        dow_stats = await self.db_handler.fetch_all(dow_query, *params)
        patterns['day_of_week_distribution'] = [dict(stat) for stat in dow_stats]
        
        # Business vs non-business hours
        business_query = f'''
            SELECT 
                CASE 
                    WHEN EXTRACT(HOUR FROM "EventTimestamp") BETWEEN 9 AND 17 THEN 'business_hours'
                    ELSE 'non_business_hours'
                END as time_period,
                COUNT(*) as count
            FROM public."ExternalAuditLogs"
            WHERE {where_clause}
            GROUP BY time_period
        '''
        business_stats = await self.db_handler.fetch_all(business_query, *params)
        patterns['business_hours_analysis'] = [dict(stat) for stat in business_stats]
        
        return patterns
    
    async def _get_risk_analysis(self, where_clause: str, params: List[Any]) -> Dict[str, Any]:
        """Analyze security and compliance risks"""
        risk_analysis = {}
        
        # Risk level distribution
        risk_query = f'''
            SELECT 
                "Metadata"->'security_context'->>'risk_level' as risk_level,
                COUNT(*) as count
            FROM public."ExternalAuditLogs"
            WHERE {where_clause}
            GROUP BY "Metadata"->'security_context'->>'risk_level'
            ORDER BY count DESC
        '''
        risk_stats = await self.db_handler.fetch_all(risk_query, *params)
        risk_analysis['risk_levels'] = [dict(stat) for stat in risk_stats]
        
        return risk_analysis
    
    async def cleanup_old_logs(self) -> int:
        """Clean up old audit logs based on retention policies"""
        query = 'SELECT cleanup_old_audit_logs()'
        deleted_count = await self.db_handler.fetchval(query)
        logger.info(f"Cleaned up {deleted_count} old audit log records")
        return deleted_count
    
    async def schedule_next_collections(self):
        """Schedule next collection times for all active sources"""
        sources = await self.get_sources(active_only=True)
        
        for source in sources:
            schedule_config = source.get('Schedule', {})
            if not schedule_config:
                continue
            
            schedule_type = schedule_config.get('type')
            if schedule_type == 'cron':
                cron_expr = schedule_config.get('expression')
                if cron_expr:
                    try:
                        cron = croniter(cron_expr, datetime.now(timezone.utc))
                        next_time = cron.get_next(datetime)
                        
                        await self.update_source(source['SourceSystem'], {
                            'NextCollectionTime': next_time
                        })
                    except Exception as e:
                        logger.error(f"Failed to calculate next collection time for {source['SourceSystem']}: {e}")
            
            elif schedule_type == 'interval':
                minutes = schedule_config.get('minutes', 60)
                next_time = datetime.now(timezone.utc) + timedelta(minutes=minutes)
                
                await self.update_source(source['SourceSystem'], {
                    'NextCollectionTime': next_time
                })
    
    def _create_ai_optimized_metadata(self, event: AuditLogEvent, mapping: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Create AI-optimized metadata for better discovery and analysis"""
        metadata = {
            'ai_structured': True,
            'processing_version': '3.0',
            'event_complexity': self._assess_event_complexity(event),
            'data_quality_score': self._assess_data_quality(event),
            'semantic_context': self._extract_semantic_context(event, mapping),
            'temporal_context': {
                'hour_of_day': event.event_timestamp.hour if event.event_timestamp else None,
                'day_of_week': event.event_timestamp.weekday() if event.event_timestamp else None,
                'is_business_hours': self._is_business_hours(event.event_timestamp) if event.event_timestamp else False,
                'timezone': str(event.event_timestamp.tzinfo) if event.event_timestamp else None
            },
            'geographic_context': self._extract_geographic_context(event),
            'security_context': {
                'risk_level': self._assess_security_risk(event, mapping),
                'anomaly_score': self._calculate_anomaly_score(event),
                'threat_indicators': self._extract_threat_indicators(event)
            },
            'compliance_context': {
                'regulatory_frameworks': self._identify_regulatory_frameworks(event, mapping),
                'data_classification': self._classify_data_sensitivity(event),
                'retention_requirements': self._determine_retention_requirements(event, mapping)
            },
            # Enhanced relationship context for knowledge graph construction
            'relationship_context': self._extract_relationship_context(event),
            'session_context': self._extract_session_context(event),
            'resource_context': self._extract_resource_context(event),
            'device_context': self._extract_device_context(event),
            'cross_service_context': self._extract_cross_service_context(event)
        }
        
        # Merge with existing metadata
        if event.metadata:
            metadata.update(event.metadata)
        
        return metadata
    
    def _create_ai_optimized_tags(self, event: AuditLogEvent, mapping: Optional[Dict[str, Any]]) -> List[str]:
        """Create AI-optimized tags for enhanced search and discovery"""
        tags = []
        
        # System tags
        tags.extend([
            f"source:{event.source_system}",
            f"event_type:{event.event_type}",
            f"actor_type:{event.actor_type}" if event.actor_type else "actor_type:unknown",
            f"target_type:{event.target_type}" if event.target_type else "target_type:unknown"
        ])
        
        # Action tags
        if event.action:
            tags.append(f"action:{event.action}")
        if event.action_result:
            tags.append(f"result:{event.action_result}")
        
        # Security tags
        if mapping and mapping.get('is_security_relevant'):
            tags.extend(['security:relevant', 'priority:high'])
        if event.actor_ip_address:
            tags.append(f"ip:{event.actor_ip_address}")
        
        # Compliance tags
        if mapping and mapping.get('is_legal_hold_relevant'):
            tags.extend(['compliance:legal_hold', 'priority:high'])
        if mapping and mapping.get('is_retention_relevant'):
            tags.extend(['compliance:retention', 'priority:medium'])
        
        # Temporal tags
        tags.extend([
            f"hour:{event.event_timestamp.hour:02d}",
            f"day:{event.event_timestamp.strftime('%A').lower()}",
            f"business_hours:{self._is_business_hours(event.event_timestamp)}"
        ])
        
        # Geographic tags
        if event.actor_location:
            country = event.actor_location.get('country')
            if country:
                tags.append(f"country:{country}")
        
        # Data sensitivity tags
        sensitivity = self._classify_data_sensitivity(event)
        if sensitivity:
            tags.append(f"sensitivity:{sensitivity}")
        
        return list(set(tags))  # Remove duplicates
    
    def _enhance_processed_data(self, processed_data: Optional[Dict[str, Any]], 
                               event: AuditLogEvent, 
                               mapping: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhance processed data for AI consumption"""
        enhanced = processed_data or {}
        
        # Add structured fields for AI analysis
        enhanced.update({
            'ai_enhanced': True,
            'event_summary': self._generate_event_summary(event),
            'actor_profile': self._extract_actor_profile(event),
            'target_profile': self._extract_target_profile(event),
            'action_context': self._extract_action_context(event),
            'risk_indicators': self._extract_risk_indicators(event),
            'compliance_indicators': self._extract_compliance_indicators(event, mapping)
        })
        
        return enhanced
    
    def _assess_event_complexity(self, event: AuditLogEvent) -> str:
        """Assess the complexity of an event for AI processing"""
        complexity_score = 0
        
        if event.actor_location:
            complexity_score += 1
        if event.action_reason:
            complexity_score += 1
        if event.target_path:
            complexity_score += 1
        if event.raw_data and len(event.raw_data) > 10:
            complexity_score += 2
        
        if complexity_score <= 1:
            return 'simple'
        elif complexity_score <= 3:
            return 'moderate'
        else:
            return 'complex'
    
    def _assess_data_quality(self, event: AuditLogEvent) -> float:
        """Assess data quality score (0-1) for AI processing"""
        score = 0.0
        total_fields = 0
        
        # Check required fields
        required_fields = ['event_id', 'event_type', 'event_timestamp']
        for field in required_fields:
            total_fields += 1
            if getattr(event, field):
                score += 1.0
        
        # Check optional but valuable fields
        optional_fields = ['actor_id', 'actor_name', 'target_id', 'target_name', 'action']
        for field in optional_fields:
            total_fields += 1
            if getattr(event, field):
                score += 0.5
        
        return score / total_fields if total_fields > 0 else 0.0
    
    def _extract_semantic_context(self, event: AuditLogEvent, mapping: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract semantic context for AI understanding"""
        context = {
            'event_category': mapping.get('mapped_event_category') if mapping else None,
            'event_subcategory': mapping.get('mapped_event_subcategory') if mapping else None,
            'action_verb': event.action,
            'target_entity': event.target_type,
            'actor_entity': event.actor_type
        }
        
        # Extract context from action reason
        if event.action_reason:
            context['action_motivation'] = event.action_reason
        
        return context
    
    def _is_business_hours(self, timestamp: datetime) -> bool:
        """Check if event occurred during business hours (9 AM - 5 PM)"""
        hour = timestamp.hour
        return 9 <= hour <= 17
    
    def _extract_geographic_context(self, event: AuditLogEvent) -> Dict[str, Any]:
        """Extract geographic context from event"""
        if not event.actor_location or not isinstance(event.actor_location, dict):
            return {}
        
        return {
            'country': event.actor_location.get('country'),
            'region': event.actor_location.get('region'),
            'city': event.actor_location.get('city'),
            'coordinates': event.actor_location.get('coordinates')
        }
    
    def _assess_security_risk(self, event: AuditLogEvent, mapping: Optional[Dict[str, Any]]) -> str:
        """Assess security risk level"""
        if mapping and mapping.get('is_security_relevant'):
            return 'high'
        
        # Check for suspicious patterns
        if event.action in ['delete', 'modify', 'access'] and event.actor_type == 'external':
            return 'medium'
        
        return 'low'
    
    def _calculate_anomaly_score(self, event: AuditLogEvent) -> float:
        """Calculate anomaly score (0-1) for the event"""
        # Simple anomaly detection - can be enhanced with ML models
        score = 0.0
        
        # Off-hours activity
        if not self._is_business_hours(event.event_timestamp):
            score += 0.3
        
        # External actor
        if event.actor_type == 'external':
            score += 0.2
        
        # Sensitive actions
        if event.action in ['delete', 'export', 'share']:
            score += 0.3
        
        return min(score, 1.0)
    
    def _extract_threat_indicators(self, event: AuditLogEvent) -> List[str]:
        """Extract potential threat indicators"""
        indicators = []
        
        if event.action in ['delete', 'export', 'share']:
            indicators.append('data_exfiltration_risk')
        
        if event.actor_type == 'external':
            indicators.append('external_access')
        
        if not self._is_business_hours(event.event_timestamp):
            indicators.append('off_hours_activity')
        
        return indicators
    
    def _identify_regulatory_frameworks(self, event: AuditLogEvent, mapping: Optional[Dict[str, Any]]) -> List[str]:
        """Identify applicable regulatory frameworks"""
        frameworks = []
        
        if mapping and mapping.get('compliance_tags'):
            for tag in mapping['compliance_tags']:
                if tag == 'gdpr':
                    frameworks.append('GDPR')
                elif tag == 'sox':
                    frameworks.append('SOX')
                elif tag == 'hipaa':
                    frameworks.append('HIPAA')
        
        return frameworks
    
    def _classify_data_sensitivity(self, event: AuditLogEvent) -> Optional[str]:
        """Classify data sensitivity level"""
        if event.target_type in ['email', 'document']:
            # Check for sensitive keywords in target name
            sensitive_keywords = ['password', 'credit', 'ssn', 'social', 'medical', 'health']
            if event.target_name:
                target_lower = event.target_name.lower()
                for keyword in sensitive_keywords:
                    if keyword in target_lower:
                        return 'high'
            return 'medium'
        
        return 'low'
    
    def _determine_retention_requirements(self, event: AuditLogEvent, mapping: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Determine retention requirements for the event"""
        requirements = {
            'retention_period_years': 7,  # Default
            'legal_hold_applicable': mapping.get('is_legal_hold_relevant', False) if mapping else False,
            'regulatory_hold': False
        }
        
        # Adjust based on event type and compliance tags
        if mapping and mapping.get('compliance_tags'):
            if 'gdpr' in mapping['compliance_tags']:
                requirements['retention_period_years'] = 6
            elif 'sox' in mapping['compliance_tags']:
                requirements['retention_period_years'] = 7
                requirements['regulatory_hold'] = True
        
        return requirements
    
    def _generate_event_summary(self, event: AuditLogEvent) -> str:
        """Generate a human-readable event summary"""
        summary_parts = []
        
        if event.actor_name:
            summary_parts.append(f"{event.actor_name}")
        elif event.actor_id:
            summary_parts.append(f"User {event.actor_id}")
        else:
            summary_parts.append("Unknown user")
        
        if event.action:
            summary_parts.append(event.action)
        
        if event.target_name:
            summary_parts.append(event.target_name)
        elif event.target_type:
            summary_parts.append(f"a {event.target_type}")
        
        if event.action_result:
            summary_parts.append(f"({event.action_result})")
        
        return " ".join(summary_parts)
    
    def _extract_actor_profile(self, event: AuditLogEvent) -> Dict[str, Any]:
        """Extract actor profile information"""
        profile = {
            'id': event.actor_id,
            'name': event.actor_name,
            'type': event.actor_type,
            'ip_address': event.actor_ip_address,
            'location': event.actor_location
        }
        
        # Remove None values
        return {k: v for k, v in profile.items() if v is not None}
    
    def _extract_target_profile(self, event: AuditLogEvent) -> Dict[str, Any]:
        """Extract target profile information"""
        profile = {
            'id': event.target_id,
            'name': event.target_name,
            'type': event.target_type,
            'path': event.target_path
        }
        
        # Remove None values
        return {k: v for k, v in profile.items() if v is not None}
    
    def _extract_action_context(self, event: AuditLogEvent) -> Dict[str, Any]:
        """Extract action context information"""
        context = {
            'action': event.action,
            'result': event.action_result,
            'reason': event.action_reason
        }
        
        # Remove None values
        return {k: v for k, v in context.items() if v is not None}
    
    def _extract_risk_indicators(self, event: AuditLogEvent) -> List[str]:
        """Extract risk indicators from the event"""
        indicators = []
        
        if event.action in ['delete', 'export', 'share']:
            indicators.append('data_loss_risk')
        
        if event.actor_type == 'external':
            indicators.append('external_access')
        
        if event.action_result == 'failure':
            indicators.append('failed_action')
        
        return indicators
    
    def _extract_compliance_indicators(self, event: AuditLogEvent, mapping: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract compliance indicators"""
        indicators = {
            'legal_hold_relevant': mapping.get('is_legal_hold_relevant', False) if mapping else False,
            'retention_relevant': mapping.get('is_retention_relevant', False) if mapping else False,
            'security_relevant': mapping.get('is_security_relevant', False) if mapping else False,
            'compliance_tags': mapping.get('compliance_tags', []) if mapping else []
        }
        
        return indicators
    
    async def _store_failed_event(self, event: AuditLogEvent, error_message: str):
        """Store failed event for retry processing"""
        try:
            query = """
                INSERT INTO public."ExternalAuditLogs" (
                    "SourceSystem", "EventId", "EventType", "EventTimestamp", 
                    "RawData", "ProcessingStatus", "ProcessingError", "RetryCount"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """
            
            await self.db_handler.execute(
                query,
                event.source_system,
                event.event_id,
                event.event_type,
                event.event_timestamp,
                json.dumps(event.raw_data) if event.raw_data else {},
                ProcessingStatus.FAILED.value,
                error_message,
                1
            )
            
            logger.warning(f"Stored failed event {event.event_id} for retry")
        except Exception as e:
            logger.error(f"Failed to store failed event {event.event_id}: {e}", exc_info=True)

    async def check_database_health(self):
        """Check database health and identify potential issues"""
        logger.info("Starting database health check...")
        
        try:
            # Test 1: Basic connection
            logger.info("Test 1: Testing basic connection...")
            await self.db_handler.connect()
            logger.info("✅ Basic connection successful")
            
            # Test 2: Simple query
            logger.info("Test 2: Testing simple SELECT query...")
            result = await self.db_handler.fetchval("SELECT 1")
            logger.info(f"✅ Simple query successful: {result}")
            
            # Test 3: Check table exists
            logger.info("Test 3: Checking if ExternalAuditLogs table exists...")
            table_check = await self.db_handler.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'ExternalAuditLogs'
                )
            """)
            logger.info(f"✅ Table exists check: {table_check}")
            
            # Test 4: Check table structure
            logger.info("Test 4: Checking table structure...")
            columns = await self.db_handler.fetch_all("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'ExternalAuditLogs'
                ORDER BY ordinal_position
            """)
            logger.info(f"✅ Table has {len(columns)} columns")
            
            # Test 5: Check for locks
            logger.info("Test 5: Checking for table locks...")
            locks = await self.db_handler.fetch_all("""
                SELECT l.pid, l.mode, l.granted, a.query_start, a.state
                FROM pg_locks l
                JOIN pg_stat_activity a ON l.pid = a.pid
                WHERE l.relation = 'public."ExternalAuditLogs"'::regclass
            """)
            logger.info(f"✅ Found {len(locks)} locks on table")
            
            # Additional lock analysis
            if len(locks) > 0:
                logger.warning(f"⚠️ {len(locks)} locks detected - this may be causing timeouts!")
                lock_count = await self.check_and_clear_table_locks()
                if lock_count > 0:
                    logger.error(f"❌ {lock_count} locks are blocking operations - attempting to clear them...")
                    
                    # Try to terminate blocking queries
                    terminated = await self.terminate_blocking_queries()
                    if terminated > 0:
                        logger.info(f"✅ Successfully terminated {terminated} blocking queries")
                        logger.info("Retrying health check after lock clearance...")
                        
                        # Re-check locks after termination
                        await asyncio.sleep(2)
                        remaining_locks = await self.db_handler.fetch_all("""
                            SELECT COUNT(*) as count
                            FROM pg_locks l
                            JOIN pg_stat_activity a ON l.pid = a.pid
                            WHERE l.relation = 'public."ExternalAuditLogs"'::regclass
                            AND EXTRACT(EPOCH FROM (now() - a.query_start)) > 300
                        """)
                        
                        if remaining_locks[0]['count'] == 0:
                            logger.info("✅ All blocking locks cleared - proceeding with import")
                        else:
                            logger.warning(f"⚠️ {remaining_locks[0]['count']} locks still remain - attempting force clear...")
                            
                            # Try force clearing remaining locks
                            force_cleared = await self.force_clear_remaining_locks()
                            if force_cleared:
                                logger.info("✅ Force clear completed - proceeding with import")
                            else:
                                logger.error("❌ Force clear failed - import may still timeout")
                                return False
                    else:
                        logger.error("❌ Failed to clear blocking locks - import will likely timeout")
                        logger.error("Recommendation: Restart the database or wait for locks to clear")
                        return False
                else:
                    logger.info("✅ Lock analysis completed")
            
            # Test 6: Check disk space
            logger.info("Test 6: Checking database size...")
            db_size = await self.db_handler.fetchval("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            logger.info(f"✅ Database size: {db_size}")
            
            # Test 7: Check connection pool status
            logger.info("Test 7: Checking connection pool...")
            if self.db_handler.pool:
                try:
                    pool_info = {
                        'min_size': getattr(self.db_handler.pool, '_minsize', 'unknown'),
                        'max_size': getattr(self.db_handler.pool, '_maxsize', 'unknown'),
                        'size': getattr(self.db_handler.pool, 'get_size', lambda: 'unknown')(),
                        'free_size': getattr(self.db_handler.pool, 'get_free_size', lambda: 'unknown')()
                    }
                    logger.info(f"✅ Connection pool: {pool_info}")
                except Exception as pool_error:
                    logger.warning(f"⚠️ Could not get pool details: {pool_error}")
                    logger.info("✅ Connection pool exists but details unavailable")
            else:
                logger.warning("⚠️ No connection pool available")
            
            logger.info("✅ Database health check completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database health check failed: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return False

    def _extract_relationship_context(self, event: AuditLogEvent) -> Dict[str, Any]:
        """Extract relationship context for knowledge graph construction"""
        context = {
            'primary_relationships': [],
            'secondary_relationships': [],
            'relationship_strength': 'medium',
            'temporal_proximity': None
        }
        
        # Extract primary relationships based on action type
        if event.action in ['MailItemsAccessed', 'Send', 'MessageDeleted']:
            if event.actor_id and event.internet_message_id:
                context['primary_relationships'].append({
                    'type': 'user_email_interaction',
                    'source': event.actor_id,
                    'target': event.internet_message_id,
                    'action': event.action
                })
        
        elif event.action in ['FileAccessed', 'FileCreated', 'FileDeleted', 'FileModified']:
            if event.actor_id and event.target_id:
                context['primary_relationships'].append({
                    'type': 'user_document_interaction',
                    'source': event.actor_id,
                    'target': event.target_id,
                    'action': event.action
                })
        
        # Extract secondary relationships from raw data
        if event.raw_data:
            if isinstance(event.raw_data, dict):
                raw_data = event.raw_data
            elif isinstance(event.raw_data, str):
                try:
                    raw_data = json.loads(event.raw_data)
                except (json.JSONDecodeError, TypeError):
                    raw_data = {}
            else:
                raw_data = {}
            
            # SharePoint relationships
            if raw_data.get('SiteUrl') and raw_data.get('ListId'):
                context['secondary_relationships'].append({
                    'type': 'document_container_relationship',
                    'document': event.target_id,
                    'site': raw_data.get('SiteUrl'),
                    'list': raw_data.get('ListId')
                })
            
            # Email folder relationships
            if event.source_folder or event.destination_folder:
                context['secondary_relationships'].append({
                    'type': 'email_folder_relationship',
                    'email': event.internet_message_id,
                    'source_folder': event.source_folder,
                    'destination_folder': event.destination_folder
                })
        
        # Assess relationship strength
        if event.action in ['Send', 'FileCreated', 'UserLoggedIn']:
            context['relationship_strength'] = 'strong'
        elif event.action in ['MailItemsAccessed', 'FileAccessed']:
            context['relationship_strength'] = 'medium'
        else:
            context['relationship_strength'] = 'weak'
        
        return context
    
    def _extract_session_context(self, event: AuditLogEvent) -> Dict[str, Any]:
        """Extract session context for session clustering"""
        context = {
            'session_id': event.session_id,
            'correlation_id': None,
            'azure_session_id': None,
            'session_duration_estimate': None,
            'cross_service_session': False
        }
        
        if event.raw_data:
            if isinstance(event.raw_data, dict):
                raw_data = event.raw_data
            elif isinstance(event.raw_data, str):
                try:
                    raw_data = json.loads(event.raw_data)
                except (json.JSONDecodeError, TypeError):
                    raw_data = {}
            else:
                raw_data = {}
            
            # Extract various session identifiers
            context['correlation_id'] = raw_data.get('CorrelationId')
            context['azure_session_id'] = raw_data.get('AzureActiveDirectoryEventType')
            
            # Check for cross-service session indicators
            if raw_data.get('Workload') and raw_data.get('RecordType'):
                workload = raw_data.get('Workload')
                if workload in ['Exchange', 'SharePoint', 'AzureActiveDirectory']:
                    context['cross_service_session'] = True
            
            # Extract session timing information
            if raw_data.get('CreationTime') and raw_data.get('EventTimestamp'):
                try:
                    from datetime import datetime
                    creation_time = datetime.fromisoformat(raw_data['CreationTime'].replace('Z', '+00:00'))
                    event_time = datetime.fromisoformat(raw_data['EventTimestamp'].replace('Z', '+00:00'))
                    context['session_duration_estimate'] = abs((event_time - creation_time).total_seconds())
                except (ValueError, TypeError):
                    pass
        
        return context
    
    def _extract_resource_context(self, event: AuditLogEvent) -> Dict[str, Any]:
        """Extract resource context for access chain analysis"""
        context = {
            'resource_hierarchy': [],
            'resource_type': event.target_type,
            'resource_permissions': [],
            'sharing_context': None
        }
        
        if event.raw_data:
            if isinstance(event.raw_data, dict):
                raw_data = event.raw_data
            elif isinstance(event.raw_data, str):
                try:
                    raw_data = json.loads(event.raw_data)
                except (json.JSONDecodeError, TypeError):
                    raw_data = {}
            else:
                raw_data = {}
            
            # Build resource hierarchy for SharePoint
            if raw_data.get('SiteUrl'):
                hierarchy = [{'type': 'site', 'id': raw_data.get('SiteUrl')}]
                
                if raw_data.get('ListId'):
                    hierarchy.append({'type': 'list', 'id': raw_data.get('ListId')})
                
                if raw_data.get('ObjectId'):
                    hierarchy.append({'type': 'object', 'id': raw_data.get('ObjectId')})
                
                context['resource_hierarchy'] = hierarchy
            
            # Extract permission information
            if raw_data.get('EventData'):
                event_data = raw_data.get('EventData', {})
                if isinstance(event_data, dict):
                    permissions = event_data.get('Permissions', [])
                    if permissions:
                        context['resource_permissions'] = permissions
            
            # Extract sharing context
            if event.action in ['FileShared', 'SharingSet', 'SharingInvitationCreated']:
                context['sharing_context'] = {
                    'action': event.action,
                    'target_user': raw_data.get('TargetUserOrGroupName'),
                    'sharing_type': raw_data.get('SharingType'),
                    'permission_level': raw_data.get('PermissionLevel')
                }
        
        return context
    
    def _extract_device_context(self, event: AuditLogEvent) -> Dict[str, Any]:
        """Extract device context for device-user mapping"""
        context = {
            'device_id': None,
            'device_info': {},
            'client_info': {},
            'location_context': {},
            'risk_indicators': []
        }
        
        if event.raw_data:
            if isinstance(event.raw_data, dict):
                raw_data = event.raw_data
            elif isinstance(event.raw_data, str):
                try:
                    raw_data = json.loads(event.raw_data)
                except (json.JSONDecodeError, TypeError):
                    raw_data = {}
            else:
                raw_data = {}
            
            # Extract device information
            context['device_id'] = raw_data.get('DeviceId')
            
            device_info = {}
            if raw_data.get('DeviceDisplayName'):
                device_info['display_name'] = raw_data.get('DeviceDisplayName')
            if raw_data.get('DeviceType'):
                device_info['type'] = raw_data.get('DeviceType')
            if raw_data.get('DeviceOS'):
                device_info['os'] = raw_data.get('DeviceOS')
            
            context['device_info'] = device_info
            
            # Extract client information
            client_info = {
                'process_name': event.client_process_name,
                'version': event.client_version,
                'ip_address': event.actor_ip_address
            }
            context['client_info'] = {k: v for k, v in client_info.items() if v is not None}
            
            # Extract location context
            if event.actor_location:
                context['location_context'] = event.actor_location
            
            # Identify risk indicators
            risk_indicators = []
            
            # Unusual client process
            if event.client_process_name and event.client_process_name not in [
                'Microsoft.Exchange.WebServices', 'Outlook', 'OWA', 'ActiveSync'
            ]:
                risk_indicators.append('unusual_client_process')
            
            # Multiple device access
            if raw_data.get('DeviceId') and event.actor_id:
                risk_indicators.append('device_user_mapping')
            
            context['risk_indicators'] = risk_indicators
        
        return context
    
    def _extract_cross_service_context(self, event: AuditLogEvent) -> Dict[str, Any]:
        """Extract cross-service context for correlation"""
        context = {
            'workload': None,
            'record_type': None,
            'tenant_id': None,
            'organization_id': event.organization_name,
            'user_object_id': None,
            'correlation_opportunities': []
        }
        
        if event.raw_data:
            if isinstance(event.raw_data, dict):
                raw_data = event.raw_data
            elif isinstance(event.raw_data, str):
                try:
                    raw_data = json.loads(event.raw_data)
                except (json.JSONDecodeError, TypeError):
                    raw_data = {}
            else:
                raw_data = {}
            
            # Extract service identifiers
            context['workload'] = raw_data.get('Workload')
            context['record_type'] = raw_data.get('RecordType')
            context['tenant_id'] = raw_data.get('TenantId')
            context['user_object_id'] = raw_data.get('UserObjectId')
            
            # Identify correlation opportunities
            correlation_opportunities = []
            
            # Cross-service user activity
            if context['user_object_id'] and context['workload']:
                correlation_opportunities.append({
                    'type': 'cross_service_user_activity',
                    'user_object_id': context['user_object_id'],
                    'workload': context['workload']
                })
            
            # Tenant-wide activity correlation
            if context['tenant_id']:
                correlation_opportunities.append({
                    'type': 'tenant_activity_correlation',
                    'tenant_id': context['tenant_id']
                })
            
            # Email-document correlation
            if event.internet_message_id and raw_data.get('ObjectId'):
                correlation_opportunities.append({
                    'type': 'email_document_correlation',
                    'email_id': event.internet_message_id,
                    'document_id': raw_data.get('ObjectId')
                })
            
            context['correlation_opportunities'] = correlation_opportunities
        
        return context

    async def check_and_clear_table_locks(self):
        """Check for and potentially clear blocking locks on the ExternalAuditLogs table"""
        logger.info("Checking for blocking locks on ExternalAuditLogs table...")
        
        try:
            # Get detailed lock information
            locks = await self.db_handler.fetch_all("""
                SELECT 
                    l.pid,
                    l.mode,
                    l.granted,
                    a.query_start,
                    a.state,
                    a.query,
                    EXTRACT(EPOCH FROM (now() - a.query_start)) as duration_seconds
                FROM pg_locks l
                JOIN pg_stat_activity a ON l.pid = a.pid
                WHERE l.relation = 'public."ExternalAuditLogs"'::regclass
                ORDER BY duration_seconds DESC
            """)
            
            logger.info(f"Found {len(locks)} locks on ExternalAuditLogs table")
            
            if locks:
                logger.info("Lock details:")
                for lock in locks:
                    logger.info(f"  PID: {lock['pid']}, Mode: {lock['mode']}, Granted: {lock['granted']}, Duration: {lock['duration_seconds']:.1f}s, State: {lock['state']}")
                    if lock['query']:
                        logger.info(f"    Query: {lock['query'][:100]}...")
                
                # Check for long-running queries that might be blocking
                long_running = [lock for lock in locks if lock['duration_seconds'] > 300]  # 5+ minutes
                if long_running:
                    logger.warning(f"Found {len(long_running)} long-running queries (>5 minutes)")
                    logger.warning("These may be blocking new inserts")
                    
                    # Option to terminate long-running queries (commented out for safety)
                    # for lock in long_running:
                    #     logger.warning(f"Would terminate PID {lock['pid']} (running for {lock['duration_seconds']:.1f}s)")
                    #     # await self.db_handler.execute(f"SELECT pg_terminate_backend({lock['pid']})")
            
            return len(locks)
            
        except Exception as e:
            logger.error(f"Error checking table locks: {str(e)}")
            return -1

    async def terminate_blocking_queries(self):
        """Safely terminate long-running queries that are blocking new inserts"""
        logger.info("Attempting to terminate blocking queries...")
        
        try:
            # First, get long-running INSERT queries specifically
            blocking_inserts = await self.db_handler.fetch_all("""
                SELECT 
                    l.pid,
                    EXTRACT(EPOCH FROM (now() - a.query_start)) as duration_seconds,
                    a.query,
                    a.state
                FROM pg_locks l
                JOIN pg_stat_activity a ON l.pid = a.pid
                WHERE l.relation = 'public."ExternalAuditLogs"'::regclass
                AND a.query LIKE '%INSERT INTO public."ExternalAuditLogs"%'
                AND EXTRACT(EPOCH FROM (now() - a.query_start)) > 300  -- 5+ minutes
                AND a.state = 'active'
                ORDER BY duration_seconds DESC
            """)
            
            terminated_count = 0
            
            if blocking_inserts:
                logger.warning(f"Found {len(blocking_inserts)} long-running INSERT queries to terminate:")
                
                for query in blocking_inserts:
                    pid = query['pid']
                    duration = query['duration_seconds']
                    logger.warning(f"Terminating PID {pid} (running for {duration:.1f}s)")
                    
                    try:
                        await self.db_handler.execute(f"SELECT pg_terminate_backend({pid})")
                        terminated_count += 1
                        logger.info(f"✅ Successfully terminated PID {pid}")
                    except Exception as e:
                        logger.error(f"❌ Failed to terminate PID {pid}: {str(e)}")
            
            # Wait a moment for INSERT locks to clear
            if terminated_count > 0:
                logger.info("Waiting 3 seconds for INSERT locks to clear...")
                await asyncio.sleep(3)
            
            # Now check for any remaining long-running queries that might be blocking
            remaining_blocking = await self.db_handler.fetch_all("""
                SELECT 
                    l.pid,
                    EXTRACT(EPOCH FROM (now() - a.query_start)) as duration_seconds,
                    a.query,
                    a.state,
                    l.mode
                FROM pg_locks l
                JOIN pg_stat_activity a ON l.pid = a.pid
                WHERE l.relation = 'public."ExternalAuditLogs"'::regclass
                AND EXTRACT(EPOCH FROM (now() - a.query_start)) > 300  -- 5+ minutes
                AND a.state IN ('active', 'idle in transaction')
                AND l.mode IN ('AccessExclusiveLock', 'ShareLock', 'RowExclusiveLock')
                ORDER BY duration_seconds DESC
            """)
            
            if remaining_blocking:
                logger.warning(f"Found {len(remaining_blocking)} additional long-running queries that may be blocking:")
                
                for query in remaining_blocking:
                    pid = query['pid']
                    duration = query['duration_seconds']
                    mode = query['mode']
                    state = query['state']
                    logger.warning(f"  PID {pid}: {mode} lock, {state} state, running for {duration:.1f}s")
                    
                    # Only terminate if it's been running for a very long time (>10 minutes)
                    if duration > 600:  # 10 minutes
                        logger.warning(f"Terminating long-running PID {pid} (running for {duration:.1f}s)")
                        try:
                            await self.db_handler.execute(f"SELECT pg_terminate_backend({pid})")
                            terminated_count += 1
                            logger.info(f"✅ Successfully terminated PID {pid}")
                        except Exception as e:
                            logger.error(f"❌ Failed to terminate PID {pid}: {str(e)}")
                    else:
                        logger.info(f"  Skipping PID {pid} (only running for {duration:.1f}s)")
            
            logger.info(f"Total terminated: {terminated_count} queries")
            
            # Final wait for all locks to clear
            if terminated_count > 0:
                logger.info("Waiting 5 seconds for all locks to clear...")
                await asyncio.sleep(5)
            
            return terminated_count
            
        except Exception as e:
            logger.error(f"Error terminating blocking queries: {str(e)}")
            return -1

    async def force_clear_remaining_locks(self):
        """Force clear any remaining locks by restarting the connection pool"""
        logger.warning("Force clearing remaining locks by restarting connection pool...")
        
        try:
            # Close the current connection pool
            if self.db_handler.pool:
                logger.info("Closing current connection pool...")
                await self.db_handler.pool.close()
                self.db_handler.pool = None
            
            # Wait a moment for connections to fully close
            await asyncio.sleep(2)
            
            # Reconnect to create a fresh pool
            logger.info("Creating fresh connection pool...")
            await self.db_handler.connect()
            
            # Wait for locks to clear
            await asyncio.sleep(3)
            
            logger.info("✅ Connection pool restarted - locks should be cleared")
            return True
            
        except Exception as e:
            logger.error(f"Error force clearing locks: {str(e)}")
            return False

# Global instance
external_audit_logs_service = ExternalAuditLogsService() 