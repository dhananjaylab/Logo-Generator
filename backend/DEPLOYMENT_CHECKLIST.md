# Deployment & Integration Checklist

## Pre-Deployment Validation

### Environment Setup
- [ ] Python 3.8+ installed
- [ ] Virtual environment activated
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] `.env` file created with API keys:
  - [ ] `GEMINI_API_KEY` set
  - [ ] `OPENAI_API_KEY` set

### Code Quality Checks
- [ ] All new files created successfully
- [ ] No syntax errors (run: `python -m py_compile backend/*.py`)
- [ ] Type hints valid (can run with Pylance)
- [ ] Imports resolve correctly

### Testing
- [ ] Run `test_refactored.py` - all tests pass
- [ ] Health endpoint responds: `GET /api/health`
- [ ] DALL-E generation works with valid response
- [ ] Gemini generation works with image saved locally
- [ ] Error handling works (test with invalid inputs)

### Documentation Review
- [ ] Read `ARCHITECTURE.md`
- [ ] Read `MIGRATION.md` (if updating frontend)
- [ ] Read `REFACTORING_SUMMARY.md`
- [ ] Review `DIAGRAMS_AND_FLOWS.md`

---

## Frontend Integration (if applicable)

### Streamlit App Updates
- [ ] Update API endpoint from `/generate` to `/api/generate`
- [ ] Change `requests.post(..., data={...})` to `requests.post(..., json={...})`
- [ ] Add `"generator"` parameter to request:
  ```python
  {
    "text": brand_name,
    "description": description,
    "style": style,
    "palette": palette,
    "generator": "dalle-3"  # User selection
  }
  ```
- [ ] Add UI element for generator selection (dropdown/radio buttons)
- [ ] Update image handling for different response formats:
  - DALL-E: URLs (display directly)
  - Gemini: File paths (may need special handling)
- [ ] Test end-to-end flow

### Optional: Gemini Image Serving
If serving Gemini-generated images via HTTP:
- [ ] Add static file mounting in `app_new.py`:
  ```python
  app.mount("/generated", StaticFiles(directory="generated_logos"), name="generated")
  ```
- [ ] Update image URLs from file paths to HTTP paths
- [ ] Create `/generated/` directory if it doesn't exist

---

## Deployment Options

### Option 1: Development Server
```bash
# Simple: Run directly
python backend/app_new.py

# With reload on changes
uvicorn backend.app_new:app --reload --port 5050
```
**Use for**: Local development, testing

### Option 2: Production Single Worker
```bash
# Uvicorn with workers
uvicorn backend.app_new:app --host 0.0.0.0 --port 5050 --workers 1
```
**Use for**: Small deployments, single server

### Option 3: Production Multi-Worker
```bash
# Gunicorn with Uvicorn workers
pip install gunicorn
gunicorn backend.app_new:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:5050 \
  --access-logfile - \
  --error-logfile -
```
**Use for**: Production, high traffic

### Option 4: Cloud Deployment
- [ ] Railway.app: `pip install -r requirements.txt`
- [ ] Heroku: Add `Procfile`: `web: uvicorn backend.app_new:app --host 0.0.0.0 --port $PORT`
- [ ] AWS Lambda: Use serverless framework
- [ ] Google Cloud Run: Containerize with Docker

---

## Deployment Checklist

### Configuration Management
- [ ] API keys stored securely (environment variables)
- [ ] No API keys in code or git
- [ ] `.env` file in `.gitignore`
- [ ] CORS settings appropriate for your domain
- [ ] Port 5050 (or configured port) open/available

### Directory Structure
- [ ] `generated_logos/` directory exists or will be created
- [ ] Write permissions to directory
- [ ] Sufficient disk space for generated images

### API Verification
- [ ] Health endpoint accessible: `curl http://localhost:5050/api/health`
- [ ] Generate endpoint accessible: `curl -X POST http://localhost:5050/api/generate ...`
- [ ] Error handling works (test with bad data)
- [ ] Rate limiting configured (if needed)

### Monitoring & Logging
- [ ] Access logs enabled
- [ ] Error logs configured
- [ ] Log file rotation set up (if using file logging)
- [ ] Monitor API latency (Gemini/DALL-E calls take time)

### Backward Compatibility
- [ ] Old `/generate` endpoint deprecated/removed
- [ ] Frontend updated to `/api/generate`
- [ ] Database migrations run (if applicable)
- [ ] Cache cleared (client-side)

---

## Post-Deployment Validation

After deploying to production:

### Endpoint Verification
- [ ] `GET /api/health` returns correct status
- [ ] Both API clients show ready
- [ ] Gemini client initialized
- [ ] OpenAI client initialized

### Generation Testing
- [ ] Create logo with DALL-E 3 generator
- [ ] Verify image URL valid and accessible
- [ ] Create logo with Gemini generator
- [ ] Verify image saved to directory
- [ ] Verify image file accessible

### Error Handling
- [ ] Invalid input returns meaningful error
- [ ] Missing API key returns 500 with message
- [ ] API rate limits handled gracefully
- [ ] Timeout handling works (long API calls)

