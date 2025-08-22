-- =====================================================
-- SimplyInspect Authentication Schema
-- Adds user authentication and role-based access control
-- Version: 1.0
-- =====================================================

-- =====================================================
-- USERS TABLE
-- =====================================================

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
    
    -- Approval tracking
    approved_by INTEGER REFERENCES public.users(id),
    approved_at TIMESTAMP,
    rejection_reason TEXT,
    
    -- Timestamps
    last_login TIMESTAMP,
    password_changed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- USER SESSIONS TABLE (for tracking active sessions)
-- =====================================================

CREATE TABLE IF NOT EXISTS public.user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token_jti VARCHAR(255) UNIQUE NOT NULL, -- JWT ID for tracking
    ip_address VARCHAR(45),
    user_agent TEXT,
    expires_at TIMESTAMP NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- USER AUDIT LOG TABLE
-- =====================================================

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

-- =====================================================
-- PASSWORD RESET TOKENS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS public.password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- USER NOTIFICATIONS TABLE (for approval notifications)
-- =====================================================

CREATE TABLE IF NOT EXISTS public.user_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES public.users(id),
    type VARCHAR(50) NOT NULL, -- 'user_registered', 'user_approved', 'user_rejected', etc.
    title VARCHAR(255) NOT NULL,
    message TEXT,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ROLE PERMISSIONS TABLE (for future extensibility)
-- =====================================================

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
-- INDEXES FOR PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_approved ON public.users(is_approved);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON public.users(is_active);

CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON public.user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token_jti ON public.user_sessions(token_jti);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON public.user_sessions(expires_at);

CREATE INDEX IF NOT EXISTS idx_user_audit_log_user_id ON public.user_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_user_audit_log_action ON public.user_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_user_audit_log_created_at ON public.user_audit_log(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON public.password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON public.password_reset_tokens(user_id);

CREATE INDEX IF NOT EXISTS idx_user_notifications_user_id ON public.user_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_user_notifications_is_read ON public.user_notifications(is_read);

-- =====================================================
-- DEFAULT ROLE PERMISSIONS
-- =====================================================

-- Administrator permissions (full access)
INSERT INTO public.role_permissions (role, resource, action) VALUES
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
    ('administrator', 'settings', 'write')
ON CONFLICT (role, resource, action) DO NOTHING;

-- Reviewer permissions (read-only for most resources)
INSERT INTO public.role_permissions (role, resource, action) VALUES
    ('reviewer', 'users', 'read_self'),  -- Can only read own profile
    ('reviewer', 'sharepoint', 'read'),
    ('reviewer', 'purview', 'read'),
    ('reviewer', 'settings', 'read')
ON CONFLICT (role, resource, action) DO NOTHING;

-- =====================================================
-- DEFAULT ADMIN USER (password: Admin123!)
-- You should change this password immediately after first login
-- =====================================================

INSERT INTO public.users (
    email,
    username,
    password_hash,
    full_name,
    role,
    is_approved,
    is_active,
    created_at
) VALUES (
    'admin@simplyinspect.com',
    'admin',
    '$2b$12$Myqe6R9HUbuAVsad5vFhEu/ZhvbBb/7qqFdQjiiT8Zm11eypkiCVK', -- Admin123!
    'System Administrator',
    'administrator',
    TRUE,
    TRUE,
    CURRENT_TIMESTAMP
) ON CONFLICT (email) DO NOTHING;

-- =====================================================
-- TRIGGER FOR UPDATED_AT TIMESTAMP
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- MIGRATION TRACKING
-- =====================================================

INSERT INTO public.schema_migrations (version) 
VALUES ('001_authentication_schema') 
ON CONFLICT (version) DO NOTHING;

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_user WHERE usename = 'simplyinspect') THEN
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO simplyinspect;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO simplyinspect;
    END IF;
END
$$;