# Frontend-Backend Integration Guide

## Overview

The new Streamlit frontend integrates with the refactored FastAPI backend to provide advanced logo generation with support for both DALL-E 3 and Gemini image generators.

---

## Architecture

### Frontend Layer (Streamlit)
- **Location:** `/frontend/streamlit_app.py`
- **Features:**
  - Multi-tab interface (Generation, Gallery, Info)
  - Advanced customization options (collapsible)
  - Real-time API health checking
  - Generation history tracking
  - Dual generator selection
  - Browser-based image download

### Backend API (FastAPI)
- **Location:** `/backend/app_new.py`
- **Endpoints:**
  - `GET /api/health` - Health check with client status
  - `POST /api/generate` - Logo generation with full parameters

### Generator Separation

#### DALL-E 3 Path
```
Frontend → Backend
  ↓
GPT-4 Turbo Prompt Refinement (OpenAI)
  ↓
DALL-E 3 Image Generation (OpenAI)
  ↓
Returns: Image URL (cloud-hosted)
```

#### Gemini Path
```
Frontend → Backend
  ↓
Gemini 2.0 Flash (All-in-one)
  - Prompt building
  - Image generation
  ↓
Returns: Local file path
```

---

## Setup Instructions

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies (if not already done)
pip install -r ../requirements.txt

# Ensure .env file exists with API keys
# .env should contain:
# GEMINI_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here

# Start the API server
python app_new.py
# Server runs on: http://localhost:5050
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Create Streamlit config directory
mkdir -p .streamlit

# Create secrets.toml for API configuration
cat > .streamlit/secrets.toml << EOF
API_BASE_URL = "http://localhost:5050"
EOF

# Install Streamlit (if not already done)
pip install streamlit

# Run the Streamlit app
streamlit run streamlit_app.py
# Opens at: http://localhost:8501
```

### 3. Verify Installation

**Check Backend Health:**
```bash
curl http://localhost:5050/api/health
```

Expected response:
```json
{
  "status": "ok",
  "gemini_ready": true,
  "openai_ready": true
}
```

**Check Frontend:**
- Open http://localhost:8501 in browser
- Look for "✅ API Connected" indicator
- Try generating a test logo

---

## API Request/Response Format

### Request Format (POST /api/generate)

```json
{
  "text": "Brand Name",
  "description": "Brand description",
  "style": "minimalist",
  "palette": "ocean",
  "generator": "dalle-3",
  
  "tagline": "Innovation at Speed",
  "typography": "Modern Sans-Serif",
  "elements_to_include": "Gear, Leaf",
  "elements_to_avoid": "Animals, Circles",
  "brand_mission": "To empower businesses worldwide"
}
```

### Response Format

**DALL-E 3 Response:**
```json
{
  "result": ["https://...image-url..."],
  "brand": "Brand Name",
  "style": "minimalist",
  "palette": "ocean",
  "prompt": "Detailed prompt used for generation",
  "generator": "dalle-3"
}
```

**Gemini Response:**
```json
{
  "result": ["generated_logos/gemini_logo_BrandName.png"],
  "brand": "Brand Name",
  "style": "minimalist",
  "palette": "ocean",
  "prompt": "Detailed prompt used for generation",
  "generator": "gemini"
}
```

---

## Key Features Implemented

### ✅ Dual Generator Support
- **DALL-E 3**: Professional, cloud-hosted images with GPT-4 refinement
- **Gemini**: Fast, independent local generation

### ✅ Advanced Customization
- Tagline/slogan input
- Typography preferences
- Element inclusion/exclusion
- Brand mission statement

### ✅ User Experience
- Tab-based interface
- Generation history
- Real-time API status
- Collapsible advanced options
- Download buttons for both generators

### ✅ API Health Monitoring
- Real-time backend status
- Individual client readiness checks
- Helpful error messages

---

## Generator Selection Logic

### When to Use DALL-E 3
- Need highest quality logos
- Want cloud-hosted URLs (no server storage needed)
- Prefer professional, refined outputs
- Don't mind slower generation (10-30 sec)

### When to Use Gemini
- Need fast generation
- Willing to work with local file storage
- Want independent, non-refined generation
- Prefer direct image generation without extra refinement step

---

## Configuration Files

### backend/.env
```env
GEMINI_API_KEY=your_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
```

### frontend/.streamlit/secrets.toml
```toml
API_BASE_URL = "http://localhost:5050"
```

### frontend/.streamlit/config.toml (optional)
```toml
[theme]
primaryColor = "#FF4444"
backgroundColor = "#FAFAFA"
secondaryBackgroundColor = "#F5F5F5"
textColor = "#151619"
font = "sans serif"

