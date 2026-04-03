# Production Deployment Guide - Logo Generator

> **Status**: All critical security and reliability issues resolved ✅

This guide covers deploying the Logo Generator to production after the comprehensive audit fixes.

## Critical Fixes Implemented

### 🔒 Security Fixes

#### 1. CORS Configuration (`app.py`)
- **Fixed**: Replaced wildcard origins with explicit allowlist
- **Changed**: `allow_origins=["*"]` → configured via `ALLOWED_ORIGINS` env var
- **Impact**: Prevents CSRF and unauthorized cross-origin requests with credentials
- **Setup**:
  ```bash
  ALLOWED_ORIGINS=https://app.yourdomain.com,https://mobile.yourdomain.com
  ```

#### 2. Authentication on Protected Endpoints
- **Fixed**: `/history` and `/ws/progress/{job_id}` now require valid JWT
- **Changed**: Removed unauthenticated access paths
- **Job Ownership**: Users can only access their own job history and WS updates
- **Impact**: Prevents job enumeration attacks and data leakage between users

#### 3. DEV_TOKEN Bypass Gating (`dependencies.py`)
- **Fixed**: Dev tokens automatically rejected in production
- **Changed**: Checks `ENV=production` env var, fails if DEV_TOKEN used
- **Impact**: Eliminates backdoor authentication in prod
- **Setup**:
  ```bash
  ENV=production
  # DEV_TOKEN will be rejected even if set
  ```

#### 4. Clerk JWT Validation
- **Fixed**: `verify_aud=True` enforced in production
- **Changed**: Enabled audience validation to prevent JWT reuse across services
- **New**: `CLERK_AUDIENCE` env var for validation
- **Setup**:
  ```bash
  CLERK_JWKS_URL=https://your-instance.clerk.accounts.com/.well-known/jwks.json
  CLERK_AUDIENCE=https://api.yourdomain.com
  ```

#### 5. Frontend Secrets Protection
- **Verified**: No R2 credentials in JavaScript bundle
- **Safe**: Backend-only env vars never bundled (no `NEXT_PUBLIC_` prefix)
- **Check**:
  ```bash
  # In .env.local, ensure these have NO NEXT_PUBLIC_ prefix:
  # ✅ CORRECT (server-side only):
  NEXT_PUBLIC_API_URL=https://api.yourdomain.com
  
  # ❌ WRONG (exposed to browser):
  NEXT_PUBLIC_R2_ACCESS_KEY=...  # Never do this!
  ```

### ⚙️ Reliability Fixes

#### 1. Redis Connection Pooling (`app.py`)
- **Fixed**: Pool created at startup, reused across requests
- **Changed**: From per-request creation to singleton pattern
- **Impact**: Prevents Redis connection exhaustion at scale
- **Monitoring**: Check pool health with `/api/health`

#### 2. ARQ Job Result TTL (`dalle_worker.py`, `gemini_worker.py`)
- **Fixed**: Jobs expire after 2 days (172800 seconds)
- **Changed**: Added `result_ttl=172800` to WorkerSettings
- **Impact**: Prevents Redis memory bloat from dead results
- **Config**: Adjust in worker settings if needed

#### 3. WebSocket Exponential Backoff (`routers.py`)
- **Fixed**: Polling interval increases from 0.5s → 4s max
- **Changed**: From fixed 2s intervals to dynamic backoff
- **Impact**: Reduces load on server under heavy queue depth
- **Algorithm**: `interval = min(4.0, 0.5 * 2^(attempts-1))`

#### 4. WebSocket Error Handling
- **Fixed**: Comprehensive auth validation before accepting connection
- **Changed**: Added user_id verification for job ownership
- **Impact**: Prevents unauthorized access to job progress

### 🏗️ Architecture Improvements

#### 1. Structured Logging (`logging_config.py`)
- **Replaced**: All `print()` statements with structured logging
- **Format**: JSON in production, human-readable in dev
- **Features**:
  - Automatic request ID tracking
  - Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  - Rotating file logging support
  - Sentry integration

#### 2. Observability & Metrics (`observability.py`)
- **Added**: Metrics collection framework
- **Tracks**:
  - Generation latency per generator
  - R2 upload performance
  - Queue depth
  - Error rates and types
  - HTTP request metrics
- **Export**: Prometheus format available via GET `/metrics` (add endpoint if needed)

