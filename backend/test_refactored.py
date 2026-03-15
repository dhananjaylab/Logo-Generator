"""
Test file for the refactored backend structure.
Tests both Gemini and DALL-E logo generation modes.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from dependencies import Clients
from services import LLMService
from config import LOGO_STYLES, COLOR_PALETTES

load_dotenv()


async def test_dalle_generation():
    """Test DALL-E 3 logo generation with Gemini refinement"""
    print("\n=== Testing DALL-E 3 Generation ===")
    
    gemini_client = Clients.get_gemini_client()
    openai_client = Clients.get_openai_client()
    
    if not gemini_client:
        print("❌ Gemini client not initialized")
        return False
    
    if not openai_client:
        print("❌ OpenAI client not initialized")
        return False
    
    try:
        llm_service = LLMService(gemini_client, openai_client)
        
        print("Generating logo with DALL-E 3...")
        image_url, prompt = await llm_service.generate_logo_with_dalle(
            text="TechVision",
            description="AI-powered vision analytics platform",
            style=LOGO_STYLES['tech'],
            palette=COLOR_PALETTES['ocean']
        )
        
        print(f"✅ DALL-E 3 generation successful!")
        print(f"Image URL: {image_url}")
        print(f"Prompt: {prompt[:100]}...")
        return True
    
    except Exception as e:
        print(f"❌ DALL-E 3 generation failed: {str(e)}")
        return False


async def test_gemini_generation():
    """Test Gemini direct logo generation"""
    print("\n=== Testing Gemini Direct Generation ===")
    
    gemini_client = Clients.get_gemini_client()
    
    if not gemini_client:
        print("❌ Gemini client not initialized")
        return False
    
    try:
        llm_service = LLMService(gemini_client, None)
        
        print("Generating logo with Gemini...")
        image_path, prompt = await llm_service.generate_logo_with_gemini(
            text="NanoBrand",
            description="Nano-scale technology company",
            style=LOGO_STYLES['minimalist'],
            palette=COLOR_PALETTES['monochrome']
        )
        
        print(f"✅ Gemini generation successful!")
        print(f"Image Path: {image_path}")
        print(f"File exists: {os.path.exists(image_path)}")
        print(f"Prompt: {prompt[:100]}...")
        return True
    
    except Exception as e:
        print(f"❌ Gemini generation failed: {str(e)}")
        return False


async def test_clients():
    """Test client initialization"""
    print("\n=== Testing Client Initialization ===")
    
    gemini_ready = Clients.is_gemini_ready()
    openai_ready = Clients.is_openai_ready()
    
    print(f"Gemini Client: {'✅ Ready' if gemini_ready else '❌ Not Ready'}")
    print(f"OpenAI Client: {'✅ Ready' if openai_ready else '❌ Not Ready'}")
    
    return gemini_ready and openai_ready


async def main():
    """Run all tests"""
    print("🚀 Starting Backend Tests")
    print("=" * 50)
    
    # Test client initialization
    if not await test_clients():
        print("\n❌ Client initialization failed. Check API keys in .env")
        return
    
    # Test DALL-E generation
    dalle_result = await test_dalle_generation()
    
    # Test Gemini generation
    gemini_result = await test_gemini_generation()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print(f"DALL-E 3 Generation: {'✅ PASSED' if dalle_result else '❌ FAILED'}")
    print(f"Gemini Generation: {'✅ PASSED' if gemini_result else '❌ FAILED'}")
    
    if dalle_result and gemini_result:
        print("\n🎉 All tests passed!")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")


if __name__ == "__main__":
    asyncio.run(main())
