# llm.py
"""
Module LLM cho hệ thống Chatbot Kinh Dịch - Tích hợp với Gemini API
"""
import os
import time
import logging
from typing import Dict, List, Optional, Any
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from config import GEMINI_API_KEY, GEMINI_MODEL

# ──────────────────────────────────────────────────────────────
# Logging Setup
# ──────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# Gemini Configuration
# ──────────────────────────────────────────────────────────────

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Generation configuration for optimal Kinh Dịch responses
GENERATION_CONFIG = {
    "temperature": 0.7,          # Balanced creativity và consistency
    "top_p": 0.8,               # Focused on high probability tokens
    "top_k": 40,                # Moderate diversity
    "max_output_tokens": 1000,  # Đủ dài cho lời giải thích chi tiết
    "response_mime_type": "text/plain"
}

# Safety settings cho nội dung văn hóa/tôn giáo
SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}

# ──────────────────────────────────────────────────────────────
# LLM Interface Classes
# ──────────────────────────────────────────────────────────────

class KinhDichLLM:
    """LLM interface cho Kinh Dịch chatbot với advanced features"""
    
    def __init__(self):
        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config=GENERATION_CONFIG,
            safety_settings=SAFETY_SETTINGS
        )
        self.conversation_history = {}
        
        # Test connection
        self._test_connection()
    
    def _test_connection(self):
        """Test Gemini API connection"""
        try:
            response = self.model.generate_content("Test connection")
            logger.info("Gemini API connection successful")
        except Exception as e:
            logger.error(f"Gemini API connection failed: {e}")
            raise
    
    def generate(self, prompt: str, session_id: str = "default", 
                 use_history: bool = False) -> str:
        """
        Generate response với optional conversation history
        
        Args:
            prompt: Input prompt đã được build
            session_id: ID phiên chat để track history
            use_history: Có sử dụng conversation history không
            
        Returns:
            Generated response text
        """
        try:
            # Prepare input với history nếu cần
            if use_history and session_id in self.conversation_history:
                # Lấy 3 tin nhắn gần nhất để context
                recent_history = self.conversation_history[session_id][-3:]
                history_context = self._build_history_context(recent_history)
                full_prompt = f"{history_context}\n\n{prompt}"
            else:
                full_prompt = prompt
            
            # Generate response
            response = self.model.generate_content(full_prompt)
            
            # Extract text từ response
            if response.text:
                generated_text = response.text.strip()
                
                # Store in history
                if session_id not in self.conversation_history:
                    self.conversation_history[session_id] = []
                
                self.conversation_history[session_id].append({
                    "prompt": prompt,
                    "response": generated_text,
                    "timestamp": time.time()
                })
                
                # Limit history size
                if len(self.conversation_history[session_id]) > 10:
                    self.conversation_history[session_id] = self.conversation_history[session_id][-10:]
                
                return generated_text
            else:
                logger.warning("Empty response from Gemini")
                return "Xin lỗi, tôi không thể tạo ra câu trả lời phù hợp lúc này."
                
        except Exception as e:
            logger.error(f"Error in LLM generation: {e}")
            return self._get_fallback_response(prompt)
    
    def _build_history_context(self, history: List[Dict]) -> str:
        """Build context từ conversation history"""
        context_parts = ["NGỮ CẢNH CUỘC TRÌNH CHUYỆN TRƯỚC:"]
        
        for item in history:
            # Chỉ lấy phần ngắn gọn để không vượt quá context limit
            prompt_preview = item["prompt"][:100] + "..." if len(item["prompt"]) > 100 else item["prompt"]
            response_preview = item["response"][:150] + "..." if len(item["response"]) > 150 else item["response"]
            
            context_parts.append(f"Hỏi: {prompt_preview}")
            context_parts.append(f"Đáp: {response_preview}")
        
        context_parts.append("---")
        return "\n".join(context_parts)
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Fallback response khi LLM fail"""
        if "quẻ" in prompt.lower() or "hexagram" in prompt.lower():
            return """Xin lỗi, tôi đang gặp khó khăn kỹ thuật. 
            
Tuy nhiên, tôi khuyên bạn nên:
1. Suy ngẫm về tình huống hiện tại
2. Tìm hiểu ý nghĩa quẻ trong bối cảnh cụ thể
3. Áp dụng triết lý cân bằng âm dương