#### 3. LLMService Connection Reuse
- **Fixed**: Clients stored in ARQ context, reused across tasks
- **Changed**: From creating new clients per task to singleton in context
- **Impact**: Reduces connection overhead, memory usage
- **Code**: Automatic in worker startup hooks

#### 4. Rate Limiting with Redis
- **Fixed**: Global rate limiting (shared across workers)
- **Changed**: From per-process memory limits to Redis-backed
- **Setup**:
  ```bash
  RATE_LIMIT_PER_MINUTE=10/minute
  RATE_LIMIT_PER_DAY=200/day
  ```

## Environment Variables Checklist

Create `.env` in backend directory with these variables:

### Essential (Required)
```bash
# Deployment
ENV=production
ALLOWED_ORIGINS=https://app.yourdomain.com

# Database
DATABASE_URL=postgresql+asyncpg://user:pwd@host/logo_generator

# Redis
REDIS_URL=redis://user:pwd@redis.host:6379/0

# OpenAI
OPENAI_API_KEY=sk_...

# Google Gemini
GEMINI_API_KEY=AIzaSyD...

# Cloudflare R2
R2_BUCKET_NAME=logo-images
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_ENDPOINT_URL=https://account.r2.cloudflarestorage.com
R2_PUBLIC_DOMAIN=https://images.yourdomain.com
```

### Authentication (Required)
```bash
CLERK_JWKS_URL=https://your-instance.clerk.accounts.com/.well-known/jwks.json
CLERK_AUDIENCE=https://api.yourdomain.com
```

### Optional (Recommended for Production)
```bash
# Error tracking
SENTRY_DSN=https://...@sentry.io/...

# Logging
LOG_FILE=/var/log/logo-generator/backend.log

# Rate limiting
RATE_LIMIT_PER_MINUTE=10/minute
RATE_LIMIT_PER_DAY=200/day
```

### Development Only (Never in Prod)
```bash
# Only set if running in development and ENV != production
DEV_TOKEN=dev-token-for-testing
```

## Deployment Checklist

### Pre-Deployment
- [ ] All env vars set (run `env | grep -E '^(DATABASE_URL|REDIS_URL|OPENAI_API_KEY|CLERK)'`)
- [ ] Database migrations run: `alembic upgrade head`
- [ ] Redis is online and accessible
- [ ] R2 bucket created and credentials tested
- [ ] Clerk JWKS URL is reachable: `curl $CLERK_JWKS_URL`
- [ ] Frontend URL correct in `ALLOWED_ORIGINS`

### Installation
```bash
cd backend
pip install -r requirements.txt
```

### Running in Production

#### Option 1: Gunicorn (Recommended)
```bash
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn app:app \
  --workers ${WORKERS:-5} \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:${PORT:-8000} \
  --access-logfile - \
  --error-logfile - \
  --log-level info
```

#### Option 2: Docker (Docker Compose)
```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### Option 3: SystemD Service
```bash
# Create /etc/systemd/system/logo-generator.service
[Unit]
Description=Logo Generator API
After=network.target redis.service postgresql.service

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/logo-generator/backend
Environment="ENV=production"
EnvironmentFile=/opt/logo-generator/backend/.env
ExecStart=/usr/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable logo-generator
sudo systemctl start logo-generator
```

### ARQ Workers

Start workers for each queue:

```bash
# DALL-E Worker
python -m arq dalle_worker.WorkerSettings

# Gemini Worker
python -m arq gemini_worker.WorkerSettings
```

Or use supervisor for process management:

```ini
# /etc/supervisor/conf.d/logo-generator.conf
[program:dalle-worker]
command=python -m arq dalle_worker.WorkerSettings
directory=/opt/logo-generator/backend
environment=ENV=production,PATH=/opt/logo-generator/backend/.env
autostart=true
autorestart=true
stderr_logfile=/var/log/logo-generator/dalle-worker.err.log
stdout_logfile=/var/log/logo-generator/dalle-worker.out.log

[program:gemini-worker]
command=python -m arq gemini_worker.WorkerSettings
directory=/opt/logo-generator/backend
environment=ENV=production,PATH=/opt/logo-generator/backend/.env
autostart=true
autorestart=true
stderr_logfile=/var/log/logo-generator/gemini-worker.err.log
stdout_logfile=/var/log/logo-generator/gemini-worker.out.log
```

### Health Checks

```bash
# API health
curl https://api.yourdomain.com/api/health
# Expected: {"status": "ok", "gemini_ready": true, "openai_ready": true}

