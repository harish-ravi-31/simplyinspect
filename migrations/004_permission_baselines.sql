-- =====================================================
-- Permission Baselines and Change Detection Schema
-- Migration 004: Add permission baseline tracking
-- =====================================================

-- Permission baselines table for storing standard configurations
CREATE TABLE IF NOT EXISTS public.permission_baselines (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(500),
    site_url TEXT,
    baseline_name VARCHAR(255) NOT NULL,
    baseline_description TEXT,
    baseline_data JSONB NOT NULL, -- Full snapshot of permissions at baseline time
    created_by VARCHAR(500),
    created_by_email VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE, -- Only one baseline can be active per site
    metadata JSONB
);

-- Create unique index to ensure only one active baseline per site
CREATE UNIQUE INDEX unique_active_baseline_per_site 
ON permission_baselines(site_id, is_active) 
WHERE is_active = true;
CREATE INDEX idx_permission_baselines_created_at ON permission_baselines(created_at);

-- Permission changes tracking table
CREATE TABLE IF NOT EXISTS public.permission_changes (
    id SERIAL PRIMARY KEY,
    baseline_id INTEGER REFERENCES permission_baselines(id) ON DELETE CASCADE,
    site_id VARCHAR(500),
    change_type VARCHAR(50) NOT NULL, -- 'added', 'removed', 'modified', 'inheritance_broken', 'inheritance_restored'
    resource_id VARCHAR(500),
    resource_name TEXT,
    resource_type VARCHAR(100),
    principal_id VARCHAR(500),
    principal_name VARCHAR(500),
    principal_email VARCHAR(500),
    principal_type VARCHAR(100),
    old_permission JSONB, -- Previous permission state
    new_permission JSONB, -- Current permission state
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notification_sent BOOLEAN DEFAULT FALSE,
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by VARCHAR(500),
    reviewed_at TIMESTAMP,
    review_notes TEXT,
    metadata JSONB
);

-- Indexes for efficient querying
CREATE INDEX idx_permission_changes_baseline ON permission_changes(baseline_id);
CREATE INDEX idx_permission_changes_site ON permission_changes(site_id);
CREATE INDEX idx_permission_changes_detected ON permission_changes(detected_at);
CREATE INDEX idx_permission_changes_unreviewed ON permission_changes(reviewed, detected_at) WHERE reviewed = false;
CREATE INDEX idx_permission_changes_notification ON permission_changes(notification_sent) WHERE notification_sent = false;

-- Email notification queue for permission changes
CREATE TABLE IF NOT EXISTS public.notification_queue (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50) DEFAULT 'permission_change', -- Can be extended for other notification types
    recipient_email VARCHAR(500) NOT NULL,
    recipient_name VARCHAR(500),
    subject VARCHAR(500) NOT NULL,
    body TEXT NOT NULL,
    html_body TEXT, -- Optional HTML version of email
    priority INTEGER DEFAULT 5, -- 1 = highest, 10 = lowest
    change_summary JSONB, -- Summary of changes for this notification
    related_baseline_id INTEGER REFERENCES permission_baselines(id) ON DELETE SET NULL,
    related_site_id VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    scheduled_for TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- When to send the notification
    sent_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'sending', 'sent', 'failed', 'cancelled'
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    metadata JSONB
);

-- Indexes for notification queue
CREATE INDEX idx_notification_queue_status ON notification_queue(status, scheduled_for) WHERE status IN ('pending', 'failed');
CREATE INDEX idx_notification_queue_recipient ON notification_queue(recipient_email);
CREATE INDEX idx_notification_queue_created ON notification_queue(created_at);

-- Notification recipients configuration
CREATE TABLE IF NOT EXISTS public.notification_recipients (
    id SERIAL PRIMARY KEY,
    site_id VARCHAR(500), -- NULL means global recipient
    recipient_email VARCHAR(500) NOT NULL,
    recipient_name VARCHAR(500),
    notification_types JSONB DEFAULT '["permission_change"]'::jsonb, -- Array of notification types to receive
    is_active BOOLEAN DEFAULT TRUE,
    frequency VARCHAR(50) DEFAULT 'immediate', -- 'immediate', 'daily', 'weekly'
    last_notification_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    CONSTRAINT unique_recipient_per_site UNIQUE(site_id, recipient_email)
);

-- Indexes for recipients
CREATE INDEX idx_notification_recipients_site ON notification_recipients(site_id);
CREATE INDEX idx_notification_recipients_active ON notification_recipients(is_active) WHERE is_active = true;

-- Baseline comparison results cache
CREATE TABLE IF NOT EXISTS public.baseline_comparison_cache (
    id SERIAL PRIMARY KEY,
    baseline_id INTEGER REFERENCES permission_baselines(id) ON DELETE CASCADE,
    site_id VARCHAR(500),
    comparison_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_permissions_baseline INTEGER,
    total_permissions_current INTEGER,
    added_count INTEGER DEFAULT 0,
    removed_count INTEGER DEFAULT 0,
    modified_count INTEGER DEFAULT 0,
    unique_permissions_count INTEGER DEFAULT 0,
    comparison_summary JSONB,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '1 hour'),
    CONSTRAINT unique_comparison_cache UNIQUE(baseline_id, comparison_date)
);

-- Index for cache expiration
CREATE INDEX idx_baseline_comparison_cache_expires ON baseline_comparison_cache(expires_at);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_permission_baselines_updated_at BEFORE UPDATE
    ON permission_baselines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notification_recipients_updated_at BEFORE UPDATE
    ON notification_recipients FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to ensure only one active baseline per site
CREATE OR REPLACE FUNCTION ensure_single_active_baseline()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = TRUE THEN
        -- Deactivate other baselines for the same site
        UPDATE permission_baselines 
        SET is_active = FALSE 
        WHERE site_id = NEW.site_id 
        AND id != NEW.id 
        AND is_active = TRUE;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for single active baseline
CREATE TRIGGER ensure_single_active_baseline_trigger
    BEFORE INSERT OR UPDATE ON permission_baselines
    FOR EACH ROW EXECUTE FUNCTION ensure_single_active_baseline();

-- Sample notification recipients (commented out, uncomment and modify as needed)
-- INSERT INTO notification_recipients (site_id, recipient_email, recipient_name, notification_types) VALUES
-- (NULL, 'admin@company.com', 'System Administrator', '["permission_change", "baseline_update"]'::jsonb),
-- (NULL, 'security@company.com', 'Security Team', '["permission_change"]'::jsonb);

-- Permissions are handled by the database connection user (postgres)
-- No explicit GRANT needed as postgres is superuser

-- Record this migration
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations (version) 
VALUES ('004_permission_baselines') 
ON CONFLICT (version) DO NOTHING;