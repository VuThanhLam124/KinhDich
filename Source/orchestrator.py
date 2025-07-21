import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from tqdm.asyncio import tqdm

from base_agent import ProcessingState
from dispatcher_agent import DispatcherAgent
from linguistics_agent import LinguisticsAgent
from retrieval_agent import RetrievalAgent
from reasoning_agent import ReasoningAgent

logger = logging.getLogger(__name__)

class MultiAgentOrchestrator:
    """Orchestrates multi-agent workflow cho Kinh Dịch chatbot"""
    
    def __init__(self):
        # Initialize agents
        self.agents = {
            "dispatcher": DispatcherAgent(),
            "linguistics": LinguisticsAgent(),
            "retrieval": RetrievalAgent(),
            "reasoning": ReasoningAgent()
        }
        
        # Workflow definition
        self.workflow = [
            "dispatcher",
            "linguistics", 
            "retrieval",
            "reasoning"
        ]
    
    async def process_query(self, query: str, user_name: str = None, hexagram_info: Optional[Dict] = None) -> Dict[str, Any]:
        """Process query through multi-agent pipeline"""
        
        # Initialize state
        state = ProcessingState(query=query, hexagram_info=hexagram_info or {})
        start_time = time.time()
        
        # Execute workflow với progress tracking
        try:
            agent_tasks = []
            for agent_name in self.workflow:
                agent = self.agents[agent_name]
                agent_tasks.append((agent_name, agent))
            
            # Process agents sequentially với tqdm progress
            for agent_name, agent in tqdm(agent_tasks, desc="Processing agents"):
                state = await agent.execute_with_monitoring(state)
                
                # Early exit nếu critical failure
                if agent_name == "retrieval" and not state.retrieved_docs:
                    break
            
            # Calculate total processing time
            total_time = time.time() - start_time
            state.processing_time["total"] = total_time
            
            # Build final result
            result = {
                "answer": state.final_response,
                "query": state.query,
                "query_type": state.query_type,
                "entities": state.entities,
                "confidence": state.confidence,
                "sources": self._format_sources(state.reranked_docs or []),
                "reasoning_chain": state.reasoning_chain,
                "performance": {
                    "total_time_ms": round(total_time * 1000, 2),
                    "agent_times": {
                        name: round(time_ms * 1000, 2) 
                        for name, time_ms in state.processing_time.items()
                    }
                },
                "agent_stats": self._get_agent_stats(),
                "success": len(state.final_response) > 0
            }
            
            return result
            
        except Exception as e:
            return self._create_error_response(query, str(e))
    
    def _format_sources(self, docs: List[Dict]) -> List[Dict]:
        """Format sources cho UI display"""
        
        sources = []
        for i, doc in enumerate(docs[:10], 1):
            source = {
                "id": i,
                "chunk_id": doc.get("_id", "unknown"),
                "hexagram": doc.get("hexagram", ""),
                "content_type": doc.get("content_type", ""),
                "relevance_score": doc.get("rerank_score", doc.get("similarity_score", 0)),
                "preview": (doc.get("text", "")[:150] + "...") if len(doc.get("text", "")) > 150 else doc.get("text", "")
            }
            sources.append(source)
        
        return sources
    
    def _get_agent_stats(self) -> Dict[str, Dict]:
        """Get performance stats từ tất cả agents"""
        
        stats = {}
        for name, agent in self.agents.items():
            stats[name] = agent.performance_stats.copy()
        
        return stats
    
    def _create_error_response(self, query: str, error: str) -> Dict[str, Any]:
        """Create error response"""
        
        return {
            "answer": "Xin lỗi, đã có lỗi xảy ra trong quá trình xử lý.",
            "query": query,
            "success": False,
            "error": error,
            "confidence": 0.0,
            "sources": [],
            "reasoning_chain": [f"Error: {error}"]
        }

# Compatibility function
async def answer_with_agents(query: str, user_name: str = None, hexagram_info: Optional[Dict] = None) -> Dict[str, Any]:
    """Main interface cho multi-agent system"""
    orchestrator = MultiAgentOrchestrator()
    return await orchestrator.process_query(query, user_name, hexagram_info)
