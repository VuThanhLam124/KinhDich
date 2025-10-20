# config.py
from pathlib import Path
import os

# ═══════════════════════════════════════════════════════════════
# DATABASE & API CONFIGURATION
# ═══════════════════════════════════════════════════════════════

MONGO_URI = (
    "mongodb+srv://thanhlamdev:Vuthanhlam124@cluster0.s9cdtme.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME = "kinhdich_enhanced_db"
COLLECTION = "enhanced_chunks"

CHUNKS_DATA_DIR = os.getenv(
    "CHUNKS_DATA_DIR",
    str(Path(__file__).resolve().parent.parent / "Kinh_Dich_Data")
)

# Kích thước batch khi insert MongoDB
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))

# ═══════════════════════════════════════════════════════════════
# EMBEDDING / RERANK MODELS
# ═══════════════════════════════════════════════════════════════

EMBED_MODEL = os.getenv("EMBED_MODEL", "keepitreal/vietnamese-sbert")
CE_MODEL = os.getenv("CE_MODEL", "intfloat/multilingual-e5-base")

# ═══════════════════════════════════════════════════════════════
# LLM PROVIDER CONFIGURATION
# ═══════════════════════════════════════════════════════════════

SUPPORTED_LLM_PROVIDERS = {"gemini", "openai", "local"}
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
if LLM_PROVIDER not in SUPPORTED_LLM_PROVIDERS:
    LLM_PROVIDER = "gemini"

# Shared generation defaults
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.8"))
LLM_TOP_K = int(os.getenv("LLM_TOP_K", "40"))
LLM_MAX_OUTPUT_TOKENS = int(os.getenv("LLM_MAX_OUTPUT_TOKENS", "1000"))

# Gemini configuration
_DEFAULT_GEMINI_KEY = "AIzaSyAHYqXx9o3dk6oswVKhISFIOija6Be91Uc"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", _DEFAULT_GEMINI_KEY)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")

# Local model configuration
LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "")
LOCAL_MODEL_TYPE = os.getenv("LOCAL_MODEL_TYPE", "auto")
LOCAL_DEVICE = os.getenv("LOCAL_DEVICE", "auto")
LOCAL_MAX_NEW_TOKENS = int(os.getenv("LOCAL_MAX_NEW_TOKENS", "512"))

# ═══════════════════════════════════════════════════════════════
# CACHE & PERFORMANCE OPTIMIZATION
# ═══════════════════════════════════════════════════════════════

CACHE_DIR = Path("./models_cache").resolve()
CACHE_DIR.mkdir(exist_ok=True)

# Set environment variables for model caching
for env in ("TRANSFORMERS_CACHE", "HF_HOME", "HUGGINGFACE_HUB_CACHE", "SENTENCE_TRANSFORMERS_HOME"):
    os.environ[env] = str(CACHE_DIR)

# ═══════════════════════════════════════════════════════════════
# SEARCH OPTIMIZATION PARAMETERS
# ═══════════════════════════════════════════════════════════════

# Optimized based on testing
TOP_K_RETRIEVE = 20      # Reduced for better precision
TOP_K_RERANK = 12         # Optimal for context window
SIMILARITY_THRESHOLD = 0.25  # Lowered to avoid empty results

# Vietnamese stop words for better search
STOP_WORDS = {
    "và", "là", "của", "cho", "trong", "một", "các", "đã", "với", "không",
    "có", "này", "để", "cũng", "thì", "như", "lại", "nếu", "sẽ", "được",
    "về", "từ", "theo", "tại", "hay", "hoặc", "khi", "đến", "ra", "up",
    "quẻ", "que", "gì", "là"
}

# ═══════════════════════════════════════════════════════════════
# XAI & CITATION CONFIGURATION
# ═══════════════════════════════════════════════════════════════

ENABLE_XAI = True
ENABLE_CITATIONS = True
MAX_CITATIONS = 10
CONFIDENCE_LEVELS = ["low", "medium", "high"]
