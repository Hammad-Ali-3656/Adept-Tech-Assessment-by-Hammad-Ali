"""Central configuration. Everything overridable via environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw" / "CustomerChurn.csv"
DATA_PROCESSED_DIR = ROOT / "data" / "processed"
DATA_CLEAN = DATA_PROCESSED_DIR / "churn_clean.csv"
ARTIFACT_DIR = ROOT / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "churn_model.joblib"
MODEL_CARD_PATH = ARTIFACT_DIR / "model_card.json"

# ---- LLM ----
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower().strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

# Default models from Groq console
DEFAULT_GROQ_PLANNER = "qwen/qwen3.6-27b"
DEFAULT_GROQ_SMALL = "openai/gpt-oss-20b"

DEFAULT_OPENROUTER_PLANNER = "qwen/qwen-2.5-72b-instruct"
DEFAULT_OPENROUTER_SMALL = "openai/gpt-4o-mini"

if LLM_PROVIDER == "groq":
    PLANNER_MODEL = os.getenv("PLANNER_MODEL", DEFAULT_GROQ_PLANNER).strip()
    SMALL_MODEL = os.getenv("SMALL_MODEL", DEFAULT_GROQ_SMALL).strip()
else:
    PLANNER_MODEL = os.getenv("PLANNER_MODEL", DEFAULT_OPENROUTER_PLANNER).strip()
    SMALL_MODEL = os.getenv("SMALL_MODEL", DEFAULT_OPENROUTER_SMALL).strip()




PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}

def api_key() -> str:
    return GROQ_API_KEY if LLM_PROVIDER == "groq" else OPENROUTER_API_KEY

def base_url() -> str:
    return PROVIDER_BASE_URLS.get(LLM_PROVIDER, PROVIDER_BASE_URLS["groq"])

# ---- Agent behaviour ----
MAX_AGENT_STEPS = int(os.getenv("MAX_AGENT_STEPS", "4"))
LLM_CACHE_SIZE = int(os.getenv("LLM_CACHE_SIZE", "256"))
TOOL_OUTPUT_CHAR_LIMIT = int(os.getenv("TOOL_OUTPUT_CHAR_LIMIT", "4000"))
SANDBOX_TIMEOUT_SECONDS = float(os.getenv("SANDBOX_TIMEOUT_SECONDS", "10"))
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "2000"))

# Numeric tolerance used by the critic / eval harness when checking that a
# number quoted in prose traces back to a computed value (rounding slack).
NUMBER_MATCH_REL_TOL = 0.02
