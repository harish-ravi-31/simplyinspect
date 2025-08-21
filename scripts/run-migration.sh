#!/bin/bash

# Run migration script for permission baselines feature
# This script can be used to manually apply the migration if needed

set -e

echo "=========================================="
echo "SimplyInspect Permission Baselines Migration"
echo "=========================================="

# Get database connection parameters from environment or use defaults
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-simplyinspect}
DB_USER=${DB_USER:-postgres}

# Check if running in Docker
if [ -f /.dockerenv ]; then
    DB_HOST=${DB_HOST:-pgvector-postgres-simplyinspect}
fi

echo "Database connection:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Check if migration file exists
MIGRATION_FILE="/app/migrations/004_permission_baselines.sql"
if [ ! -f "$MIGRATION_FILE" ]; then
    MIGRATION_FILE="../migrations/004_permission_baselines.sql"
    if [ ! -f "$MIGRATION_FILE" ]; then
        echo "Error: Migration file not found!"
        echo "Looked for:"
        echo "  - /app/migrations/004_permission_baselines.sql"
        echo "  - ../migrations/004_permission_baselines.sql"
        exit 1
    fi
fi

echo "Migration file found: $MIGRATION_FILE"
echo ""

# Check if migration has already been applied
echo "Checking migration status..."
MIGRATION_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT 1 FROM schema_migrations WHERE version = '004_permission_baselines' LIMIT 1;" 2>/dev/null || echo "")

if [ ! -z "$MIGRATION_EXISTS" ]; then
    echo "✓ Migration '004_permission_baselines' has already been applied."
    echo "  Skipping..."
    exit 0
fi

# Run the migration
echo "Applying migration..."
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $MIGRATION_FILE

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Migration completed successfully!"
    echo ""
    echo "New features available:"
    echo "  - Permission Baselines: Create and manage permission standards"
    echo "  - Change Detection: Automatic monitoring of permission changes"
    echo "  - Email Notifications: Get alerts when permissions change"
    echo "  - PDF Reports: Export comprehensive permission reports"
    echo ""
    echo "Don't forget to:"
    echo "  1. Configure SMTP settings in docker-compose.yml or .env"
    echo "  2. Add notification recipients in the UI"
    echo "  3. Create your first baseline for each site"
else
    echo ""
    echo "✗ Migration failed!"
    echo "Please check the error messages above."
    exit 1
fi