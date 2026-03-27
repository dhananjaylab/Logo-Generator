import asyncio
from arq import worker
from google import genai
from openai import AsyncOpenAI

from config import REDIS_URL
from services import LLMService
from dependencies import Clients

async def generate_logo_task(ctx, generator: str, user_ip: str, **kwargs):
    """
    Background task to generate a logo using LLMService.
    """
    gemini_client = Clients.get_gemini_client()
    openai_client = Clients.get_openai_client()
    
    llm = LLMService(gemini_client, openai_client)
    
    print(f"[Worker] Starting generation for {kwargs.get('text')} using {generator}")
    
    try:
        if generator == "dalle-3":
            path, prompt = await llm.generate_logo_with_dalle(user_ip=user_ip, **kwargs)
            return {"result": [path], "generator": "dalle-3", "prompt": prompt, "status": "completed"}
        else:
            path, prompt = await llm.generate_logo_with_gemini(user_ip=user_ip, **kwargs)
            return {"result": [path], "generator": "gemini", "prompt": prompt, "status": "completed"}
    except Exception as exc:
        print(f"[Worker] Generation failed: {exc}")
        return {"status": "failed", "error": str(exc)}

async def startup(ctx):
    print("[Worker] Starting up...")
    # Initialize clients ensures they are ready
    Clients.get_gemini_client()
    Clients.get_openai_client()

async def shutdown(ctx):
    print("[Worker] Shutting down...")

class WorkerSettings:
    """
    ARQ worker settings.
    """
    functions = [generate_logo_task]
    redis_settings = worker.RedisSettings.from_dsn(REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
