from typing import List, Dict, Optional
import json
from mapping import detect_divination_query

class EnhancedPromptBuilder:
    """Enhanced prompt builder với XAI và citation support"""
    
    def __init__(self):
        self.base_prompt = self._load_base_prompt()
    
    def _load_base_prompt(self) -> str:
        return """Bạn là Thầy Kinh Dịch, một chuyên gia sâu sắc về Kinh Dịch với kiến thức uyên thâm về 64 quẻ.

NGUYÊN TẮC TRẢ LỜI:
1. Dựa vào tài liệu được cung cấp làm cơ sở chính
2. Trích dẫn cụ thể nguồn bằng [số] ngay sau mỗi thông tin
3. Giải thích rõ ràng ý nghĩa và ứng dụng thực tế
4. Sử dụng ngôn ngữ trang trọng nhưng dễ hiểu
5. Đưa ra lời khuyên cụ thể và khả thi

QUY TẮC TRÍCH DẪN:
- Mỗi thông tin PHẢI có [số] tương ứng với nguồn
- Không được tạo ra thông tin không có trong tài liệu
- Nếu không chắc chắn, hãy nói rõ điều đó"""
    
    def build_enhanced_prompt(self, query: str, docs: List[Dict], user_name: str = None, 
                            hexagram_info: Dict = None) -> Dict[str, str]:
        """Build enhanced prompt với citation context"""
        
        query_type = self._detect_query_type(query)
        
        # Build context với numbered citations
        context = self._build_numbered_context(docs)
        
        # Build citation reference
        citations_ref = self._build_citations_reference(docs)
        
        # Build reasoning context
        reasoning_context = self._build_reasoning_context(query, docs, hexagram_info)
        
        if query_type == "divination":
            prompt = self._build_divination_prompt(query, context, citations_ref, user_name, hexagram_info)
        else:
            prompt = self._build_knowledge_prompt(query, context, citations_ref, user_name)
        
        return {
            "prompt": prompt,
            "context": context,
            "citations_reference": citations_ref,
            "reasoning_context": reasoning_context,
            "query_type": query_type
        }
    
    def _build_numbered_context(self, docs: List[Dict]) -> str:
        """Build context với numbered citations"""
        context_parts = []
        
        for i, doc in enumerate(docs, 1):
            text = doc.get("text", "")
            hexagram = doc.get("hexagram", "")
            content_type = doc.get("content_type", "")
            
            # Format context entry với số thứ tự
            context_entry = f"[{i}] "
            if hexagram:
                context_entry += f"Quẻ {hexagram} - "
            if content_type:
                context_entry += f"({content_type}) "
            
            context_entry += text[:400]  # Limit length
            if len(text) > 400:
                context_entry += "..."
            
            context_parts.append(context_entry)
        
        return "\n\n".join(context_parts)
    
    def _build_citations_reference(self, docs: List[Dict]) -> str:
        """Build detailed citations reference"""
        citations = []
        
        for i, doc in enumerate(docs, 1):
            original_chunk = doc.get("original_chunk", {})
            
            citation = f"[{i}] {doc.get('_id', 'N/A')}"
            
            if original_chunk.get("title"):
                citation += f" - {original_chunk['title']}"
            
            if original_chunk.get("reference"):
                citation += f" ({original_chunk['reference']})"
            
            # Add notes if available
            notes = original_chunk.get("notes", {})
            if notes:
                notes_text = "; ".join([f"[{k}] {v}" for k, v in notes.items()])
                citation += f" | Chú thích: {notes_text}"
            
            citations.append(citation)
        
        return "\n".join(citations)
    
    def _build_reasoning_context(self, query: str, docs: List[Dict], hexagram_info: Dict = None) -> str:
        """Build reasoning context for XAI"""
        parts = [
            f"Câu hỏi: {query}",
            f"Số tài liệu liên quan: {len(docs)}"
        ]
        
        if hexagram_info:
            parts.append(f"Quẻ được phát hiện: {hexagram_info}")
        
        doc_types = list(set([doc.get("content_type", "unknown") for doc in docs]))
        parts.append(f"Loại tài liệu: {', '.join(doc_types)}")
        
        return " | ".join(parts)
    
    def _build_divination_prompt(self, query: str, context: str, citations: str, 
                               user_name: str = None, hexagram_info: Dict = None) -> str:
        """Build prompt for divination queries"""
        
        greeting = f"Kính chào {user_name}! " if user_name else "Kính chào! "
        
        hexagram_context = ""
        if hexagram_info:
            hexagram_context = f"""
THÔNG TIN QUẺ:
- Quẻ: {hexagram_info.get('name', 'N/A')}
- Mã: {hexagram_info.get('code', 'N/A')}
- Cấu trúc: {hexagram_info.get('structure', 'N/A')}
"""
        
        return f"""{self.base_prompt}

{greeting}

CÂU HỎI GIEO QUẺ: "{query}"

{hexagram_context}

TÀI LIỆU THAM KHẢO:
{context}

NGUỒN CHI TIẾT:
{citations}

YÊU CẦU ĐẶC BIỆT:
- Phân tích ý nghĩa quẻ trong bối cảnh câu hỏi
- Trích dẫn cụ thể [số] cho mọi thông tin
- Đưa ra lời khuyên thực tế và khả thi
- Giải thích tại sao quẻ này phù hợp

TRẢ LỜI (tối đa 750 từ):"""
    
    def _build_knowledge_prompt(self, query: str, context: str, citations: str, 
                              user_name: str = None) -> str:
        """Build prompt for knowledge queries"""
        
        greeting = f"Kính chào {user_name}! " if user_name else "Kính chào! "
        
        return f"""{self.base_prompt}

{greeting}

CÂU HỎI TRI THỨC: "{query}"

TÀI LIỆU THAM KHẢO:
{context}

NGUỒN CHI TIẾT:
{citations}

YÊU CẦU ĐẶC BIỆT:
- Giải thích ý nghĩa sâu sắc và rõ ràng
- Trích dẫn chính xác [số] cho mọi thông tin
- Đưa ra ví dụ minh họa cụ thể
- Liên hệ với đời sống hiện đại

TRẢ LỜI (tối đa 700 từ):"""
    
    def _detect_query_type(self, query: str) -> str:
        """Detect query type"""
        return "divination" if detect_divination_query(query) else "knowledge"

# Main interface function
def build_enhanced_prompt(query: str, docs: List[Dict], user_name: str = None, 
                         hexagram_info: Dict = None) -> Dict[str, str]:
    """Main interface for enhanced prompt building"""
    builder = EnhancedPromptBuilder()
    return builder.build_enhanced_prompt(query, docs, user_name, hexagram_info)

# Compatibility function
def build_prompt(query: str, docs: List[Dict], name: str = None) -> str:
    """Compatibility function"""
    result = build_enhanced_prompt(query, docs, name)
    return result["prompt"]
