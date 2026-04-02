import os

from groq import Groq
from fastapi.security import APIKeyHeader
from dotenv import load_dotenv

# ============================================================
# CONFIG
# ============================================================

load_dotenv()

GROQ_API_KEY = (os.getenv("GROQ_API_KEY") or "").strip()
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found")

GROQ_MODEL = (os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile").strip()
client = Groq(api_key=GROQ_API_KEY)

API_SECRET_TOKEN = (os.getenv("API_SECRET_KEY") or "").strip()
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

MIN_DELAY = float(os.getenv("MIN_HUMAN_DELAY_S", "0.10"))
MAX_DELAY = float(os.getenv("MAX_HUMAN_DELAY_S", "0.28"))

PORT = int(os.getenv("PORT", "8000"))

# ============================================================
# SIMPLE CHAT LOGGING
# ============================================================

def log_chat(sender: str, text: str):
    print(f"{sender.upper()}: {text}")
