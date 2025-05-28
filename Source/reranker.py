# source/reranker.py
from typing import List, Dict
from sentence_transformers import CrossEncoder
from Source.config import CE_MODEL, TOP_K_RERANK

ce = CrossEncoder(CE_MODEL)

def rerank(query: str, docs: List[Dict]) -> List[Dict]:
    pairs = [[query, d["text"][:1024]] for d in docs]
    scores = ce.predict(pairs)
    idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:TOP_K_RERANK]
    return [docs[i] for i in idx]
