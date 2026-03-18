# Architecture Diagram & Flow

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                      │
│                            (app_new.py)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │            Router Layer (routers.py)                      │  │
│  │                                                            │  │
│  │  GET  /api/health       → Health Check Endpoint          │  │
│  │  POST /api/generate     → Logo Generation Endpoint       │  │
│  └───────────────────────────────────────────────────────────┘  │
│           │                                  │                   │
│           ▼                                  ▼                   │
│  ┌───────────────────────┐    ┌──────────────────────────┐      │
│  │   Input Validation    │    │   Dependency Injection   │      │
│  │    (models.py)        │    │   (dependencies.py)      │      │
│  │                       │    │                          │      │
│  │ • LogoGenRequest    │    │ • Gemini Client        │      │
│  │ • LogoGenResponse   │    │ • OpenAI Client        │      │
│  │ • HealthResponse    │    │ • Client Status Checks │      │
│  └───────────────────────┘    └──────────────────────────┘      │
│           │                                  │                   │
│           └──────────────┬───────────────────┘                   │
│                          ▼                                        │
│                 ┌──────────────────────┐                        │
│                 │  Service Layer       │                        │
│                 │  (services.py)       │                        │
│                 │                      │                        │
│         ┌───────┴──────────┬───────────┴────────┐              │
│         │                  │                    │              │
│         ▼                  ▼                    ▼              │
│    ┌─────────────┐  ┌──────────────┐  ┌──────────────┐       │
│    │   Gemini    │  │    DALLE     │  │     LLM      │       │
│    │  Service    │  │   Service    │  │   Service    │       │
│    │             │  │              │  │   (Facade)   │       │
│    │ • Refine    │  │ • Generate   │  │              │       │
│    │   Prompt    │  │   Image      │  │ • Delegates  │       │
│    │ • Generate  │  │ • URL Format │  │   to Gemini  │       │
│    │   Image     │  │              │  │   or DALLE   │       │
│    └─────────────┘  └──────────────┘  └──────────────┘       │
│         │                  │                    │              │
└─────────┼──────────────────┼────────────────────┼──────────────┘
          │                  │                    │
          ▼                  ▼                    ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │   Gemini     │    │   OpenAI     │    │   Utilities  │
    │   API        │    │   API        │    │  (utils.py)  │
    │              │    │              │    │              │
    │ • Text Gen   │    │ • DALL-E 3   │    │ • File Paths │
    │ • Image Gen  │    │              │    │ • Sanitize   │
    └──────────────┘    └──────────────┘    │ • Directories│
                                             └──────────────┘
```

## Request Flow: DALL-E 3 Generation

```
User Request
    │
    │ POST /api/generate
    │ {
    │   "text": "TechCorp",
    │   "generator": "dalle-3",
    │   "style": "minimalist",
    │   ...
    │ }
    │
    ▼
┌─────────────────────────────────────────┐
│ Pydantic Validation (LogoGenerationRequest)
│ ✓ Type checking
│ ✓ Field validation
│ ✓ Generator validation
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Dependency Injection                    │
│ • Load Gemini Client                    │
│ • Load OpenAI Client                    │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ LLMService.generate_logo_with_dalle()   │
└─────────────────────────────────────────┘
    │
    ├─────────────────────────────────┐
    │                                 │
    ▼                                 ▼
┌──────────────────────────┐  ┌─────────────────────────┐
│GeminiService.refine_prompt()│ │ DALLEService.generate  │
│                          │  │ _logo()                 │
│• Build prompt template   │  │                         │
│• Call Gemini API         │  │• Take refined prompt    │
│• Get optimized prompt    │  │• Call DALL-E 3 API      │
│                          │  │• Get image URL          │
└──────────────────────────┘  └─────────────────────────┘
    │                                 │
    └────────────┬────────────────────┘
                 │
                 ▼
        ┌──────────────────────┐
        │ Return Response:     │
        │ {                    │
        │  "result": [URL],    │
        │  "brand": "TechCorp",│
        │  "generator": "dalle-3"
        │  "prompt": "..."     │
        │ }                    │
        └──────────────────────┘
```

## Request Flow: Gemini Direct Generation

```
User Request
    │
    │ POST /api/generate
    │ {
    │   "text": "TechCorp",
    │   "generator": "gemini",
    │   "style": "minimalist",
    │   ...
    │ }
    │
    ▼
┌─────────────────────────────────────────┐
│ Pydantic Validation (LogoGenerationRequest)
│ ✓ Type checking
│ ✓ Field validation
│ ✓ Generator validation
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ Dependency Injection                    │
│ • Load Gemini Client                    │
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│ LLMService.generate_logo_with_gemini()  │
└─────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────┐
│GeminiService.generate_logo()                     │
│                                                  │
│• Build generation template                      │
│• Call Gemini API with image generation model    │
│• Extract image from response.candidates[0]      │
│  .content.parts[].inline_data.data               │
│• Create PIL Image from bytes                    │
│• Sanitize filename                              │
│• Save to generated_logos/ directory             │
└──────────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────┐
│ Utils (get_output_path)  │
│ • Ensure directory exists │
│ • Return proper file path│
└──────────────────────────┘
    │
    ▼
