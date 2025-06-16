# dispatcher_agent.py - Query classification và workflow routing
import re
from typing import Dict, List
from sentence_transformers import SentenceTransformer
import numpy as np

from base_agent import BaseAgent, AgentType, ProcessingState

class DispatcherAgent(BaseAgent):
    """Agent phân loại query và điều phối workflow"""
    
    def __init__(self):
        super().__init__("DispatcherAgent", AgentType.DISPATCHER)
        self.classifier_model = SentenceTransformer('keepitreal/vietnamese-sbert')
        
        # Query type templates cho classification
        self.query_templates = {
            "divination": [
                "tôi gieo được", "lời khuyên", "tư vấn", "đồng xu", 
                "ngửa úp", "gieo quẻ", "bói toán"
            ],
            "hexagram_specific": [
                "quẻ [name] là gì", "quẻ [name] có ý nghĩa", 
                "que [name]", "hexagram [name]"
            ],
            "philosophy": [
                "triết lý", "được hiểu như thế nào", "ý nghĩa của",
                "âm dương", "ngũ hành", "trong kinh dịch"
            ],
            "general": [
                "kinh dịch", "dịch học", "văn hóa đông phương"
            ]
        }
    
    async def process(self, state: ProcessingState) -> ProcessingState:
        """Classify query và set strategy"""
        
        query = state.query.lower().strip()
        
        # Fast rule-based classification
        state.query_type = self._rule_based_classification(query)
        
        # If ambiguous, use embedding-based classification
        if state.query_type == "ambiguous":
            state.query_type = await self._embedding_classification(query)
        
        state.reasoning_chain.append(
            f"Query classified as: {state.query_type}"
        )
        
        return state
    
    def _rule_based_classification(self, query: str) -> str:
        """Fast rule-based classification"""
        
        # Check for divination patterns
        divination_patterns = [
            r'\btôi (được|gieo)\b', r'\b(ngửa|úp)\b', 
            r'\blời khuyên\b', r'\btư vấn\b'
        ]
        if any(re.search(pattern, query) for pattern in divination_patterns):
            return "divination"
        
        # Check for specific hexagram patterns
        hexagram_patterns = [r'\bquẻ \w+\b', r'\bque \w+\b']
        if any(re.search(pattern, query) for pattern in hexagram_patterns):
            return "hexagram_specific"
        
        # Check for philosophy patterns
        philosophy_patterns = [
            r'\btriết lý\b', r'\bđược hiểu như thế nào\b',
            r'\bý nghĩa của\b', r'\bâm dương\b'
        ]
        if any(re.search(pattern, query) for pattern in philosophy_patterns):
            return "philosophy"
        
        return "ambiguous"
    
    async def _embedding_classification(self, query: str) -> str:
        """Embedding-based classification cho ambiguous cases"""
        
        # Create template embeddings
        template_embeddings = {}
        for category, templates in self.query_templates.items():
            if category != "hexagram_specific":  # Skip pattern-based category
                combined_template = " ".join(templates)
                template_embeddings[category] = self.classifier_model.encode([combined_template])[0]
        
        # Get query embedding
        query_embedding = self.classifier_model.encode([query])[0]
        
        # Find best match
        best_category = "general"
        best_similarity = 0.0
        
        for category, template_emb in template_embeddings.items():
            similarity = np.dot(query_embedding, template_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(template_emb)
            )
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_category = category
        
        return best_category if best_similarity > 0.3 else "general"