### Performance
- [ ] Response times acceptable (usually 10-30s)
- [ ] No memory leaks from long-running requests
- [ ] Async operations working (non-blocking)
- [ ] Multiple concurrent requests handled

### Monitoring
- [ ] Check logs for errors
- [ ] Monitor failed API calls
- [ ] Track API quota usage (OpenAI/Gemini)
- [ ] Monitor disk space (generated images)

---

## Rollback Plan

If issues occur in production:

### Quick Rollback
```bash
# Switch back to old app
git checkout HEAD~1 backend/app.py
# or
cp backend/app.py.backup backend/app.py
# Restart server
```

### Data Preservation
- [ ] Backup `.env` with API keys
- [ ] Preserve `generated_logos/` directory
- [ ] Export logs before rollback
- [ ] Keep generated images safe

### Communication
- [ ] Notify users of issue
- [ ] Provide ETA for fix
- [ ] Share workaround if available
- [ ] Post-mortem after resolution

---

## Maintenance Checklist

After successful deployment:

### Regular Tasks
- [ ] Monitor API quotas (weekly)
- [ ] Check error rates (daily)
- [ ] Clean old generated images (monthly)
- [ ] Review and rotate logs (weekly)

### Updates
- [ ] Monitor for dependency updates
- [ ] Test updates in dev environment
- [ ] Deploy security patches promptly
- [ ] Keep documentation up-to-date

### Improvements
- [ ] Collect User feedback
- [ ] Monitor popular styles/palettes
- [ ] Track generation success rates
- [ ] Identify performance bottlenecks
- [ ] Plan feature enhancements

---

## Troubleshooting Guide

## Common Issues & Solutions

### Issue: "Gemini API Client not initialized"
**Solution:**
1. Check `.env` has `GEMINI_API_KEY`
2. Verify API key is valid
3. Restart application
4. Check `/api/health` endpoint

### Issue: "OpenAI API Client not initialized"
**Solution:**
1. Check `.env` has `OPENAI_API_KEY`
2. Verify API key is valid
3. Verify API key has credits
4. Restart application

### Issue: Generation takes very long or times out
**Solutions:**
1. Gemini/DALL-E APIs are slow by design (~10-30s)
2. Check network connectivity
3. Verify API quota not exceeded
4. Monitor server logs

### Issue: "ValueError: No image generated"
**Solutions (Gemini):**
1. Model name might be outdated
2. Region might not support image generation
3. Prompt might trigger safety filters
4. Check Gemini API documentation

### Issue: Image generation fails intermittently
**Solutions:**
1. Check API rate limits
2. Verify API quotas
3. Check server logs for specific errors
4. Handle retries in client code

### Issue: Generated images not found (Gemini)
**Solutions:**
1. Check `generated_logos/` directory exists
2. Verify write permissions
3. Check disk space available
4. Monitor file system

---

## Security Checklist

- [ ] API keys never in version control
- [ ] `.env` file in `.gitignore`
- [ ] CORS configured for allowed origins only
- [ ] Rate limiting configured (prevent abuse)
- [ ] Input validation on all endpoints
- [ ] Error messages don't expose sensitive info
- [ ] HTTPS enabled in production
- [ ] Log PII masked (user data)
- [ ] Regular security updates applied
- [ ] API keys rotated periodically

---

## Performance Optimization

### Caching (Future Enhancement)
- [ ] Cache prompts for same inputs
- [ ] Cache API credentials
- [ ] Implement image caching

### Scaling
- [ ] Multiple worker processes
- [ ] Load balancing across servers
- [ ] CDN for image serving
- [ ] Cache generated images

### Monitoring
- [ ] Response time tracking
- [ ] Error rate monitoring
- [ ] API quota monitoring
- [ ] Disk space monitoring

---

## Support Matrix

| Component | Version | Status | Support |
|-----------|---------|--------|---------|
| Python | 3.8+ | ✅ | Active |
| FastAPI | 0.109.0+ | ✅ | Active |
| Gemini API | Latest | ✅ | Active |
| OpenAI API | Latest | ✅ | Active |
| google-genai | 0.3.0+ | ✅ | Active |
| openai | 1.3.0+ | ✅ | Active |

---

## Quick Reference Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python backend/test_refactored.py

# Start development server
python backend/app_new.py

# Start with reload
uvicorn backend.app_new:app --reload --port 5050

# Check health
curl http://localhost:5050/api/health

# Generate with DALL-E
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Brand","generator":"dalle-3","style":"minimalist","palette":"ocean"}'

# Generate with Gemini
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{"text":"Brand","generator":"gemini","style":"minimalist","palette":"ocean"}'
```

---

## Sign-Off Template

When deployment is complete, confirm:

```
Deployment Checklist Completed: _____ (Initials)
Date: ___________________
Environment: Production / Staging / Development
Version: app_new.py

☐ All tests passed
☐ Documentation reviewed  
☐ API endpoints working
☐ Error handling verified
☐ Monitoring configured
☐ Rollback plan ready
☐ Team notified of deployment
```
