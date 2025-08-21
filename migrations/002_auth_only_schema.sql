-- =====================================================
-- SimplyInspect Authentication Schema Only  
-- Creates only the authentication tables needed for user management
-- Version: 1.0
-- =====================================================

-- =====================================================
-- AUTHENTICATION SYSTEM TABLES
-- =====================================================

-- Users table with authentication and profile information
CREATE TABLE IF NOT EXISTS public.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'reviewer' CHECK (role IN ('administrator', 'reviewer')),
    
    -- Profile information
    department VARCHAR(255),
    company VARCHAR(255),
    phone VARCHAR(50),
    
    -- Account status
    is_approved BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Approval tracking
    approved_by INTEGER REFERENCES public.users(id),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    
    -- Security tracking
    last_login TIMESTAMP,
    password_changed_at TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    
    -- Audit timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User sessions for JWT token management
CREATE TABLE IF NOT EXISTS public.user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE
);

-- User audit log for tracking authentication and administrative actions
CREATE TABLE IF NOT EXISTS public.user_audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password reset tokens
CREATE TABLE IF NOT EXISTS public.password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User notifications system
CREATE TABLE IF NOT EXISTS public.user_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    data JSONB,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Role permissions mapping (for future extensibility)
CREATE TABLE IF NOT EXISTS public.role_permissions (
    id SERIAL PRIMARY KEY,
    role VARCHAR(50) NOT NULL,
    permission VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(role, permission)
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

-- User table indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users (email);
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users (username);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users (role);
CREATE INDEX IF NOT EXISTS idx_users_is_approved ON public.users (is_approved);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users (is_active);
CREATE INDEX IF NOT EXISTS idx_users_approved_by ON public.users (approved_by);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON public.users (created_at);

-- Session table indexes  
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON public.user_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_jti ON public.user_sessions (token_jti);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON public.user_sessions (expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_is_active ON public.user_sessions (is_active);

-- Audit log indexes
CREATE INDEX IF NOT EXISTS idx_user_audit_log_user_id ON public.user_audit_log (user_id);
CREATE INDEX IF NOT EXISTS idx_user_audit_log_action ON public.user_audit_log (action);
CREATE INDEX IF NOT EXISTS idx_user_audit_log_created_at ON public.user_audit_log (created_at);

-- Password reset token indexes
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON public.password_reset_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON public.password_reset_tokens (token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON public.password_reset_tokens (expires_at);

-- Notification indexes
CREATE INDEX IF NOT EXISTS idx_user_notifications_user_id ON public.user_notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_user_notifications_type ON public.user_notifications (type);
CREATE INDEX IF NOT EXISTS idx_user_notifications_read_at ON public.user_notifications (read_at);
CREATE INDEX IF NOT EXISTS idx_user_notifications_created_at ON public.user_notifications (created_at);

-- Permission indexes
CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON public.role_permissions (role);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission ON public.role_permissions (permission);

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Create default administrator user (password: AdminPassword123!)
INSERT INTO public.users (
    email, 
    username, 
    password_hash, 
    full_name, 
    role, 
    is_approved, 
    is_active,
    company,
    created_at,
    updated_at
) 
SELECT 
    'admin@simplyinspect.com',
    'admin',
    '$2b$12$5vHZQS0JjjJGYqoGm8tK6eH7Q8q7KPEoXj9WfV8LHZ5z.2K6sPpIG',
    'System Administrator',
    'administrator',
    true,
    true,
    'SimplyInspect',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
WHERE NOT EXISTS (
    SELECT 1 FROM public.users WHERE email = 'admin@simplyinspect.com'
);

-- Insert default role permissions
INSERT INTO public.role_permissions (role, permission) 
SELECT * FROM (VALUES
    ('administrator', 'user_management'),
    ('administrator', 'system_configuration'),
    ('administrator', 'audit_log_access'),
    ('administrator', 'sharepoint_analysis'),
    ('administrator', 'purview_analysis'),
    ('reviewer', 'sharepoint_analysis'),
    ('reviewer', 'purview_analysis')
) AS v(role, permission)
WHERE NOT EXISTS (
    SELECT 1 FROM public.role_permissions 
    WHERE role_permissions.role = v.role 
    AND role_permissions.permission = v.permission
);

-- =====================================================
-- MIGRATION COMPLETION LOG
-- =====================================================
-- This will be logged by the migration system automatically