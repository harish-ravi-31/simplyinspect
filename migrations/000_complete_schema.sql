-- =====================================================
-- SimplyInspect Complete Database Schema
-- Single comprehensive initialization script
-- Version: 1.0
-- =====================================================

-- Drop existing schema if needed (WARNING: This will delete all data!)
-- Uncomment the following lines only for a complete reset:
-- DROP SCHEMA IF EXISTS public CASCADE;
-- CREATE SCHEMA public;

-- =====================================================
-- SHAREPOINT PERMISSIONS TABLES
-- =====================================================

-- Main SharePoint permissions table with all columns
CREATE TABLE IF NOT EXISTS public.sharepoint_permissions (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255),
    site_id VARCHAR(500),
    site_url TEXT,
    resource_id VARCHAR(500),
    resource_name TEXT,
    resource_type VARCHAR(100),
    resource_url TEXT,
    permission_type VARCHAR(100),
    permission_level VARCHAR(255),
    principal_id VARCHAR(500),
    principal_name VARCHAR(500),
    principal_email VARCHAR(500),
    principal_type VARCHAR(100),
    is_human BOOLEAN DEFAULT false,
    has_broken_inheritance BOOLEAN DEFAULT false,
    inherited_from_resource VARCHAR(500),
    -- Additional columns from migration 004
    parent_resource_id VARCHAR(500),
    parent_resource_name TEXT,
    parent_resource_type VARCHAR(100),
    inherited_from_parent BOOLEAN DEFAULT false,
    -- Metadata and timestamps
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    -- Correct unique constraint from migration 005
    CONSTRAINT sharepoint_permissions_resource_principal_unique UNIQUE (resource_id, principal_id)
);

