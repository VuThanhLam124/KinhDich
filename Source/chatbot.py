import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from retriever import smart_search
from reranker import rerank
from prompt_builder import build_enhanced_prompt
from llm import generate_advanced
from mapping import detect_hexagram

logger = logging.getLogger(__name__)

class KinhDichChatbot:
    """Enhanced Chatbot với XAI capabilities"""
    
    def __init__(self):
        self.conversation_history = {}
        self.citation_tracker = CitationTracker()
    
    def answer(self, query: str, user_name: str = None, session_id: str = "default") -> Dict:
        """Basic answer method for compatibility"""
        result = self.answer_with_xai(query, user_name, session_id)
        return {
            "answer": result["answer"],
            "detected_hexagram": result.get("detected_hexagram"),
            "confidence": result.get("confidence", 0.7)
        }
    
    def answer_with_xai(self, query: str, user_name: str = None, session_id: str = "default", 
                       confidence_threshold: float = 0.3) -> Dict[str, Any]:
        """Enhanced answer với XAI features"""
        
        logger.info(f"Processing query: '{query}' (session: {session_id})")
        
        try:
            # 1. Detect hexagram and query type
            detected_hexagram = detect_hexagram(query)
            logger.info(f"Detected hexagram: {detected_hexagram}")
            
            # 2. Retrieve documents
            docs = smart_search(query)
            logger.info(f"Retrieved {len(docs)} documents")
            
            if not docs:
                logger.warning("No documents retrieved!")
                return self._fallback_response(query, detected_hexagram)
            
            # 3. Rerank for better relevance
            reranked_docs = rerank(query, docs)
            logger.info(f"Reranked to {len(reranked_docs)} documents")
            
            # 4. Filter by confidence threshold
            filtered_docs = [doc for doc in reranked_docs 
                           if doc.get("rerank_score", 0) >= confidence_threshold]
            
            if not filtered_docs:
                logger.warning(f"No docs above confidence threshold {confidence_threshold}")
                filtered_docs = reranked_docs[:3]  # Take top 3 anyway
            
            # 5. Build enhanced prompt with citation tracking
            prompt_result = build_enhanced_prompt(query, filtered_docs, user_name, detected_hexagram)
            
            # 6. Generate response with advanced LLM
            llm_result = generate_advanced(prompt_result["prompt"], filtered_docs, session_id)
            
            # 7. Build comprehensive result
            result = {
                "answer": llm_result["answer"],
                "query": query,
                "detected_hexagram": detected_hexagram,
                "confidence": llm_result.get("confidence", 0.7),
                "sources": self._extract_enhanced_sources(filtered_docs),
                "reasoning": {
                    "search_strategy": "hybrid_semantic" if detected_hexagram else "semantic",
                    "retrieved_docs": len(docs),
                    "reranked_docs": len(reranked_docs),
                    "filtered_docs": len(filtered_docs),
                    "confidence_threshold": confidence_threshold,
                    "reasoning_path": prompt_result.get("reasoning_context", ""),
                    "confidence": llm_result.get("confidence", 0.7)
                },
                "citations": llm_result.get("citations", []),
                "timestamp": datetime.now().isoformat()
            }
            
            # 8. Store conversation history
            self._store_conversation(session_id, query, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in answer_with_xai: {e}")
            return self._error_response(query, str(e))
    
    def _extract_enhanced_sources(self, docs: List[Dict]) -> List[Dict]:
        """Extract detailed source information for XAI"""
        sources = []
        for i, doc in enumerate(docs, 1):
            source = {
                "id": i,
                "chunk_id": doc.get("_id"),
                "hexagram": doc.get("hexagram"),
                "content_type": doc.get("content_type"),
                "score": doc.get("rerank_score", doc.get("similarity_score", 0)),
                "preview": doc.get("text", "")[:200] + "...",
                "notes": doc.get("original_chunk", {}).get("notes", {}),
                "reference": doc.get("original_chunk", {}).get("reference", ""),
                "title": doc.get("original_chunk", {}).get("title", "")
            }
            sources.append(source)
        return sources
    
    def _fallback_response(self, query: str, hexagram: str = None) -> Dict:
        """Fallback response when no documents found"""
        return {
            "answer": "Xin lỗi, tôi không tìm thấy thông tin phù hợp trong cơ sở tri thức. Vui lòng thử câu hỏi khác hoặc kiểm tra lại cách diễn đạt.",
            "query": query,
            "detected_hexagram": hexagram,
            "confidence": 0.1,
            "sources": [],
            "reasoning": {
                "search_strategy": "fallback",
                "retrieved_docs": 0,
                "reasoning_path": "Không tìm thấy tài liệu liên quan"
            }
        }
    
    def _error_response(self, query: str, error: str) -> Dict:
        """Error response with debugging info"""
        return {
            "answer": f"Đã xảy ra lỗi kỹ thuật: {error}. Vui lòng thử lại sau.",
            "query": query,
            "confidence": 0.0,
            "sources": [],
            "error": error
        }
    
    def _store_conversation(self, session_id: str, query: str, result: Dict):
        """Store conversation for context"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        self.conversation_history[session_id].append({
            "query": query,
            "response": result["answer"],
            "confidence": result.get("confidence", 0),
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 10 exchanges
        if len(self.conversation_history[session_id]) > 10:
            self.conversation_history[session_id] = self.conversation_history[session_id][-10:]

class CitationTracker:
    """Track citations for XAI"""
    
    def __init__(self):
        self.citations = {}
        self.citation_count = 0
    
    def add_citation(self, chunk_id: str, content_excerpt: str, source_type: str) -> str:
        """Add citation and return citation key"""
        self.citation_count += 1
        citation_key = f"[{self.citation_count}]"
        
        self.citations[citation_key] = {
            "chunk_id": chunk_id,
            "content_excerpt": content_excerpt[:200] + "...",
            "source_type": source_type,
            "full_reference": self._build_full_reference(chunk_id)
        }
        
        return citation_key
    
    def _build_full_reference(self, chunk_id: str) -> str:
        """Build full reference from chunk ID"""
        if "QUE_" in chunk_id:
            return f"Kinh Dịch - {chunk_id}"
        elif "DICH_THUYET" in chunk_id:
            return f"Dịch Thuyết Cương Lĩnh - {chunk_id}"
        else:
            return f"Tài liệu: {chunk_id}"

# Compatibility function
def answer(query: str, user_name: str = None) -> str:
    chatbot = KinhDichChatbot()
    result = chatbot.answer(query, user_name)
    return result["answer"]
