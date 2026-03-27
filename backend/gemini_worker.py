import asyncio
from arq import worker
from google import genai

from config import REDIS_URL
from services import LLMService
from dependencies import Clients

async def generate_gemini_task(ctx, user_ip: str, **kwargs):
    """
    Background task to generate a logo using Gemini.
    """
    gemini_client = Clients.get_gemini_client()
    llm = LLMService(gemini_client, None)
    
    print(f"[Gemini Worker] Starting generation for {kwargs.get('text')}")
    
    try:
        path, prompt = await llm.generate_logo_with_gemini(user_ip=user_ip, **kwargs)
        return {"result": [path], "generator": "gemini", "prompt": prompt, "status": "completed"}
    except Exception as exc:
        print(f"[Gemini Worker] Generation failed: {exc}")
        return {"status": "failed", "error": str(exc)}

async def startup(ctx):
    print("[Gemini Worker] Starting up...")
    Clients.get_gemini_client()

async def shutdown(ctx):
    print("[Gemini Worker] Shutting down...")

class WorkerSettings:
    """
    ARQ worker settings for Gemini.
    """
    functions = [generate_gemini_task]
    redis_settings = worker.RedisSettings.from_dsn(REDIS_URL)
    queue_name = 'gemini_queue'
    on_startup = startup
    on_shutdown = shutdown
