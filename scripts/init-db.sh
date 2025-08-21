#!/bin/bash

# =====================================================
# SimplyInspect Database Initialization Script
# Safe deployment script for database setup
# Runs the consolidated init_database.sql migration
# =====================================================

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "SimplyInspect Database Initialization"
echo "========================================"

# Database connection parameters (from environment or use defaults)
DB_HOST="${DB_HOST:-postgres16-pgvector}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-SD-11}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD}"

echo "Host: $DB_HOST:$DB_PORT"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "========================================"

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is ready!${NC}"
        break
    fi
    echo "PostgreSQL is not ready yet. Retrying in 2 seconds..."
    sleep 2
    retry_count=$((retry_count + 1))
done

if [ $retry_count -eq $max_retries ]; then
    echo -e "${RED}✗ Failed to connect to PostgreSQL after $max_retries attempts${NC}"
    exit 1
fi

# Determine which migration file to use
MIGRATION_FILE=""

# Check for the new consolidated migration first
if [ -f "/app/migrations/init_database.sql" ]; then
    MIGRATION_FILE="/app/migrations/init_database.sql"
    echo "Using consolidated init_database.sql"
elif [ -f "/app/migrations/000_complete_schema.sql" ]; then
    MIGRATION_FILE="/app/migrations/000_complete_schema.sql"
    echo "Using 000_complete_schema.sql"
else
    # Try relative path for local development
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/../migrations/init_database.sql" ]; then
        MIGRATION_FILE="$SCRIPT_DIR/../migrations/init_database.sql"
        echo "Using local init_database.sql"
    elif [ -f "$SCRIPT_DIR/../migrations/000_complete_schema.sql" ]; then
        MIGRATION_FILE="$SCRIPT_DIR/../migrations/000_complete_schema.sql"
        echo "Using local 000_complete_schema.sql"
    else
        echo -e "${RED}✗ No migration file found!${NC}"
        exit 1
    fi
fi

# Check if migrations table exists
echo "Checking migration status..."
MIGRATION_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='schema_migrations');" 2>/dev/null || echo "f")

if [ "$MIGRATION_EXISTS" = "f" ]; then
    echo -e "${YELLOW}Migration tracking table does not exist. Running full initialization...${NC}"
    echo "Applying migration: $MIGRATION_FILE"
    
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < "$MIGRATION_FILE"; then
        echo -e "${GREEN}✓ Database schema initialized successfully!${NC}"
    else
        echo -e "${RED}✗ Migration failed!${NC}"
        exit 1
    fi
else
    # Check if the new consolidated migration has been applied
    INIT_V2_APPLIED=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT EXISTS (SELECT 1 FROM schema_migrations WHERE version='init_database_v2');" 2>/dev/null || echo "f")
    
    if [ "$INIT_V2_APPLIED" = "f" ]; then
        echo -e "${YELLOW}Consolidated migration not yet applied. Running safe update...${NC}"
        echo "Applying migration: $MIGRATION_FILE"
        
        if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME < "$MIGRATION_FILE"; then
            echo -e "${GREEN}✓ Database schema updated successfully!${NC}"
        else
            echo -e "${RED}✗ Migration failed!${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}✓ Database schema is up to date${NC}"
    fi
fi

# Verify critical tables exist
echo ""
echo "Verifying database structure..."
TABLES_TO_CHECK=(
    "sharepoint_permissions" 
    "sharepoint_structure" 
    "sharepoint_libraries"
    "reviewer_library_assignments"
    "group_memberships"
    "users"
    "user_sessions"
    "ExternalAuditLogs" 
    "Configurations"
)

all_tables_exist=true
for table in "${TABLES_TO_CHECK[@]}"; do
    TABLE_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='$table');" 2>/dev/null || echo "f")
    if [ "$TABLE_EXISTS" = "t" ]; then
        echo -e "${GREEN}✓ Table '$table' exists${NC}"
    else
        echo -e "${RED}✗ Table '$table' is missing!${NC}"
        all_tables_exist=false
    fi
done

if [ "$all_tables_exist" = false ]; then
    echo -e "${RED}✗ Some tables are missing. Please check the migration.${NC}"
    exit 1
fi

# Show summary
echo ""
echo "========================================"
echo "Database Summary:"
echo "========================================"

# Count tables
TABLE_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" 2>/dev/null || echo "0")
echo "Total tables: $TABLE_COUNT"

# Count users
USER_COUNT=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM public.users WHERE is_active = TRUE;" 2>/dev/null || echo "0")
echo "Active users: $USER_COUNT"

# Check for admin user
ADMIN_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -tAc "SELECT COUNT(*) FROM public.users WHERE role = 'administrator' AND is_active = TRUE;" 2>/dev/null || echo "0")
if [ "$ADMIN_EXISTS" -gt 0 ]; then
    echo -e "${GREEN}✓ Admin user exists${NC}"
    echo ""
    echo "Default admin credentials:"
    echo "  Email: admin@simplyinspect.com"
    echo "  Password: Admin123!"
    echo -e "${YELLOW}⚠ Please change the admin password after first login${NC}"
fi

echo ""
echo "========================================"
echo -e "${GREEN}✓ Database initialization complete!${NC}"
echo "========================================"