# Root endpoint
curl https://api.yourdomain.com/
# Should return API info
```

## Monitoring & Observability

### Logs
- **Location**: Specified in `LOG_FILE` env var or stdout if not set
- **Format**: JSON in production (machine-readable)
- **Rotation**: Automatic at 10MB per file, keeps 5 backups

### Sentry Integration
Set `SENTRY_DSN` to enable error tracking:
```bash
SENTRY_DSN=https://your-key@sentry.io/project-id
```

### Metrics
Access metrics in Prometheus format (add `/metrics` endpoint if needed):
```bash
curl https://api.yourdomain.com/metrics
```

Tracks:
- `generation_requests_total` - Total requests by generator
- `generation_latency_seconds` - Generation duration histogram
- `queue_depth` - Current job queue depth
- `r2_upload_latency_seconds` - R2 upload performance
- `errors_total` - Error count by type

## Troubleshooting

### ❌ "CORS_ERROR: No 'Access-Control-Allow-Origin' header"
**Cause**: Frontend URL not in `ALLOWED_ORIGINS`  
**Fix**: Add frontend URL to env var:
```bash
ALLOWED_ORIGINS=https://app.yourdomain.com
# Restart API server
```

### ❌ "Invalid or expired token"
**Cause**: JWT validation failed  
**Fix**: Check:
1. CLERK_JWKS_URL is correct
2. Token audience matches CLERK_AUDIENCE
3. Token not expired (check exp claim)
4. In production, verify_aud is enforced

### ❌ "You don't have permission to access this job"
**Cause**: User trying to access another user's job  
**Fix**: Normal security behavior. Each user can only see their own jobs.

### ❌ "Rate limited: 200 per day"
**Cause**: Rate limit exceeded  
**Fix**: Adjust limits in env vars:
```bash
RATE_LIMIT_PER_DAY=500/day
```

### ❌ Redis connection errors
**Cause**: Redis unreachable  
**Fix**: Check:
1. Redis URL syntax: `redis://[user:password@]host:port[/database]`
2. Redis service is running: `redis-cli ping`
3. Network connectivity: `nc -zv redis.host 6379`

## Performance Tuning

### Worker Count (Gunicorn)
```bash
WORKERS=$(($(nproc) * 2 + 1))  # CPU cores * 2 + 1
```

### Connection Pools
- Redis: Configured in `REDIS_SETTINGS` (app.py)
- Database: Adjust in SQLAlchemy if needed
- Rate limiting: Uses Redis

### Queue Settings
Adjust in worker files if needed:
```python
class WorkerSettings:
    result_ttl = 172800  # Job result expiry (2 days)
    # Add more settings as needed
```

## Security Hardening

### 🔐 Production Checklist
- [ ] All secrets in env vars (not in code)
- [ ] HTTPS enforced (certificate from Let's Encrypt)
- [ ] CORS properly configured
- [ ] DEV_TOKEN not set or ENV != production
- [ ] Database password strong and rotated
- [ ] Redis password set and TLS if remote
- [ ] Firewall rules restrict backend access
- [ ] Rate limiting appropriate for use case
- [ ] Logging enabled and monitored
- [ ] Error tracking (Sentry) configured
- [ ] Regular backups of database
- [ ] Security headers configured (nginx/caddy)

### NGINX Configuration (Example)
```nginx
upstream logo_api {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;
    
    location / {
        proxy_pass http://logo_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Rollback Plan

If issues occur in production:

1. **Stop the deployment**:
   ```bash
   systemctl stop logo-generator
   ```

2. **Check recent logs** for errors:
   ```bash
   tail -100 /var/log/logo-generator/backend.log
   ```

3. **Verify env vars** haven't changed
4. **Database migrations**: May need to rollback if schema changed
5. **Redis**: Check for keys that should have expired
6. **Re-deploy previous version** if issue persists

## Support & Escalation

- 🐛 **Bug**: Check logs, enable DEBUG level if needed
- 📊 **Performance**: Check metrics, queue depth, worker status
- 🔒 **Security**: Review audit logs, check for unauthorized access
- 💾 **Data**: Database backups are in `/backups` (configure as needed)

---

**Last Updated**: April 3, 2026  
**Security Review**: All critical issues resolved ✅
