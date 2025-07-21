"""
Memory-Aware Conversation State
Extends base state with intelligent memory management
"""
from typing import Dict, Any, List, Optional, Annotated
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from app.state.conversation_state import ConversationState


class MemoryAwareState(ConversationState):
    """
    Enhanced state with memory management capabilities
    Separates current from historical, maintains agent contexts
    """
    
    # Current conversation thread only (no history)
    current_thread_messages: Annotated[List[BaseMessage], add_messages] = Field(
        default_factory=list,
        description="Messages from current conversation only"
    )
    
    # Historical summary (compressed)
    historical_summary: str = Field(
        default="",
        description="Summarized historical context"
    )
    
    # Agent-specific working memory
    agent_working_memory: Dict[str, List[BaseMessage]] = Field(
        default_factory=dict,
        description="Isolated working memory per agent"
    )
    
    # Current active agent
    active_agent: Optional[str] = Field(
        None,
        description="Currently active agent"
    )
    
    # Handoff context
    handoff_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Context passed during agent handoff"
    )
    
    # Message counter for memory management
    message_count: int = Field(
        default=0,
        description="Total messages in current thread"
    )
    
    # Memory window size
    memory_window_size: int = Field(
        default=10,
        description="Maximum messages to keep in active memory"
    )
    
    def add_current_message(self, message: BaseMessage) -> None:
        """Add message to current thread with overflow management"""
        self.current_thread_messages.append(message)
        self.message_count += 1
        
        # Check for overflow
        if len(self.current_thread_messages) > self.memory_window_size:
            # Move oldest messages to summary
            overflow = self.current_thread_messages[:-self.memory_window_size]
            self._update_historical_summary(overflow)
            # Keep only recent messages
            self.current_thread_messages = self.current_thread_messages[-self.memory_window_size:]
    
    def get_agent_context(self, agent_name: str) -> List[BaseMessage]:
        """Get isolated context for specific agent"""
        if agent_name not in self.agent_working_memory:
            self.agent_working_memory[agent_name] = []
        
        # Return only this agent's working memory
        return self.agent_working_memory[agent_name][-6:]  # Last 6 messages
    
    def add_agent_message(self, agent_name: str, message: BaseMessage) -> None:
        """Add message to agent's working memory"""
        if agent_name not in self.agent_working_memory:
            self.agent_working_memory[agent_name] = []
        
        self.agent_working_memory[agent_name].append(message)
        
        # Limit agent memory
        if len(self.agent_working_memory[agent_name]) > 10:
            self.agent_working_memory[agent_name] = self.agent_working_memory[agent_name][-10:]
    
    def prepare_handoff(self, from_agent: str, to_agent: str, reason: str) -> None:
        """Prepare context for agent handoff"""
        self.handoff_context = {
            "from": from_agent,
            "to": to_agent,
            "reason": reason,
            "extracted_data": self.extracted_data,
            "last_intent": self.current_intent,
            "timestamp": self.message_count
        }
        
        # Clear target agent's memory
        self.agent_working_memory[to_agent] = []
        
        # Update active agent
        self.active_agent = to_agent
    
    def _update_historical_summary(self, old_messages: List[BaseMessage]) -> None:
        """Update historical summary with old messages"""
        # Simple summary for now - can be enhanced with LLM summarization
        summary_points = []
        
        for msg in old_messages:
            if hasattr(msg, 'content') and msg.content:
                # Extract key information
                content = msg.content.lower()
                if "appointment" in content or "cita" in content:
                    summary_points.append("Discussed appointment booking")
                elif "business" in content or "negocio" in content:
                    if self.extracted_data.get("business_type"):
                        summary_points.append(f"Business: {self.extracted_data['business_type']}")
                elif "problem" in content or "problema" in content:
                    if self.extracted_data.get("goal"):
                        summary_points.append(f"Problem: {self.extracted_data['goal']}")
        
        if summary_points:
            self.historical_summary = f"Previous discussion: {'; '.join(set(summary_points))}"
    
    def get_relevant_context(self, agent_name: str, include_historical: bool = False) -> Dict[str, Any]:
        """
        Get optimized context for an agent
        This is the main method agents should use
        """
        context = {
            "agent_name": agent_name,
            "current_messages": self.get_agent_context(agent_name),
            "extracted_data": self.extracted_data,
            "current_intent": self.current_intent,
            "handoff_info": self.handoff_context if self.active_agent == agent_name else None,
        }
        
        if include_historical and self.historical_summary:
            context["historical_context"] = self.historical_summary
        
        return context
    
    def clear_conversation_memory(self) -> None:
        """Clear all conversation memory - for new conversations"""
        self.current_thread_messages = []
        self.agent_working_memory = {}
        self.historical_summary = ""
        self.handoff_context = None
        self.message_count = 0
        self.active_agent = None