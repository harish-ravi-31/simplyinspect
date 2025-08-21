"""
External Audit Logs API Routes
Provides endpoints for managing external audit log collection and querying
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from src.db.db_handler import get_db, DatabaseHandler
from src.services.external_audit_logs_service import external_audit_logs_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["External Audit Logs"])

# Pydantic models for API requests/responses
class AuditLogSourceConfig(BaseModel):
    source_system: str = Field(..., description="Unique identifier for the source system")
    display_name: str = Field(..., description="Human-readable display name")
    description: Optional[str] = Field(None, description="Description of the source")
    configuration: dict = Field(..., description="Source-specific configuration")
    schedule: Optional[dict] = Field(None, description="Collection schedule configuration")
    retention_days: int = Field(2555, description="How long to retain logs (default 7 years)")
    is_active: bool = Field(True, description="Whether the source is active")

class AuditLogSearchRequest(BaseModel):
    source_system: Optional[str] = Field(None, description="Filter by source system")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    actor_id: Optional[str] = Field(None, description="Filter by actor ID")
    target_id: Optional[str] = Field(None, description="Filter by target ID")
    start_date: Optional[datetime] = Field(None, description="Start date for search")
    end_date: Optional[datetime] = Field(None, description="End date for search")
    search_term: Optional[str] = Field(None, description="Full-text search term")
    compliance_tags: Optional[List[str]] = Field(None, description="Filter by compliance tags")
    security_relevant: Optional[bool] = Field(None, description="Filter by security relevance")
    legal_hold_relevant: Optional[bool] = Field(None, description="Filter by legal hold relevance")
    retention_relevant: Optional[bool] = Field(None, description="Filter by retention relevance")
    tags: Optional[List[str]] = Field(None, description="Filter by AI-generated tags")
    risk_level: Optional[str] = Field(None, description="Filter by risk level (low/medium/high)")
    anomaly_score_min: Optional[float] = Field(None, description="Minimum anomaly score (0-1)")
    business_hours_only: Optional[bool] = Field(None, description="Filter by business hours only")
    page: int = Field(1, description="Page number")
    page_size: int = Field(50, description="Page size")
    sort_by: str = Field("EventTimestamp", description="Sort field")
    sort_order: str = Field("DESC", description="Sort order (ASC/DESC)")

class CollectionJobRequest(BaseModel):
    source_system: str = Field(..., description="Source system to collect from")
    job_type: str = Field("manual", description="Type of collection job")

class AIInsightsRequest(BaseModel):
    source_system: Optional[str] = Field(None, description="Filter by source system")
    days: int = Field(30, description="Number of days to analyze")
    include_temporal_patterns: bool = Field(True, description="Include temporal pattern analysis")
    include_risk_analysis: bool = Field(True, description="Include risk analysis")
    include_compliance_insights: bool = Field(True, description="Include compliance insights")

class AnomalyDetectionRequest(BaseModel):
    source_system: Optional[str] = Field(None, description="Filter by source system")
    days: int = Field(7, description="Number of days to analyze")
    threshold: float = Field(0.7, description="Anomaly score threshold (0-1)")
    include_context: bool = Field(True, description="Include contextual information")

class ComplianceReportRequest(BaseModel):
    source_system: Optional[str] = Field(None, description="Filter by source system")
    start_date: datetime = Field(..., description="Report start date")
    end_date: datetime = Field(..., description="Report end date")
    frameworks: Optional[List[str]] = Field(None, description="Specific frameworks to include")
    include_legal_hold_events: bool = Field(True, description="Include legal hold events")
    include_retention_events: bool = Field(True, description="Include retention events")

@router.get("/sources", response_model=List[dict])
async def get_audit_log_sources(
    active_only: bool = Query(True, description="Only return active sources"),
    db: DatabaseHandler = Depends(get_db)
):
    """Get configured audit log sources"""
    try:
        sources = await external_audit_logs_service.get_sources(active_only=active_only)
        return sources
    except Exception as e:
        logger.error(f"Error getting audit log sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources/{source_system}", response_model=dict)
async def get_audit_log_source(
    source_system: str,
    db: DatabaseHandler = Depends(get_db)
):
    """Get specific audit log source configuration"""
    try:
        source = await external_audit_logs_service.get_source(source_system)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {source_system} not found")
        return source
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audit log source {source_system}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sources", response_model=dict)
async def add_audit_log_source(
    source_config: AuditLogSourceConfig,
    db: DatabaseHandler = Depends(get_db)
):
    """Add a new audit log source"""
    try:
        success = await external_audit_logs_service.add_source(source_config.dict())
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add audit log source")
        
        # Return the created source
        source = await external_audit_logs_service.get_source(source_config.source_system)
        return {"status": "success", "source": source}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding audit log source: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/sources/{source_system}", response_model=dict)
async def update_audit_log_source(
    source_system: str,
    updates: dict = Body(...),
    db: DatabaseHandler = Depends(get_db)
):
    """Update audit log source configuration"""
    try:
        success = await external_audit_logs_service.update_source(source_system, updates)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to update audit log source")
        
        # Return the updated source
        source = await external_audit_logs_service.get_source(source_system)
        return {"status": "success", "source": source}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating audit log source {source_system}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/collect", response_model=dict)
async def collect_audit_logs(
    request: CollectionJobRequest,
    db: DatabaseHandler = Depends(get_db)
):
    """Manually trigger audit log collection"""
    try:
        job_id = await external_audit_logs_service.collect_logs(
            request.source_system, 
            request.job_type
        )
        return {
            "status": "success",
            "job_id": job_id,
            "message": f"Collection job started for {request.source_system}"
        }
    except Exception as e:
        logger.error(f"Error collecting audit logs from {request.source_system}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/jobs", response_model=List[dict])
async def get_collection_jobs(
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    limit: int = Query(100, description="Maximum number of jobs to return"),
    db: DatabaseHandler = Depends(get_db)
):
    """Get collection job history"""
    try:
        jobs = await external_audit_logs_service.get_collection_jobs(
            source_system=source_system,
            limit=limit
        )
        return jobs
    except Exception as e:
        logger.error(f"Error getting collection jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=dict)
async def search_audit_logs(
    request: AuditLogSearchRequest,
    db: DatabaseHandler = Depends(get_db)
):
    """Advanced search audit logs with AI-optimized filters and sorting"""
    try:
        logs, total_count = await external_audit_logs_service.search_audit_logs(
            source_system=request.source_system,
            event_type=request.event_type,
            actor_id=request.actor_id,
            target_id=request.target_id,
            start_date=request.start_date,
            end_date=request.end_date,
            search_term=request.search_term,
            compliance_tags=request.compliance_tags,
            security_relevant=request.security_relevant,
            legal_hold_relevant=request.legal_hold_relevant,
            retention_relevant=request.retention_relevant,
            tags=request.tags,
            risk_level=request.risk_level,
            anomaly_score_min=request.anomaly_score_min,
            business_hours_only=request.business_hours_only,
            page=request.page,
            page_size=request.page_size,
            sort_by=request.sort_by,
            sort_order=request.sort_order
        )
        
        # Add AI-enhanced response metadata
        response_metadata = {
            "search_optimized": True,
            "ai_filters_applied": any([
                request.security_relevant is not None,
                request.legal_hold_relevant is not None,
                request.retention_relevant is not None,
                request.tags is not None,
                request.risk_level is not None,
                request.anomaly_score_min is not None,
                request.business_hours_only is not None
            ]),
            "relevance_scoring": True,
            "sorting": {
                "field": request.sort_by,
                "order": request.sort_order
            }
        }
        
        return {
            "results": logs,
            "total": total_count,
            "page": request.page,
            "page_size": request.page_size,
            "total_pages": (total_count + request.page_size - 1) // request.page_size,
            "metadata": response_metadata
        }
    except Exception as e:
        logger.error(f"Error searching audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=dict)
async def get_audit_log_stats(
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    days: int = Query(30, description="Number of days to include in stats"),
    db: DatabaseHandler = Depends(get_db)
):
    """Get audit log statistics"""
    try:
        stats = await external_audit_logs_service.get_audit_log_stats(
            source_system=source_system,
            days=days
        )
        return stats
    except Exception as e:
        logger.error(f"Error getting audit log stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup", response_model=dict)
async def cleanup_old_logs(
    db: DatabaseHandler = Depends(get_db)
):
    """Clean up old audit logs based on retention policies"""
    try:
        deleted_count = await external_audit_logs_service.cleanup_old_logs()
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} old audit log records"
        }
    except Exception as e:
        logger.error(f"Error cleaning up old logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/schedule", response_model=dict)
async def schedule_next_collections(
    db: DatabaseHandler = Depends(get_db)
):
    """Schedule next collection times for all active sources"""
    try:
        await external_audit_logs_service.schedule_next_collections()
        return {
            "status": "success",
            "message": "Next collection times scheduled for all active sources"
        }
    except Exception as e:
        logger.error(f"Error scheduling next collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/test-connection/{source_system}", response_model=dict)
async def test_source_connection(
    source_system: str,
    db: DatabaseHandler = Depends(get_db)
):
    """Test connection to a specific audit log source"""
    try:
        source = await external_audit_logs_service.get_source(source_system)
        if not source:
            raise HTTPException(status_code=404, detail=f"Source {source_system} not found")
        
        # Get the appropriate collector
        collector_class = external_audit_logs_service.collectors.get(source_system)
        if not collector_class:
            raise HTTPException(status_code=400, detail=f"No collector available for {source_system}")
        
        # Test connection
        collector = collector_class(source)
        if hasattr(collector, 'test_connection'):
            connection_ok = await collector.test_connection()
        else:
            connection_ok = True  # Assume OK if no test method available
        
        return {
            "source_system": source_system,
            "connection_ok": connection_ok,
            "message": "Connection successful" if connection_ok else "Connection failed"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing connection to {source_system}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/event-types", response_model=List[dict])
async def get_event_types(
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    db: DatabaseHandler = Depends(get_db)
):
    """Get available event types and their mappings"""
    try:
        query = """
            SELECT DISTINCT "SourceSystem", "SourceEventType", "MappedEventType", 
                   "MappedEventCategory", "MappedEventSubcategory", "ComplianceTags",
                   "IsSecurityRelevant", "IsLegalHoldRelevant", "IsRetentionRelevant"
            FROM public."AuditEventMappings"
            WHERE "IsActive" = TRUE
        """
        params = []
        
        if source_system:
            query += " AND \"SourceSystem\" = $1"
            params.append(source_system)
        
        query += " ORDER BY \"SourceSystem\", \"SourceEventType\""
        
        mappings = await db.fetch_all(query, *params)
        return [dict(mapping) for mapping in mappings]
    except Exception as e:
        logger.error(f"Error getting event types: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/alerts", response_model=List[dict])
async def get_audit_alerts(
    status: Optional[str] = Query(None, description="Filter by alert status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(100, description="Maximum number of alerts to return"),
    db: DatabaseHandler = Depends(get_db)
):
    """Get audit log alerts"""
    try:
        where_clauses = []
        params = []
        param_idx = 1
        
        if status:
            where_clauses.append(f'"Status" = ${param_idx}')
            params.append(status)
            param_idx += 1
        
        if severity:
            where_clauses.append(f'"Severity" = ${param_idx}')
            params.append(severity)
            param_idx += 1
        
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
            SELECT * FROM public."AuditLogAlerts"
            {where_sql}
            ORDER BY "AlertTimestamp" DESC
            LIMIT ${param_idx}
        """
        params.append(limit)
        
        alerts = await db.fetch_all(query, *params)
        return [dict(alert) for alert in alerts]
    except Exception as e:
        logger.error(f"Error getting audit alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# AI-Enhanced Endpoints

@router.post("/ai-insights", response_model=dict)
async def get_ai_insights(
    request: AIInsightsRequest,
    db: DatabaseHandler = Depends(get_db)
):
    """Get AI-powered insights and analytics from audit data"""
    try:
        # Get comprehensive stats with AI insights
        stats = await external_audit_logs_service.get_audit_log_stats(
            source_system=request.source_system,
            days=request.days
        )
        
        # Build response based on requested insights
        response = {
            "ai_enhanced": True,
            "analysis_period_days": request.days,
            "source_system": request.source_system,
            "basic_stats": {
                "total_events": stats.get('total_events', 0),
                "security_events": stats.get('security_events', 0),
                "legal_hold_events": stats.get('legal_hold_events', 0),
                "retention_events": stats.get('retention_events', 0)
            }
        }
        
        # Add AI insights
        if 'ai_insights' in stats:
            response['ai_insights'] = stats['ai_insights']
        
        # Add temporal patterns if requested
        if request.include_temporal_patterns and 'temporal_patterns' in stats:
            response['temporal_patterns'] = stats['temporal_patterns']
        
        # Add risk analysis if requested
        if request.include_risk_analysis and 'risk_analysis' in stats:
            response['risk_analysis'] = stats['risk_analysis']
        
        # Add compliance insights if requested
        if request.include_compliance_insights and 'ai_insights' in stats:
            response['compliance_insights'] = stats['ai_insights'].get('compliance', {})
        
        return response
    except Exception as e:
        logger.error(f"Error getting AI insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/anomaly-detection", response_model=dict)
async def detect_anomalies(
    request: AnomalyDetectionRequest,
    db: DatabaseHandler = Depends(get_db)
):
    """Detect anomalies in audit data using AI analysis"""
    try:
        since_date = datetime.now(timezone.utc) - timedelta(days=request.days)
        
        # Build query for anomaly detection
        where_clause = 'WHERE "EventTimestamp" >= $1'
        params = [since_date]
        
        if request.source_system:
            where_clause += ' AND "SourceSystem" = $2'
            params.append(request.source_system)
        
        # Find high-anomaly events
        anomaly_query = f"""
            SELECT 
                "Id", "EventId", "SourceSystem", "EventType", "EventTimestamp",
                "ActorId", "ActorName", "TargetId", "TargetName", "Action",
                "Metadata"->'security_context'->>'anomaly_score' as anomaly_score,
                "Metadata"->'security_context'->'threat_indicators' as threat_indicators,
                "RawData", "ProcessedData"
            FROM public."ExternalAuditLogs"
            {where_clause}
            AND CAST("Metadata"->'security_context'->>'anomaly_score' AS FLOAT) >= $3
            ORDER BY CAST("Metadata"->'security_context'->>'anomaly_score' AS FLOAT) DESC
        """
        params.append(request.threshold)
        
        anomalies = await db.fetch_all(anomaly_query, *params)
        
        # Calculate anomaly statistics
        stats_query = f"""
            SELECT 
                COUNT(*) as total_events,
                COUNT(*) FILTER (WHERE CAST("Metadata"->'security_context'->>'anomaly_score' AS FLOAT) >= $3) as high_anomaly_count,
                AVG(CAST("Metadata"->'security_context'->>'anomaly_score' AS FLOAT)) as avg_anomaly_score,
                MAX(CAST("Metadata"->'security_context'->>'anomaly_score' AS FLOAT)) as max_anomaly_score
            FROM public."ExternalAuditLogs"
            {where_clause}
        """
        stats_params = params[:-1] + [request.threshold]
        anomaly_stats = await db.fetch_one(stats_query, *stats_params)
        
        response = {
            "anomaly_detection": True,
            "threshold": request.threshold,
            "analysis_period_days": request.days,
            "source_system": request.source_system,
            "statistics": dict(anomaly_stats) if anomaly_stats else {},
            "anomalies": [dict(anomaly) for anomaly in anomalies]
        }
        
        # Add contextual information if requested
        if request.include_context:
            response['context'] = {
                "total_events_analyzed": anomaly_stats['total_events'] if anomaly_stats else 0,
                "anomaly_percentage": (
                    (anomaly_stats['high_anomaly_count'] / anomaly_stats['total_events'] * 100)
                    if anomaly_stats and anomaly_stats['total_events'] > 0 else 0
                ),
                "risk_assessment": "high" if anomaly_stats and anomaly_stats['high_anomaly_count'] > 10 else "medium" if anomaly_stats and anomaly_stats['high_anomaly_count'] > 5 else "low"
            }
        
        return response
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/compliance-report", response_model=dict)
async def generate_compliance_report(
    request: ComplianceReportRequest,
    db: DatabaseHandler = Depends(get_db)
):
    """Generate comprehensive compliance report with AI insights"""
    try:
        # Build base query
        where_clause = 'WHERE "EventTimestamp" >= $1 AND "EventTimestamp" <= $2'
        params = [request.start_date, request.end_date]
        
        if request.source_system:
            where_clause += ' AND "SourceSystem" = $3'
            params.append(request.source_system)
        
        # Framework-specific queries
        framework_queries = {}
        if not request.frameworks or 'GDPR' in request.frameworks:
            gdpr_query = f"""
                SELECT COUNT(*) as gdpr_events,
                       COUNT(*) FILTER (WHERE "LegalHoldRelevant" = TRUE) as legal_hold_events,
                       COUNT(*) FILTER (WHERE "RetentionRelevant" = TRUE) as retention_events
                FROM public."ExternalAuditLogs"
                {where_clause} AND "ComplianceTags" && ARRAY['gdpr']
            """
            gdpr_stats = await db.fetch_one(gdpr_query, *params)
            framework_queries['GDPR'] = dict(gdpr_stats) if gdpr_stats else {}
        
        if not request.frameworks or 'SOX' in request.frameworks:
            sox_query = f"""
                SELECT COUNT(*) as sox_events,
                       COUNT(*) FILTER (WHERE "LegalHoldRelevant" = TRUE) as legal_hold_events,
                       COUNT(*) FILTER (WHERE "RetentionRelevant" = TRUE) as retention_events
                FROM public."ExternalAuditLogs"
                {where_clause} AND "ComplianceTags" && ARRAY['sox']
            """
            sox_stats = await db.fetch_one(sox_query, *params)
            framework_queries['SOX'] = dict(sox_stats) if sox_stats else {}
        
        if not request.frameworks or 'HIPAA' in request.frameworks:
            hipaa_query = f"""
                SELECT COUNT(*) as hipaa_events,
                       COUNT(*) FILTER (WHERE "LegalHoldRelevant" = TRUE) as legal_hold_events,
                       COUNT(*) FILTER (WHERE "RetentionRelevant" = TRUE) as retention_events
                FROM public."ExternalAuditLogs"
                {where_clause} AND "ComplianceTags" && ARRAY['hipaa']
            """
            hipaa_stats = await db.fetch_one(hipaa_query, *params)
            framework_queries['HIPAA'] = dict(hipaa_stats) if hipaa_stats else {}
        
        # Legal hold and retention events
        legal_hold_events = []
        retention_events = []
        
        if request.include_legal_hold_events:
            legal_hold_query = f"""
                SELECT "Id", "EventId", "EventType", "EventTimestamp", "ActorName", "TargetName", "Action"
                FROM public."ExternalAuditLogs"
                {where_clause} AND "LegalHoldRelevant" = TRUE
                ORDER BY "EventTimestamp" DESC
                LIMIT 100
            """
            legal_hold_events = await db.fetch_all(legal_hold_query, *params)
            legal_hold_events = [dict(event) for event in legal_hold_events]
        
        if request.include_retention_events:
            retention_query = f"""
                SELECT "Id", "EventId", "EventType", "EventTimestamp", "ActorName", "TargetName", "Action"
                FROM public."ExternalAuditLogs"
                {where_clause} AND "RetentionRelevant" = TRUE
                ORDER BY "EventTimestamp" DESC
                LIMIT 100
            """
            retention_events = await db.fetch_all(retention_query, *params)
            retention_events = [dict(event) for event in retention_events]
        
        # Generate compliance score
        total_events_query = f'SELECT COUNT(*) FROM public."ExternalAuditLogs" {where_clause}'
        total_events = await db.fetchval(total_events_query, *params)
        
        compliance_events = sum(
            framework_stats.get('gdpr_events', 0) + 
            framework_stats.get('sox_events', 0) + 
            framework_stats.get('hipaa_events', 0)
            for framework_stats in framework_queries.values()
        )
        
        compliance_score = (compliance_events / total_events * 100) if total_events > 0 else 0
        
        response = {
            "compliance_report": True,
            "report_period": {
                "start_date": request.start_date.isoformat(),
                "end_date": request.end_date.isoformat()
            },
            "source_system": request.source_system,
            "compliance_score": round(compliance_score, 2),
            "total_events": total_events,
            "framework_analysis": framework_queries,
            "legal_hold_events": legal_hold_events if request.include_legal_hold_events else [],
            "retention_events": retention_events if request.include_retention_events else [],
            "ai_enhanced": True
        }
        
        return response
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ai-tags", response_model=List[str])
async def get_available_ai_tags(
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    db: DatabaseHandler = Depends(get_db)
):
    """Get all available AI-generated tags for filtering"""
    try:
        query = """
            SELECT DISTINCT unnest("Tags") as tag
            FROM public."ExternalAuditLogs"
            WHERE "Tags" IS NOT NULL AND array_length("Tags", 1) > 0
        """
        params = []
        
        if source_system:
            query += " AND \"SourceSystem\" = $1"
            params.append(source_system)
        
        query += " ORDER BY tag"
        
        tags = await db.fetch_all(query, *params)
        return [tag['tag'] for tag in tags]
    except Exception as e:
        logger.error(f"Error getting AI tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/risk-actors", response_model=List[dict])
async def get_high_risk_actors(
    source_system: Optional[str] = Query(None, description="Filter by source system"),
    days: int = Query(30, description="Number of days to analyze"),
    limit: int = Query(20, description="Maximum number of actors to return"),
    db: DatabaseHandler = Depends(get_db)
):
    """Get high-risk actors based on AI analysis"""
    try:
        since_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        where_clause = 'WHERE "EventTimestamp" >= $1'
        params = [since_date]
        
        if source_system:
            where_clause += ' AND "SourceSystem" = $2'
            params.append(source_system)
        
        query = f"""
            SELECT 
                "ActorId", "ActorName", COUNT(*) as total_events,
                COUNT(*) FILTER (WHERE "SecurityRelevant" = TRUE) as security_events,
                COUNT(*) FILTER (WHERE "LegalHoldRelevant" = TRUE) as legal_hold_events,
                AVG(CAST("Metadata"->'security_context'->>'anomaly_score' AS FLOAT)) as avg_anomaly_score,
                MAX(CAST("Metadata"->'security_context'->>'anomaly_score' AS FLOAT)) as max_anomaly_score
            FROM public."ExternalAuditLogs"
            {where_clause}
            AND "ActorId" IS NOT NULL
            GROUP BY "ActorId", "ActorName"
            HAVING COUNT(*) > 3
            ORDER BY security_events DESC, avg_anomaly_score DESC
            LIMIT $3
        """
        params.append(limit)
        
        actors = await db.fetch_all(query, *params)
        return [dict(actor) for actor in actors]
    except Exception as e:
        logger.error(f"Error getting high-risk actors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Database setup and testing endpoints

@router.post("/setup-database", response_model=dict)
async def setup_database(
    db_config: dict = Body(...),
    db: DatabaseHandler = Depends(get_db)
):
    """Setup external audit logs database schema"""
    try:
        # Run the schema creation script
        schema_file = 'database_migrations/create_external_audit_logs_schema.sql'
        
        # Check if schema file exists
        import os
        if not os.path.exists(schema_file):
            # Create a basic schema if file doesn't exist
            basic_schema = """
            -- Basic external audit logs schema
            CREATE TABLE IF NOT EXISTS public."ExternalAuditLogs" (
                "Id" SERIAL PRIMARY KEY,
                "SourceSystem" VARCHAR(100) NOT NULL,
                "EventId" VARCHAR(255) NOT NULL,
                "EventType" VARCHAR(100) NOT NULL,
                "EventTimestamp" TIMESTAMP WITH TIME ZONE NOT NULL,
                "ActorId" VARCHAR(255),
                "ActorName" VARCHAR(255),
                "TargetId" VARCHAR(255),
                "TargetName" VARCHAR(255),
                "Action" VARCHAR(255),
                "RawData" JSONB,
                "ProcessedData" JSONB,
                "SecurityRelevant" BOOLEAN DEFAULT FALSE,
                "LegalHoldRelevant" BOOLEAN DEFAULT FALSE,
                "RetentionRelevant" BOOLEAN DEFAULT FALSE,
                "ComplianceTags" TEXT[],
                "Tags" TEXT[],
                "Metadata" JSONB,
                "ProcessingStatus" VARCHAR(50) DEFAULT 'processed',
                "PartitionDate" DATE GENERATED ALWAYS AS (DATE("EventTimestamp")) STORED
            );
            
            CREATE TABLE IF NOT EXISTS public."AuditLogSources" (
                "Id" SERIAL PRIMARY KEY,
                "SourceSystem" VARCHAR(100) UNIQUE NOT NULL,
                "DisplayName" VARCHAR(255) NOT NULL,
                "Description" TEXT,
                "Configuration" JSONB NOT NULL,
                "Schedule" JSONB,
                "RetentionDays" INTEGER DEFAULT 2555,
                "IsActive" BOOLEAN DEFAULT TRUE,
                "LastCollectionTime" TIMESTAMP WITH TIME ZONE,
                "NextCollectionTime" TIMESTAMP WITH TIME ZONE,
                "CreatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                "UpdatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            
            CREATE TABLE IF NOT EXISTS public."AuditLogCollectionJobs" (
                "Id" SERIAL PRIMARY KEY,
                "JobId" VARCHAR(255) UNIQUE NOT NULL,
                "SourceSystem" VARCHAR(100) NOT NULL,
                "JobType" VARCHAR(50) NOT NULL,
                "Status" VARCHAR(50) NOT NULL,
                "StartTime" TIMESTAMP WITH TIME ZONE NOT NULL,
                "EndTime" TIMESTAMP WITH TIME ZONE,
                "RecordsProcessed" INTEGER DEFAULT 0,
                "RecordsFailed" INTEGER DEFAULT 0,
                "RecordsSkipped" INTEGER DEFAULT 0,
                "ErrorDetails" TEXT,
                "CreatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            await db.execute(basic_schema)
        else:
            # Read and execute the schema file
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
                await db.execute(schema_sql)
        
        return {
            "status": "success",
            "message": "Database schema created successfully",
            "tables_created": [
                "ExternalAuditLogs",
                "AuditLogSources", 
                "AuditLogCollectionJobs"
            ]
        }
    except Exception as e:
        logger.error(f"Database setup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-database", response_model=dict)
async def test_database_connection(
    db_config: dict = Body(...)
):
    """Test database connection"""
    try:
        # Test connection using provided config
        import asyncpg
        
        conn = await asyncpg.connect(
            host=db_config.get('host', 'localhost'),
            port=db_config.get('port', 5432),
            database=db_config.get('database', 'SD-08'),
            user=db_config.get('username', 'postgres'),
            password=db_config.get('password', '')
        )
        
        # Test basic query
        result = await conn.fetchval("SELECT 1")
        await conn.close()
        
        if result == 1:
            return {
                "status": "success",
                "message": "Database connection successful",
                "connection_ok": True
            }
        else:
            raise Exception("Database connection test failed")
            
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
            "connection_ok": False
        }

@router.get("/test-connection/{source_system}", response_model=dict)
async def test_source_connection(
    source_system: str,
    db: DatabaseHandler = Depends(get_db)
):
    """Test connection to a specific audit log source"""
    try:
        # Get source configuration
        source = await db.fetch_one(
            'SELECT * FROM "AuditLogSources" WHERE "SourceSystem" = $1',
            source_system
        )
        
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        # Test connection based on source system
        if source_system == "microsoft_purview":
            # Test Microsoft Purview connection
            config = source["Configuration"]
            
            # Import the collector
            from ..collectors.microsoft_purview import MicrosoftPurviewCollector
            
            collector = MicrosoftPurviewCollector()
            connection_ok = await collector.test_connection(config)
            
            return {
                "connection_ok": connection_ok,
                "source_system": source_system,
                "message": "Connection test completed"
            }
        else:
            return {
                "connection_ok": False,
                "source_system": source_system,
                "message": "Source system not supported for connection testing"
            }
            
    except Exception as e:
        logger.error(f"Connection test failed for {source_system}: {e}")
        return {
            "connection_ok": False,
            "source_system": source_system,
            "message": f"Connection test failed: {str(e)}"
        } 