# Backend Refactoring Guide

## What Changed?

The FastAPI backend has been completely restructured for better maintainability and extensibility:

### Old Structure
```
app.py (single monolithic file with all logic)
```

### New Structure
```
app_new.py         # Main FastAPI application
routers.py         # API routes
services.py        # Business logic (Gemini, DALL-E)
models.py          # Pydantic models
config.py          # Constants and templates
dependencies.py    # Client management
utils.py           # Helper functions
ARCHITECTURE.md    # Detailed architecture docs
```

## Key Improvements

### 1. **Dual Generator Support**
Users can now choose between:
- **DALL-E 3**: Refined prompts through Gemini → DALL-E image generation
- **Gemini**: Direct Gemini image generation (see `test_nano.py` approach)

### 2. **Modular Services**
- `GeminiService`: Handles Gemini operations (prompt refinement + image generation)
- `DALLEService`: Handles DALL-E operations
- `LLMService`: Unified interface for both generators

### 3. **Type Safety**
- Request/response models with Pydantic validation
- Better error handling and validation messages

### 4. **Configuration Management**
- All constants in `config.py`
- Easy to add new styles/palettes
- Prompt templates centralized

## API Changes

### Endpoint: POST /api/generate

#### Request Format
```json
{
  "text": "BrandName",
  "description": "Optional brand description",
  "style": "minimalist",      // or: tech, vintage, abstract, mascot, luxury
  "palette": "monochrome",    // or: ocean, sunset, forest, royal, neon
  "generator": "dalle-3"      // NEW: choose "dalle-3" or "gemini"
}
```

#### Response Format (DALL-E)
```json
{
  "result": ["https://...image-url..."],
  "brand": "BrandName",
  "style": "minimalist",
  "palette": "monochrome",
  "prompt": "Optimized prompt used for generation",
  "generator": "dalle-3"
}
```

#### Response Format (Gemini)
```json
{
  "result": ["generated_logos/gemini_logo_BrandName.png"],
  "brand": "BrandName",
  "style": "minimalist",
  "palette": "monochrome",
  "prompt": "Prompt used for generation",
  "generator": "gemini"
}
```

#### New Endpoint: GET /api/health

```json
{
  "status": "ok",
  "gemini_ready": true,
  "openai_ready": true
}
```

## Frontend Updates

### Update API calls in `streamlit_app.py`:

#### Old Code Example
```python
# Old - single generator
response = requests.post(
    "http://localhost:5050/generate",
    data={
        "text": brand_name,
        "description": brand_desc,
        "style": style,
        "palette": palette
    }
)
```

#### New Code Example
```python
# New - choose generator
response = requests.post(
    "http://localhost:5050/api/generate",  # Note: /api/ prefix
    json={
        "text": brand_name,
        "description": brand_desc,
        "style": style,
        "palette": palette,
        "generator": "dalle-3"  # or "gemini"
    }
)
```

**Important**: Change `data=` to `json=` when using Pydantic models!

## Running the Refactored Backend

### Option 1: Direct Python
```bash
cd backend
python app_new.py
```

### Option 2: Uvicorn
```bash
cd backend
uvicorn app_new:app --reload --port 5050
```

### Option 3: Rename and use as app.py
```bash
# After testing, rename the new app to replace the old one
mv app_new.py app.py
python app.py
```

## Testing the Backend

### Run the automated tests:
```bash
cd backend
python test_refactored.py
```

### Test with curl:
```bash
# Health check
curl http://localhost:5050/api/health

# Generate with DALL-E 3
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "MyBrand",
    "description": "My company",
    "style": "minimalist",
    "palette": "ocean",
    "generator": "dalle-3"
  }'

# Generate with Gemini
curl -X POST http://localhost:5050/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "MyBrand",
    "description": "My company",
    "style": "minimalist",
    "palette": "ocean",
    "generator": "gemini"
  }'
```

## Migration Checklist

- [ ] Read `ARCHITECTURE.md` for detailed structure
- [ ] Test new backend with `test_refactored.py`
- [ ] Update frontend calls to use `/api/` prefix
- [ ] Update frontend to use `json=` instead of `data=` in requests
- [ ] Add `generator` parameter to API calls
- [ ] Test Gemini image generation (may need to handle local file paths)
- [ ] Consider where to save/serve Gemini-generated images
- [ ] Update frontend UI to include generator selection
- [ ] Replace old `app.py` with `app_new.py` after validation

## Handling Generated Images

### DALL-E Images
- Returned as URLs (valid for 1 hour by default)
- Display directly in browser
- Can be downloaded/cached as needed

### Gemini Images
- Saved locally to `generated_logos/` directory
- Paths returned in response
- Need to serve via static file endpoint (optional)
- Consider implementing image serving endpoint for Gemini images

## Optional: Add Static File Serving for Gemini Images

If you want to serve Gemini-generated images via HTTP:

```python
# Add to app_new.py
from fastapi.staticfiles import StaticFiles

app.mount("/generated", StaticFiles(directory="generated_logos"), name="generated")

# Then Gemini image paths can be accessed at:
# http://localhost:5050/generated/gemini_logo_BrandName.png
```

## Troubleshooting

### "Gemini API Client not initialized"
- Check `GEMINI_API_KEY` in `.env`
- Verify API key is valid

### "OpenAI API Client not initialized"
- Check `OPENAI_API_KEY` in `.env`
- Verify API key is valid

### Gemini generation fails
- Model might be `gemini-3.5-flash-image-preview` (check latest)
- Some regions may have limited image generation support

### DALL-E generation fails
- Verify OpenAI API credits
- Check prompt quality (may violate policy)

## Version Compatibility

- FastAPI >= 0.109.0
- Pydantic >= 2.0 (required for new model features)
- google-genai >= 0.3.0
- openai >= 1.3.0

All dependencies are in `requirements.txt`
