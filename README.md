# SimplyInspect

A focused application for SharePoint permissions inspection and Microsoft Purview audit log analysis.

## Features

- **SharePoint Permissions Analysis**: Comprehensive view of file, folder, and site permissions
- **SharePoint Structure Mapping**: Visual representation of SharePoint document libraries
- **Microsoft Purview Audit Logs**: Collection and analysis of external audit logs
- **Group Membership Sync**: Synchronization with Azure AD/Entra ID groups

## Architecture

SimplyInspect is extracted from the SimplyArchive project and includes only:
- SharePoint permissions and structure analysis
- Microsoft Purview (External Audit Logs) collection
- Identity and group membership management

## Requirements

- PostgreSQL 12+ (uses existing SimplyArchive database)
- Docker and Docker Compose
- Azure AD application with appropriate permissions:
  - `Sites.Read.All` - For SharePoint permissions
  - `Group.Read.All` - For group membership sync
  - `AuditLog.Read.All` - For Purview audit logs

## Installation

### Using Docker Compose (Recommended)

1. Clone the repository
2. Copy `.env.example` to `.env` and configure your settings
3. Run the application:

```bash
docker-compose up -d
```

The application will be available at:
- UI: http://localhost:3001
- API: http://localhost:8000

### Manual Installation

#### Backend
```bash
cd src
pip install -r ../requirements.txt
python -m api
```

#### Frontend
```bash
cd src/ui
npm install
npm run dev
```

## Database Schema

SimplyInspect uses a subset of the SimplyArchive database schema. Run the migration script to create required tables:

```bash
psql -U postgres -d your_database < migrations/001_simply_inspect_schema.sql
```

## Configuration

Key environment variables:

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - PostgreSQL connection
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` - Azure AD authentication
- `SHAREPOINT_URL` - Your SharePoint tenant URL

## API Endpoints

### SharePoint
- `GET /api/v1/sharepoint-simple/sites` - List all SharePoint sites
- `GET /api/v1/sharepoint-simple/item/{item_id}/permissions` - Get item permissions
- `POST /api/v1/sharepoint-simple/group/{group_id}/sync` - Sync group members

### Purview
- `GET /api/v1/external-audit-logs` - List audit logs
- `POST /api/v1/external-audit-logs/sync` - Trigger audit log sync
- `GET /api/v1/external-audit-logs/stats` - Get audit log statistics

### Identity
- `POST /api/v1/identities/sync` - Sync all identities from Entra ID
- `GET /api/v1/identities/groups/{group_id}/members` - Get group members

## Development

### Project Structure
```
simply-inspect/
├── src/
│   ├── api/           # FastAPI application
│   ├── routes/        # API endpoints
│   ├── services/      # Business logic
│   ├── db/            # Database handlers
│   └── ui/            # Vue.js frontend
├── migrations/        # Database migrations
├── docker-compose.yml # Docker configuration
└── requirements.txt   # Python dependencies
```

### Running Tests
```bash
pytest tests/
```

## License

Proprietary - Simply Discover

## Support

For issues and questions, contact the Simply Discover development team.