# Deep-Doc-Analysis Production Runbook

## Overview

This runbook provides operational procedures for managing the Deep-Doc-Analysis application deployed on Hetzner infrastructure.

**Target Infrastructure**: Hetzner CX31+ (2 vCPU, 8GB RAM)
**Operating System**: Ubuntu 22.04 LTS
**Deployment Method**: Docker Compose
**Last Updated**: 2025-01-16

---

## 1. Quick Reference

### 1.1 Server Information

```bash
# Server IP
SERVER_IP="<YOUR_HETZNER_IP>"

# Domain
DOMAIN="yourdomain.com"

# SSH Access
ssh root@$SERVER_IP

# Application Directory
APP_DIR="/opt/deepdoc"
```

### 1.2 Service URLs

- **Frontend**: https://yourdomain.com
- **Backend API**: https://yourdomain.com/api/v1
- **Health Check**: https://yourdomain.com/health
- **Metabase**: http://localhost:3001 (SSH tunnel only)

### 1.3 Container Names

- `deep-doc-backend` - FastAPI backend
- `deep-doc-frontend` - React + Nginx frontend
- `deep-doc-metabase` - Analytics dashboard

---

## 2. Common Operations

### 2.1 View Application Logs

```bash
# All services
cd /opt/deepdoc/app
docker-compose -f docker-compose.prod.yml logs -f

# Backend only
docker-compose -f docker-compose.prod.yml logs -f backend

# Frontend only
docker-compose -f docker-compose.prod.yml logs -f frontend

# Last 100 lines
docker logs --tail 100 deep-doc-backend

# Search logs
docker logs deep-doc-backend 2>&1 | grep "ERROR"
```

### 2.2 Restart Services

```bash
# Restart all services
cd /opt/deepdoc/app
docker-compose -f docker-compose.prod.yml restart

# Restart single service
docker-compose -f docker-compose.prod.yml restart backend

# Force recreate containers
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### 2.3 Check Service Status

```bash
# Container status
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml ps

# Detailed container info
docker inspect deep-doc-backend

# Resource usage
docker stats

# Health check
curl -f https://yourdomain.com/health
```

### 2.4 Update Application

```bash
cd /opt/deepdoc/app

# Pull latest code
git pull origin main

# Rebuild containers
docker-compose -f docker-compose.prod.yml build

# Restart with new images
docker-compose -f docker-compose.prod.yml up -d

# Verify
docker-compose -f docker-compose.prod.yml ps
curl -f https://yourdomain.com/health
```

---

## 3. Backup & Restore

### 3.1 Manual Backup

```bash
# Run backup script
/opt/deepdoc/scripts/backup.sh

# Verify backup
/opt/deepdoc/scripts/backup.sh --verify

