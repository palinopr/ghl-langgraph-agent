"""
Sofia - Appointment Setting Agent
Professional appointment setter focused on booking consultations
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import pytz
from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..state.conversation_state import ConversationState
from ..tools.agent_tools import appointment_tools
from ..utils.simple_logger import get_logger
from ..config import get_settings

logger = get_logger("sofia")


class SofiaAgent:
    """Sofia - Professional appointment setting agent"""
    
    def __init__(self):
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,
            api_key=settings.openai_api_key
        ).bind_tools(appointment_tools)
        
        self.system_prompt = """You are Sofia, a professional appointment setter for Main Outlet Media.

Your primary goal is to book appointments for consultations while maintaining a professional, 
friendly tone. You should:

1. Warmly greet new contacts and introduce yourself
2. Gather necessary information (name, business type, main challenges)
3. Check for existing appointments before creating new ones
4. Offer available time slots with proper timezone indication (EDT/EST)
5. Confirm appointment details clearly
6. Only book ONE appointment per contact

Important guidelines:
- Always check existing appointments first
- Present times in a clear format (e.g., "Tuesday at 2:00 PM EDT")
- Be conversational but professional
- Focus on understanding their needs
- Create appointments only after confirming all details
- Add appropriate tags and notes after booking

Remember: You're representing a professional digital marketing agency. 
Be helpful, efficient, and respectful of the prospect's time."""
    
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """
        Process conversation state and generate response
        
        Args:
            state: Current conversation state
            
        Returns:
            Updated state with Sofia's response
        """
        try:
            # Extract contact info
            contact_id = state["contact_id"]
            messages = state["messages"]
            
            # Build conversation for LLM
            llm_messages = [SystemMessage(content=self.system_prompt)]
            
            # Add conversation history
            for msg in messages[-10:]:  # Last 10 messages for context
                llm_messages.append(msg)
            
            # Generate response with tools
            response = await self.llm.ainvoke(llm_messages)
            
            # Log the interaction
            logger.info(f"Sofia processing for contact {contact_id}")
            logger.debug(f"Generated response: {response.content[:100]}...")
            
            # Check if appointment was created
            appointment_created = False
            if hasattr(response, 'tool_calls'):
                for tool_call in response.tool_calls:
                    if tool_call['name'] == 'create_appointment':
                        appointment_created = True
                        state["appointment_status"] = "booked"
                        state["appointment_id"] = tool_call.get('id')
                        break
            
            # Update analysis
            analysis = {
                "agent": "sofia",
                "response_generated": True,
                "appointment_created": appointment_created,
                "tools_used": len(response.tool_calls) if hasattr(response, 'tool_calls') else 0,
                "timestamp": datetime.now(pytz.UTC).isoformat()
            }
            
            # Return updated state
            return {
                "messages": [response],
                "current_agent": "sofia",
                "agent_responses": state.get("agent_responses", []) + [{
                    "agent": "sofia",
                    "response": response.content,
                    "timestamp": datetime.now(pytz.UTC).isoformat()
                }],
                "analysis": {**state.get("analysis", {}), "sofia": analysis}
            }
            
        except Exception as e:
            logger.error(f"Error in Sofia agent: {str(e)}", exc_info=True)
            
            # Return error response
            error_message = AIMessage(
                content="I apologize, but I'm experiencing technical difficulties. "
                        "Please try again in a moment or contact support."
            )
            
            return {
                "messages": [error_message],
                "current_agent": "sofia",
                "error": str(e)
            }
    
    def should_handle(self, state: ConversationState) -> bool:
        """
        Determine if Sofia should handle this conversation
        
        Args:
            state: Current conversation state
            
        Returns:
            True if Sofia should handle, False otherwise
        """
        # Sofia handles appointment-related queries
        last_message = state["messages"][-1].content.lower() if state["messages"] else ""
        
        appointment_keywords = [
            "appointment", "book", "schedule", "consultation",
            "meeting", "call", "demo", "available", "calendar",
            "time", "slot", "talk", "discuss"
        ]
        
        # Check if message contains appointment-related keywords
        if any(keyword in last_message for keyword in appointment_keywords):
            return True
            
        # Check if we're in an appointment booking flow
        if state.get("current_agent") == "sofia" and not state.get("appointment_status"):
            return True
            
        # Check for existing appointment status
        if state.get("checking_appointments") or state.get("booking_appointment"):
            return True
            
        return False


# Create agent node for LangGraph
async def sofia_node(state: ConversationState) -> Dict[str, Any]:
    """Sofia agent node for LangGraph"""
    agent = SofiaAgent()
    return await agent.process(state)