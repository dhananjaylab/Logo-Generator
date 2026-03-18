# Backend Architecture Documentation

## Project Structure

The refactored backend follows a modular, scalable architecture:

```
backend/
├── app_new.py           # Main FastAPI application
├── routers.py           # API route handlers
├── services.py          # Business logic (GeminiService, DALLEService, LLMService)
├── models.py            # Pydantic request/response models
├── config.py            # Constants and configuration
├── dependencies.py      # Dependency injection for API clients
├── utils.py             # Utility functions
├── app.py               # (Legacy) Old app.py
├── diagnostic.py        # Diagnostics
└── test_backend.py      # Tests
```

## Architecture Overview

### Core Components

#### 1. **Models** (`models.py`)
Pydantic models for request/response validation:
- `LogoGenerationRequest`: Request parameters for logo generation
- `LogoGenerationResponse`: Response with generated logo and metadata
- `HealthResponse`: Health check response
- `LogoModificationRequest`: Future modification endpoint (prepared)

#### 2. **Configuration** (`config.py`)
Centralized constants and configuration:
- `LOGO_STYLES`: Available logo design styles
- `COLOR_PALETTES`: Available color palettes
- `DALLE3_PROMPT_TEMPLATE`: Prompt template for DALL-E refinement
- `GEMINI_GENERATION_TEMPLATE`: Prompt template for Gemini image generation
- `SUPPORTED_GENERATORS`: List of supported image generators

#### 3. **Dependencies** (`dependencies.py`)
Dependency injection for API clients:
- `Clients` singleton class for managing API client instances
- `get_gemini_client()`: FastAPI dependency for Gemini client
- `get_openai_client()`: FastAPI dependency for OpenAI client
- Client initialization from environment variables

#### 4. **Services** (`services.py`)
Core business logic with three main services:

**GeminiService**
- `refine_prompt()`: Use Gemini to refine prompts for DALL-E
- `generate_logo()`: Generate logos directly using Gemini's image generation capabilities

**DALLEService**
- `generate_logo()`: Generate logos using DALL-E 3
- `refine_and_generate()`: Generate from pre-refined prompts

**LLMService** (Facade Pattern)
- Unified interface for logo generation
- `generate_logo_with_dalle()`: DALL-E generation with Gemini refinement
- `generate_logo_with_gemini()`: Direct Gemini image generation

#### 5. **Routers** (`routers.py`)
API endpoints:
- `GET /api/health`: Health check
- `POST /api/generate`: Generate logo with choice of generator

#### 6. **Utilities** (`utils.py`)
Helper functions:
- `ensure_output_directory()`: Create output directory structure
- `get_output_path()`: Get proper file paths for saving images
- `sanitize_filename()`: Clean filenames for safe storage

#### 7. **Main Application** (`app_new.py`)
FastAPI application setup:
- CORS middleware configuration
- Router registration
- Root endpoint
- Server startup configuration

## Usage Flow

### DALL-E 3 Generation Flow
```
User Request
    ↓
Pydantic Validation
    ↓
LLMService.generate_logo_with_dalle()
    ↓
GeminiService.refine_prompt()  (Prompt engineering)
    ↓
DALLEService.generate_logo()  (Image generation)
    ↓
Response with image URL
```

### Gemini Direct Generation Flow
```
User Request
    ↓
Pydantic Validation
    ↓
LLMService.generate_logo_with_gemini()
    ↓
GeminiService.generate_logo()
    ↓
Image saved locally (using utils.get_output_path())
    ↓
Response with image path
```

## API Endpoints

### Health Check
```
GET /api/health

Response:
{
  "status": "ok",
  "gemini_ready": true,
  "openai_ready": true
}
```

### Generate Logo
```
POST /api/generate

Request:
{
  "text": "MyBrand",
  "description": "Creative tech company",
  "style": "minimalist",
  "palette": "ocean",
  "generator": "dalle-3"  // or "gemini"
}

Response:
{
  "result": ["image_url_or_path"],
  "brand": "MyBrand",
  "style": "minimalist",
  "palette": "ocean",
  "prompt": "Optimized prompt used",
  "generator": "dalle-3"
}
```

## Supported Styles & Palettes

**Styles:**
- minimalist
- tech
- vintage
- abstract
- mascot
- luxury

**Palettes:**
- monochrome
- ocean
- sunset
- forest
- royal
- neon

## Migration from Old app.py

To migrate from the old `app.py` to the new architecture:

1. Replace imports and routes with `app_new.py`
2. Rename `app_new.py` to `app.py` (after testing)
3. Update your imports to use modular components
4. No changes needed to API consumers - endpoints remain the same

## Setup

1. Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

2. Set environment variables in `.env`:
```
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
```

3. Run the application:
```bash
python app_new.py
```

Or with uvicorn:
```bash
uvicorn app_new:app --reload --port 5050
```

## Key Design Improvements

1. **Separation of Concerns**: Each module has a single responsibility
2. **Dependency Injection**: Loose coupling between components
3. **Service Abstraction**: Business logic isolated from routing
4. **Type Safety**: Pydantic models for validation
5. **Configurability**: Easy to add new styles, palettes, or generators
6. **Extensibility**: Service layer can easily add new generators (e.g., Midjourney, Stable Diffusion)
7. **Error Handling**: Centralized validation and error responses
8. **Code Reusability**: Shared utilities and client management

## Future Enhancements

- [ ] Logo modification endpoint implementation
- [ ] Support for additional image generators (Midjourney, Stable Diffusion)
- [ ] Image caching and deduplication
- [ ] Batch logo generation
- [ ] Logo history and favorites storage
- [ ] Advanced filtering and search
