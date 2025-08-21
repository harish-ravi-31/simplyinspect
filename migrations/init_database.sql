-- =====================================================
-- SimplyInspect Complete Database Initialization Script
-- Safe for both new installations and existing databases
-- Version: 2.0 - Fully Idempotent
-- =====================================================
-- This script can be run multiple times safely without data loss
-- It creates all necessary tables, indexes, and constraints
-- It will skip creation if objects already exist
-- =====================================================

-- Start transaction for atomic execution
BEGIN;

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to check if a constraint exists
CREATE OR REPLACE FUNCTION constraint_exists(
    p_constraint_name TEXT,
    p_table_name TEXT DEFAULT NULL
) RETURNS BOOLEAN AS $$
BEGIN
    IF p_table_name IS NULL THEN
        RETURN EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = p_constraint_name
        );
    ELSE
        RETURN EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = p_constraint_name 
            AND table_name = p_table_name
        );
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Function to safely add columns if they don't exist
CREATE OR REPLACE FUNCTION add_column_if_not_exists(
    p_table_name TEXT,
    p_column_name TEXT,
    p_column_definition TEXT
) RETURNS VOID AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = p_table_name 
        AND column_name = p_column_name
    ) THEN
        EXECUTE format('ALTER TABLE %I ADD COLUMN %I %s', 
            p_table_name, p_column_name, p_column_definition);
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- MIGRATION TRACKING TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- =====================================================
-- SHAREPOINT PERMISSIONS TABLES
-- =====================================================

-- Main SharePoint permissions table
CREATE TABLE IF NOT EXISTS public.sharepoint_permissions (
    permission_id SERIAL PRIMARY KEY,
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
    parent_resource_id VARCHAR(500),
    parent_resource_name TEXT,
    parent_resource_type VARCHAR(100),
    inherited_from_parent BOOLEAN DEFAULT false,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- Add unique constraint if it doesn't exist (handle both old and new constraint names)
DO $$
BEGIN
    -- Drop old constraint if it exists with wrong name
    IF constraint_exists('sharepoint_permissions_unique', 'sharepoint_permissions') THEN
        ALTER TABLE sharepoint_permissions 
        DROP CONSTRAINT sharepoint_permissions_unique;
    END IF;
    
    -- Add correct constraint if it doesn't exist
    IF NOT constraint_exists('sharepoint_permissions_resource_principal_unique', 'sharepoint_permissions') THEN
        ALTER TABLE sharepoint_permissions 
        ADD CONSTRAINT sharepoint_permissions_resource_principal_unique 
        UNIQUE (resource_id, principal_id);
    END IF;
END $$;

-- SharePoint structure table
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

-- Group memberships table
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
    metadata JSONB
);

-- Add unique constraint if it doesn't exist
DO $$
BEGIN
    IF NOT constraint_exists('group_memberships_unique', 'group_memberships') THEN
        ALTER TABLE group_memberships 
        ADD CONSTRAINT group_memberships_unique 
        UNIQUE(group_id, member_id);
    END IF;
END $$;

-- Group sync status table
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
-- AUTHENTICATION TABLES
-- =====================================================

-- Users table
CREATE TABLE IF NOT EXISTS public.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'reviewer' CHECK (role IN ('administrator', 'reviewer')),
    is_approved BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    department VARCHAR(255),
    company VARCHAR(255),
    phone VARCHAR(50),
    approved_by INTEGER REFERENCES public.users(id),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    last_login TIMESTAMP,
    password_changed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User sessions table
CREATE TABLE IF NOT EXISTS public.user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User audit log table
CREATE TABLE IF NOT EXISTS public.user_audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES public.users(id),
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_id INTEGER REFERENCES public.user_sessions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password reset tokens table
CREATE TABLE IF NOT EXISTS public.password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User notifications table
CREATE TABLE IF NOT EXISTS public.user_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES public.users(id),
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Role permissions table
CREATE TABLE IF NOT EXISTS public.role_permissions (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    is_allowed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role, resource, action)
);

