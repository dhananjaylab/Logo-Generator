import os
import base64
import io
import asyncio
from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from google import genai
from openai import AsyncOpenAI
from dotenv import load_dotenv
from PIL import Image

# Load API key
load_dotenv()

app = FastAPI()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Clients
gemini_client = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)

openai_client = None
if OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Design Constants from LogoForge AI
LOGO_STYLES = {
    'minimalist': 'clean minimalist vector logo, flat design, simple geometric shapes',
    'tech': 'modern futuristic tech logo, sleek lines, digital aesthetic',
    'vintage': 'vintage retro style logo, classic typography, badge style',
    'abstract': 'abstract creative logo, unique symbolic representation',
    'mascot': 'character mascot logo, friendly and recognizable',
    'luxury': 'elegant luxury brand logo, sophisticated, high-end aesthetic',
}

COLOR_PALETTES = {
    'monochrome': 'Monochrome (Black, White)',
    'ocean': 'Ocean (Blue, Light Blue, Cyan)',
    'sunset': 'Sunset (Red, Orange, Yellow)',
    'forest': 'Forest (Dark Green, Green, Mint)',
    'royal': 'Royal (Purple, Gold, White)',
    'neon': 'Neon (Green, Magenta, Cyan)',
}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/generate")
async def generate_logo(
    text: str = Form("Brand"),
    description: str = Form(""),
    style: str = Form("minimalist"),
    palette: str = Form("monochrome")
):
    if not gemini_client:
        raise HTTPException(status_code=500, detail="Gemini API Client not initialized.")
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API Client not initialized.")

    try:
        # 1. Use Gemini to engineer a high-quality prompt based on styles and palettes
        style_prompt = LOGO_STYLES.get(style, LOGO_STYLES['minimalist'])
        palette_desc = COLOR_PALETTES.get(palette, COLOR_PALETTES['monochrome'])

        refine_prompt = (
            f"You are a world-class logo designer and prompt engineer. "
            f"Craft a detailed, high-quality image generation prompt for a brand named '{text}'.\n"
            f"Context: {description}\n"
            f"Requested Style: {style_prompt}\n"
            f"Color Palette: {palette_desc}\n\n"
            f"Guidelines:\n"
            f"- Focus on professional, high-concept visual metaphors.\n"
            f"- Ensure a clean white background.\n"
            f"- Maintain a sharp, vector-ready aesthetic.\n"
            f"- The prompt should be optimized for DALL-E 3.\n"
            f"- DO NOT mention any text other than '{text}' if it fits the design.\n"
            f"Return ONLY the optimized prompt text."
        )

        response = await asyncio.to_thread(
            gemini_client.models.generate_content,
            model='gemini-2.0-flash',
            contents=refine_prompt
        )
        
        optimized_prompt = response.text.strip()
        print(f"Optimized Prompt: {optimized_prompt}")

        # 2. Use DALL-E 3 for the actual image generation
        dalle_response = await openai_client.images.generate(
            model="dall-e-3",
            prompt=optimized_prompt,
            n=1,
            size="1024x1024"
        )

        image_url = dalle_response.data[0].url

        return {
            "result": [image_url],
            "brand": text,
            "style": style,
            "palette": palette,
            "prompt": optimized_prompt
        }

    except Exception as e:
        print(f"Generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.post("/modify")
async def modify_logo(
    logo_image: UploadFile = File(...),
    logo_instructions: str = Form(...)
):
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API Client not initialized.")

    try:
        # Fallback to DALL-E 3 for modification if needed, 
        # but DALL-E 3 doesn't typically accept mask/image for modification as easily as DALL-E 2 edit.
        # For now, let's just mark it as needing update or use DALL-E 2.
        raise HTTPException(status_code=501, detail="Modify endpoint is currently being upgraded.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=5050)