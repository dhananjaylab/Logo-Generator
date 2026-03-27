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

# ── Endpoints ───────────────────────────────────────────────────────────────

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