-- =====================================================
-- REVIEWER LIBRARY ASSIGNMENTS
-- =====================================================

-- SharePoint libraries table
CREATE TABLE IF NOT EXISTS public.sharepoint_libraries (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(255) NOT NULL,
    site_name VARCHAR(500),
    site_url TEXT,
    library_id VARCHAR(255) NOT NULL,
    library_name VARCHAR(500) NOT NULL,
    library_url TEXT,
    item_count INTEGER DEFAULT 0,
    last_synced TIMESTAMP,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, library_id)
);

-- Add site_url column if it doesn't exist (for backward compatibility)
SELECT add_column_if_not_exists('sharepoint_libraries', 'site_url', 'TEXT');

-- Reviewer library assignments table
CREATE TABLE IF NOT EXISTS public.reviewer_library_assignments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    library_id INTEGER NOT NULL REFERENCES public.sharepoint_libraries(id) ON DELETE CASCADE,
    assigned_by INTEGER REFERENCES public.users(id),
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    permissions JSONB DEFAULT '{"can_view": true, "can_export": false, "can_analyze": true}',
    notes TEXT,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(user_id, library_id)
);

-- =====================================================
-- PURVIEW / EXTERNAL AUDIT LOGS TABLES
-- =====================================================

-- External audit logs table
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

-- Audit log sync status table
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
    "UpdatedAt" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add unique constraint if it doesn't exist
DO $$
BEGIN
    IF NOT constraint_exists('audit_log_sync_unique', '"AuditLogSyncStatus"') THEN
        ALTER TABLE "AuditLogSyncStatus" 
        ADD CONSTRAINT audit_log_sync_unique 
        UNIQUE("TenantId", "ContentType");
    END IF;
END $$;

-- =====================================================
-- CONFIGURATION TABLES
-- =====================================================

-- Configuration table
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

-- Identities table
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
-- CREATE INDEXES (IF NOT EXISTS)
-- =====================================================

-- SharePoint permissions indexes
CREATE INDEX IF NOT EXISTS idx_sp_permissions_tenant_site 
    ON sharepoint_permissions(tenant_id, site_id);
CREATE INDEX IF NOT EXISTS idx_sp_permissions_resource 
    ON sharepoint_permissions(resource_id);
CREATE INDEX IF NOT EXISTS idx_sp_permissions_principal 
    ON sharepoint_permissions(principal_id);
CREATE INDEX IF NOT EXISTS idx_sp_permissions_collected 
    ON sharepoint_permissions(collected_at DESC);
CREATE INDEX IF NOT EXISTS idx_sp_permissions_parent_resource 
    ON sharepoint_permissions(parent_resource_id);
CREATE INDEX IF NOT EXISTS idx_sp_permissions_permission_type 
    ON sharepoint_permissions(permission_type);

-- SharePoint structure indexes
CREATE INDEX IF NOT EXISTS idx_sp_structure_tenant_site 
    ON sharepoint_structure(tenant_id, site_id);
CREATE INDEX IF NOT EXISTS idx_sp_structure_library 
    ON sharepoint_structure(library_id);
CREATE INDEX IF NOT EXISTS idx_sp_structure_parent 
    ON sharepoint_structure(parent_id);
CREATE INDEX IF NOT EXISTS idx_sp_structure_item_type 
    ON sharepoint_structure(item_type);

