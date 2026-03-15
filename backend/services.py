import io
import asyncio
from typing import Optional, Tuple
from PIL import Image
from google import genai
from openai import AsyncOpenAI
from config import DALLE3_PROMPT_TEMPLATE, GEMINI_GENERATION_TEMPLATE
from utils import get_output_path, sanitize_filename


class PromptRefinementService:
    """Service for refining prompts using OpenAI GPT-4"""

    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def refine_for_dalle(self, 
                               text: str, 
                               description: str, 
                               style: str, 
                               palette: str,
                               tagline: str = "",
                               typography: str = "",
                               elements_to_include: str = "",
                               elements_to_avoid: str = "",
                               brand_mission: str = "") -> str:
        """
        Use OpenAI GPT-4 Turbo to refine a prompt for DALL-E 3.
        Provides better quality prompts than template-based approaches.
        """
        
        detailed_prompt = (
            f"Professional logo design prompt engineering:\n"
            f"Brand Name: {text}\n"
            f"Description: {description}\n"
            f"Style: {style}\n"
            f"Color Palette: {palette}\n"
            f"{f'Tagline: {tagline}' if tagline else ''}\n"
            f"{f'Typography Preference: {typography}' if typography else ''}\n"
            f"{f'Brand Mission: {brand_mission}' if brand_mission else ''}\n"
            f"{f'Elements to Include: {elements_to_include}' if elements_to_include else ''}\n"
            f"{f'Elements to Avoid: {elements_to_avoid}' if elements_to_avoid else ''}\n\n"
            
            f"Create a detailed, high-quality DALL-E 3 prompt for a professional logo that:\n"
            f"- Captures the brand essence\n"
            f"- Uses the specified color palette\n"
            f"- Matches the visual style\n"
            f"- Is vector-ready and scalable\n"
            f"- Has a clean white background\n"
            f"- Is suitable for modern web and mobile applications\n\n"
            f"Return ONLY the optimized prompt text, nothing else."
        )

        response = await self.client.chat.completions.create(
            model="gpt-4-turbo",  # Using latest GPT-4 Turbo model
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert logo designer and AI prompt engineer. Create detailed, high-quality prompts for DALL-E 3 image generation."
                },
                {
                    "role": "user",
                    "content": detailed_prompt
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()


class GeminiService:
    """Service for Gemini API operations"""

    def __init__(self, client: genai.Client):
        self.client = client

    async def generate_logo(self, 
                           text: str, 
                           description: str, 
                           style: str, 
                           palette: str,
                           tagline: str = "",
                           typography: str = "",
                           elements_to_include: str = "",
                           elements_to_avoid: str = "",
                           brand_mission: str = "") -> Tuple[str, str]:
        """
        Generate a logo using Gemini's image generation capabilities.
        Gemini-only path: no external refinement services used.
        
        Returns:
            Tuple of (image_path, prompt_used)
        """
        
        # Build comprehensive prompt using all available parameters
        prompt = (
            f"Create a professional, high-quality logo for a brand named '{text}'.\n\n"
            f"Brand Details:\n"
            f"- Description: {description}\n"
            f"{f'- Tagline: {tagline}' if tagline else ''}\n"
            f"{f'- Mission: {brand_mission}' if brand_mission else ''}\n\n"
            f"Design Specifications:\n"
            f"- Visual Style: {style}\n"
            f"- Color Palette: {palette}\n"
            f"{f'- Typography: {typography}' if typography else ''}\n"
            f"{f'- Must Include: {elements_to_include}' if elements_to_include else ''}\n"
            f"{f'- Must Avoid: {elements_to_avoid}' if elements_to_avoid else ''}\n\n"
            f"Requirements:\n"
            f"- Professional, high-resolution quality\n"
            f"- Vector-style, scalable design\n"
            f"- Clean white or transparent background\n"
            f"- Suitable for professional use on web and mobile\n"
            f"- Modern and timeless design"
        )

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model='gemini-2.0-flash-001',  # Latest stable Gemini model for images
            contents=[prompt],
        )

        image_path = None
        # Process response and extract image
        for part in response.candidates[0].content.parts:
            if part.inline_data:
                # Save image from inline data
                image = Image.open(io.BytesIO(part.inline_data.data))
                sanitized_name = sanitize_filename(f"gemini_logo_{text.replace(' ', '_')}.png")
                image_path = get_output_path(sanitized_name)
                image.save(image_path)
                break

        if not image_path:
            raise ValueError("No image generated by Gemini")

        return image_path, prompt


class DALLEService:
    """Service for OpenAI DALL-E 3 operations"""

    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def generate_logo(self, prompt: str) -> str:
        """
        Generate a logo using DALL-E 3.
        
        Args:
            prompt: The prompt to use for image generation
            
        Returns:
            Image URL
        """
        response = await self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="hd",  # Use high definition for professional logos
            style="natural"
        )

        return response.data[0].url


class LLMService:
    """Unified service for LLM operations - acts as a facade"""

    def __init__(self, gemini_client: genai.Client, openai_client: AsyncOpenAI):
        self.gemini_service = GeminiService(gemini_client)
        self.dalle_service = DALLEService(openai_client)
        self.prompt_refiner = PromptRefinementService(openai_client)

    async def generate_logo_with_dalle(self, 
                                       text: str, 
                                       description: str, 
                                       style: str, 
                                       palette: str,
                                       tagline: str = "",
                                       typography: str = "",
                                       elements_to_include: str = "",
                                       elements_to_avoid: str = "",
                                       brand_mission: str = "") -> Tuple[str, str]:
        """
        Generate logo using DALL-E 3 with GPT-4 prompt refinement.
        DALL-E path: Uses only OpenAI services (GPT-4 for refinement + DALL-E 3 for generation)
        
        Returns:
            Tuple of (image_url, optimized_prompt)
        """
        # Step 1: Use OpenAI GPT-4 Turbo to refine the prompt
        optimized_prompt = await self.prompt_refiner.refine_for_dalle(
            text, description, style, palette,
            tagline, typography, 
            elements_to_include, elements_to_avoid, brand_mission
        )

        # Step 2: Use DALL-E 3 for image generation
        image_url = await self.dalle_service.generate_logo(optimized_prompt)

        return image_url, optimized_prompt

    async def generate_logo_with_gemini(self, 
                                        text: str, 
                                        description: str, 
                                        style: str, 
                                        palette: str,
                                        tagline: str = "",
                                        typography: str = "",
                                        elements_to_include: str = "",
                                        elements_to_avoid: str = "",
                                        brand_mission: str = "") -> Tuple[str, str]:
        """
        Generate logo directly using Gemini's image generation.
        Gemini path: Uses only Gemini services (no external LLM calls)
        
        Returns:
            Tuple of (image_path, prompt_used)
        """
        image_path, prompt = await self.gemini_service.generate_logo(
            text, description, style, palette,
            tagline, typography,
            elements_to_include, elements_to_avoid, brand_mission
        )

        return image_path, prompt
