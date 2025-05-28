from pathlib import Path
import os

# ─── Mongo Atlas URI ───────────────────────────────────────────────
MONGO_URI = (
    "mongodb+srv://thanhlamdev:lamvthe180779@cluster0.jvlxnix.mongodb.net/"
    "?retryWrites=true&w=majority"
)
DB_NAME        = "kinhdich_kb"
COLLECTION     = "chunks"

# ─── Embedding & Rerank ────────────────────────────────────────────
EMBED_MODEL    = "VoVanPhuc/sup-SimCSE-VietNamese-phobert-base"   # 768-d
CE_MODEL       = "intfloat/multilingual-e5-base"                  # cross-encoder

# ─── Gemini (free) ────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyAHYqXx9o3dk6oswVKhISFIOija6Be91Uc"
GEMINI_MODEL   = "gemini-2.0-flash"

# ─── Cache thư mục HF ─────────────────────────────────────────────
CACHE_DIR = Path("./hf_cache").resolve()
CACHE_DIR.mkdir(exist_ok=True)
for env in ("TRANSFORMERS_CACHE","HF_HOME","HUGGINGFACE_HUB_CACHE","SENTENCE_TRANSFORMERS_HOME"):
    os.environ[env] = str(CACHE_DIR)

# ─── Stop-words & tham số ────────────────────────────────────────
STOP_WORDS = {
    "và","là","của","cho","trong","một","các","đã","với","không",
    "có","này","để","cũng","thì","như","lại","nếu","sẽ","được"
}
TOP_K_RETRIEVE = 30
TOP_K_RERANK   = 5