-- SharePoint files and folders structure
CREATE TABLE IF NOT EXISTS public.sharepoint_structure (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(255),
    site_id VARCHAR(500),
    site_url TEXT,
    library_id VARCHAR(500),
    library_name VARCHAR(500),
    item_id VARCHAR(500) UNIQUE,
    item_name TEXT,
    item_type VARCHAR(50),
    item_path TEXT,
    parent_id VARCHAR(500),
    size_bytes BIGINT,
    created_at TIMESTAMP,
    modified_at TIMESTAMP,
    created_by VARCHAR(500),
    modified_by VARCHAR(500),
    has_unique_permissions BOOLEAN DEFAULT false,
    permission_inheritance_broken BOOLEAN DEFAULT false,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Group membership tables for caching
CREATE TABLE IF NOT EXISTS public.group_memberships (
    id SERIAL PRIMARY KEY,
    group_id VARCHAR(255) NOT NULL,
    group_name VARCHAR(500),
    group_type VARCHAR(50),
    member_id VARCHAR(255) NOT NULL,
    member_name VARCHAR(500),
    member_email VARCHAR(500),
    member_type VARCHAR(50),
    member_upn VARCHAR(500),
    job_title VARCHAR(500),
    department VARCHAR(500),
    office_location VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    CONSTRAINT group_memberships_unique UNIQUE(group_id, member_id)
);

-- Group sync status tracking
CREATE TABLE IF NOT EXISTS public.group_sync_status (
    group_id VARCHAR(255) PRIMARY KEY,
    group_name VARCHAR(500),
    sync_status VARCHAR(50),
    member_count INTEGER DEFAULT 0,
    last_sync_at TIMESTAMP,
    next_sync_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PURVIEW / EXTERNAL AUDIT LOGS TABLES
-- =====================================================

-- External audit logs from Microsoft Purview
CREATE TABLE IF NOT EXISTS public."ExternalAuditLogs" (
    "Id" SERIAL PRIMARY KEY,
    "RecordId" VARCHAR(255) UNIQUE,
    "CreationTime" TIMESTAMP,
    "Operation" VARCHAR(500),
    "OrganizationId" VARCHAR(255),
    "RecordType" INTEGER,
    "ResultStatus" VARCHAR(100),
    "UserKey" VARCHAR(500),
    "UserType" VARCHAR(100),
    "Version" INTEGER,
    "Workload" VARCHAR(100),
    "ClientIP" VARCHAR(100),
    "UserId" VARCHAR(500),
    "AzureActiveDirectoryEventType" INTEGER,
    "ExtendedProperties" JSONB,
    "ModifiedProperties" JSONB,
    "Actor" JSONB,
    "ActorIpAddress" VARCHAR(100),
    "ActorUserId" VARCHAR(500),
    "ActorYammerUserId" VARCHAR(500),
    "AlertEntityId" VARCHAR(255),
    "AlertId" VARCHAR(255),
    "AlertPolicyId" VARCHAR(255),
    "AlertType" VARCHAR(255),
    "ApplicationId" VARCHAR(255),
    "AzureADAppId" VARCHAR(255),
    "ClientInfoString" TEXT,
    "Comments" TEXT,
    "CorrelationId" VARCHAR(255),
    "CreationDate" TIMESTAMP,
    "CustomUniqueId" VARCHAR(255),
    "Data" TEXT,
    "DataType" VARCHAR(100),
    "EntityType" VARCHAR(100),
    "EventData" TEXT,
    "EventSource" VARCHAR(100),
    "ExceptionInfo" TEXT,
    "FileSizeBytes" BIGINT,
    "InterSystemsId" VARCHAR(255),
    "IntraSystemId" VARCHAR(255),
    "ItemName" TEXT,
    "ItemType" VARCHAR(100),
    "ListId" VARCHAR(255),
    "ListItemUniqueId" VARCHAR(255),
    "LogonError" VARCHAR(500),
    "MailboxGuid" VARCHAR(255),
    "MailboxOwnerMasterAccountSid" VARCHAR(500),
    "MailboxOwnerSid" VARCHAR(500),
    "MailboxOwnerUPN" VARCHAR(500),
    "Name" VARCHAR(500),
    "ObjectId" VARCHAR(500),
    "PolicyDetails" JSONB,
    "PolicyId" VARCHAR(255),
    "RecordVersion" VARCHAR(50),
    "Severity" VARCHAR(50),
    "Site" VARCHAR(500),
    "SiteUrl" TEXT,
    "Source" VARCHAR(255),
    "SourceFileExtension" VARCHAR(50),
    "SourceFileName" TEXT,
    "SourceRelativeUrl" TEXT,
    "Status" VARCHAR(100),
    "Target" JSONB,
    "TargetUserOrGroupName" VARCHAR(500),
    "TargetUserOrGroupType" VARCHAR(100),
    "UniqueSharingId" VARCHAR(255),
    "UserAgent" TEXT,
    "UserDomain" VARCHAR(500),
    "UserSharedWith" VARCHAR(500),
    "RawData" JSONB,
    "ProcessedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "CollectedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit log sync status
CREATE TABLE IF NOT EXISTS public."AuditLogSyncStatus" (
    "Id" SERIAL PRIMARY KEY,
    "TenantId" VARCHAR(255),
    "ContentType" VARCHAR(100),
    "LastSyncTime" TIMESTAMP,
    "LastSuccessfulSync" TIMESTAMP,
    "NextSyncTime" TIMESTAMP,
    "Status" VARCHAR(50),
    "ErrorMessage" TEXT,
    "RecordsProcessed" INTEGER DEFAULT 0,
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "UpdatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT audit_log_sync_unique UNIQUE("TenantId", "ContentType")
);

-- =====================================================
-- CONFIGURATION TABLES
-- =====================================================

-- Configuration table for Azure/Microsoft credentials
CREATE TABLE IF NOT EXISTS public."Configurations" (
    "Id" SERIAL PRIMARY KEY,
    "Name" VARCHAR(255) UNIQUE NOT NULL,
    "TenantId" VARCHAR(255),
    "ClientId" VARCHAR(255),
    "ClientSecret" TEXT,
    "SharePointUrl" TEXT,
    "GraphApiScopes" TEXT,
    "PurviewEndpoint" TEXT,
    "Settings" JSONB,
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "UpdatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Identities table for users and groups
CREATE TABLE IF NOT EXISTS public."Identities" (
    "Id" SERIAL PRIMARY KEY,
    "ClientId" VARCHAR(255) UNIQUE,
    "Name" VARCHAR(500),
    "Email" VARCHAR(500),
    "TenantId" VARCHAR(255),
    "Roles" VARCHAR(100),
    "Department" VARCHAR(500),
    "JobTitle" VARCHAR(500),
    "OfficeLocation" VARCHAR(500),
    "IsActive" BOOLEAN DEFAULT TRUE,
    "LastSeen" TIMESTAMP,
    "Metadata" JSONB,
    "CreatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "UpdatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- PERFORMANCE INDEXES
-- =====================================================

-- SharePoint permissions indexes
CREATE INDEX IF NOT EXISTS idx_sp_permissions_tenant_site ON sharepoint_permissions(tenant_id, site_id);
CREATE INDEX IF NOT EXISTS idx_sp_permissions_resource ON sharepoint_permissions(resource_id);
CREATE INDEX IF NOT EXISTS idx_sp_permissions_principal ON sharepoint_permissions(principal_id);
CREATE INDEX IF NOT EXISTS idx_sp_permissions_collected ON sharepoint_permissions(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_sp_permissions_parent_resource ON sharepoint_permissions(parent_resource_id);

-- SharePoint structure indexes
CREATE INDEX IF NOT EXISTS idx_sp_structure_tenant_site ON sharepoint_structure(tenant_id, site_id);
CREATE INDEX IF NOT EXISTS idx_sp_structure_library ON sharepoint_structure(library_id);
CREATE INDEX IF NOT EXISTS idx_sp_structure_parent ON sharepoint_structure(parent_id);
CREATE INDEX IF NOT EXISTS idx_sp_structure_item_type ON sharepoint_structure(item_type);

-- Group memberships indexes
CREATE INDEX IF NOT EXISTS idx_group_memberships_group ON group_memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_member ON group_memberships(member_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_active ON group_memberships(is_active);

-- External audit logs indexes
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_creation_time ON public."ExternalAuditLogs" ("CreationTime");
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_operation ON public."ExternalAuditLogs" ("Operation");
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_user_id ON public."ExternalAuditLogs" ("UserId");
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_workload ON public."ExternalAuditLogs" ("Workload");
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_record_type ON public."ExternalAuditLogs" ("RecordType");

-- Identities indexes
CREATE INDEX IF NOT EXISTS idx_identities_tenant ON public."Identities"("TenantId");
CREATE INDEX IF NOT EXISTS idx_identities_email ON public."Identities"("Email");
CREATE INDEX IF NOT EXISTS idx_identities_roles ON public."Identities"("Roles");

-- =====================================================
-- DEFAULT DATA INSERTION
-- =====================================================

-- Insert default configuration (will be updated via Settings page)
INSERT INTO public."Configurations" (
    "Name",
    "TenantId",
    "ClientId",
    "ClientSecret",
    "SharePointUrl",
    "GraphApiScopes",
    "PurviewEndpoint",
    "Settings",
    "CreatedAt",
    "UpdatedAt"
) VALUES (
    'Archive',  -- Using 'Archive' for compatibility with existing code
    '',  -- To be configured via Settings page
    '',  -- To be configured via Settings page
    '',  -- To be configured via Settings page
    '',  -- To be configured via Settings page
    'https://graph.microsoft.com/.default',
    'https://manage.office.com',
    '{
        "sync_interval_hours": 24,
        "enable_sharepoint_sync": true,
        "enable_purview_sync": true,
        "max_sync_retries": 3,
        "batch_size": 1000
    }'::jsonb,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
) ON CONFLICT ("Name") DO NOTHING;

-- =====================================================
-- PERMISSIONS SETUP
-- =====================================================

-- Grant necessary permissions (adjust user as needed)
-- These commands will only work if the simplyinspect user exists
DO $$
BEGIN
    -- Check if the user exists before granting permissions
    IF EXISTS (SELECT 1 FROM pg_user WHERE usename = 'simplyinspect') THEN
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO simplyinspect;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO simplyinspect;
        GRANT ALL PRIVILEGES ON SCHEMA public TO simplyinspect;
    END IF;
END
$$;

-- =====================================================
-- MIGRATION TRACKING
-- =====================================================

-- Create migration tracking table to prevent re-running
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Record this migration
INSERT INTO public.schema_migrations (version) 
VALUES ('000_complete_schema') 
ON CONFLICT (version) DO NOTHING;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Uncomment to verify schema creation:
/*
SELECT table_name, table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

SELECT 
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'public'
    AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
ORDER BY tc.table_name, tc.constraint_type;

SELECT 
    schemaname,
    tablename,
    indexname
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
*/