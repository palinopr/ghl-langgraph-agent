"""
Context Filter - Intelligent message filtering for agents
Prevents context pollution and confusion
"""
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from app.utils.simple_logger import get_logger

logger = get_logger("context_filter")


class ContextFilter:
    """
    Filters and prepares context for agents
    Ensures each agent only sees relevant information
    """
    
    @staticmethod
    def filter_messages_for_agent(
        messages: List[BaseMessage], 
        agent_name: str,
        max_messages: int = 10
    ) -> List[BaseMessage]:
        """
        Filter messages to only include relevant ones for the specific agent
        
        Args:
            messages: All messages in conversation
            agent_name: Name of the agent requesting context
            max_messages: Maximum number of messages to return
            
        Returns:
            Filtered list of messages relevant to the agent
        """
        filtered = []
        
        for msg in messages:
            # Always include human messages
            if isinstance(msg, HumanMessage) or (hasattr(msg, 'type') and msg.type == "human"):
                # But skip historical human messages
                if hasattr(msg, 'additional_kwargs'):
                    if msg.additional_kwargs.get('source') == 'ghl_history':
                        continue
                filtered.append(msg)
                continue
            
            # Check if message is from this agent
            if hasattr(msg, 'name') and msg.name == agent_name:
                filtered.append(msg)
                continue
            
            # Include system messages for this agent
            if isinstance(msg, SystemMessage):
                if hasattr(msg, 'additional_kwargs'):
                    target_agent = msg.additional_kwargs.get('target_agent')
                    if target_agent == agent_name or target_agent == 'all':
                        filtered.append(msg)
        
        # Return only the most recent messages
        return filtered[-max_messages:] if len(filtered) > max_messages else filtered
    
    @staticmethod
    def separate_current_from_historical(
        messages: List[BaseMessage]
    ) -> Tuple[List[BaseMessage], List[BaseMessage]]:
        """
        Separate current conversation from historical messages
        
        Returns:
            Tuple of (current_messages, historical_messages)
        """
        current = []
        historical = []
        
        for msg in messages:
            # Check if message is historical
            is_historical = False
            
            if hasattr(msg, 'additional_kwargs'):
                source = msg.additional_kwargs.get('source', '')
                if source == 'ghl_history':
                    is_historical = True
            
            if is_historical:
                historical.append(msg)
            else:
                current.append(msg)
        
        logger.info(f"Separated {len(messages)} messages: {len(current)} current, {len(historical)} historical")
        return current, historical
    
    @staticmethod
    def extract_relevant_historical_context(
        historical_messages: List[BaseMessage],
        current_topic: str,
        extracted_data: Dict[str, Any]
    ) -> str:
        """
        Extract only relevant historical context as a summary
        
        Args:
            historical_messages: Historical messages
            current_topic: Current conversation topic
            extracted_data: Already extracted customer data
            
        Returns:
            Summary string of relevant historical context
        """
        if not historical_messages:
            return ""
        
        # Topic keywords for relevance matching
        topic_keywords = {
            "appointment": ["appointment", "cita", "schedule", "calendar", "booking"],
            "business": ["business", "negocio", "company", "empresa", "restaurant"],
            "problem": ["problem", "problema", "challenge", "issue", "help"],
            "budget": ["budget", "price", "cost", "precio", "presupuesto", "$"],
            "contact": ["email", "phone", "contact", "correo", "teléfono"]
        }
        
        # Get keywords for current topic
        keywords = topic_keywords.get(current_topic, [])
        
        # Find relevant historical messages
        relevant_points = []
        
        for msg in historical_messages:
            if hasattr(msg, 'content') and msg.content:
                content = msg.content.lower()
                
                # Check if message contains relevant keywords
                if any(keyword in content for keyword in keywords):
                    # Extract key point
                    if "appointment" in content and "booked" in content:
                        relevant_points.append("Previously booked appointment")
                    elif "business" in content and extracted_data.get("business_type"):
                        relevant_points.append(f"Discussed {extracted_data['business_type']} business")
                    elif "problem" in content and "solved" in content:
                        relevant_points.append("Previous issue was resolved")
        
        if relevant_points:
            return f"Historical context: {'; '.join(set(relevant_points))}"
        
        return ""
    
    @staticmethod
    def prepare_agent_context(
        agent_name: str,
        messages: List[BaseMessage],
        extracted_data: Dict[str, Any],
        current_intent: Optional[str] = None,
        include_historical: bool = False
    ) -> Dict[str, Any]:
        """
        Prepare complete, filtered context for an agent
        
        This is the main method to use for preparing agent context
        
        Args:
            agent_name: Name of the agent
            messages: All available messages
            extracted_data: Extracted customer data
            current_intent: Current conversation intent
            include_historical: Whether to include historical context
            
        Returns:
            Complete context dictionary for the agent
        """
        # Separate current from historical
        current_messages, historical_messages = ContextFilter.separate_current_from_historical(messages)
        
        # Filter current messages for this agent
        agent_messages = ContextFilter.filter_messages_for_agent(current_messages, agent_name)
        
        # Build context
        context = {
            "agent_name": agent_name,
            "messages": agent_messages,
            "extracted_data": extracted_data,
            "current_intent": current_intent,
            "message_count": len(agent_messages)
        }
        
        # Add historical context if requested and available
        if include_historical and historical_messages:
            historical_summary = ContextFilter.extract_relevant_historical_context(
                historical_messages,
                current_intent or "general",
                extracted_data
            )
            if historical_summary:
                context["historical_summary"] = historical_summary
        
        # Add current customer message
        for msg in reversed(current_messages):
            if isinstance(msg, HumanMessage):
                context["current_customer_message"] = msg.content
                break
        
        logger.info(f"Prepared context for {agent_name}: {len(agent_messages)} messages, "
                   f"historical: {include_historical}")
        
        return context
    
    @staticmethod
    def create_handoff_message(
        from_agent: str,
        to_agent: str,
        reason: str,
        key_facts: Dict[str, Any]
    ) -> SystemMessage:
        """
        Create a clean handoff message between agents
        
        Args:
            from_agent: Agent handing off
            to_agent: Agent receiving handoff
            reason: Reason for handoff
            key_facts: Important facts to pass along
            
        Returns:
            SystemMessage with handoff context
        """
        # Build concise handoff summary
        facts_summary = []
        
        if key_facts.get("name"):
            facts_summary.append(f"Customer: {key_facts['name']}")
        
        if key_facts.get("business_type"):
            facts_summary.append(f"Business: {key_facts['business_type']}")
        
        if key_facts.get("goal"):
            facts_summary.append(f"Need: {key_facts['goal']}")
        
        if key_facts.get("budget_confirmed"):
            facts_summary.append("Budget: Confirmed ($300+)")
        
        handoff_content = (
            f"Handoff from {from_agent} → {to_agent}\n"
            f"Reason: {reason}\n"
            f"Context: {' | '.join(facts_summary) if facts_summary else 'Initial contact'}"
        )
        
        return SystemMessage(
            content=handoff_content,
            additional_kwargs={
                "target_agent": to_agent,
                "from_agent": from_agent,
                "handoff": True
            }
        )
    
    @staticmethod
    def should_include_message(
        message: BaseMessage,
        agent_name: str,
        conversation_stage: str
    ) -> bool:
        """
        Determine if a message should be included in agent's context
        
        Args:
            message: Message to evaluate
            agent_name: Current agent name
            conversation_stage: Current conversation stage
            
        Returns:
            Boolean indicating if message should be included
        """
        # Always include human messages from current conversation
        if isinstance(message, HumanMessage):
            if hasattr(message, 'additional_kwargs'):
                if message.additional_kwargs.get('source') != 'ghl_history':
                    return True
            else:
                return True
        
        # Include agent's own messages
        if hasattr(message, 'name') and message.name == agent_name:
            return True
        
        # Include relevant system messages
        if isinstance(message, SystemMessage):
            if hasattr(message, 'additional_kwargs'):
                target = message.additional_kwargs.get('target_agent')
                if target == agent_name or target == 'all':
                    return True
        
        # Exclude messages from other agents
        return False