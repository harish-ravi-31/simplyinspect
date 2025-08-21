# SimplyInspect - New Features Deployment Guide

## 🚀 New Features Added

### 1. **PDF Permission Reports**
- Export comprehensive PDF reports of SharePoint permissions
- Includes charts, statistics, and detailed breakdowns
- Respects current filters and user roles

### 2. **Permission Baselines & Change Detection**
- Create permission baselines as "standards" for sites
- Automatic detection of permission changes
- Email notifications when changes are detected
- Review and track changes over time

## 📋 Deployment Steps

### Option 1: Docker Deployment (Recommended)

The migration will run **automatically** when you deploy with Docker:

```bash
# 1. Stop existing containers
docker-compose down

# 2. Rebuild with new features
docker-compose build

# 3. Start services (migration runs automatically)
docker-compose up -d

# 4. Check logs to confirm migration
docker-compose logs api | grep -i migration
```

### Option 2: Manual Deployment

If deploying manually, run the migration first:

```bash
# 1. Run the migration
psql -U postgres -d simplyinspect < migrations/004_permission_baselines.sql

# OR use the provided script
./scripts/run-migration.sh

# 2. Install new Python dependencies
pip install -r requirements.txt

# 3. Restart the application
```

## ⚙️ Configuration

### 1. **Email Notifications Setup**

Add these environment variables to your `docker-compose.yml` or `.env` file:

```yaml
# For Office 365
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=notifications@yourdomain.com
SMTP_PASSWORD=your-password
SMTP_FROM=notifications@yourdomain.com
SMTP_USE_TLS=true

# For Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=app-specific-password
SMTP_FROM=your-email@gmail.com
SMTP_USE_TLS=true
```

### 2. **Change Detection Schedule**

Configure how often to check for changes:

```yaml
# Check every hour (3600 seconds)
CHANGE_DETECTION_ENABLED=true
CHANGE_DETECTION_INTERVAL=3600

# OR use cron expression
CHANGE_DETECTION_CRON=0 */6 * * *  # Every 6 hours
```

## ✅ Verification Steps

After deployment, verify the new features:

### 1. **Check Database Tables**
```sql
-- Connect to database
psql -U postgres -d simplyinspect

-- Verify new tables exist
\dt permission_baselines
\dt permission_changes
\dt notification_queue
\dt notification_recipients
\dt baseline_comparison_cache
```

### 2. **Test PDF Export**
1. Navigate to SharePoint Permissions view
2. Click "Export PDF" button
3. Verify PDF downloads successfully

### 3. **Test Baselines**
1. Navigate to "Permission Baselines" (new menu item)
2. Click "Create Baseline"
3. Select a site and create a baseline
4. Click "Compare" to see current vs baseline

### 4. **Configure Notifications**
1. In Permission Baselines view, click "Notification Settings"
2. Add email recipients
3. Test by making a permission change in SharePoint
4. Wait for the detection interval or manually trigger detection

## 🔍 Monitoring

### Check Migration Status
```bash
# In Docker
docker exec -it simplyinspect-api psql -U postgres -d simplyinspect -c "SELECT * FROM schema_migrations;"

# Should see:
# version                | applied_at
# 004_permission_baselines | 2024-xx-xx
```

### Check Scheduled Jobs
```bash
# View API logs for scheduler
docker-compose logs api | grep -i scheduler

# Should see:
# Scheduled change detection every 3600 seconds
# Scheduler service started successfully
```

### Check Email Queue
```sql
-- View pending notifications
SELECT * FROM notification_queue WHERE status = 'pending';

-- View sent notifications
SELECT * FROM notification_queue WHERE status = 'sent' ORDER BY sent_at DESC LIMIT 10;
```

## 🐛 Troubleshooting

### Migration Fails
```bash
# Check if tables already exist
psql -U postgres -d simplyinspect -c "\dt permission_*"

# If partially created, drop and retry
psql -U postgres -d simplyinspect -c "DROP TABLE IF EXISTS permission_baselines CASCADE;"
psql -U postgres -d simplyinspect < migrations/004_permission_baselines.sql
```

### Emails Not Sending
1. Check SMTP configuration in environment variables
2. Check notification queue: `SELECT * FROM notification_queue WHERE status = 'failed';`
3. Check API logs: `docker-compose logs api | grep -i smtp`
4. Test SMTP credentials with a mail client

### Change Detection Not Running
1. Verify `CHANGE_DETECTION_ENABLED=true`
2. Check scheduler status in logs
3. Manually trigger: POST to `/api/v1/change-detection/detect-all`

## 📖 User Guide

### For Administrators

1. **Create Baselines**
   - Go to Permission Baselines
   - Click "Create Baseline" 
   - Select site and name it (e.g., "Q1 2024 Standard")
   - Set as active to enable monitoring

2. **Configure Notifications**
   - Click "Notification Settings"
   - Add team members who should receive alerts
   - Choose frequency (immediate/daily/weekly)

3. **Review Changes**
   - Check "Recent Changes" section
   - Review detected changes
   - Mark as reviewed when verified

### For Reviewers

1. **Export Reports**
   - Apply filters in SharePoint view
   - Click "Export PDF"
   - Share report with stakeholders

2. **Monitor Changes**
   - View Permission Baselines
   - See changes for assigned sites
   - Compare current state with baseline

## 🔐 Security Notes

- SMTP passwords are never logged
- PDF reports respect role-based access
- Reviewers only see assigned sites
- All changes are audited with timestamps

## 📞 Support

If you encounter issues:
1. Check the logs: `docker-compose logs api`
2. Verify migration: `SELECT * FROM schema_migrations;`
3. Check environment variables are set correctly
4. Ensure PostgreSQL has sufficient connections available

---

**Version:** 2.0.0  
**Release Date:** 2024  
**New Features:** PDF Reports, Permission Baselines, Change Detection, Email Notifications