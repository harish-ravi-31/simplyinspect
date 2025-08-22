# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SimplyInspect is a focused application for SharePoint permissions inspection and Microsoft Purview audit log analysis. It's extracted from the SimplyArchive project and provides:
- SharePoint permissions and structure analysis
- Microsoft Purview (External Audit Logs) collection
- Identity and group membership management with Azure AD/Entra ID sync
- Role-based access control with administrator/reviewer roles

## Common Development Commands

### Running the Application

```bash
# Using Docker Compose (recommended for development)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after changes
docker-compose build --no-cache
docker-compose up -d
```

### Frontend Development

```bash
cd src/ui
npm install
npm run dev    # Development server on port 3000
npm run build  # Production build
```

### Backend Development

```bash
cd src
pip install -r ../requirements.txt
python -m api  # Runs FastAPI on port 8000 with hot reload
```

### Database Operations

```bash
# Initialize new database (uses migrations/000_complete_schema.sql)
psql -h localhost -p 5432 -U postgres -d simplyinspect < migrations/000_complete_schema.sql

# Connect to database
psql -h localhost -p 5432 -U postgres -d simplyinspect

# Reset admin password (standalone script)
python reset_password.py
```

### Deployment

```bash
# Standard deployment with Docker Compose
./deploy.sh

# Standalone deployment (single container)
./deploy-standalone.sh
```

## Architecture

### Tech Stack
- **Backend**: FastAPI (Python 3.9+) with async/await patterns
- **Frontend**: Vue 3 with Vuetify 3 Material Design components
- **Database**: PostgreSQL 12+ with pgvector extension
- **Authentication**: JWT-based with role-based access control
- **Container**: Docker with multi-stage builds

### Project Structure

```
/src/
├── api/              # FastAPI main application entry point
├── routes/           # API endpoints (sharepoint, purview, auth, admin, etc.)
├── services/         # Business logic layer
├── db/               # Database handlers and initialization
├── middleware/       # Authentication and role-based access middleware
├── models/           # Pydantic models for data validation
├── collectors/       # SharePoint and Purview data collectors
└── ui/              # Vue.js frontend application
    ├── src/
    │   ├── views/    # Page components
    │   ├── components/ # Reusable UI components
    │   ├── services/ # API client
    │   └── router/   # Vue Router configuration
    └── package.json
```

### Key API Routes

- **Authentication**: `/api/v1/auth/*` - Login, register, token refresh
- **SharePoint**: `/api/v1/sharepoint-simple/*` - Permissions, structure, sites
- **Purview**: `/api/v1/external-audit-logs/*` - Audit log collection and analysis
- **Identity**: `/api/v1/identities/*` - User and group sync from Entra ID
- **Configuration**: `/api/v1/configuration/*` - Azure AD credentials and settings
- **Admin**: `/api/v1/admin/*` - User management for administrators
- **Baselines**: `/api/v1/baselines/*` - Permission baseline management

### Database Schema

The application uses PostgreSQL with the following key tables:
- `sharepoint_permissions` - SharePoint permission entries with unique constraint on (resource_id, principal_id)
- `sharepoint_structure` - File/folder hierarchy from SharePoint
- `ExternalAuditLogs` - Microsoft Purview audit log entries
- `Configurations` - Azure AD credentials and application settings
- `Users` - Authentication and user management
- `Identities` - Synced users and groups from Entra ID
- `permission_baselines` - Baseline permissions for change detection

### Authentication Flow

1. JWT-based authentication with access and refresh tokens
2. Role-based access: `administrator` (full access) and `reviewer` (limited to assigned libraries)
3. Middleware validates tokens and enforces role permissions on all protected routes
4. Library assignments for reviewers stored in `reviewer_library_assignments` table

### Azure AD Integration

Required Azure AD application permissions:
- `Sites.Read.All` - SharePoint permissions reading
- `Group.Read.All` - Group membership synchronization
- `AuditLog.Read.All` - Purview audit log collection

Configuration stored in database `Configurations` table, managed via UI at `/settings`.

## Important Implementation Notes

1. **Async/Await**: All database operations and external API calls use async/await patterns
2. **Connection Pooling**: Database uses asyncpg for efficient connection pooling
3. **Error Handling**: Comprehensive try/catch blocks with proper logging
4. **CORS**: Configured to allow all origins in development (restrict in production)
5. **Migration System**: Database schema tracked in `schema_migrations` table
6. **Background Tasks**: Scheduler service for periodic syncs (configurable intervals)
7. **Change Detection**: Tracks permission changes between syncs with email notifications

## Environment Variables

Key variables configured in `.env` file:
- Database: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- JWT: `JWT_SECRET_KEY` (must be changed in production)
- Azure: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
- SMTP: Email configuration for notifications
- Change Detection: `CHANGE_DETECTION_ENABLED`, `CHANGE_DETECTION_INTERVAL`

## Deployment Considerations

- Application runs on ports: API (8000/8001), UI (3001), Database (5432)
- Docker images use multi-stage builds for optimization
- nginx serves static frontend files and proxies API requests
- Health check endpoint at `/health` for monitoring
- Supports both Docker Compose and standalone Docker deployment

### Azure Deployment

The application can be deployed to Azure Container Instances using the provided deployment script:

```bash
# Deploy to Azure
./azure-deployment/deploy-azure.sh
```

**Default Admin Credentials** (created automatically):
- **Email**: admin@simplyinspect.com
- **Password**: Admin123!

**Important**: Change default credentials in production!

### Deployment Lessons Learned

Based on deployment experience, key considerations:

1. **PostgreSQL Version**: Use PostgreSQL 16+ to support all migration syntax (UNIQUE constraints with NULLS NOT DISTINCT)
2. **Password Hashing**: Admin user passwords must be created using the application's `AuthService` to ensure proper bcrypt format compatibility with passlib
3. **Migration Validation**: Always verify database migrations completed successfully before proceeding
4. **Health Checks**: Wait for API container to respond to health checks before testing login functionality
5. **Environment Variables**: Validate all required configuration values before deployment

### Common Issues and Troubleshooting

**Login Issues (401/500 errors)**:
1. Check if admin user exists: `SELECT * FROM users WHERE email = 'admin@simplyinspect.com';`
2. Verify password hash format: Hash should start with `$2b$12$` (no backslash escaping)
3. Regenerate password hash using application's AuthService if needed
4. Check API container logs: `az container logs --resource-group <rg> --name <container-group> --container-name simplyinspect-api`

**Migration Failures**:
1. Ensure PostgreSQL version 16+ is used
2. Check for syntax compatibility issues in migration files
3. Verify database connection parameters are correct
4. Check container logs for specific migration errors

**502 Bad Gateway Errors**:
1. Verify API container is running and healthy
2. Check nginx proxy configuration in UI container
3. Ensure containers can communicate via localhost within the container group
4. Test API health endpoint directly: `/health`