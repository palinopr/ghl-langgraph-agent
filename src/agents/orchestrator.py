"""
Orchestrator for routing messages to appropriate agents
Uses LLM to analyze intent and route to Sofia, Carlos, or Maria
"""
from typing import Dict, Any, Literal
from datetime import datetime
import pytz
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from ..state.conversation_state import ConversationState
from ..utils.simple_logger import get_logger
from ..config import get_settings

logger = get_logger("orchestrator")


class Orchestrator:
    """Intelligent router for agent selection"""
    
    def __init__(self):
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.2,
            api_key=settings.openai_api_key
        )
        
        self.system_prompt = """You are an intelligent routing system for Main Outlet Media.

Analyze the user's message and conversation history to determine which agent should handle the request:

1. **Sofia** - Appointment Setting Specialist
   - Routes: appointment booking, scheduling, calendar inquiries
   - Keywords: book, schedule, appointment, meeting, consultation, available times
   
2. **Carlos** - Lead Qualification Specialist  
   - Routes: business information gathering, needs assessment, qualification
   - Keywords: business, company, challenges, goals, budget, marketing needs
   
3. **Maria** - Customer Support Representative
   - Routes: general inquiries, support issues, complaints, basic information
   - Keywords: help, question, problem, issue, services, information
   
Based on the message, respond with ONLY one of: sofia, carlos, or maria

Consider:
- The explicit intent of the message
- Previous conversation context
- Current conversation flow
- If an agent is already handling, continue with them unless explicitly requesting another

Examples:
- "I'd like to book a consultation" -> sofia
- "Tell me about your marketing services" -> maria  
- "We're a growing e-commerce business looking for help" -> carlos
- "I have a question about your pricing" -> maria
- "What times are available next week?" -> sofia
- "Our main challenge is lead generation" -> carlos"""
    
    async def route(self, state: ConversationState) -> str:
        """
        Determine which agent should handle the conversation
        
        Args:
            state: Current conversation state
            
        Returns:
            Agent name: "sofia", "carlos", or "maria"
        """
        try:
            # Check if there's an explicit next_agent set
            if state.get("next_agent"):
                logger.info(f"Routing to explicitly set agent: {state['next_agent']}")
                return state["next_agent"]
            
            # If no messages, default to Maria
            if not state.get("messages"):
                return "maria"
            
            # Get last few messages for context
            recent_messages = state["messages"][-5:]
            
            # Build prompt for routing decision
            routing_prompt = f"Current agent: {state.get('current_agent', 'none')}\n\n"
            routing_prompt += "Recent conversation:\n"
            
            for msg in recent_messages:
                role = "User" if msg.type == "human" else "Assistant"
                routing_prompt += f"{role}: {msg.content}\n"
            
            routing_prompt += "\nWhich agent should handle the next response?"
            
            # Get routing decision
            messages = [
                SystemMessage(content=self.system_prompt),
                SystemMessage(content=routing_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            agent_name = response.content.strip().lower()
            
            # Validate response
            valid_agents = ["sofia", "carlos", "maria"]
            if agent_name not in valid_agents:
                logger.warning(f"Invalid agent name from LLM: {agent_name}, defaulting to maria")
                agent_name = "maria"
            
            logger.info(f"Routing decision: {agent_name}")
            
            # Update analysis
            state["analysis"] = state.get("analysis", {})
            state["analysis"]["routing"] = {
                "selected_agent": agent_name,
                "previous_agent": state.get("current_agent"),
                "timestamp": datetime.now(pytz.UTC).isoformat(),
                "reason": f"Based on message intent and context"
            }
            
            return agent_name
            
        except Exception as e:
            logger.error(f"Error in orchestrator routing: {str(e)}", exc_info=True)
            # Default to Maria on error
            return "maria"
    
    async def should_continue(self, state: ConversationState) -> bool:
        """
        Determine if conversation should continue or end
        
        Args:
            state: Current conversation state
            
        Returns:
            True if should continue, False if conversation is complete
        """
        # Check if appointment was booked
        if state.get("appointment_status") == "booked":
            logger.info("Appointment booked, conversation can end")
            return False
            
        # Check if lead was qualified
        if state.get("qualification_status") in ["hot", "qualified"]:
            logger.info("Lead qualified, checking if appointment needed")
            # Continue if appointment might be needed
            return True
            
        # Check message count
        if len(state.get("messages", [])) > 20:
            logger.info("Long conversation, considering ending")
            # Check if last message seems like a conclusion
            last_message = state["messages"][-1].content.lower()
            conclusion_phrases = ["thank you", "thanks", "goodbye", "bye", "have a nice day"]
            if any(phrase in last_message for phrase in conclusion_phrases):
                return False
                
        # Default to continue
        return True


# Create orchestrator node for LangGraph
async def orchestrator_node(state: ConversationState) -> Dict[str, Any]:
    """Orchestrator node for agent routing"""
    orchestrator = Orchestrator()
    
    # Get routing decision
    selected_agent = await orchestrator.route(state)
    
    # Check if should continue
    should_continue = await orchestrator.should_continue(state)
    
    return {
        "next_agent": selected_agent,
        "should_continue": should_continue,
        "routing_timestamp": datetime.now(pytz.UTC).isoformat()
    }