import os
from dotenv import load_dotenv

load_dotenv()

# Cloudflare R2 Configuration
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_SESSION_TOKEN = os.getenv("R2_SESSION_TOKEN")
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

SUPPORTED_GENERATORS = ['gpt-image-2-2026-04-21', 'gemini']

# Prompt engineering templates
GPT_IMAGE_PROMPT_TEMPLATE = (
    "You are a world-class logo designer and prompt engineer. "
    "Craft a detailed, high-quality image generation prompt for a brand named '{text}'.\n"
    "Context: {description}\n"
    "Requested Style: {style}\n"
    "Color Palette: {palette}\n\n"
    "Guidelines:\n"
    "- Focus on professional, high-concept visual metaphors.\n"
    "- Ensure a clean white background.\n"
    "- Maintain a sharp, vector-ready aesthetic.\n"
    "- The prompt should be optimized for GPT image generation.\n"
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

# ─────────────────────────────────────────────────────────────────────────────
# P3.2 — Cost Tracking
# ─────────────────────────────────────────────────────────────────────────────
# Approximate per-generation cost in USD, used to populate cost_usd on each
# LogoGeneration row and to drive the Grafana cost dashboard / budget alerts.
# These are illustrative estimates — update to match your actual negotiated
# provider pricing. They are intentionally simple (no token-counting) since
# the goal is budget visibility, not penny-accurate billing reconciliation.
GENERATION_COST_USD = {
    "gpt-image-2-2026-04-21": {
        "low": 0.04,
        "medium": 0.08,
        "high": 0.12,
    },
    "gemini": 0.02,  # flat estimate for gemini-2.5-flash-image
}

# ─────────────────────────────────────────────────────────────────────────────
# P3.3 — Data Retention
# ─────────────────────────────────────────────────────────────────────────────
# Default retention window (in days) for generation history. The maintenance
# worker's daily cron job (see maintenance_worker.py) permanently deletes any
# LogoGeneration row — and its associated R2 image — older than this window,
# satisfying the GDPR Article 5(1)(e) storage-limitation principle.
DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "365"))