┌──────────────────────────────┐
│ Return Response:             │
│ {                            │
│  "result": [file_path],      │
│  "brand": "TechCorp",        │
│  "generator": "gemini",      │
│  "prompt": "..."             │
│ }                            │
└──────────────────────────────┘
```

## Module Dependencies

```
┌──────────────────┐
│  app_new.py      │ (FastAPI App)
└────────┬─────────┘
         │ imports
         ▼
┌──────────────────┐     ┌────────────────┐
│  routers.py      ├────→│  models.py     │ (Pydantic)
└────────┬─────────┘     └────────────────┘
         │
         │ imports
         ├────────────────────────────────────┐
         │                                    │
         ▼                                    ▼
┌──────────────────┐              ┌────────────────────┐
│  services.py     │              │ dependencies.py    │
│                  │              │                    │
│ ├─ Gemini        │              │ ├─ Clients class  │
│ ├─ DALLE         │              │ ├─ get_gemini()   │
│ └─ LLM (Facade)  │              │ └─ get_openai()   │
└────────┬─────────┘              └────────────────────┘
         │
         │ imports
         ├──────────────────────────────┬───────────┐
         │                              │           │
         ▼                              ▼           ▼
┌──────────────────┐         ┌─────────────┐  ┌──────────┐
│  config.py       │         │  utils.py   │  │ External │
│                  │         │             │  │  APIs    │
│ • Styles        │         │ • File Path │  │          │
│ • Palettes      │         │ • Sanitize  │  │ Gemini   │
│ • Templates     │         │ • Dirs      │  │ OpenAI   │
│ • Generators    │         │             │  │          │
└──────────────────┘         └─────────────┘  └──────────┘
```

## Development Workflow

```
┌────────────────────────────────────────────┐
│ Development/Testing                        │
├────────────────────────────────────────────┤
│                                            │
│  test_refactored.py                       │
│  ├─ Test client initialization           │
│  ├─ Test DALL-E generation               │
│  ├─ Test Gemini generation               │
│  └─ Validate responses                   │
│                                            │
│  $ python test_refactored.py              │
│                                            │
└────────────────────────────────────────────┘
         │
         │ ✓ Tests Pass
         │
         ▼
┌────────────────────────────────────────────┐
│ Local Testing                              │
├────────────────────────────────────────────┤
│                                            │
│  $ python app_new.py                      │
│  [or] uvicorn app_new:app --reload        │
│                                            │
│  $ curl -X POST http://localhost:5050/... │
│                                            │
└────────────────────────────────────────────┘
         │
         │ ✓ Works Locally
         │
         ▼
┌────────────────────────────────────────────┐
│ Production Deployment                      │
├────────────────────────────────────────────┤
│                                            │
│  Option 1:                                 │
│  $ mv app_new.py app.py                   │
│  $ python app.py                          │
│                                            │
│  Option 2:                                 │
│  $ uvicorn app_new:app --host 0.0.0.0    │
│                                            │
│  Option 3:                                 │
│  $ gunicorn -w 4 -k uvicorn.workers...   │
│                                            │
└────────────────────────────────────────────┘
```

## Configuration Flow

```
.env
 │
 │ load_dotenv()
 │
 ▼
dependencies.py
 │ Clients class
 │ ├─ GEMINI_API_KEY → gemini_client
 │ └─ OPENAI_API_KEY → openai_client
 │
 ▼
services.py
 │
 ├─ GeminiService(client)
 ├─ DALLEService(client)
 └─ LLMService(gemini_client, openai_client)
 
routers.py
 │
 └─ Dependencies injected into endpoints
    via Depends(get_gemini_client) etc.
```

## Error Handling Flow

```
Request
    │
    ▼
Pydantic Validation
    │
    ├─ Invalid input? → 400 Bad Request
    │  • Helpful error message
    │  • Field validation details
    │
    └─ ✓ Valid
        │
        ▼
    Client Check
        │
        ├─ Client missing? → 500 Internal Server Error
        │
        └─ ✓ Ready
            │
            ▼
        Service Generation
            │
            ├─ API Error? → 500 Internal Server Error
            │  • Try/catch with error details
            │
            └─ ✓ Success
                │
                ▼
            Return Response
```

## File I/O Flow (Gemini Generation)

```
Gemini API Response
    │
    │ response.candidates[0].content.parts
    │
    ▼
Extract image data
    │
    │ part.inline_data.data (bytes)
    │
    ▼
io.BytesIO (bytes → file-like)
    │
    │
    ▼
PIL.Image.open() (deserialize)
    │
    │
    ▼
utils.sanitize_filename()
    │
    │
    ▼
utils.get_output_path()
    │
    │ (ensures generated_logos/ exists)
    │
    ▼
image.save(path)
    │
    │
    ▼
Return path in response
```

## Technology Stack

```
FastAPI          Request handling, async, validation
Pydantic         Request/response models, validation
Gemini API       Prompt refinement, image generation
OpenAI API       DALL-E 3 image generation
Pillow (PIL)     Image processing
python-dotenv    Environment configuration
asyncio          Concurrent operations
```
