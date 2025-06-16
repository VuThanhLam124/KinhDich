# chatbot.py - Enhanced với XAI
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import time 

from retriever import smart_search, get_retriever
from reranker import rerank
from prompt_builder import build_enhanced_prompt
from llm import generate_advanced
from mapping import detect_hexagram, get_hexagram_info

logger = logging.getLogger(__name__)

class EnhancedKinhDichChatbot:
    """Enhanced Chatbot với XAI, citation tracking và performance monitoring"""
    
    def __init__(self):
        self.conversation_history = {}
        self.citation_tracker = CitationTracker()
        self.performance_tracker = PerformanceTracker()
    
    def answer_with_xai(self, query: str, user_name: str = None, session_id: str = "default", 
                       confidence_threshold: float = 0.3) -> Dict[str, Any]:
        """Enhanced answer với comprehensive XAI"""
        
        # Start performance tracking
        operation_id = self.performance_tracker.start_operation("answer_with_xai")
        
        try:
            logger.info(f"Processing: '{query}' (user: {user_name}, session: {session_id})")
            
            # Phase 1: Query Analysis & Hexagram Detection
            analysis_start = self.performance_tracker.start_phase("query_analysis")
            detected_hexagram = detect_hexagram(query)
            hexagram_info = get_hexagram_info(detected_hexagram) if detected_hexagram else None
            self.performance_tracker.end_phase(analysis_start)
            
            logger.info(f"Detected hexagram: {detected_hexagram}")
            
            # Phase 2: Document Retrieval
            retrieval_start = self.performance_tracker.start_phase("retrieval")
            docs = smart_search(query)
            self.performance_tracker.end_phase(retrieval_start)
            
            logger.info(f"Retrieved: {len(docs)} documents")
            
            if not docs:
                return self._create_no_docs_response(query, detected_hexagram, operation_id)
            
            # Phase 3: Reranking
            rerank_start = self.performance_tracker.start_phase("reranking")
            reranked_docs = rerank(query, docs) if len(docs) > 1 else docs
            self.performance_tracker.end_phase(rerank_start)
            
            logger.info(f"Reranked to: {len(reranked_docs)} documents")
            
            # Phase 4: Confidence Filtering
            filtered_docs = self._filter_by_confidence(reranked_docs, confidence_threshold)
            logger.info(f"Filtered: {len(filtered_docs)} high-confidence documents")
            
            # Phase 5: Prompt Building với Citation Tracking
            prompt_start = self.performance_tracker.start_phase("prompt_building")
            prompt_result = build_enhanced_prompt(query, filtered_docs, user_name, hexagram_info)
            self.performance_tracker.end_phase(prompt_start)
            
            # Phase 6: LLM Generation
            generation_start = self.performance_tracker.start_phase("generation")
            llm_result = generate_advanced(prompt_result["prompt"], filtered_docs, session_id)
            self.performance_tracker.end_phase(generation_start)
            
            # Phase 7: Response Assembly với XAI
            response = self._assemble_xai_response(
                query, llm_result, filtered_docs, detected_hexagram, 
                hexagram_info, prompt_result, operation_id
            )
            
            # Store conversation
            self._store_enhanced_conversation(session_id, query, response)
            
            self.performance_tracker.end_operation(operation_id, True)
            return response
            
        except Exception as e:
            logger.error(f"Error in answer_with_xai: {e}")
            self.performance_tracker.end_operation(operation_id, False)
            return self._create_error_response(query, str(e), operation_id)
    
    def _filter_by_confidence(self, docs: List[Dict], threshold: float) -> List[Dict]:
        """Filter documents by confidence threshold"""
        filtered = [doc for doc in docs 
                   if doc.get("rerank_score", doc.get("similarity_score", 0)) >= threshold]
        
        # Ensure we have at least some documents
        if not filtered and docs:
            filtered = docs[:min(3, len(docs))]
            logger.warning(f"⚠️ No docs above threshold {threshold}, using top {len(filtered)}")
        
        return filtered
    
    def _assemble_xai_response(self, query: str, llm_result: Dict, docs: List[Dict],
                              detected_hexagram: str, hexagram_info: Dict, 
                              prompt_result: Dict, operation_id: str) -> Dict[str, Any]:
        """Assemble comprehensive XAI response"""
        
        # Extract and verify citations
        citations = self._extract_and_verify_citations(llm_result.get("answer", ""), docs)
        
        # Calculate comprehensive confidence
        confidence_data = self._calculate_enhanced_confidence(docs, llm_result, citations)
        
        # Build reasoning explanation
        reasoning = self._build_comprehensive_reasoning(
            query, docs, detected_hexagram, prompt_result, confidence_data
        )
        
        # Prepare sources with full metadata
        sources = self._prepare_enhanced_sources(docs, citations)
        
        response = {
            "answer": llm_result.get("answer", ""),
            "query": query,
            "detected_hexagram": detected_hexagram,
            "hexagram_info": hexagram_info,
            "confidence": confidence_data,
            "sources": sources,
            "citations": citations,
            "reasoning": reasoning,
            "performance": self.performance_tracker.get_operation_stats(operation_id),
            "timestamp": datetime.now().isoformat(),
            "session_metadata": {
                "operation_id": operation_id,
                "total_processing_time": self.performance_tracker.get_total_time(operation_id)
            }
        }
        
        return response
    
    def _extract_and_verify_citations(self, answer: str, docs: List[Dict]) -> List[Dict]:
        """Extract and verify citations from answer"""
        import re
        
        citation_pattern = r'\[(\d+)\]'
        cited_numbers = re.findall(citation_pattern, answer)
        
        verified_citations = []
        for num_str in cited_numbers:
            try:
                num = int(num_str)
                if 1 <= num <= len(docs):
                    doc = docs[num - 1]
                    citation = {
                        "number": num,
                        "chunk_id": doc.get("_id"),
                        "valid": True,
                        "source_type": doc.get("content_type"),
                        "hexagram": doc.get("hexagram"),
                        "confidence": doc.get("rerank_score", doc.get("similarity_score", 0))
                    }
                else:
                    citation = {
                        "number": num,
                        "valid": False,
                        "error": "Citation number out of range"
                    }
                verified_citations.append(citation)
            except ValueError:
                continue
        
        return verified_citations
    
    def _calculate_enhanced_confidence(self, docs: List[Dict], llm_result: Dict, 
                                     citations: List[Dict]) -> Dict[str, Any]:
        """Calculate comprehensive confidence metrics"""
        
        # Document confidence
        doc_scores = [doc.get("rerank_score", doc.get("similarity_score", 0)) for doc in docs]
        doc_confidence = sum(doc_scores) / len(doc_scores) if doc_scores else 0
        
        # Citation confidence
        valid_citations = len([c for c in citations if c.get("valid", False)])
        total_citations = len(citations)
        citation_confidence = valid_citations / total_citations if total_citations > 0 else 0
        
        # LLM confidence
        llm_confidence = llm_result.get("confidence", 0.5)
        
        # Weighted overall confidence
        overall_confidence = (
            0.4 * doc_confidence +
            0.3 * citation_confidence +
            0.3 * llm_confidence
        )
        
        return {
            "overall": round(overall_confidence, 3),
            "document_relevance": round(doc_confidence, 3),
            "citation_accuracy": round(citation_confidence, 3),
            "llm_confidence": round(llm_confidence, 3),
            "level": self._get_confidence_level(overall_confidence),
            "details": {
                "total_documents": len(docs),
                "avg_doc_score": round(doc_confidence, 3),
                "valid_citations": f"{valid_citations}/{total_citations}",
                "reasoning": self._explain_confidence(overall_confidence)
            }
        }
    
    def _get_confidence_level(self, confidence: float) -> str:
        """Get confidence level description"""
        if confidence >= 0.7:
            return "high"
        elif confidence >= 0.4:
            return "medium"
        else:
            return "low"
    
    def _explain_confidence(self, confidence: float) -> str:
        """Explain confidence level"""
        if confidence >= 0.7:
            return "Độ tin cậy cao - Thông tin được hỗ trợ tốt bởi tài liệu"
        elif confidence >= 0.4:
            return "Độ tin cậy trung bình - Thông tin có sự hỗ trợ nhưng cần thêm xác thực"
        else:
            return "Độ tin cậy thấp - Thông tin có thể không đầy đủ hoặc cần kiểm tra thêm"
    
    def _build_comprehensive_reasoning(self, query: str, docs: List[Dict], 
                                     detected_hexagram: str, prompt_result: Dict,
                                     confidence_data: Dict) -> Dict[str, Any]:
        """Build comprehensive reasoning explanation"""
        
        return {
            "search_strategy": self._explain_search_strategy(query, detected_hexagram),
            "document_selection": {
                "total_retrieved": len(docs),
                "selection_criteria": "Semantic similarity + reranking + confidence filtering",
                "document_types": list(set([doc.get("content_type", "unknown") for doc in docs])),
                "hexagram_coverage": len([doc for doc in docs if doc.get("hexagram")])
            },
            "prompt_strategy": {
                "type": prompt_result.get("query_type", "unknown"),
                "context_length": len(prompt_result.get("context", "")),
                "citation_method": "Numbered references with source tracking"
            },
            "confidence_assessment": confidence_data["details"],
            "quality_indicators": {
                "has_specific_hexagram": detected_hexagram is not None,
                "document_diversity": len(set([doc.get("section", "") for doc in docs])),
                "citation_density": len([c for c in confidence_data.get("citations", []) if c.get("valid")])
            }
        }
    
    def _explain_search_strategy(self, query: str, detected_hexagram: str) -> str:
        """Explain the search strategy used"""
        if detected_hexagram:
            return f"Hybrid search: Hexagram-specific ({detected_hexagram}) + semantic similarity"
        else:
            return "General semantic search with multi-strategy fallback"
    
    def _prepare_enhanced_sources(self, docs: List[Dict], citations: List[Dict]) -> List[Dict]:
        """Prepare enhanced source information"""
        sources = []
        
        for i, doc in enumerate(docs, 1):
            # Check if this source is cited
            is_cited = any(c.get("number") == i and c.get("valid") for c in citations)
            
            source = {
                "id": i,
                "chunk_id": doc.get("_id"),
                "hexagram": doc.get("hexagram"),
                "section": doc.get("section"),
                "content_type": doc.get("content_type"),
                "relevance_score": doc.get("rerank_score", doc.get("similarity_score", 0)),
                "is_cited": is_cited,
                "preview": doc.get("text", "")[:200] + "...",
                "metadata": self._extract_source_metadata(doc)
            }
            sources.append(source)
        
        return sources
    
    def _extract_source_metadata(self, doc: Dict) -> Dict:
        """Extract comprehensive metadata from document"""
        original_chunk = doc.get("original_chunk", {})
        
        return {
            "title": original_chunk.get("title", ""),
            "reference": original_chunk.get("reference", ""),
            "notes": original_chunk.get("notes", {}),
            "chunk_type": doc.get("content_type", ""),
            "source_quality": self._assess_source_quality(doc)
        }
    
    def _assess_source_quality(self, doc: Dict) -> str:
        """Assess quality of source document"""
        score = doc.get("rerank_score", doc.get("similarity_score", 0))
        
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        else:
            return "poor"
    
    def _create_no_docs_response(self, query: str, detected_hexagram: str, operation_id: str) -> Dict:
        """Create response when no documents are found"""
        return {
            "answer": "Xin lỗi, tôi không tìm thấy thông tin phù hợp trong cơ sở tri thức. Vui lòng thử câu hỏi khác hoặc kiểm tra lại cách diễn đạt.",
            "query": query,
            "detected_hexagram": detected_hexagram,
            "confidence": {"overall": 0.1, "level": "low"},
            "sources": [],
            "citations": [],
            "reasoning": {
                "search_strategy": "Comprehensive search with all fallback strategies",
                "issue": "No relevant documents found in knowledge base",
                "suggestions": [
                    "Try rephrasing the question",
                    "Check if the hexagram name is correct",
                    "Ask about available hexagrams"
                ]
            },
            "performance": self.performance_tracker.get_operation_stats(operation_id)
        }
    
    def _create_error_response(self, query: str, error: str, operation_id: str) -> Dict:
        """Create error response with debugging info"""
        return {
            "answer": f"Đã xảy ra lỗi kỹ thuật: {error}. Vui lòng thử lại sau.",
            "query": query,
            "confidence": {"overall": 0.0, "level": "error"},
            "sources": [],
            "error": error,
            "performance": self.performance_tracker.get_operation_stats(operation_id),
            "debug_info": {
                "retriever_stats": get_retriever().get_performance_stats(),
                "timestamp": datetime.now().isoformat()
            }
        }
    
    def _store_enhanced_conversation(self, session_id: str, query: str, response: Dict):
        """Store conversation with enhanced metadata"""
        if session_id not in self.conversation_history:
            self.conversation_history[session_id] = []
        
        conversation_entry = {
            "query": query,
            "response": response["answer"],
            "confidence": response.get("confidence", {}).get("overall", 0),
            "detected_hexagram": response.get("detected_hexagram"),
            "source_count": len(response.get("sources", [])),
            "citation_count": len(response.get("citations", [])),
            "timestamp": response.get("timestamp")
        }
        
        self.conversation_history[session_id].append(conversation_entry)
        
        # Keep only last 20 exchanges for performance
        if len(self.conversation_history[session_id]) > 20:
            self.conversation_history[session_id] = self.conversation_history[session_id][-20:]

