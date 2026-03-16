import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from routers import router as logo_router

app = FastAPI(
    title="Logo Generator API",
    description="Generate logos using Gemini or DALL-E 3",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static file serving for generated logos ───────────────────────────────────
# Gemini saves to: generated_logos/gemini/
# DALL-E saves to: generated_logos/dalle/
# Both are served under /static/generated_logos/<subdir>/<file>
# which matches the path the frontend constructs from the returned relative path.

_BASE   = Path("generated_logos")
_GEMINI = _BASE / "gemini"
_DALLE  = _BASE / "dalle"

for d in [_BASE, _GEMINI, _DALLE]:
    d.mkdir(parents=True, exist_ok=True)

# Mount the whole generated_logos tree so sub-paths resolve automatically
app.mount(
    "/static/generated_logos",
    StaticFiles(directory=str(_BASE)),
    name="generated_logos",
)

app.include_router(logo_router)


@app.get("/")
async def root():
    return {
        "message": "Logo Generator API v2.1",
        "docs":    "/docs",
        "health":  "/api/health",
        "generate":"/api/generate",
        "static":  "/static/generated_logos/<gemini|dalle>/<filename>",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5050, reload=False)