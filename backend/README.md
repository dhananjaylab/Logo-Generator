# Backend API - Logo Generator Service

FastAPI-based backend for professional logo generation with DALL-E 3 and Gemini support.

## Quick Start

```bash
# Install dependencies
pip install -r ../requirements.txt

# Set environment variables
# Create ../.env with:
# GEMINI_API_KEY=...
# OPENAI_API_KEY=...

# Run server
python app_new.py
```

Server runs on: http://localhost:5050

## Essential Files

| File | Purpose | Size | Status |
|------|---------|------|--------|
| `app_new.py` | Main FastAPI app | ~50 lines | ✅ USE THIS |
| `routers.py` | API endpoints | ~100 lines | ✅ Core |
| `services.py` | Generator services | ~200 lines | ✅ Core |
| `models.py` | Pydantic models | ~50 lines | ✅ Core |
| `dependencies.py` | Dependency injection | ~30 lines | ✅ Core |
| `config.py` | Constants & templates | ~40 lines | ✅ Core |
| `utils.py` | Utilities | ~30 lines | ✅ Core |

## Optional Files

| File | Purpose | Status |
|------|---------|--------|
| `test_refactored.py` | Integration tests | ✅ For testing |
| `diagnostic.py` | Pipeline diagnostics | ⚠️ Debugging only |
| `README.md` | Documentation | ℹ️ Documentation |
| `ARCHITECTURE.md` | Design patterns | ℹ️ Documentation |
| `DEPLOYMENT_CHECKLIST.md` | Production guide | ℹ️ Reference |
| `DIAGRAMS_AND_FLOWS.md` | Visual flows | ℹ️ Reference |

## Structure

```
backend/
├── Essential Files
│   ├── app_new.py           FastAPI server
│   ├── routers.py           API routes
│   ├── services.py          Business logic
│   ├── models.py            Data validation
│   ├── dependencies.py      DI container
│   ├── config.py            Constants
│   └── utils.py             Utilities
│
├── Testing & Diagnostics
│   ├── test_refactored.py   Tests
│   └── diagnostic.py        Diagnostics
│
├── Documentation
│   ├── README.md            This file
│   ├── ARCHITECTURE.md      Design details
│   ├── DIAGRAMS_AND_FLOWS.md Visual flows
│   └── DEPLOYMENT_CHECKLIST.md Production
│
├── Runtime
│   └── generated_logos/     Output directory
│
└── Python Cache
    └── __pycache__/         (Can be deleted)
```

## API Endpoints

### Health Check
```
GET /api/health
```
Check if backend and clients are ready.

### Generate Logo
```
POST /api/generate
```
Generate a professional logo.

**Request Body:**
```json
{
  "text": "Brand Name",
  "description": "Brand description",
  "style": "minimalist",
  "palette": "ocean",
  "generator": "dalle-3",
  "tagline": "Your slogan (optional)",
  "typography": "Font (optional)",
  "elements_to_include": "Elements (optional)",
  "elements_to_avoid": "Elements (optional)",
  "brand_mission": "Mission (optional)"
}
```

**Response:**
```json
{
  "result": ["image_url_or_path"],
  "brand": "Brand Name",
  "style": "minimalist",
  "palette": "ocean",
  "prompt": "Engineered prompt",
  "generator": "dalle-3"
}
```

## Generator Isolation

### DALL-E 3 Path
1. GPT-4 Turbo refines prompt
2. DALL-E 3 generates image
3. Returns cloud URL

### Gemini Path
1. Direct generation
2. Local file saved
3. Returns file path

**No cross-contamination** - Each generator works independently

## Configuration

### Environment Variables
```env
GEMINI_API_KEY=your_key
OPENAI_API_KEY=your_key
```

### Output Directory
Generated logos sto at: `backend/generated_logos/`
(Created automatically on first use)

## Development

### Running Tests
```bash
python -m pytest test_refactored.py -v
```

### Diagnostics
```bash
python diagnostic.py
```

### Requirements
See `../requirements.txt` for all dependencies:
- fastapi >= 0.109.0
- uvicorn >= 0.27.0
- openai >= 1.3.0
- google-genai >= 0.3.0
- pydantic >= 2.0
- pillow >= 10.2.0
- python-dotenv >= 1.0.0

## Deployment

See `DEPLOYMENT_CHECKLIST.md` for production deployment guide.

### Quick Deploy
```bash
# Using Gunicorn + Uvicorn
pip install gunicorn
gunicorn backend.app_new:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:5050
```

## Troubleshooting

### "Cannot import X"
- Reinstall: `pip install -r ../requirements.txt`

### "API key invalid"
- Check `.env` file in project root
- Keys should not be in code

### "Port already in use"
- Change port in `app_new.py`: `port=8000`
- Update frontend config accordingly

### Generation fails
- Check backend logs
- Verify API keys are valid
- Check API quotas

## Architecture

See `ARCHITECTURE.md` for:
- Service layer design
- Generator isolation
- Async patterns
- Error handling

See `DIAGRAMS_AND_FLOWS.md` for:
- Request flow diagrams
- Generator separation visuals
- System architecture

## API Docs

Live API documentation available at:
```
http://localhost:5050/docs
```

Interactive Swagger UI with try-it-out functionality.

## Support

For issues:
1. Check logs in terminal
2. Run `python diagnostic.py`
3. See `../TROUBLESHOOTING.md`
4. Check `ARCHITECTURE.md` for design details