[client]
showErrorDetails = true
```

---

## File Structure

```
Logo-Generator/
├── backend/
│   ├── app_new.py                    # Main FastAPI app ← USE THIS
│   ├── routers.py                    # API routes
│   ├── services.py                   # Gemini & DALLE services
│   ├── models.py                     # Pydantic models (updated)
│   ├── dependencies.py               # Client management
│   ├── config.py                     # Constants & configs
│   ├── utils.py                      # Utilities
│   ├── test_refactored.py           # Tests
│   └── generated_logos/              # Output directory (created at runtime)
│
├── frontend/
│   ├── streamlit_app.py             # Main Streamlit app (NEW)
│   ├── .streamlit/
│   │   └── secrets.toml              # API configuration
│   │
│   ├── static/                       # Static assets (CSS, etc.)
│   └── templates/                    # HTML templates (optional)
│
└── requirements.txt                  # Python dependencies
```

---

## Troubleshooting

### Issue: "Cannot connect to API"
**Solution:**
1. Ensure backend is running: `python backend/app_new.py`
2. Check API URL in `.streamlit/secrets.toml`
3. Verify firewall isn't blocking port 5050

### Issue: "Gemini not ready" or "OpenAI not ready"
**Solution:**
1. Check `.env` file has correct API keys
2. Verify API keys are valid
3. Restart backend: `python backend/app_new.py`

### Issue: DALL-E generation fails
**Solution:**
1. Check OpenAI API credit balance
2. Verify `OPENAI_API_KEY` in `.env`
3. Check API quota hasn't been exceeded

### Issue: Gemini generation fails
**Solution:**
1. Verify `GEMINI_API_KEY` in `.env`
2. Check API key is valid
3. Verify Gemini API access is enabled

### Issue: Images won't download
**Solution:**
- For DALL-E: Images are temporary URLs (expire in 1 hour)
- For Gemini: Ensure write permissions to `backend/generated_logos/`

---

## Performance Considerations

### Generation Time
- **DALL-E 3**: 15-30 seconds (includes GPT-4 refinement + image generation)
- **Gemini**: 10-20 seconds (direct generation)

### Optimization Tips
1. Use Gemini for faster iterations
2. Use DALL-E for production-quality results
3. Keep descriptions concise (improves prompt quality)
4. Avoid very stylized requests that take longer

---

## API Request Examples

### Using cURL

**Health Check:**
```bash
curl http://localhost:5050/api/health
```

**Generate with DALL-E 3:**
```bash
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "TechVision",
    "description": "AI company",
    "style": "tech",
    "palette": "ocean",
    "generator": "dalle-3"
  }'
```

**Generate with Gemini:**
```bash
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "TechVision",
    "description": "AI company",
    "style": "minimalist",
    "palette": "monochrome",
    "generator": "gemini"
  }'
```

### Using Python

```python
import requests

API_BASE_URL = "http://localhost:5050"

request_data = {
    "text": "MyBrand",
    "description": "My company description",
    "style": "minimalist",
    "palette": "ocean",
    "generator": "dalle-3",
    "tagline": "Innovation at Speed",
    "typography": "Modern Sans-Serif"
}

response = requests.post(
    f"{API_BASE_URL}/api/generate",
    json=request_data
)

if response.status_code == 200:
    result = response.json()
    print(f"Generated logo: {result['result'][0]}")
else:
    print(f"Error: {response.json()}")
```

---

## Development Workflow

1. **Start Backend**
   ```bash
   cd backend
   python app_new.py
   ```

2. **In Another Terminal: Start Frontend**
   ```bash
   cd frontend
   streamlit run streamlit_app.py
   ```

3. **Access Application**
   - Backend API: http://localhost:5050
   - API Docs: http://localhost:5050/docs
   - Streamlit UI: http://localhost:8501

4. **Make Changes**
   - Backend changes: Restart `app_new.py`
   - Frontend changes: Streamlit auto-reloads

---

## Production Deployment

### Backend Deployment

**Option 1: Uvicorn with Workers**
```bash
pip install gunicorn
gunicorn backend.app_new:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:5050
```

**Option 2: Docker**
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY backend/ .
CMD ["python", "app_new.py"]
```

### Frontend Deployment

**Streamlit Cloud:**
```bash
# Push to GitHub, then deploy via Streamlit Cloud dashboard
# Add API_BASE_URL to secrets in Streamlit Cloud
```

**Self-Hosted:**
```bash
pip install streamlit
streamlit run frontend/streamlit_app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --logger.level=error
```

---

## Security Considerations

1. **API Keys**: Never expose in frontend code
2. **Environment Variables**: Use `.env` for credentials
3. **CORS**: Configure allowed origins in production
4. **Rate Limiting**: Implement to prevent abuse
5. **Input Validation**: All validated by Pydantic models

---

## Monitoring & Logging

### Backend Logs
Check for errors:
```bash
# Tail backend logs
tail -f backend/app.log
```

### Frontend Logs
Check browser console for errors:
- Open DevTools (F12)
- Check Console tab

### API Monitoring
Monitor endpoints:
```bash
# Health check periodically
watch -n 5 'curl -s http://localhost:5050/api/health | jq .'
```

---

## Support & Documentation

- **API Docs**: http://localhost:5050/docs (when running)
- **Backend Guide**: See `backend/ARCHITECTURE.md`
- **Architecture Diagrams**: See `backend/DIAGRAMS_AND_FLOWS.md`
- **Deployment Help**: See `backend/DEPLOYMENT_CHECKLIST.md`

---

## Next Steps

1. ✅ Backend is running with advanced services
2. ✅ Frontend is configured with new UI
3. 📝 **Test Logo Generation**
   - Try both DALL-E 3 and Gemini
   - Use advanced options
   - Download and verify results
4. 💾 **Store Generated Images**
   - Set up image archival system
   - Consider CDN for DALL-E URLs
5. 🚀 **Deploy to Production**
   - Follow deployment guides
   - Set up monitoring
   - Configure backups

---

## Contact & Issues

For issues or questions:
1. Check this guide first
2. Review backend documentation
3. Check API health status
4. Verify configuration files
5. Check browser console for errors