class CitationTracker:
    """Enhanced citation tracking"""
    
    def __init__(self):
        self.citations = {}
        self.citation_count = 0
        self.verification_stats = {"total": 0, "verified": 0, "failed": 0}
    
    def verify_citation(self, citation_text: str, source_docs: List[Dict]) -> bool:
        """Verify if citation exists in source documents"""
        self.verification_stats["total"] += 1
        
        # Simple verification - check if citation text appears in any source
        for doc in source_docs:
            if citation_text.lower() in doc.get("text", "").lower():
                self.verification_stats["verified"] += 1
                return True
        
        self.verification_stats["failed"] += 1
        return False
    
    def get_verification_stats(self) -> Dict:
        """Get citation verification statistics"""
        total = self.verification_stats["total"]
        if total == 0:
            return {"accuracy": 0, "total": 0}
        
        accuracy = (self.verification_stats["verified"] / total) * 100
        return {
            "accuracy": round(accuracy, 2),
            "total": total,
            "verified": self.verification_stats["verified"],
            "failed": self.verification_stats["failed"]
        }

class PerformanceTracker:
    """Track performance metrics for optimization"""
    
    def __init__(self):
        self.operations = {}
        self.phases = {}
    
    def start_operation(self, operation_name: str) -> str:
        """Start tracking an operation"""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        self.operations[operation_id] = {
            "name": operation_name,
            "start_time": time.time(),
            "phases": {}
        }
        return operation_id
    
    def start_phase(self, phase_name: str) -> str:
        """Start tracking a phase within operation"""
        phase_id = f"{phase_name}_{int(time.time() * 1000)}"
        self.phases[phase_id] = {
            "name": phase_name,
            "start_time": time.time()
        }
        return phase_id
    
    def end_phase(self, phase_id: str):
        """End phase tracking"""
        if phase_id in self.phases:
            self.phases[phase_id]["duration"] = time.time() - self.phases[phase_id]["start_time"]
    
    def end_operation(self, operation_id: str, success: bool):
        """End operation tracking"""
        if operation_id in self.operations:
            self.operations[operation_id]["duration"] = time.time() - self.operations[operation_id]["start_time"]
            self.operations[operation_id]["success"] = success
    
    def get_operation_stats(self, operation_id: str) -> Dict:
        """Get operation statistics"""
        if operation_id not in self.operations:
            return {}
        
        operation = self.operations[operation_id]
        
        # Get phase timings
        phase_timings = {}
        for phase_id, phase_data in self.phases.items():
            if phase_data.get("duration") is not None:
                phase_timings[phase_data["name"]] = round(phase_data["duration"] * 1000, 2)  # ms
        
        return {
            "total_time_ms": round(operation.get("duration", 0) * 1000, 2),
            "phase_timings_ms": phase_timings,
            "success": operation.get("success", False)
        }
    
    def get_total_time(self, operation_id: str) -> float:
        """Get total operation time"""
        return self.operations.get(operation_id, {}).get("duration", 0)

# Compatibility functions
def answer(query: str, user_name: str = None) -> str:
    """Compatibility function for basic usage"""
    chatbot = EnhancedKinhDichChatbot()
    result = chatbot.answer_with_xai(query, user_name)
    return result["answer"]
