from pathlib import Path
import os

# ─── Database Configuration ──────────────────────────────────────
# MONGO_URI = (
#     "mongodb+srv://thanhlamdev:lamvthe180779@cluster0.jvlxnix.mongodb.net/"
#     "?retryWrites=true&w=majority"
# )
MONGO_URI = (
    "mongodb+srv://vuthanhlam848:bfwYK9jyLG5fqHoX@cluster0.s9cdtme.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
DB_NAME = "kinhdich_db"
COLLECTION = "chunks"

# ─── Embedding Models ───────────────────────────────────────────
# Thay đổi model để tối ưu cho retrieval tiếng Việt
EMBED_MODEL = "keepitreal/vietnamese-sbert"  # 768-d, tốt hơn cho Vietnamese
# EMBED_MODEL = "AITeamVN/Vietnamese_Embedding"  # Alternative: 1024-d, SOTA performance
CE_MODEL = "intfloat/multilingual-e5-base"  # Cross-encoder for reranking

# ─── LLM Configuration ──────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyAHYqXx9o3dk6oswVKhISFIOija6Be91Uc"
GEMINI_MODEL = "gemini-2.0-flash-exp"

# ─── Cache và Performance ───────────────────────────────────────
CACHE_DIR = Path("./models_cache").resolve()
CACHE_DIR.mkdir(exist_ok=True)

for env in ("TRANSFORMERS_CACHE", "HF_HOME", "HUGGINGFACE_HUB_CACHE", "SENTENCE_TRANSFORMERS_HOME"):
    os.environ[env] = str(CACHE_DIR)

# ─── Search Parameters ──────────────────────────────────────────
STOP_WORDS = {
    "và", "là", "của", "cho", "trong", "một", "các", "đã", "với", "không",
    "có", "này", "để", "cũng", "thì", "như", "lại", "nếu", "sẽ", "được",
    "về", "từ", "theo", "tại", "hay", "hoặc", "khi", "đến", "ra", "up"
}

# Search configuration
TOP_K_RETRIEVE = 20  # Giảm xuống để tăng tốc
TOP_K_RERANK = 15     # Tối ưu cho context window
SIMILARITY_THRESHOLD = 0.5  # Ngưỡng similarity tối thiểu
