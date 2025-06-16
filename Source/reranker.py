from typing import List, Dict
from sentence_transformers import CrossEncoder
import numpy as np

from config import CE_MODEL, TOP_K_RERANK, CACHE_DIR

class KinhDichReranker:
    """Cross-encoder reranker cho Kinh Dịch"""
    
    def __init__(self):
        self.cross_encoder = CrossEncoder(CE_MODEL, cache_folder=CACHE_DIR)
    
    def rerank(self, query: str, docs: List[Dict]) -> List[Dict]:
        """Rerank documents bằng cross-encoder"""
        if not docs:
            return docs
        
        # Chuẩn bị pairs cho cross-encoder
        pairs = []
        for doc in docs:
            # Truncate text để fit vào context window
            text = doc["text"][:1024] if len(doc["text"]) > 1024 else doc["text"]
            pairs.append([query, text])
        
        # Tính scores
        scores = self.cross_encoder.predict(pairs)
        
        # Kết hợp với vector similarity scores nếu có
        final_scores = []
        for i, score in enumerate(scores):
            vector_score = docs[i].get("similarity_score", 0.0)
            # Weighted combination: 70% cross-encoder, 30% vector similarity
            combined_score = 0.7 * score + 0.3 * vector_score
            final_scores.append(combined_score)
        
        # Sort và lấy top-k
        sorted_indices = np.argsort(final_scores)[::-1][:TOP_K_RERANK]
        
        reranked_docs = []
        for idx in sorted_indices:
            doc = docs[idx]
            doc["rerank_score"] = final_scores[idx]
            reranked_docs.append(doc)
        
        return reranked_docs

# Compatibility function
def rerank(query: str, docs: List[Dict]) -> List[Dict]:
    reranker = KinhDichReranker()
    return reranker.rerank(query, docs)
