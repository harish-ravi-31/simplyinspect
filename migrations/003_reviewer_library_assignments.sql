-- Migration: Add reviewer library assignments
-- Description: Allows administrators to assign specific SharePoint libraries to reviewers

-- Create table for storing SharePoint libraries
CREATE TABLE IF NOT EXISTS public.sharepoint_libraries (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(255) NOT NULL,
    site_name VARCHAR(500) NOT NULL,
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

-- Create table for reviewer-library assignments
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

-- Create indexes for performance
CREATE INDEX idx_sharepoint_libraries_site_id ON public.sharepoint_libraries(site_id);
CREATE INDEX idx_sharepoint_libraries_library_id ON public.sharepoint_libraries(library_id);
CREATE INDEX idx_reviewer_assignments_user_id ON public.reviewer_library_assignments(user_id);
CREATE INDEX idx_reviewer_assignments_library_id ON public.reviewer_library_assignments(library_id);
CREATE INDEX idx_reviewer_assignments_active ON public.reviewer_library_assignments(is_active) WHERE is_active = true;

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_sharepoint_libraries_updated_at 
    BEFORE UPDATE ON public.sharepoint_libraries 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for easy access to reviewer assignments with library details
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

-- Add audit log entry for tracking
INSERT INTO public.user_audit_log (user_id, action, details, ip_address, created_at)
VALUES (
    1, -- System user
    'migration',
    '{"migration": "003_reviewer_library_assignments", "description": "Added reviewer library assignment tables"}',
    '127.0.0.1',
    CURRENT_TIMESTAMP
);

-- Grant appropriate permissions (if using specific database roles)
-- GRANT SELECT ON public.sharepoint_libraries TO app_user;
-- GRANT SELECT ON public.reviewer_library_assignments TO app_user;
-- GRANT SELECT ON public.reviewer_library_access TO app_user;