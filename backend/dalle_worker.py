import asyncio
from arq import worker
from google import genai
from openai import AsyncOpenAI

from config import REDIS_URL
from services import LLMService
from dependencies import Clients

async def generate_dalle_task(ctx, user_ip: str, **kwargs):
    """
    Background task to generate a logo using DALL-E 3.
    """
    openai_client = Clients.get_openai_client()
    llm = LLMService(None, openai_client)
    
    print(f"[DALL-E Worker] Starting generation for {kwargs.get('text')}")
    
    try:
        path, prompt = await llm.generate_logo_with_dalle(user_ip=user_ip, **kwargs)
        return {"result": [path], "generator": "dalle-3", "prompt": prompt, "status": "completed"}
    except Exception as exc:
        print(f"[DALL-E Worker] Generation failed: {exc}")
        return {"status": "failed", "error": str(exc)}

async def startup(ctx):
    print("[DALL-E Worker] Starting up...")
    Clients.get_openai_client()

async def shutdown(ctx):
    print("[DALL-E Worker] Shutting down...")

class WorkerSettings:
    """
    ARQ worker settings for DALL-E.
    """
    functions = [generate_dalle_task]
    redis_settings = worker.RedisSettings.from_dsn(REDIS_URL)
    queue_name = 'dalle_queue'
    on_startup = startup
    on_shutdown = shutdown
