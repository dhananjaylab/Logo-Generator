import os
from functools import lru_cache
from google import genai
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Clients:
    """Container for API clients"""
    _gemini_client = None
    _openai_client = None

    @classmethod
    def get_gemini_client(cls):
        """Get or initialize Gemini client"""
        if cls._gemini_client is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                cls._gemini_client = genai.Client(api_key=api_key)
        return cls._gemini_client

    @classmethod
    def get_openai_client(cls):
        """Get or initialize OpenAI client"""
        if cls._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                cls._openai_client = AsyncOpenAI(api_key=api_key)
        return cls._openai_client

    @classmethod
    def is_gemini_ready(cls):
        """Check if Gemini client is ready"""
        return cls.get_gemini_client() is not None

    @classmethod
    def is_openai_ready(cls):
        """Check if OpenAI client is ready"""
        return cls.get_openai_client() is not None


# Dependency functions for FastAPI
def get_gemini_client():
    """Dependency for Gemini client"""
    return Clients.get_gemini_client()


def get_openai_client():
    """Dependency for OpenAI client"""
    return Clients.get_openai_client()
