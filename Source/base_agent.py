# base_agent.py - Base architecture cho multi-agent system
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import time
from tqdm import tqdm

logger = logging.getLogger(__name__)

class AgentType(Enum):
    DISPATCHER = "dispatcher"
    LINGUISTICS = "linguistics"  # Tích hợp NER + WSD + Expansion
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"      # Tích hợp Reranking + Response

@dataclass
class AgentMessage:
    """Standardized message format giữa agents"""
    type: str
    content: Any
    metadata: Dict[str, Any]
    timestamp: float
    source_agent: str
    target_agent: Optional[str] = None

@dataclass
class ProcessingState:
    """Shared state giữa các agents"""
    query: str
    query_type: str = ""
    entities: Dict[str, List[str]] = None
    expanded_query: str = ""
    retrieved_docs: List[Dict] = None
    reranked_docs: List[Dict] = None
    final_response: str = ""
    confidence: float = 0.0
    reasoning_chain: List[str] = None
    processing_time: Dict[str, float] = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = {}
        if self.reasoning_chain is None:
            self.reasoning_chain = []
        if self.processing_time is None:
            self.processing_time = {}

class BaseAgent(ABC):
    """Base class cho tất cả agents"""
    
    def __init__(self, name: str, agent_type: AgentType):
        self.name = name
        self.agent_type = agent_type
        self.performance_stats = {
            "total_requests": 0,
            "avg_processing_time": 0.0,
            "success_rate": 0.0
        }
    
    @abstractmethod
    async def process(self, state: ProcessingState) -> ProcessingState:
        """Main processing method - must be implemented by subclasses"""
        pass
    
    async def execute_with_monitoring(self, state: ProcessingState) -> ProcessingState:
        """Execute với performance monitoring"""
        start_time = time.time()
        
        try:
            logger.info(f"🤖 {self.name} processing...")
            result = await self.process(state)
            
            # Update performance stats
            processing_time = time.time() - start_time
            state.processing_time[self.name] = processing_time
            self._update_performance_stats(processing_time, True)
            
            logger.info(f"✅ {self.name} completed in {processing_time:.3f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_performance_stats(processing_time, False)
            logger.error(f"❌ {self.name} failed: {e}")
            raise
    
    def _update_performance_stats(self, processing_time: float, success: bool):
        """Update agent performance statistics"""
        self.performance_stats["total_requests"] += 1
        
        # Update average processing time
        total = self.performance_stats["total_requests"]
        current_avg = self.performance_stats["avg_processing_time"]
        self.performance_stats["avg_processing_time"] = (
            (current_avg * (total - 1) + processing_time) / total
        )
        
        # Update success rate
        if success:
            current_success = self.performance_stats.get("successful_requests", 0)
            self.performance_stats["successful_requests"] = current_success + 1
        
        self.performance_stats["success_rate"] = (
            self.performance_stats.get("successful_requests", 0) / total * 100
        )
