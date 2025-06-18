# config.py
from pathlib import Path
import os

# ═══════════════════════════════════════════════════════════════
# DATABASE & API CONFIGURATION
# ═══════════════════════════════════════════════════════════════

MONGO_URI = (
    "mongodb+srv://thanhlamdev:lamvthe180779@cluster0.jvlxnix.mongodb.net/"
    "?retryWrites=true&w=majority"
)
DB_NAME = "kinhdich_kb"
COLLECTION = "chunks"

# ═══════════════════════════════════════════════════════════════
# MODEL CONFIGURATION - Optimized for Vietnamese
# ═══════════════════════════════════════════════════════════════

EMBED_MODEL = "keepitreal/vietnamese-sbert"  # Better for Vietnamese retrieval
CE_MODEL = "intfloat/multilingual-e5-base"   # Cross-encoder for reranking
GEMINI_API_KEY = "AIzaSyAHYqXx9o3dk6oswVKhISFIOija6Be91Uc"
GEMINI_MODEL = "gemini-2.0-flash-exp"
# GEMINI_MODEL = "gemini-2.5-flash"

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
