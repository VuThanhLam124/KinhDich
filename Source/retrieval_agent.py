# retrieval_agent.py - Hybrid retrieval với multiple strategies
import asyncio
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from underthesea import word_tokenize
from pymongo import MongoClient
import numpy as np

from base_agent import BaseAgent, AgentType, ProcessingState
from config import *
from mapping import detect_hexagram

class RetrievalAgent(BaseAgent):
    """Hybrid retrieval agent với semantic + hexagram + fallback"""
    
    def __init__(self):
        super().__init__("RetrievalAgent", AgentType.RETRIEVAL)
        
        # Initialize components
        self.client = MongoClient(MONGO_URI)
        self.collection = self.client[DB_NAME][COLLECTION]
        self.embedder = SentenceTransformer(EMBED_MODEL, cache_folder=CACHE_DIR)
        
        # Retrieval strategies
        self.strategies = [
            ("semantic_search", self._semantic_search),
            ("hexagram_search", self._hexagram_search),
            ("text_search", self._text_search),
            ("fallback_search", self._fallback_search)
        ]
    
    async def process(self, state: ProcessingState) -> ProcessingState:
        """Execute hybrid retrieval strategy"""
        
        query = state.expanded_query or state.query
        query_type = state.query_type
        
        # Choose strategy based on query type và entities
        if query_type == "hexagram_specific" or state.entities.get("hexagrams"):
            # Try hexagram-specific first
            docs = await self._hexagram_search(query, state)
            if docs:
                state.retrieved_docs = docs
                state.reasoning_chain.append("Hexagram-specific search successful")
                return state
        
        # Execute strategies in order until we get results
        for strategy_name, strategy_func in self.strategies:
            try:
                docs = await strategy_func(query, state)
                if docs:
                    state.retrieved_docs = docs
                    state.reasoning_chain.append(f"Retrieved {len(docs)} docs via {strategy_name}")
                    return state
            except Exception as e:
                logger.warning(f"Strategy {strategy_name} failed: {e}")
                continue
        
        # If all strategies fail
        state.retrieved_docs = []
        state.reasoning_chain.append("All retrieval strategies failed")
        return state
    
    async def _semantic_search(self, query: str, state: ProcessingState) -> List[Dict]:
        """Vector-based semantic search"""
        
        try:
            # Tokenize và encode
            tokenized_query = word_tokenize(query, format="text")
            query_embedding = self.embedder.encode(tokenized_query).tolist()
            
            # Vector search pipeline
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
                }
            ]
            
            results = list(self.collection.aggregate(pipeline))
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    async def _hexagram_search(self, query: str, state: ProcessingState) -> List[Dict]:
        """Hexagram-specific search"""
        
        # Try to detect hexagram from query hoặc entities
        hexagram_code = detect_hexagram(query)
        
        if not hexagram_code and state.entities.get("hexagrams"):
            # Extract hexagram name từ entities
            hexagram_names = state.entities["hexagrams"]
            for name in hexagram_names:
                hexagram_code = detect_hexagram(name)
                if hexagram_code:
                    break
        
        if not hexagram_code:
            return []
        
        # Search by hexagram
        try:
            docs = list(self.collection.find(
                {"hexagram": hexagram_code}
            ).limit(TOP_K_RETRIEVE))
            
            return docs
            
        except Exception as e:
            logger.error(f"Hexagram search failed: {e}")
            return []
    
    async def _text_search(self, query: str, state: ProcessingState) -> List[Dict]:
        """Text index search fallback"""
        
        try:
            # Ensure text index exists
            try:
                self.collection.create_index([("text", "text")])
            except:
                pass
            
            docs = list(self.collection.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(TOP_K_RETRIEVE))
            
            return docs
            
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            return []
    
    async def _fallback_search(self, query: str, state: ProcessingState) -> List[Dict]:
        """Last resort random sampling"""
        
        try:
            docs = list(self.collection.aggregate([
                {"$sample": {"size": min(TOP_K_RETRIEVE, 5)}}
            ]))
            
            return docs
            
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []
