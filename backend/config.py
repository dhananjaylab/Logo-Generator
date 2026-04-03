import os
from dotenv import load_dotenv

load_dotenv()

# Cloudflare R2 Configuration
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
R2_PUBLIC_DOMAIN = os.getenv("R2_PUBLIC_DOMAIN", "").rstrip("/")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Redis / ARQ Settings
from arq.connections import RedisSettings
_temp_settings = RedisSettings.from_dsn(REDIS_URL)
REDIS_SETTINGS = RedisSettings(
    host=_temp_settings.host,
    port=_temp_settings.port,
    database=_temp_settings.database,
    password=_temp_settings.password,
    conn_timeout=20,
)

# Design Constants and Configuration

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

SUPPORTED_GENERATORS = ['dall-e-3', 'gemini']

# Prompt engineering templates
DALLE3_PROMPT_TEMPLATE = (
    "You are a world-class logo designer and prompt engineer. "
    "Craft a detailed, high-quality image generation prompt for a brand named '{text}'.\n"
    "Context: {description}\n"
    "Requested Style: {style}\n"
    "Color Palette: {palette}\n\n"
    "Guidelines:\n"
    "- Focus on professional, high-concept visual metaphors.\n"
    "- Ensure a clean white background.\n"
    "- Maintain a sharp, vector-ready aesthetic.\n"
    "- The prompt should be optimized for DALL-E 3.\n"
    "- DO NOT mention any text other than '{text}' if it fits the design.\n"
    "Return ONLY the optimized prompt text."
)

GEMINI_GENERATION_TEMPLATE = (
    "Create a professional logo for a brand named '{text}'. "
    "Style: {style}. "
    "Color Palette: {palette}. "
    "Context: {description}. "
    "The logo should be clean, vector-ready, and suitable for professional use. "
    "Ensure a white or transparent background."
)
