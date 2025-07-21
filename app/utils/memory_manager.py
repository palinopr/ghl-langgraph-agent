"""
Memory Manager - Intelligent context and memory management for agents
Solves: Context confusion, memory overflow, agent isolation
"""
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from app.utils.simple_logger import get_logger
from datetime import datetime

logger = get_logger("memory_manager")


class AgentMemorySpace:
    """Individual memory space for each agent with sliding window"""
    
    def __init__(self, agent_name: str, window_size: int = 6):
        self.agent_name = agent_name
        self.window_size = window_size
        self.current_context = deque(maxlen=window_size)
        self.handoff_context = {}
        self.last_active = datetime.now()
    
    def add_message(self, message: BaseMessage):
        """Add message to agent's context window"""
        self.current_context.append(message)
        self.last_active = datetime.now()
    
    def get_context(self) -> List[BaseMessage]:
        """Get current context for this agent"""
        return list(self.current_context)
    
    def clear_context(self):
        """Clear agent's working memory"""
        self.current_context.clear()
        self.handoff_context = {}
    
    def prepare_handoff(self, reason: str, key_facts: Dict) -> Dict:
        """Prepare minimal context for handoff"""
        return {
            "from_agent": self.agent_name,
            "reason": reason,
            "key_facts": key_facts,
            "last_topic": self._extract_last_topic()
        }
    
    def _extract_last_topic(self) -> str:
        """Extract the last discussed topic"""
        if not self.current_context:
            return "initial_contact"
        
        # Look at last 2 messages for topic
        recent = list(self.current_context)[-2:]
        for msg in reversed(recent):
            if hasattr(msg, 'content'):
                content = msg.content.lower()
                if "appointment" in content or "cita" in content:
                    return "appointment_booking"
                elif "business" in content or "negocio" in content:
                    return "business_qualification"
                elif "problem" in content or "problema" in content:
                    return "problem_discussion"
        
        return "general_inquiry"


