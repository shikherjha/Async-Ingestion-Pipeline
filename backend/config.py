import os
from dotenv import load_dotenv

load_dotenv()


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pipeline.db")

GROQ_API_KEYS = [
    k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()
]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.0-flash")

RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "10"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", "8000"))
MAX_LLM_RETRIES = int(os.getenv("MAX_LLM_RETRIES", "3"))

CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_TIMEOUT = 60
