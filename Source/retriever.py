# retriever.py - Optimized Retriever
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
from underthesea import word_tokenize
from pymongo import MongoClient
from tqdm import tqdm
import time 

from config import *
from mapping import detect_hexagram

logger = logging.getLogger(__name__)

class OptimizedKinhDichRetriever:
    """Optimized Retriever với multi-strategy fallback và performance tracking"""
    
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.collection = self.client[DB_NAME][COLLECTION]
        self.embedder = None  # Lazy loading
        self.performance_stats = {"searches": 0, "avg_time": 0, "success_rate": 0}
        
        # Verify setup with progress bar
        self._verify_setup_with_progress()
    
    def _get_embedder(self):
        """Lazy loading embedder to save memory"""
        if self.embedder is None:
            print("Loading embedding model...")
            self.embedder = SentenceTransformer(EMBED_MODEL, cache_folder=CACHE_DIR)
        return self.embedder
    
    def _verify_setup_with_progress(self):
        """Verify setup với tqdm progress tracking"""
        
        checks = [
            ("MongoDB Connection", self._check_connection),
            ("Collection Exists", self._check_collection),
            ("Documents Count", self._check_documents),
            ("Embeddings Coverage", self._check_embeddings)
        ]
        
        print("🔧 Verifying system setup...")
        for desc, check_func in tqdm(checks, desc="Setup Verification"):
            try:
                result = check_func()
                logger.info(f"{desc}: {result}")
            except Exception as e:
                logger.error(f"{desc}: {e}")
                raise
    
    def _check_connection(self):
        self.client.admin.command('ping')
        return "Connected"
    
    def _check_collection(self):
        if COLLECTION not in self.client[DB_NAME].list_collection_names():
            raise Exception(f"Collection '{COLLECTION}' not found")
        return "Exists"
    
    def _check_documents(self):
        count = self.collection.count_documents({})
        if count == 0:
            raise Exception("Collection is empty")
        return f"{count} documents"
    
    def _check_embeddings(self):
        embedding_count = self.collection.count_documents({"embedding": {"$exists": True}})
        total_count = self.collection.count_documents({})
        coverage = (embedding_count / total_count) * 100 if total_count > 0 else 0
        return f"{embedding_count}/{total_count} ({coverage:.1f}%)"
    
    def smart_search(self, query: str) -> List[Dict]:
        """Optimized smart search với comprehensive fallback"""
        
        start_time = time.time()
        self.performance_stats["searches"] += 1
        
        try:
            # Strategy 1: Hexagram-specific search
            hexagram_code = detect_hexagram(query)
            if hexagram_code:
                logger.info(f"Hexagram detected: {hexagram_code}")
                results = self._hexagram_focused_search(hexagram_code, query)
                if results:
                    self._update_performance_stats(start_time, True)
                    return results
            
            # Strategy 2: Vector search
            logger.info("Attempting vector search...")
            results = self._vector_search_with_fallback(query)
            if results:
                self._update_performance_stats(start_time, True)
                return results
            
            # Strategy 3: Multi-level fallback
            logger.warning("Vector search failed, using fallback strategies...")
            results = self._comprehensive_fallback_search(query)
            
            self._update_performance_stats(start_time, len(results) > 0)
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            self._update_performance_stats(start_time, False)
            return self._emergency_fallback(query)
    
    def _hexagram_focused_search(self, hexagram_code: str, query: str) -> List[Dict]:
        """Optimized hexagram-specific search"""
        
        # Primary hexagram filter
        primary_filter = {"hexagram": hexagram_code}
        docs = list(self.collection.find(primary_filter).limit(TOP_K_RETRIEVE))
        
        if docs:
            logger.info(f"Found {len(docs)} docs for {hexagram_code}")
            return docs
        
        # Fallback: Search by hexagram name in text
        hexagram_name = hexagram_code.replace("QUE_", "").lower()
        text_filter = {"text": {"$regex": hexagram_name, "$options": "i"}}
        docs = list(self.collection.find(text_filter).limit(TOP_K_RETRIEVE))
        
        if docs:
            logger.info(f"Found {len(docs)} docs by name search")
            return docs
        
        logger.warning(f"No specific docs found for {hexagram_code}")
        return []
    
    def _vector_search_with_fallback(self, query: str) -> List[Dict]:
        """Vector search với intelligent fallback"""
        
        try:
            embedder = self._get_embedder()
            tokenized_query = word_tokenize(query, format="text")
            query_embedding = embedder.encode(tokenized_query).tolist()
            
            # Optimized vector search pipeline
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": "vector_index",
                        "path": "embedding",
                        "queryVector": query_embedding,
                        "numCandidates": TOP_K_RETRIEVE * 3,
                        "limit": TOP_K_RETRIEVE
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
                },
                {
                    "$project": {
                        "_id": 1, "text": 1, "hexagram": 1, "section": 1,
                        "content_type": 1, "similarity_score": 1, "original_chunk": 1
                    }
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            
            if results:
                logger.info(f"Vector search: {len(results)} results")
                return results
            else:
                logger.warning("Vector search returned 0 results")
                return []
                
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []
    
    def _comprehensive_fallback_search(self, query: str) -> List[Dict]:
        """Comprehensive fallback với multiple strategies"""
        
        strategies = [
            ("Text Index Search", self._text_search),
            ("Keyword Regex Search", self._keyword_search),
            ("Section-based Search", self._section_search),
            ("Random Sampling", self._random_search)
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"Trying {strategy_name}...")
                results = strategy_func(query)
                if results:
                    logger.info(f"{strategy_name} found {len(results)} results")
                    return results
            except Exception as e:
                logger.warning(f"{strategy_name} failed: {e}")
                continue
        
        logger.error("All fallback strategies failed")
        return []
    
    def _text_search(self, query: str) -> List[Dict]:
        """Text index search"""
        try:
            self.collection.create_index([("text", "text")])
        except:
            pass  # Index might already exist
        
        return list(self.collection.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(TOP_K_RETRIEVE))
    
    def _keyword_search(self, query: str) -> List[Dict]:
        """Smart keyword regex search"""
        keywords = [w.strip().lower() for w in query.split() 
                   if len(w.strip()) > 2 and w.strip().lower() not in STOP_WORDS]
        
        if not keywords:
            return []
        
        regex_queries = []
        for keyword in keywords[:3]:  # Limit to top 3 keywords
            regex_queries.extend([
                {"text": {"$regex": keyword, "$options": "i"}},
                {"hexagram": {"$regex": keyword, "$options": "i"}},
                {"section": {"$regex": keyword, "$options": "i"}}
            ])
        
        return list(self.collection.find({"$or": regex_queries}).limit(TOP_K_RETRIEVE))
    
    def _section_search(self, query: str) -> List[Dict]:
        """Search by section/content_type"""
        # Try to match common section patterns
        section_patterns = ["THUONG_KINH", "HA_KINH", "DICH_THUYET", "CHU_HY"]
        
        for pattern in section_patterns:
            if pattern.lower() in query.lower():
                return list(self.collection.find(
                    {"section": {"$regex": pattern, "$options": "i"}}
                ).limit(TOP_K_RETRIEVE))
        
        return []
    
    def _random_search(self, query: str) -> List[Dict]:
        """Random sampling as last resort"""
        return list(self.collection.aggregate([
            {"$sample": {"size": TOP_K_RETRIEVE}},
            {"$project": {
                "_id": 1, "text": 1, "hexagram": 1, "section": 1,
                "content_type": 1, "original_chunk": 1
            }}
        ]))
    
    def _emergency_fallback(self, query: str) -> List[Dict]:
        """Emergency fallback - return anything"""
        try:
            return list(self.collection.find({}).limit(5))
        except:
            return []
    
    def _update_performance_stats(self, start_time: float, success: bool):
        """Update performance statistics"""
        elapsed = time.time() - start_time
        
        # Update average time
        current_avg = self.performance_stats["avg_time"]
        search_count = self.performance_stats["searches"]
        
        self.performance_stats["avg_time"] = (
            (current_avg * (search_count - 1) + elapsed) / search_count
        )
        
        # Update success rate
        if success:
            current_success = self.performance_stats.get("successful_searches", 0)
            self.performance_stats["successful_searches"] = current_success + 1
        
        self.performance_stats["success_rate"] = (
            self.performance_stats.get("successful_searches", 0) / search_count * 100
        )
    
    def get_performance_stats(self) -> Dict:
        """Get current performance statistics"""
        return self.performance_stats.copy()

# Global instance with lazy initialization
_retriever_instance = None

def get_retriever():
    """Get optimized retriever instance"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = OptimizedKinhDichRetriever()
    return _retriever_instance

def smart_search(query: str) -> List[Dict]:
    """Optimized smart search interface"""
    retriever = get_retriever()
    return retriever.smart_search(query)
