#!/bin/bash

set -e

echo "=========================================="
echo "SimplyInspect Container Starting"
echo "=========================================="

# Wait for database to be ready
echo "Waiting for database..."
until PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
  echo "Database is unavailable - sleeping"
  sleep 2
done

echo "✓ Database is ready!"

# The Python application will handle migrations through init_database.py
# But we'll check if the new migration needs to be applied
echo "Checking for pending migrations..."

# Check if the permission baselines migration has been applied
MIGRATION_EXISTS=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT 1 FROM schema_migrations WHERE version = '004_permission_baselines' LIMIT 1;" 2>/dev/null || echo "")

if [ -z "$MIGRATION_EXISTS" ]; then
    echo "Applying permission baselines migration..."
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f /app/migrations/004_permission_baselines.sql
    if [ $? -eq 0 ]; then
        echo "✓ Permission baselines migration applied successfully"
    else
        echo "⚠ Warning: Permission baselines migration failed, but continuing..."
    fi
else
    echo "✓ Permission baselines migration already applied"
fi

echo ""
echo "Starting API server..."
echo "=========================================="

# Execute the main command
exec "$@"