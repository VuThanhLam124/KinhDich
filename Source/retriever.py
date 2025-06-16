import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from underthesea import word_tokenize
from pymongo import MongoClient

from config import *
from mapping import detect_hexagram

class KinhDichRetriever:
    """Retriever tối ưu cho Kinh Dịch với hybrid search"""
    
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.collection = self.client[DB_NAME][COLLECTION]
        self.embedder = SentenceTransformer(EMBED_MODEL, cache_folder=CACHE_DIR)
    
    def semantic_search(self, query: str, limit: int = TOP_K_RETRIEVE, 
                       filters: Dict = None) -> List[Dict]:
        """Vector search sử dụng MongoDB Atlas"""
        # Tokenize query
        tokenized_query = word_tokenize(query, format="text")
        query_embedding = self.embedder.encode(tokenized_query).tolist()
        
        # Xây dựng aggregation pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # Tên index tạo trên Atlas
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": limit * 5,  # Oversampling
                    "limit": limit
                }
            },
            {
                "$addFields": {
                    "similarity_score": {"$meta": "vectorSearchScore"}
                }
            },
            {
                "$match": {
                    "similarity_score": {"$gte": SIMILARITY_THRESHOLD}
                }
            }
        ]
        
        # Thêm filters nếu có
        if filters:
            pipeline.insert(-1, {"$match": filters})
        
        # Project fields cần thiết
        pipeline.append({
            "$project": {
                "_id": 1,
                "text": 1,
                "hexagram": 1,
                "section": 1,
                "content_type": 1,
                "similarity_score": 1,
                "original_chunk": 1
            }
        })
        
        try:
            results = list(self.collection.aggregate(pipeline))
            return results
        except Exception as e:
            # Fallback nếu vector search không hoạt động
            print(f"Vector search failed: {e}, using fallback...")
            return self._fallback_search(query, limit)
    
    def _fallback_search(self, query: str, limit: int) -> List[Dict]:
        """Fallback search khi vector search không hoạt động"""
        # Text search đơn giản
        docs = list(self.collection.find(
            {"$text": {"$search": query}},
            {"_id": 1, "text": 1, "hexagram": 1, "section": 1, "content_type": 1, "original_chunk": 1}
        ).limit(limit))
        
        if not docs:
            # Random sampling nếu không có kết quả
            docs = list(self.collection.find({}).limit(limit))
        
        return docs
    
    def hexagram_specific_search(self, hexagram_code: str, 
                                query: str = None, limit: int = 10) -> List[Dict]:
        """Tìm kiếm cụ thể theo quẻ"""
        filters = {"hexagram": hexagram_code}
        
        if query:
            return self.semantic_search(query, limit, filters)
        else:
            # Lấy tất cả chunks của quẻ
            return list(self.collection.find(
                filters,
                {"_id": 1, "text": 1, "hexagram": 1, "content_type": 1, "original_chunk": 1}
            ).limit(limit))
    
    def smart_search(self, query: str) -> List[Dict]:
        """Hybrid search thông minh"""
        # 1. Detect hexagram
        hexagram_code = detect_hexagram(query)
        
        if hexagram_code:
            # Search specific hexagram
            results = self.hexagram_specific_search(hexagram_code, query, TOP_K_RETRIEVE // 2)
            
            # Bổ sung với general search
            general_results = self.semantic_search(query, TOP_K_RETRIEVE // 2)
            
            # Merge và deduplicate
            seen_ids = set()
            combined_results = []
            
            for result in results + general_results:
                if result["_id"] not in seen_ids:
                    seen_ids.add(result["_id"])
                    combined_results.append(result)
            
            return combined_results[:TOP_K_RETRIEVE]
        else:
            # General semantic search
            return self.semantic_search(query, TOP_K_RETRIEVE)

def smart_search(query: str) -> List[Dict[str, Any]]:
    """Interface tương thích với code cũ"""
    retriever = KinhDichRetriever()
    return retriever.smart_search(query)
