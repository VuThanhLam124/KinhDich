import re
import logging
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
import numpy as np

from base_agent import BaseAgent, AgentType, ProcessingState
from llm import generate_advanced
from config import *

logger = logging.getLogger(__name__)

class ReasoningAgent(BaseAgent):
    """Tích hợp reranking và response generation"""
    
    def __init__(self):
        super().__init__("ReasoningAgent", AgentType.REASONING)
        
        # Initialize models
        try:
            self.cross_encoder = CrossEncoder(CE_MODEL, cache_folder=CACHE_DIR)
        except:
            self.cross_encoder = None
            logger.warning("Cross-encoder not available, skipping reranking")
    
    async def process(self, state: ProcessingState) -> ProcessingState:
        """Execute reranking + response generation"""
        
        if not state.retrieved_docs:
            state.final_response = "Xin lỗi, tôi không tìm thấy thông tin phù hợp."
            state.confidence = 0.1
            return state
        
        # Step 1: Reranking
        reranked_docs = await self._rerank_documents(state.query, state.retrieved_docs)
        state.reranked_docs = reranked_docs
        
        # Step 2: Build response với citations
        response_data = await self._generate_response(state)
        state.final_response = response_data["answer"]
        state.confidence = response_data["confidence"]
        
        state.reasoning_chain.extend([
            f"Reranked {len(state.retrieved_docs)} -> {len(reranked_docs)} documents",
            f"Generated response with confidence: {state.confidence:.2%}"
        ])
        
        return state
    
    async def _rerank_documents(self, query: str, docs: List[Dict]) -> List[Dict]:
        """Rerank documents using cross-encoder"""
        
        if not self.cross_encoder or len(docs) <= 1:
            return docs[:TOP_K_RERANK]
        
        try:
            # Prepare query-document pairs
            pairs = []
            for doc in docs:
                doc_text = doc.get("text", "")[:512]  # Truncate for efficiency
                pairs.append([query, doc_text])
            
            # Get cross-encoder scores
            cross_scores = self.cross_encoder.predict(pairs)
            
            # Combine với vector similarity scores
            final_scores = []
            for i, doc in enumerate(docs):
                vector_score = doc.get("similarity_score", 0.0)
                cross_score = cross_scores[i]
                
                # Weighted combination
                combined_score = 0.7 * cross_score + 0.3 * vector_score
                final_scores.append(combined_score)
                
                # Add score to document
                doc["rerank_score"] = combined_score
            
            # Sort by combined score
            sorted_indices = np.argsort(final_scores)[::-1]
            reranked_docs = [docs[i] for i in sorted_indices[:TOP_K_RERANK]]
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return docs[:TOP_K_RERANK]
    
    async def _generate_response(self, state: ProcessingState) -> Dict[str, Any]:
        """Generate response with citations và XAI"""
        
        # Build enhanced prompt
        prompt = self._build_enhanced_prompt(state)
        
        # Generate using LLM
        try:
            llm_result = generate_advanced(prompt, state.reranked_docs)
            
            # Process citations
            processed_answer = self._process_citations(
                llm_result["answer"], 
                state.reranked_docs
            )
            
            # Calculate confidence
            confidence = self._calculate_confidence(state.reranked_docs, llm_result)
            
            return {
                "answer": processed_answer,
                "confidence": confidence,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {
                "answer": "Xin lỗi, đã có lỗi xảy ra trong quá trình tạo phản hồi.",
                "confidence": 0.1,
                "success": False
            }
    
    def _build_enhanced_prompt(self, state: ProcessingState) -> str:
        """Build prompt với hexagram context + specialized templates"""
        
        # Build context từ documents (giữ từ phiên bản mới)
        context_parts = []
        for i, doc in enumerate(state.reranked_docs[:8], 1):
            text = doc.get("text", "")
            if len(text) > 400:
                text = text[:400] + "..."
            
            hexagram = doc.get("hexagram", "")
            content_type = doc.get("content_type", "")
            
            context_entry = f"[{i}] "
            if hexagram:
                context_entry += f"Quẻ {hexagram} - "
            if content_type:
                context_entry += f"({content_type}) "
            context_entry += text
            
            context_parts.append(context_entry)
        
        context = "\n\n".join(context_parts)
        
        # Build hexagram context (giữ từ phiên bản mới)
        hexagram_context = ""
        if state.hexagram_info and state.hexagram_info.get("name"):
            info = state.hexagram_info
            hexagram_context = f"""THÔNG TIN QUẺ ĐÃ GIEO:
- Tên quẻ: {info.get('name', 'N/A')}
- Ý nghĩa chung: {info.get('general_meaning', 'N/A')}
- Hào động (nếu có): {info.get('changing_lines', 'Không có')}
"""

        # HYBRID: Specialized templates theo query type (từ phiên bản cũ) + hexagram context (từ phiên bản mới)
        return self._get_specialized_prompt(state.query_type, hexagram_context, state.query, context)
    
    def _get_specialized_prompt(self, query_type: str, hexagram_context: str, query: str, context: str) -> str:
        """Get specialized prompt template based on query type"""
        
        if query_type == "divination":
            return f"""Bạn là chuyên gia Kinh Dịch có kinh nghiệm sâu rộng, chuyên về giải quẻ và tư vấn định hướng.

{hexagram_context}

⚠️  QUAN TRỌNG: Bạn PHẢI phân tích quẻ đã gieo ở trên, KHÔNG được nhầm lẫn với các quẻ khác trong tài liệu tham khảo.

CÂU HỎI GIEO QUẺ: "{query}"

TÀI LIỆU THAM KHẢO (chỉ để hỗ trợ):
{context}

YÊU CẦU NGHIÊM NGẶT:
1. **FOCUS CHÍNH vào quẻ đã gieo**: Phân tích chính xác quẻ đã được gieo (xem phần "THÔNG TIN QUẺ ĐÃ GIEO")
2. **KHÔNG nhầm lẫn quẻ**: Nếu tài liệu tham khảo đề cập đến quẻ khác, chỉ dùng để hỗ trợ thông tin, KHÔNG phân tích thay thế
3. **Phân tích quẻ và tình huống**: Kết hợp ý nghĩa quẻ đã gieo với bối cảnh câu hỏi cụ thể
4. **Lời khuyên thực tế**: Đưa ra định hướng rõ ràng, hành động cụ thể dựa trên quẻ đã gieo
5. **Giải thích ý nghĩa sâu sắc**: Phân tích tầng lớp ẩn ý của quẻ đã gieo
6. **Trích dẫn nguồn**: Sử dụng [số] để tham chiếu tài liệu (nếu phù hợp)
7. **Giọng văn**: Trang trọng, thấu hiểu và đồng cảm

🎯 LƯU Ý: Nếu tài liệu tham khảo nói về quẻ khác, hãy nói rõ "Tài liệu đề cập đến quẻ [tên], nhưng quẻ bạn đã gieo là [tên quẻ đã gieo]"

TRẢ LỜI:"""
        
        elif query_type == "philosophy":
            context_section = f"\n\nTÀI LIỆU THAM KHẢO:\n{context}" if context.strip() else ""
            hexagram_section = f"\n{hexagram_context}" if hexagram_context.strip() else ""
            
            return f"""Bạn là học giả Kinh Dịch uyên thâm, am hiểu sâu sắc về triết lý Đông phương.{hexagram_section}

CÂU HỎI TRIẾT HỌC: "{query}"{context_section}

YÊU CẦU:
1. **Giải thích triết lý sâu sắc**: Phân tích bản chất và nguồn gốc tư tưởng
2. **Kết nối tư tưởng Đông phương**: Liên hệ với các trường phái khác
3. **Ví dụ minh họa**: Đưa ra các ví dụ cụ thể, dễ hiểu
4. **Trích dẫn nguồn**: Sử dụng [số] để tham chiếu tài liệu
5. **Giọng văn**: Học thuật, khách quan và sâu sắc

TRẢ LỜI:"""
        
        else:  # General or hexagram-specific
            context_section = f"\n\nTÀI LIỆU THAM KHẢO:\n{context}" if context.strip() else ""
            hexagram_section = f"\n{hexagram_context}" if hexagram_context.strip() else ""
            
            return f"""Bạn là chuyên gia Kinh Dịch với kiến thức toàn diện về hệ thống 64 quẻ.{hexagram_section}

CÂU HỎI: "{query}"{context_section}

YÊU CẦU:
1. **Trả lời chính xác**: Dựa trên tài liệu và kiến thức Kinh Dịch
2. **Giải thích rõ ràng**: Dễ hiểu, có cấu trúc logic
3. **Thông tin hữu ích**: Cung cấp insight có giá trị thực tế
4. **Trích dẫn nguồn**: Sử dụng [số] để tham chiếu tài liệu
5. **Giọng văn**: Thân thiện, chuyên nghiệp và dễ tiếp cận

TRẢ LỜI:"""
    
    def _process_citations(self, answer: str, docs: List[Dict]) -> str:
        """Process citations - thay thế [n] bằng nội dung notes"""
        
        def replace_citation(match):
            try:
                cite_num = int(match.group(1))
                if 1 <= cite_num <= len(docs):
                    doc = docs[cite_num - 1]
                    notes = doc.get("original_chunk", {}).get("notes", {})
                    
                    # If có notes cho citation number này
                    if str(cite_num) in notes:
                        return f" ({notes[str(cite_num)]}) "
                    
                    # Fallback: return original citation
                    return match.group(0)
                else:
                    return match.group(0)
            except:
                return match.group(0)
        
        # Replace [n] với nội dung notes
        processed_answer = re.sub(r'\[(\d+)\]', replace_citation, answer)
        
        return processed_answer
    
    def _calculate_confidence(self, docs: List[Dict], llm_result: Dict) -> float:
        """Calculate overall confidence score"""
        
        if not docs:
            return 0.1
        
        # Document relevance confidence
        doc_scores = [doc.get("rerank_score", doc.get("similarity_score", 0)) for doc in docs]
        doc_confidence = sum(doc_scores) / len(doc_scores) if doc_scores else 0
        
        # LLM confidence
        llm_confidence = llm_result.get("confidence", 0.5)
        
        # Combined confidence
        overall_confidence = (doc_confidence + llm_confidence) / 2
        
        return min(max(overall_confidence, 0.0), 1.0)