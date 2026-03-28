# 🚀 LogoForge AI - Production & Deployment Guide

This guide outlines the configurations and infrastructure required to move LogoForge AI from development to a secure, scalable production environment.

---

## 🛡️ Authentication: Clerk (Production)

To transition from the `DEV_TOKEN` bypass to full Clerk authentication:

### 1. Backend Integration (`backend/dependencies.py`)
- **Disable Dev Bypass**: In production, ensure `DEV_TOKEN` is **NOT** set in your environment variables.
- **JWKS URL**: Set `CLERK_JWKS_URL` to your production URL: `https://<clerk-id>.clerk.accounts.dev/.well-known/jwks.json`.
- **Audience & Issuer**: Update `jwt.decode` in `validate_clerk_token` to include your Clerk Client ID (Audience) to prevent token spoofing.

### 2. Frontend Integration
The Next.js frontend is built to use the [Clerk Next.js SDK](https://clerk.com/docs/references/nextjs/overview).
- Retrieve the JWT using `await window.Clerk.session.getToken()` in your React components.
- Attach it to the `Authorization: Bearer <token>` header of every API request.

---

## ☁️ Infrastructure & Storage

### 1. Cloudflare R2 (Persistent Storage)
Ensure your production environment variables are fully configured:
- `R2_BUCKET_NAME`: Production bucket name.
- `R2_ACCESS_KEY_ID` & `R2_SECRET_ACCESS_KEY`.
- `R2_ENDPOINT_URL`: The S3 API endpoint for your Cloudflare account.
- `R2_PUBLIC_DOMAIN`: The public URL (either from your domain or `pub-<id>.r2.dev`) used to serve files.

### 2. Redis (Job Queue & Rate Limiting)
- **Timeouts**: We use a `REDIS_SETTINGS` configuration with high timeouts (20s) in `backend/config.py` to handle latency if using managed Redis (e.g., Upstash).
- **Rate Limiting**: `slowapi` enforces limits per IP address using the Redis backend. Ensure persistence is enabled on your Redis instance.

### 3. PostgreSQL (Historical Metadata)
- The database stores job UUIDs, prompt metadata, and user identifiers.
- Ensure your `DATABASE_URL` uses the `postgresql+asyncpg://` driver for non-blocking I/O.

---

## 📉 Scalability & Performance

### 1. Decoupled Workers
In production, you should scale the **DALL-E** and **Gemini** workers independently:
- **DALL-E Worker**: Heavier resource usage (waiting for OpenAI). Scale this if you have high generation volume.
- **Gemini Worker**: Low latency. 

Run them via a process manager like `pm2` or in separate Docker containers:
```bash
# Example PM2 start
pm2 start "arq dalle_worker.WorkerSettings" --name dalle-worker
pm2 start "arq gemini_worker.WorkerSettings" --name gemini-worker
```

### 2. Production API Server
Do **not** use `python app.py` for production. Use `gunicorn` with the `uvicorn` worker class:
```bash
gunicorn backend.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

---

## 🛠️ Final Production Checklist

1. [ ] **Environment**: Set `ENV=production` in `backend/.env`.
2. [ ] **Rate Limiting**: Set `RATE_LIMIT_PER_MINUTE` (e.g., 5-10) and `RATE_LIMIT_PER_DAY`.
3. [ ] **CORS**: Correctly configure `CORSMiddleware` in `backend/app.py` to only allow your specific production frontend domain.
4. [ ] **Logging**: Configure `LOG_LEVEL=WARNING` or `ERROR` to minimize noise while preserving critical diagnostic data.