-- Group memberships indexes
CREATE INDEX IF NOT EXISTS idx_group_memberships_group 
    ON group_memberships(group_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_member 
    ON group_memberships(member_id);
CREATE INDEX IF NOT EXISTS idx_group_memberships_active 
    ON group_memberships(is_active);

-- User indexes
CREATE INDEX IF NOT EXISTS idx_users_email 
    ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_username 
    ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_users_role 
    ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_approved 
    ON public.users(is_approved);
CREATE INDEX IF NOT EXISTS idx_users_is_active 
    ON public.users(is_active);

-- User sessions indexes
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id 
    ON public.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_jti 
    ON public.user_sessions(token_jti);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at 
    ON public.user_sessions(expires_at);

-- User audit log indexes
CREATE INDEX IF NOT EXISTS idx_user_audit_log_user_id 
    ON public.user_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_audit_log_action 
    ON public.user_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_user_audit_log_created_at 
    ON public.user_audit_log(created_at DESC);

-- Library assignment indexes
CREATE INDEX IF NOT EXISTS idx_sharepoint_libraries_site_id 
    ON public.sharepoint_libraries(site_id);
CREATE INDEX IF NOT EXISTS idx_sharepoint_libraries_library_id 
    ON public.sharepoint_libraries(library_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_assignments_user_id 
    ON public.reviewer_library_assignments(user_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_assignments_library_id 
    ON public.reviewer_library_assignments(library_id);
CREATE INDEX IF NOT EXISTS idx_reviewer_assignments_active 
    ON public.reviewer_library_assignments(is_active) WHERE is_active = true;

-- External audit logs indexes
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_creation_time 
    ON public."ExternalAuditLogs" ("CreationTime");
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_operation 
    ON public."ExternalAuditLogs" ("Operation");
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_user_id 
    ON public."ExternalAuditLogs" ("UserId");
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_workload 
    ON public."ExternalAuditLogs" ("Workload");
CREATE INDEX IF NOT EXISTS idx_external_audit_logs_record_type 
    ON public."ExternalAuditLogs" ("RecordType");

-- Identities indexes
CREATE INDEX IF NOT EXISTS idx_identities_tenant 
    ON public."Identities"("TenantId");
CREATE INDEX IF NOT EXISTS idx_identities_email 
    ON public."Identities"("Email");
CREATE INDEX IF NOT EXISTS idx_identities_roles 
    ON public."Identities"("Roles");

-- =====================================================
-- CREATE OR REPLACE VIEWS
-- =====================================================

-- Reviewer library access view
CREATE OR REPLACE VIEW public.reviewer_library_access AS
SELECT 
    rla.id as assignment_id,
    rla.user_id,
    u.email as user_email,
    u.full_name as user_name,
    sl.id as library_id,
    sl.site_id,
    sl.site_name,
    sl.library_id as sp_library_id,
    sl.library_name,
    sl.library_url,
    sl.item_count,
    rla.permissions,
    rla.assigned_at,
    rla.assigned_by,
    admin.full_name as assigned_by_name,
    rla.is_active
FROM public.reviewer_library_assignments rla
JOIN public.users u ON rla.user_id = u.id
JOIN public.sharepoint_libraries sl ON rla.library_id = sl.id
LEFT JOIN public.users admin ON rla.assigned_by = admin.id
WHERE rla.is_active = true AND u.is_active = true;

-- =====================================================
-- CREATE OR REPLACE FUNCTIONS
-- =====================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- =====================================================
-- CREATE TRIGGERS (DROP AND RECREATE TO ENSURE CONSISTENCY)
-- =====================================================

-- Users table trigger
DROP TRIGGER IF EXISTS update_users_updated_at ON public.users;
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- SharePoint libraries trigger
DROP TRIGGER IF EXISTS update_sharepoint_libraries_updated_at ON public.sharepoint_libraries;
CREATE TRIGGER update_sharepoint_libraries_updated_at 
    BEFORE UPDATE ON public.sharepoint_libraries 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- DEFAULT DATA (INSERT ONLY IF NOT EXISTS)
-- =====================================================

-- Default configuration
INSERT INTO public."Configurations" (
    "Name", "TenantId", "ClientId", "ClientSecret",
    "SharePointUrl", "GraphApiScopes", "PurviewEndpoint", "Settings"
) VALUES (
    'Archive', '', '', '',
    '', 'https://graph.microsoft.com/.default',
    'https://manage.office.com',
    '{
        "sync_interval_hours": 24,
        "enable_sharepoint_sync": true,
        "enable_purview_sync": true,
        "max_sync_retries": 3,
        "batch_size": 1000
    }'::jsonb
) ON CONFLICT ("Name") DO NOTHING;

-- Default admin user (only if no admin exists)
INSERT INTO public.users (
    email, username, password_hash, full_name,
    role, is_approved, is_active, company
) 
SELECT 
    'admin@simplyinspect.com', 'admin',
    '$2b$12$K6HXYqVVjNZH4dQXsNnYVuGXjLV5GYKxGZEGJYnXGZQKxVXJZ5j7i', -- Admin123!
    'System Administrator', 'administrator', TRUE, TRUE, 'SimplyInspect'
WHERE NOT EXISTS (
    SELECT 1 FROM public.users WHERE role = 'administrator' AND is_active = TRUE
);

-- Default role permissions
INSERT INTO public.role_permissions (role, resource, action) VALUES
    -- Administrator permissions
    ('administrator', 'users', 'create'),
    ('administrator', 'users', 'read'),
    ('administrator', 'users', 'update'),
    ('administrator', 'users', 'delete'),
    ('administrator', 'users', 'approve'),
    ('administrator', 'sharepoint', 'read'),
    ('administrator', 'sharepoint', 'write'),
    ('administrator', 'sharepoint', 'delete'),
    ('administrator', 'purview', 'read'),
    ('administrator', 'purview', 'write'),
    ('administrator', 'purview', 'delete'),
    ('administrator', 'settings', 'read'),
    ('administrator', 'settings', 'write'),
    -- Reviewer permissions
    ('reviewer', 'users', 'read_self'),
    ('reviewer', 'sharepoint', 'read'),
    ('reviewer', 'purview', 'read'),
    ('reviewer', 'settings', 'read')
ON CONFLICT (role, resource, action) DO NOTHING;

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================

DO $$
BEGIN
    -- Grant permissions if the user exists
    IF EXISTS (SELECT 1 FROM pg_user WHERE usename = 'simplyinspect') THEN
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO simplyinspect;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO simplyinspect;
        GRANT ALL PRIVILEGES ON SCHEMA public TO simplyinspect;
    END IF;
    
    -- Also grant to the common postgres user if different
    IF EXISTS (SELECT 1 FROM pg_user WHERE usename = 'postgres') THEN
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;
    END IF;
END $$;

-- =====================================================
-- RECORD MIGRATION
-- =====================================================

INSERT INTO public.schema_migrations (version, description) 
VALUES (
    'init_database_v2', 
    'Complete consolidated initialization script - fully idempotent'
) ON CONFLICT (version) DO NOTHING;

-- =====================================================
-- CLEANUP HELPER FUNCTIONS
-- =====================================================

DROP FUNCTION IF EXISTS constraint_exists(TEXT, TEXT);
DROP FUNCTION IF EXISTS add_column_if_not_exists(TEXT, TEXT, TEXT);

-- =====================================================
-- FINAL VERIFICATION
-- =====================================================

DO $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
    user_count INTEGER;
BEGIN
    -- Count tables
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';
    
    -- Count indexes
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes 
    WHERE schemaname = 'public';
    
    -- Count users
    SELECT COUNT(*) INTO user_count
    FROM public.users 
    WHERE is_active = TRUE;
    
    RAISE NOTICE 'Database initialization complete:';
    RAISE NOTICE '  Tables created: %', table_count;
    RAISE NOTICE '  Indexes created: %', index_count;
    RAISE NOTICE '  Active users: %', user_count;
END $$;

-- Commit the transaction
COMMIT;

-- =====================================================
-- POST-DEPLOYMENT NOTES
-- =====================================================
-- 1. Default admin credentials: admin@simplyinspect.com / Admin123!
-- 2. Configure Azure settings through the UI at /settings
-- 3. This script is fully idempotent and can be run multiple times
-- 4. No data will be lost when re-running this script
-- =====================================================