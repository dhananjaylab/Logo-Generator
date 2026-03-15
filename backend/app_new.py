import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import routers
from routers import router as logo_router

# Create FastAPI app
app = FastAPI(
    title="Logo Generator API",
    description="Generate logos using Gemini or DALL-E 3",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(logo_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Logo Generator API",
        "docs": "/docs",
        "health": "/api/health",
        "generate": "/api/generate"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=5050)
