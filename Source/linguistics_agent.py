# linguistics_agent.py - Tích hợp NER + WSD + Expansion
import re
from typing import Dict, List, Set
import spacy
from spacy.matcher import Matcher
from sentence_transformers import SentenceTransformer
import numpy as np

from base_agent import BaseAgent, AgentType, ProcessingState

class LinguisticsAgent(BaseAgent):
    """Tích hợp NER, WSD, và Query Expansion trong 1 agent"""
    
    def __init__(self):
        super().__init__("LinguisticsAgent", AgentType.LINGUISTICS)
        
        # Initialize NLP models
        self.nlp = spacy.blank("vi")
        self.matcher = Matcher(self.nlp.vocab)
        self.embedder = SentenceTransformer('keepitreal/vietnamese-sbert')
        
        # Setup NER patterns
        self._setup_ner_patterns()
        
        # WSD sense definitions
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
            "âm dương": ["yin yang", "negative positive", "âm dương"]
        }
    
    def _setup_ner_patterns(self):
        """Setup NER patterns cho Kinh Dịch entities"""
        
        # Hexagram patterns
        hexagram_patterns = [
            [{"LOWER": "quẻ"}, {"IS_ALPHA": True}],
            [{"LOWER": "que"}, {"IS_ALPHA": True}],
            [{"LOWER": "hexagram"}, {"IS_ALPHA": True}]
        ]
        self.matcher.add("HEXAGRAM", hexagram_patterns)
        
        # Philosophy patterns
        philosophy_patterns = [
            [{"LOWER": "triết"}, {"LOWER": "lý"}],
            [{"LOWER": "âm"}, {"LOWER": "dương"}],
            [{"LOWER": "ngũ"}, {"LOWER": "hành"}]
        ]
        self.matcher.add("PHILOSOPHY", philosophy_patterns)
        
        # Divination patterns
        divination_patterns = [
            [{"LOWER": "gieo"}, {"LOWER": "quẻ"}],
            [{"LOWER": "lời"}, {"LOWER": "khuyên"}]
        ]
        self.matcher.add("DIVINATION", divination_patterns)
    
    async def process(self, state: ProcessingState) -> ProcessingState:
        """Process NER + WSD + Expansion in pipeline"""
        
        query = state.query
        
        # Step 1: Named Entity Recognition
        entities = self._extract_entities(query)
        state.entities = entities
        
        # Step 2: Word Sense Disambiguation
        disambiguated_query = self._disambiguate_senses(query, entities)
        
        # Step 3: Query Expansion
        expanded_query = self._expand_query(disambiguated_query)
        state.expanded_query = expanded_query
        
        # Add reasoning
        state.reasoning_chain.extend([
            f"Entities detected: {entities}",
            f"WSD applied to ambiguous terms",
            f"Query expanded with aliases and synonyms"
        ])
        
        return state
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities using spaCy matcher"""
        
        doc = self.nlp(text)
        matches = self.matcher(doc)
        
        entities = {
            "hexagrams": [],
            "philosophy_concepts": [],
            "divination_terms": []
        }
        
        for match_id, start, end in matches:
            label = self.nlp.vocab.strings[match_id]
            span_text = doc[start:end].text
            
            if label == "HEXAGRAM":
                entities["hexagrams"].append(span_text)
            elif label == "PHILOSOPHY":
                entities["philosophy_concepts"].append(span_text)
            elif label == "DIVINATION":
                entities["divination_terms"].append(span_text)
        
        return entities
    
    def _disambiguate_senses(self, query: str, entities: Dict) -> str:
        """Word Sense Disambiguation using context"""
        
        query_lower = query.lower()
        query_embedding = self.embedder.encode([query])[0]
        
        # Check each ambiguous word
        for word, senses in self.sense_definitions.items():
            if word in query_lower:
                
                # Calculate similarity với mỗi sense
                best_sense = None
                best_similarity = 0.0
                
                for sense_key, sense_desc in senses.items():
                    sense_embedding = self.embedder.encode([sense_desc])[0]
                    similarity = np.dot(query_embedding, sense_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(sense_embedding)
                    )
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_sense = sense_key
                
                # Apply disambiguation logic
                if word == "ly" and best_sense == "philosophy":
                    # If "ly" is used in philosophy context, don't treat as hexagram
                    if "triết lý" in query_lower or "lý thuyết" in query_lower:
                        continue  # Keep as is, don't mark as hexagram
        
        return query
    
    def _expand_query(self, query: str) -> str:
        """Expand query với aliases và synonyms"""
        
        expanded_terms = set([query])
        query_words = set(query.lower().split())
        
        # Add aliases
        for term, aliases in self.expansion_aliases.items():
            if term in query.lower():
                expanded_terms.update(aliases)
        
        # Combine original query với expanded terms
        expanded_query = query + " " + " ".join(expanded_terms - {query})
        
        return expanded_query
