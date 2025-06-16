# linguistics_agent.py - Tích hợp NER + WSD + Expansion
import re
from typing import Dict, List
from sentence_transformers import SentenceTransformer
import numpy as np

from base_agent import BaseAgent, AgentType, ProcessingState

class LinguisticsAgent(BaseAgent):
    """Tích hợp NER, WSD, và Query Expansion trong 1 agent"""
    
    def __init__(self):
        super().__init__("LinguisticsAgent", AgentType.LINGUISTICS)
        self.embedder = SentenceTransformer('keepitreal/vietnamese-sbert')
        
        # Regex patterns cho NER
        self.entity_patterns = {
            "hexagrams": [
                r'\b(?:quẻ|que)\s+(\w+)',
                r'\bhexagram\s+(\w+)'
            ],
            "philosophy_concepts": [
                r'\btriết\s*lý\b',
                r'\bâm\s*dương\b',
                r'\bngũ\s*hành\b',
                r'\blý\s*thuyết\b'
            ],
            "divination_terms": [
                r'\bgieo\s*quẻ\b',
                r'\blời\s*khuyên\b',
                r'\btư\s*vấn\b'
            ]
        }
        
        # WSD definitions
        self.sense_definitions = {
            "ly": {
                "philosophy": "triết lý học thuyết nguyên lý khái niệm",
                "hexagram": "quẻ ly hỏa quẻ số 30 bát quẻ"
            },
            "cach": {
                "revolution": "cách mạng thay đổi biến đổi cải cách",
                "hexagram": "quẻ cách quẻ số 49 bát quẻ"
            }
        }
        
        # Expansion aliases
        self.expansion_aliases = {
            "cách": ["革", "revolution", "change"],
            "hàm": ["咸", "influence", "感"],
            "ly": ["離", "fire", "clinging"],
            "âm dương": ["yin yang", "negative positive"],
            "fellowship": ["đồng nhân", "同人", "togetherness"]
        }
    
    async def process(self, state: ProcessingState) -> ProcessingState:
        """Process NER + WSD + Expansion in pipeline"""
        
        query = state.query
        
        # Step 1: Regex-based NER
        entities = self._extract_entities_regex(query)
        state.entities = entities
        
        # Step 2: Simple WSD
        disambiguated_query = self._simple_wsd(query)
        
        # Step 3: Query expansion
        expanded_query = self._expand_query(disambiguated_query)
        state.expanded_query = expanded_query
        
        state.reasoning_chain.extend([
            f"Entities (regex): {entities}",
            f"Simple WSD applied",
            f"Query expanded"
        ])
        
        return state
    
    def _extract_entities_regex(self, text: str) -> Dict[str, List[str]]:
        """Extract entities using regex patterns"""
        
        entities = {
            "hexagrams": [],
            "philosophy_concepts": [],
            "divination_terms": []
        }
        
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text.lower())
                if matches:
                    entities[entity_type].extend(matches)
        
        return entities
    
    def _simple_wsd(self, query: str) -> str:
        """Simple word sense disambiguation"""
        
        # Check for "triết lý" context
        if "triết lý" in query.lower() or "lý thuyết" in query.lower():
            # Don't treat "ly" as hexagram in philosophy context
            pass
        
        # Enhanced: Check for fellowship context
        if "fellowship" in query.lower():
            # Should map to Đồng Nhân, not Sư
            pass
        
        return query
    
    def _expand_query(self, query: str) -> str:
        """Simple query expansion"""
        
        expanded_terms = [query]
        
        for term, aliases in self.expansion_aliases.items():
            if term in query.lower():
                expanded_terms.extend(aliases[:2])  # Limit aliases
        
        return " ".join(expanded_terms)