# Check backup files
ls -lh /opt/deepdoc/backups/*/
```

### 3.2 Restore from Backup

#### Restore Analytics Database

```bash
# Stop backend
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml stop backend

# Restore database
BACKUP_FILE=$(ls -t /opt/deepdoc/backups/analytics/analytics_*.db | head -1)
docker cp "$BACKUP_FILE" deep-doc-backend:/app/analytics.db

# Start backend
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml start backend

# Verify
docker exec deep-doc-backend sqlite3 /app/analytics.db "SELECT COUNT(*) FROM analytics_events;"
```

#### Restore Uploaded Files

```bash
# Find latest backup
BACKUP_FILE=$(ls -t /opt/deepdoc/backups/uploads/uploads_*.tar.gz | head -1)

# Extract to uploads directory
tar -xzf "$BACKUP_FILE" -C /opt/deepdoc/

# Verify
ls -lh /opt/deepdoc/uploads/
```

#### Restore Metabase

```bash
# Stop Metabase
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml stop metabase

# Find latest backup
BACKUP_FILE=$(ls -t /opt/deepdoc/backups/metabase/metabase_*.tar.gz | head -1)

# Extract
tar -xzf "$BACKUP_FILE" -C /tmp/

# Copy to data directory
rm -rf /opt/deepdoc/data/metabase/*
cp -r /tmp/metabase-backup/* /opt/deepdoc/data/metabase/

# Start Metabase
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml start metabase
```

---

## 4. Monitoring

### 4.1 System Health Checks

```bash
# Disk space
df -h /opt/deepdoc

# Memory usage
free -h

# CPU usage
top -bn1 | head -20

# Docker resource usage
docker stats --no-stream
```

### 4.2 Application Health Checks

```bash
# Backend health
curl -f https://yourdomain.com/health
# Expected: {"status":"ok"}

# Frontend
curl -I https://yourdomain.com
# Expected: HTTP/2 200

# Database connection
docker exec deep-doc-backend python -c "
import sqlite3
conn = sqlite3.connect('/app/analytics.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM analytics_events')
print(f'Total events: {cursor.fetchone()[0]}')
"
```

### 4.3 Check Logs for Errors

```bash
# Check for errors in last hour
docker logs --since 1h deep-doc-backend 2>&1 | grep -i error

# Count errors by type
docker logs deep-doc-backend 2>&1 | grep -i error | sort | uniq -c

# Check Nginx errors
tail -100 /var/log/nginx/deepdoc_error.log
```

### 4.4 Monitor API Costs

```bash
# Check Anthropic API usage
docker exec deep-doc-backend python -c "
import sqlite3
conn = sqlite3.connect('/app/analytics.db')
cursor = conn.cursor()
cursor.execute('''
    SELECT
        DATE(timestamp) as date,
        COUNT(*) as queries
    FROM analytics_events
    WHERE event_type = 'query'
    GROUP BY DATE(timestamp)
    ORDER BY date DESC
    LIMIT 7
''')
for row in cursor.fetchall():
    print(f'{row[0]}: {row[1]} queries')
"

# Estimate tokens used (approximate)
# Average query: ~10K input + ~5K output tokens
# Cost: $3/million input, $15/million output
```

---

## 5. Troubleshooting

### 5.1 Backend Won't Start

**Symptoms**: Backend container exits immediately

**Diagnosis**:
```bash
# Check container logs
docker logs deep-doc-backend

# Common issues:
# - Missing environment variables
# - Database connection errors
# - Port already in use
```

**Solutions**:

1. **Missing Environment Variables**:
```bash
# Verify .env.production exists
ls -la /opt/deepdoc/app/.env.production

# Check required variables
grep ANTHROPIC_API_KEY /opt/deepdoc/app/.env.production
grep STYTCH_PROJECT_ID /opt/deepdoc/app/.env.production
```

2. **Port Conflict**:
```bash
# Check if port 8000 is in use
sudo netstat -tlnp | grep :8000

# Kill conflicting process
sudo kill <PID>
```

3. **Database Issues**:
```bash
# Reset analytics database
docker exec deep-doc-backend rm -f /app/analytics.db
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml restart backend
```

### 5.2 Frontend Returns 502 Bad Gateway

**Symptoms**: Nginx returns 502 error

**Diagnosis**:
```bash
# Check if backend is running
docker ps | grep deep-doc-backend

# Check backend health
curl http://localhost:8000/health

# Check Nginx error logs
tail -50 /var/log/nginx/deepdoc_error.log
```

**Solutions**:

1. **Backend is Down**:
```bash
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml start backend
```

2. **Nginx Configuration Issue**:
```bash
# Test Nginx config
nginx -t

# Reload Nginx
systemctl reload nginx
```

3. **Network Issue**:
```bash
# Check Docker network
docker network inspect deep-doc-network

# Recreate network
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml down
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml up -d
```

### 5.3 SSL Certificate Expired

**Symptoms**: Browser shows SSL error

**Diagnosis**:
```bash
# Check certificate expiry
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

**Solutions**:
```bash
# Renew certificate
certbot renew

# Force renewal
certbot renew --force-renewal

# Reload Nginx
systemctl reload nginx
```

### 5.4 High Memory Usage

**Symptoms**: Server slow, OOM errors

**Diagnosis**:
```bash
# Check memory usage
free -h

# Check container memory
docker stats --no-stream

# Check for memory leaks
docker logs deep-doc-backend | grep -i "memory"
```

**Solutions**:

1. **Restart Backend**:
```bash
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml restart backend
```

2. **Increase Swap** (if needed):
```bash
# Create 2GB swap file
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

3. **Upgrade Server**:
- Consider upgrading to CX41 (16GB RAM)

### 5.5 Disk Space Full

**Symptoms**: "No space left on device" errors

**Diagnosis**:
```bash
# Check disk usage
df -h

# Find largest directories
du -sh /opt/deepdoc/* | sort -rh | head -10

# Check Docker disk usage
docker system df
```

**Solutions**:

1. **Clean Old Uploads**:
```bash
# Delete uploads older than 30 days
find /opt/deepdoc/uploads -type f -mtime +30 -delete
```

2. **Clean Docker**:
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Full cleanup
docker system prune -a --volumes
```

3. **Clean Old Logs**:
```bash
# Truncate Docker logs
truncate -s 0 $(docker inspect --format='{{.LogPath}}' deep-doc-backend)
truncate -s 0 $(docker inspect--format='{{.LogPath}}' deep-doc-frontend)
```

4. **Delete Old Backups**:
```bash
# Delete backups older than 30 days
find /opt/deepdoc/backups -type f -mtime +30 -delete
```

### 5.6 Stytch Authentication Fails

**Symptoms**: Users can't log in, magic link errors

**Diagnosis**:
```bash
# Check backend logs for Stytch errors
docker logs deep-doc-backend | grep -i stytch

# Verify environment variables
docker exec deep-doc-backend env | grep STYTCH
```

**Solutions**:

1. **Verify Credentials**:
- Check Stytch dashboard: https://stytch.com/dashboard
- Ensure using production (live) credentials
- Verify domain is whitelisted in Stytch settings

2. **Check CORS**:
```bash
# Verify CORS settings
docker exec deep-doc-backend env | grep CORS
```

3. **Test API Connection**:
```bash
docker exec deep-doc-backend python -c "
import requests
resp = requests.get('https://api.stytch.com/v1/projects/health')
print(resp.status_code)
"
```

---

## 6. Security Operations

### 6.1 Rotate API Keys

#### Anthropic API Key

```bash
# 1. Generate new key from Anthropic Console
# 2. Update environment file
nano /opt/deepdoc/app/.env.production
# Update ANTHROPIC_API_KEY=<new-key>

# 3. Restart backend
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml restart backend

# 4. Verify
curl -f https://yourdomain.com/health
```

#### Stytch Credentials

```bash
# 1. Rotate in Stytch dashboard
# 2. Update .env.production
nano /opt/deepdoc/app/.env.production
# Update STYTCH_PROJECT_ID, STYTCH_SECRET, VITE_STYTCH_PUBLIC_TOKEN

# 3. Rebuild frontend (token is baked in)
cd /opt/deepdoc/app
docker-compose -f docker-compose.prod.yml build frontend

# 4. Restart services
docker-compose -f docker-compose.prod.yml up -d

# 5. Clear user sessions
# Users will need to re-authenticate
```

### 6.2 Review Access Logs

```bash
# Recent access
tail -100 /var/log/nginx/deepdoc_access.log

# Find suspicious IPs
awk '{print $1}' /var/log/nginx/deepdoc_access.log | sort | uniq -c | sort -rn | head -20

# Check for rate limit violations (429 errors)
grep "429" /var/log/nginx/deepdoc_access.log
```

### 6.3 Block Malicious IP

```bash
# Using fail2ban
fail2ban-client set nginx-http-auth banip <IP_ADDRESS>

# Using UFW
ufw deny from <IP_ADDRESS>

# Using Nginx
# Add to /etc/nginx/sites-available/deepdoc:
# deny <IP_ADDRESS>;
nginx -t && systemctl reload nginx
```

---

## 7. Performance Optimization

### 7.1 Database Optimization

```bash
# Vacuum analytics database
docker exec deep-doc-backend sqlite3 /app/analytics.db "VACUUM;"

# Analyze tables
docker exec deep-doc-backend sqlite3 /app/analytics.db "ANALYZE;"

# Check database size
docker exec deep-doc-backend ls -lh /app/analytics.db
```

### 7.2 Clear Old Analytics Data

```bash
# Delete events older than 90 days
docker exec deep-doc-backend sqlite3 /app/analytics.db "
DELETE FROM analytics_events
WHERE timestamp < datetime('now', '-90 days');

VACUUM;
"
```

### 7.3 Optimize Docker Images

```bash
# Rebuild with optimizations
cd /opt/deepdoc/app
docker-compose -f docker-compose.prod.yml build --no-cache

# Clean build cache
docker builder prune
```

---

## 8. Maintenance Windows

### 8.1 Scheduled Downtime

**Recommended Schedule**: Sunday 2-4 AM UTC

**Pre-Maintenance Checklist**:
- [ ] Notify users (if applicable)
- [ ] Create full backup
- [ ] Test rollback procedure
- [ ] Prepare rollback commands

**Maintenance Procedure**:
```bash
# 1. Create backup
/opt/deepdoc/scripts/backup.sh

# 2. Stop services
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml down

# 3. Perform maintenance (updates, migrations, etc.)

# 4. Start services
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml up -d

# 5. Verify
curl -f https://yourdomain.com/health

# 6. Monitor logs for 15 minutes
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml logs -f
```

### 8.2 Emergency Rollback

```bash
# 1. Stop current version
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml down

# 2. Restore previous version from backup
cd /opt/deepdoc/app
git log --oneline -n 5  # Find previous commit
git checkout <previous-commit-hash>

# 3. Restore database if needed
docker cp /opt/deepdoc/backups/analytics/analytics_latest.db \
    deep-doc-backend:/app/analytics.db

# 4. Start services
docker-compose -f docker-compose.prod.yml up -d

# 5. Verify
curl -f https://yourdomain.com/health
```

---

## 9. Disaster Recovery

### 9.1 Complete Server Failure

**Recovery Steps**:

1. **Provision New Hetzner Server** (same specs)

2. **Restore from Backups**:
```bash
# On new server
# 1. Install Docker, Nginx, etc.
/opt/deepdoc/app/deployment/scripts/deploy.sh --init

# 2. Stop services
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml down

# 3. Restore backups from off-site storage
rsync -avz \
    u123456@u123456.your-storagebox.de:/backups/deepdoc/ \
    /opt/deepdoc/backups/

# 4. Restore data
# (See section 3.2 for detailed restore procedures)

# 5. Update DNS to point to new server IP

# 6. Start services
docker-compose -f /opt/deepdoc/app/docker-compose.prod.yml up -d
```

**RTO (Recovery Time Objective)**: 2-4 hours
**RPO (Recovery Point Objective)**: 24 hours (daily backups)

---

## 10. Contact Information

### 10.1 External Services

- **Hetzner Support**: https://console.hetzner.cloud
- **Anthropic Support**: https://console.anthropic.com/settings/support
- **Stytch Support**: https://stytch.com/contact
- **Domain Registrar**: [Your DNS provider]

### 10.2 Useful Links

- **Application Repository**: [Your GitHub repo]
- **Documentation**: /opt/deepdoc/app/docs/
- **Monitoring Dashboard**: [UptimeRobot, etc.]
- **Error Tracking**: [Sentry, etc.]

---

## 11. Appendix

### 11.1 Environment Variables Reference

See `.env.production.template` for full list.

**Critical Variables**:
- `ANTHROPIC_API_KEY` - Claude API access
- `STYTCH_PROJECT_ID` - Authentication project
- `STYTCH_SECRET` - Backend auth secret
- `VITE_STYTCH_PUBLIC_TOKEN` - Frontend auth token
- `BACKEND_CORS_ORIGINS` - Allowed origins

### 11.2 File Locations

```
/opt/deepdoc/
├── app/                    # Application code
├── uploads/                # User uploaded files
├── data/
│   ├── analytics/          # SQLite database
│   └── metabase/           # Metabase database
├── logs/                   # Application logs
├── backups/                # Backup files
└── scripts/                # Operational scripts

/etc/nginx/
└── sites-available/
    └── deepdoc             # Nginx configuration

/var/log/
├── nginx/
│   ├── deepdoc_access.log  # Access logs
│   └── deepdoc_error.log   # Error logs
└── deepdoc-backup.log      # Backup logs
```

### 11.3 Port Reference

- **80**: HTTP (redirects to HTTPS)
- **443**: HTTPS (public)
- **3000**: Frontend (localhost only)
- **3001**: Metabase (localhost only)
- **8000**: Backend API (localhost only)

---

**Last Updated**: 2025-01-16
**Version**: 1.0
**Maintained By**: DevOps Team
