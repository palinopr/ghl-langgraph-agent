"""
Carlos - Lead Qualification Agent
Professional lead qualifier focused on gathering business information
"""
from typing import Dict, Any
from datetime import datetime
import pytz
from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..state.conversation_state import ConversationState
from ..tools.agent_tools import lead_qualification_tools
from ..utils.simple_logger import get_logger
from ..config import get_settings

logger = get_logger("carlos")


class CarlosAgent:
    """Carlos - Professional lead qualification agent"""
    
    def __init__(self):
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.4,
            api_key=settings.openai_api_key
        ).bind_tools(lead_qualification_tools)
        
        self.system_prompt = """You are Carlos, a professional lead qualification specialist for Main Outlet Media.

Your role is to gather important business information and qualify leads by understanding:

1. Business name and industry
2. Current marketing challenges
3. Business goals and objectives
4. Budget range for marketing
5. Timeline for implementation
6. Decision-making process

Guidelines:
- Be professional yet conversational
- Ask one or two questions at a time
- Show genuine interest in their business
- Update contact custom fields with gathered information
- Add relevant tags based on their industry and needs
- Create detailed notes summarizing the qualification

Important: 
- Focus on understanding their pain points
- Don't be pushy about budget, but try to understand their investment capacity
- Qualify leads as Hot, Warm, or Cold based on:
  * Hot: Ready to move forward, has budget, clear need
  * Warm: Interested but needs nurturing, timeline 1-3 months
  * Cold: Not ready, just researching, timeline 3+ months

Always maintain a helpful, consultative approach."""
    
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """
        Process conversation state and generate response
        
        Args:
            state: Current conversation state
            
        Returns:
            Updated state with Carlos's response
        """
        try:
            contact_id = state["contact_id"]
            messages = state["messages"]
            
            # Build conversation for LLM
            llm_messages = [SystemMessage(content=self.system_prompt)]
            
            # Add conversation history
            for msg in messages[-10:]:
                llm_messages.append(msg)
            
            # Generate response with tools
            response = await self.llm.ainvoke(llm_messages)
            
            logger.info(f"Carlos processing for contact {contact_id}")
            logger.debug(f"Generated response: {response.content[:100]}...")
            
            # Analyze qualification status
            lead_qualified = False
            qualification_score = "unknown"
            
            if hasattr(response, 'tool_calls'):
                for tool_call in response.tool_calls:
                    if tool_call['name'] == 'add_contact_tags':
                        tags = tool_call.get('args', {}).get('tags', [])
                        if any(tag in ['hot-lead', 'warm-lead', 'qualified'] for tag in tags):
                            lead_qualified = True
                            if 'hot-lead' in tags:
                                qualification_score = "hot"
                            elif 'warm-lead' in tags:
                                qualification_score = "warm"
                            else:
                                qualification_score = "qualified"
            
            # Update analysis
            analysis = {
                "agent": "carlos",
                "response_generated": True,
                "lead_qualified": lead_qualified,
                "qualification_score": qualification_score,
                "tools_used": len(response.tool_calls) if hasattr(response, 'tool_calls') else 0,
                "timestamp": datetime.now(pytz.UTC).isoformat()
            }
            
            # Update qualification status
            qualification_update = {}
            if lead_qualified:
                qualification_update["qualification_status"] = qualification_score
                qualification_update["qualified_at"] = datetime.now(pytz.UTC).isoformat()
            
            return {
                "messages": [response],
                "current_agent": "carlos",
                "agent_responses": state.get("agent_responses", []) + [{
                    "agent": "carlos",
                    "response": response.content,
                    "timestamp": datetime.now(pytz.UTC).isoformat()
                }],
                "analysis": {**state.get("analysis", {}), "carlos": analysis},
                **qualification_update
            }
            
        except Exception as e:
            logger.error(f"Error in Carlos agent: {str(e)}", exc_info=True)
            
            error_message = AIMessage(
                content="I apologize for the technical issue. Let me try to help you another way. "
                        "Could you tell me about your business and what you're looking to achieve?"
            )
            
            return {
                "messages": [error_message],
                "current_agent": "carlos",
                "error": str(e)
            }
    
    def should_handle(self, state: ConversationState) -> bool:
        """
        Determine if Carlos should handle this conversation
        
        Args:
            state: Current conversation state
            
        Returns:
            True if Carlos should handle, False otherwise
        """
        last_message = state["messages"][-1].content.lower() if state["messages"] else ""
        
        # Carlos handles business and qualification queries
        qualification_keywords = [
            "business", "company", "marketing", "challenge", "problem",
            "goal", "objective", "budget", "invest", "cost", "price",
            "timeline", "when", "decision", "industry", "service",
            "help", "need", "looking for", "interested"
        ]
        
        # Check if message contains qualification keywords
        if any(keyword in last_message for keyword in qualification_keywords):
            # But not if it's clearly appointment-related
            appointment_keywords = ["book", "schedule", "appointment", "calendar"]
            if not any(keyword in last_message for keyword in appointment_keywords):
                return True
        
        # Continue if already in qualification flow
        if state.get("current_agent") == "carlos" and not state.get("qualification_status"):
            return True
            
        # Handle if specifically asked about services or pricing
        if "what do you do" in last_message or "services" in last_message:
            return True
            
        return False


# Create agent node for LangGraph
async def carlos_node(state: ConversationState) -> Dict[str, Any]:
    """Carlos agent node for LangGraph"""
    agent = CarlosAgent()
    return await agent.process(state)