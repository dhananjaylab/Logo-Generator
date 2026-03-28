# Logo Generator - Deployment & Production Guide

This document outlines the steps and configuration required to move the Logo Generator from a local development environment to a secure production deployment.

## 1. Authentication: Clerk (Production)

Currently, the app uses a `DEV_TOKEN` for local testing. To transition to full production Clerk authentication:

### Backend Configuration (`backend/dependencies.py`)
- **[REQUIRED] Remove Dev Bypass**: In production, delete or comment out the `Dev Token Bypass` block in `validate_clerk_token`. Alternatively, ensure `DEV_TOKEN` is **NOT** set in your production environment variables.
- **[REQUIRED] JWKS URL**: Set `CLERK_JWKS_URL` to your production URL: `https://<your-id>.clerk.accounts.dev/.well-known/jwks.json`.
- **[SECURITY] Token Verification**: Update the `jwt.decode` options to include your Clerk Client ID (Audience) and Issuer for strict validation:
  ```python
  payload = jwt.decode(
      token, 
      jwks, 
      algorithms=["RS256"],
      audience="your_clerk_client_id_here",
      issuer="https://your-clerk-issuer-url"
  )
  ```

### Frontend Integration
The current Streamlit UI uses a manual text popup. For production:
- Use the [Clerk JavaScript SDK](https://clerk.com/docs/quickstarts/javascript) to handle the login flow.
- Retrieve the JWT using `await getToken()` and pass it in the `Authorization: Bearer <token>` header of your API requests.

---

## 2. Infrastructure & Stability

### Redis (Abuse Prevention)
- **Timeouts**: We have configured `REDIS_SETTINGS` in `backend/config.py` with a 20s timeout. This is critical for remote cloud instances (e.g., Upstash or RedisLabs) to handle network latency.
- **Persistence**: Ensure your production Redis instance has persistence enabled so rate-limit counts are not lost during restarts.

### Database (PostgreSQL)
- **Connection**: Ensure `DATABASE_URL` is set to your production PostgreSQL instance.
- **Logs**: The `logo_generations` table now tracks `user_id` and `ip_address` for every generation, allowing you to audit usage from the backend.

### Storage (Cloudflare R2)
- Ensure all R2 environment variables are production-level:
  - `R2_BUCKET_NAME`
  - `R2_ENDPOINT_URL` (S3 API Endpoint)
  - `R2_PUBLIC_DOMAIN` (Public URL for images)

---

## 3. Rate Limiting Strategy

Rate limits are currently configured in your `.env` file:
- **`RATE_LIMIT_PER_MINUTE`**: Recommended 5-10 for free users.
- **`RATE_LIMIT_PER_DAY`**: Recommended 20-100 depending on your API budget.

The backend automatically enforces these limits per IP address using the `slowapi` library.

---

## 4. Final Deployment Checklist

1. [ ] Set `ENV=production` in environment variables.
2. [ ] Use a production WSGI/ASGI server like `gunicorn` with `uvicorn.workers.UvicornWorker` instead of `python app.py`.
3. [ ] Configure CORS headers in `backend/app.py` to allow only your production frontend domain.
4. [ ] Ensure Cloudflare R2 bucket has the correct CORS policy to allow your frontend to download images.
5. [ ] Monitor your OpenAI and Google API usage dashboards for unusual spikes.