Vui lòng thử lại sau."""
        else:
            return "Xin lỗi, tôi đang gặp sự cố kỹ thuật. Vui lòng thử lại sau."

# ──────────────────────────────────────────────────────────────
# Advanced LLM Features
# ──────────────────────────────────────────────────────────────

class KinhDichLLMAdvanced(KinhDichLLM):
    """Advanced LLM với features mở rộng cho Kinh Dịch"""
    
    def __init__(self):
        super().__init__()
        self.response_cache = {}  # Simple caching
        
    def generate_with_analysis(self, prompt: str, retrieved_docs: List[Dict],
                              session_id: str = "default") -> Dict[str, Any]:
        """
        Generate response với detailed analysis
        
        Returns:
            Dict với answer, confidence, reasoning, citations
        """
        try:
            # Generate main response
            response = self.generate(prompt, session_id)
            
            # Analyze response quality
            analysis = self._analyze_response_quality(response, retrieved_docs)
            
            # Extract citations
            citations = self._extract_citations(response, retrieved_docs)
            
            return {
                "answer": response,
                "confidence": analysis["confidence"],
                "reasoning": analysis["reasoning"],
                "citations": citations,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error in advanced generation: {e}")
            return {
                "answer": self._get_fallback_response(prompt),
                "confidence": 0.1,
                "reasoning": "Fallback response due to technical error",
                "citations": [],
                "error": str(e)
            }
    
    def _analyze_response_quality(self, response: str, docs: List[Dict]) -> Dict:
        """Phân tích chất lượng response"""
        confidence = 0.5  # Base confidence
        reasoning_points = []
        
        # Check response length
        if len(response) > 100:
            confidence += 0.1
            reasoning_points.append("Response có độ dài phù hợp")
        
        # Check if mentions specific hexagrams
        if any(doc.get("hexagram") and doc["hexagram"] in response 
               for doc in docs):
            confidence += 0.2
            reasoning_points.append("Reference đến quẻ cụ thể")
        
        # Check for Vietnamese cultural context
        cultural_keywords = ["âm dương", "thiên địa", "ngũ hành", "quẻ", "triết lý"]
        if any(keyword in response.lower() for keyword in cultural_keywords):
            confidence += 0.1
            reasoning_points.append("Có bối cảnh văn hóa phù hợp")
        
        # Check citation pattern
        citation_pattern = r'\[\d+\]'
        import re
        if re.search(citation_pattern, response):
            confidence += 0.1
            reasoning_points.append("Có trích dẫn nguồn")
        
        return {
            "confidence": min(confidence, 1.0),
            "reasoning": " | ".join(reasoning_points)
        }
    
    def _extract_citations(self, response: str, docs: List[Dict]) -> List[Dict]:
        """Extract citations từ response"""
        citations = []
        import re
        
        # Tìm pattern [số]
        citation_matches = re.findall(r'\[(\d+)\]', response)
        
        for match in citation_matches:
            try:
                doc_index = int(match) - 1  # Convert to 0-based index
                if 0 <= doc_index < len(docs):
                    doc = docs[doc_index]
                    citations.append({
                        "index": int(match),
                        "chunk_id": doc.get("_id"),
                        "hexagram": doc.get("hexagram"),
                        "content_preview": doc.get("text", "")[:200] + "...",
                        "source_type": doc.get("content_type")
                    })
            except (ValueError, IndexError):
                continue
        
        return citations

# ──────────────────────────────────────────────────────────────
# Main Interface Functions
# ──────────────────────────────────────────────────────────────

# Global LLM instance
_llm_instance = None

def get_llm() -> KinhDichLLM:
    """Get singleton LLM instance"""
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = KinhDichLLMAdvanced()
    return _llm_instance

def generate(prompt: str, session_id: str = "default", 
             use_history: bool = False) -> str:
    """
    Main interface function for LLM generation
    Compatible với existing chatbot code
    
    Args:
        prompt: Input prompt
        session_id: Session identifier
        use_history: Whether to use conversation history
        
    Returns:
        Generated response text
    """
    llm = get_llm()
    return llm.generate(prompt, session_id, use_history)

def generate_advanced(prompt: str, retrieved_docs: List[Dict],
                     session_id: str = "default") -> Dict[str, Any]:
    """
    Advanced generation với analysis
    
    Args:
        prompt: Input prompt
        retrieved_docs: Documents từ retrieval
        session_id: Session identifier
        
    Returns:
        Dict với detailed response analysis
    """
    llm = get_llm()
    if isinstance(llm, KinhDichLLMAdvanced):
        return llm.generate_with_analysis(prompt, retrieved_docs, session_id)
    else:
        # Fallback to simple generation
        response = llm.generate(prompt, session_id)
        return {
            "answer": response,
            "confidence": 0.7,
            "reasoning": "Basic generation",
            "citations": []
        }

# ──────────────────────────────────────────────────────────────
# Testing và Debugging
# ──────────────────────────────────────────────────────────────

def test_llm():
    """Test LLM functionality"""
    print("Testing Kinh Dịch LLM...")
    
    test_prompts = [
        "Quẻ Cách có ý nghĩa gì?",
        "Hãy giải thích triết lý âm dương trong Kinh Dịch",
        "Tôi nên làm gì khi gặp khó khăn?"
    ]
    
    llm = get_llm()
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nTest {i}: {prompt}")
        try:
            response = generate(prompt, f"test_session_{i}")
            print(f"Response: {response[:100]}...")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nLLM testing completed!")

if __name__ == "__main__":
    test_llm()
