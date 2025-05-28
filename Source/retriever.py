# Source/retriever.py
import numpy as np
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from underthesea import word_tokenize
from langchain_huggingface import HuggingFaceEmbeddings
from Source.db import collection, embedder
from Source.mapping import detect_hexagram
from Source.config import STOP_WORDS, TOP_K_RETRIEVE

vectorizer = TfidfVectorizer(
    tokenizer=lambda t: " ".join(x for x in word_tokenize(t, format="text").split()
                                 if x.lower() not in STOP_WORDS),
    lowercase=False, max_features=8000)

def _score(query: str, docs: List[Dict], hex_code: str|None) -> np.ndarray:
    tfidf = vectorizer.fit_transform([d["text"] for d in docs] + [query])
    kw    = (tfidf[-1] @ tfidf[:-1].T).toarray()[0]
    qvec  = embedder.embed_query(query)
    embs  = np.array([d["embedding"] for d in docs])
    sem   = cosine_similarity([qvec], embs)[0]
    bonus = np.array([1.0 if hex_code and d["hexagram"] == hex_code else 0.0 for d in docs])
    return 0.25*kw + 0.5*sem + 0.25*bonus

def smart_search(query: str) -> List[Dict[str, Any]]:
    hex_code = detect_hexagram(query)
    proj = {"_id":1,"text":1,"embedding":1,"hexagram":1,"source_page_range":1}

    # 1) Thử lọc theo quẻ (nếu phát hiện)
    docs = []
    if hex_code:
        docs = list(collection.find({"hexagram": hex_code}, proj).limit(500))

    # 2) Nếu rỗng, fallback: lấy random 1 000 docs toàn tập
    if not docs:
        docs = list(collection.find({}, proj).limit(1000))

    # 3) Tính điểm & chọn top-N
    scores = _score(query, docs, hex_code)
    top_idx = np.argsort(scores)[::-1][:TOP_K_RETRIEVE]
    return [docs[i] for i in top_idx]