class MemoryManager:
    """
    Central memory management system for all agents
    Handles context isolation, handoffs, and memory lifecycle
    """
    
    def __init__(self):
        self.agent_memories: Dict[str, AgentMemorySpace] = {}
        self.shared_facts: Dict[str, Any] = {}
        self.conversation_summary: str = ""
        self.current_agent: Optional[str] = None
        
    def get_or_create_agent_memory(self, agent_name: str) -> AgentMemorySpace:
        """Get or create memory space for an agent"""
        if agent_name not in self.agent_memories:
            logger.info(f"Creating new memory space for {agent_name}")
            self.agent_memories[agent_name] = AgentMemorySpace(agent_name)
        return self.agent_memories[agent_name]
    
    def get_agent_context(self, agent_name: str, state: Dict) -> Dict[str, Any]:
        """
        Get optimized context for a specific agent
        This is the main method agents should use
        """
        memory_space = self.get_or_create_agent_memory(agent_name)
        
        # Get extracted data (shared facts)
        extracted_data = state.get("extracted_data", {})
        
        # Get agent's recent context
        agent_context = memory_space.get_context()
        
        # Check if this is a handoff
        handoff_info = None
        if self.current_agent and self.current_agent != agent_name:
            # This is a handoff
            previous_memory = self.agent_memories.get(self.current_agent)
            if previous_memory:
                handoff_info = previous_memory.prepare_handoff(
                    reason=state.get("escalation_reason", "workflow_routing"),
                    key_facts=extracted_data
                )
        
        # Update current agent
        self.current_agent = agent_name
        
        # Build optimized context
        context = {
            "agent_name": agent_name,
            "messages": agent_context,  # Only this agent's recent messages
            "extracted_data": extracted_data,  # Shared facts
            "handoff_info": handoff_info,  # Handoff context if switching
            "current_message": self._get_current_message(state),
            "conversation_stage": state.get("conversation_stage", "initial"),
        }
        
        logger.info(f"Prepared context for {agent_name}: {len(agent_context)} messages")
        return context
    
    def add_agent_message(self, agent_name: str, message: BaseMessage):
        """Add a message to an agent's memory"""
        memory_space = self.get_or_create_agent_memory(agent_name)
        memory_space.add_message(message)
        logger.debug(f"Added message to {agent_name}'s memory")
    
    def handle_agent_handoff(self, from_agent: str, to_agent: str, state: Dict) -> Dict:
        """
        Handle clean handoff between agents
        Clears unnecessary context and prepares minimal handoff
        """
        logger.info(f"Handling handoff: {from_agent} → {to_agent}")
        
        # Get memories
        from_memory = self.agent_memories.get(from_agent)
        to_memory = self.get_or_create_agent_memory(to_agent)
        
        # Clear target agent's old context
        to_memory.clear_context()
        
        # Prepare handoff message
        handoff_data = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "reason": state.get("escalation_reason", "workflow_routing"),
            "extracted_data": state.get("extracted_data", {}),
            "key_context": self._extract_key_context(from_memory) if from_memory else {}
        }
        
        # Add handoff as system message to new agent
        handoff_msg = SystemMessage(
            content=f"Handoff from {from_agent}: {handoff_data['reason']}. "
                   f"Customer data: {handoff_data['extracted_data']}"
        )
        to_memory.add_message(handoff_msg)
        
        # Update current agent
        self.current_agent = to_agent
        
        return handoff_data
    
    def filter_messages_for_agent(self, messages: List[BaseMessage], agent_name: str) -> List[BaseMessage]:
        """
        Filter messages to only include relevant ones for the agent
        Removes internal messages from other agents
        """
        filtered = []
        
        for msg in messages:
            # Skip if it's another agent's internal message
            if hasattr(msg, 'additional_kwargs'):
                msg_agent = msg.additional_kwargs.get('agent')
                if msg_agent and msg_agent != agent_name:
                    continue
            
            # Include human messages and this agent's messages
            if isinstance(msg, HumanMessage) or \
               (hasattr(msg, 'name') and msg.name == agent_name):
                filtered.append(msg)
        
        return filtered
    
    def separate_historical_from_current(self, messages: List[BaseMessage]) -> Tuple[List[BaseMessage], List[BaseMessage]]:
        """
        Separate historical messages from current conversation
        Historical = marked with source='ghl_history'
        """
        historical = []
        current = []
        
        for msg in messages:
            if hasattr(msg, 'additional_kwargs') and \
               msg.additional_kwargs.get('source') == 'ghl_history':
                historical.append(msg)
            else:
                current.append(msg)
        
        logger.info(f"Separated messages: {len(historical)} historical, {len(current)} current")
        return historical, current
    
    def get_relevant_history(self, historical_messages: List[BaseMessage], current_intent: str) -> List[BaseMessage]:
        """
        Extract only relevant historical messages based on current intent
        """
        relevant = []
        
        intent_keywords = {
            "appointment": ["appointment", "cita", "schedule", "calendar"],
            "business": ["business", "negocio", "company", "empresa"],
            "problem": ["problem", "problema", "challenge", "issue"],
            "budget": ["budget", "price", "cost", "precio", "presupuesto"]
        }
        
        keywords = intent_keywords.get(current_intent, [])
        
        for msg in historical_messages:
            if hasattr(msg, 'content'):
                content = msg.content.lower()
                if any(keyword in content for keyword in keywords):
                    relevant.append(msg)
        
        # Limit to most recent 3 relevant historical messages
        return relevant[-3:] if relevant else []
    
    def update_shared_facts(self, new_facts: Dict[str, Any]):
        """Update shared facts that all agents can access"""
        self.shared_facts.update(new_facts)
        logger.info(f"Updated shared facts: {list(new_facts.keys())}")
    
    def _get_current_message(self, state: Dict) -> Optional[str]:
        """Extract the current human message from state"""
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) or (hasattr(msg, 'type') and msg.type == "human"):
                return msg.content if hasattr(msg, 'content') else None
        return None
    
    def _extract_key_context(self, memory_space: Optional[AgentMemorySpace]) -> Dict:
        """Extract key context from an agent's memory"""
        if not memory_space:
            return {}
        
        context = memory_space.get_context()
        if not context:
            return {}
        
        # Extract last question asked and answer given
        last_exchange = {}
        for i in range(len(context) - 1, 0, -1):
            if isinstance(context[i], AIMessage) and isinstance(context[i-1], HumanMessage):
                last_exchange = {
                    "last_customer_message": context[i-1].content,
                    "last_agent_response": context[i].content
                }
                break
        
        return last_exchange
    
    def clear_all_memories(self):
        """Clear all agent memories - use when starting new conversation"""
        for agent_memory in self.agent_memories.values():
            agent_memory.clear_context()
        self.shared_facts.clear()
        self.conversation_summary = ""
        self.current_agent = None
        logger.info("Cleared all agent memories")


# Global memory manager instance
memory_manager = MemoryManager()


def get_memory_manager() -> MemoryManager:
    """Get the global memory manager instance"""
    return memory_manager