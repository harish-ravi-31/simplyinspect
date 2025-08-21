# SimplyInspect Database Migrations

## Overview

This directory contains database migration scripts for SimplyInspect. The migrations have been consolidated into a single comprehensive schema file for easier deployment.

## Files

### Primary Schema File
- **`000_complete_schema.sql`** - Complete, consolidated database schema including all tables, indexes, constraints, and default data. **USE THIS FOR NEW INSTALLATIONS.**

### Legacy Migration Files (Historical Reference)
These files are kept for historical reference but should not be used for new installations:
- `001_simply_inspect_schema.sql` - Original base schema
- `002_initial_config.sql` - Initial configuration data
- `003_update_azure_config.sql` - Azure configuration update template
- `004_add_missing_columns.sql` - Added missing columns to sharepoint_permissions
- `005_add_unique_constraint.sql` - Fixed unique constraints

## Usage

### For New Installations

1. Connect to your PostgreSQL database:
```bash
psql -h localhost -p 5433 -U simplyinspect -d simplyinspect
```

2. Run the complete schema:
```sql
\i /path/to/000_complete_schema.sql
```

Or via Docker:
```bash
docker exec -i simplyinspect-db psql -U simplyinspect -d simplyinspect < migrations/000_complete_schema.sql
```

### For Existing Installations

If you have an existing database with partial migrations applied, you can check which migrations have been applied:

```sql
SELECT * FROM schema_migrations ORDER BY applied_at;
```

## Schema Overview

The consolidated schema includes:

### SharePoint Tables
- `sharepoint_permissions` - Stores SharePoint permission data with proper unique constraints
- `sharepoint_structure` - File and folder structure from SharePoint
- `group_memberships` - Cached group membership information
- `group_sync_status` - Tracks group synchronization status

### Purview/Audit Tables
- `ExternalAuditLogs` - Microsoft Purview audit log data
- `AuditLogSyncStatus` - Tracks audit log synchronization

### Configuration Tables
- `Configurations` - Stores Azure credentials and application settings
- `Identities` - User and group identity information

### Key Features
- All necessary columns included (no incremental fixes needed)
- Proper unique constraints on `(resource_id, principal_id)` for SharePoint permissions
- Comprehensive indexes for performance
- Migration tracking table to prevent re-running
- Default configuration record for easy setup

## Configuration

After running the schema, configure your Azure credentials through the SimplyInspect Settings page at http://localhost:3001/settings

## Troubleshooting

### Duplicate Key Errors
The schema includes proper ON CONFLICT clauses to handle duplicate entries gracefully.

### Missing Columns
All columns are included in the consolidated schema, eliminating the need for incremental column additions.

### Permission Issues
The schema automatically grants permissions to the `simplyinspect` user if it exists.

## Database Reset (Warning: Destroys All Data)

If you need to completely reset the database:

```sql
-- WARNING: This will delete all data!
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
\i /path/to/000_complete_schema.sql
```