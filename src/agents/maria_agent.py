"""
Maria - Customer Support Agent
Friendly support agent for general inquiries and assistance
"""
from typing import Dict, Any
from datetime import datetime
import pytz
from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from ..state.conversation_state import ConversationState
from ..tools.agent_tools import support_tools
from ..utils.simple_logger import get_logger
from ..config import get_settings

logger = get_logger("maria")


class MariaAgent:
    """Maria - Friendly customer support agent"""
    
    def __init__(self):
        settings = get_settings()
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.5,
            api_key=settings.openai_api_key
        ).bind_tools(support_tools)
        
        self.system_prompt = """You are Maria, a friendly customer support representative for Main Outlet Media.

Your role is to provide helpful, empathetic support for general inquiries including:

1. Answering questions about our services
2. Providing general information
3. Handling complaints or concerns
4. Offering assistance with technical issues
5. Routing complex issues appropriately

Guidelines:
- Be warm, friendly, and empathetic
- Use a conversational, approachable tone
- Show genuine concern for their needs
- Provide clear, helpful information
- Create notes for important interactions
- Add tags for issue categorization

Our services include:
- Social media marketing and management
- Website design and development
- Search engine optimization (SEO)
- Pay-per-click advertising (PPC)
- Content creation and marketing
- Email marketing campaigns
- Brand strategy and consulting

Important:
- If someone wants to book an appointment, acknowledge this and let them know Sofia will help
- If someone wants to discuss their business needs, mention Carlos can assist
- Always maintain a positive, helpful attitude
- Never make promises about specific results
- Focus on being helpful and building rapport"""
    
    async def process(self, state: ConversationState) -> Dict[str, Any]:
        """
        Process conversation state and generate response
        
        Args:
            state: Current conversation state
            
        Returns:
            Updated state with Maria's response
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
            
            logger.info(f"Maria processing for contact {contact_id}")
            logger.debug(f"Generated response: {response.content[:100]}...")
            
            # Analyze if routing is needed
            needs_routing = False
            route_to = None
            
            response_lower = response.content.lower()
            if "sofia" in response_lower and ("appointment" in response_lower or "book" in response_lower):
                needs_routing = True
                route_to = "sofia"
            elif "carlos" in response_lower and ("business" in response_lower or "needs" in response_lower):
                needs_routing = True
                route_to = "carlos"
            
            # Update analysis
            analysis = {
                "agent": "maria",
                "response_generated": True,
                "needs_routing": needs_routing,
                "route_to": route_to,
                "tools_used": len(response.tool_calls) if hasattr(response, 'tool_calls') else 0,
                "timestamp": datetime.now(pytz.UTC).isoformat()
            }
            
            # Prepare state update
            state_update = {
                "messages": [response],
                "current_agent": "maria",
                "agent_responses": state.get("agent_responses", []) + [{
                    "agent": "maria",
                    "response": response.content,
                    "timestamp": datetime.now(pytz.UTC).isoformat()
                }],
                "analysis": {**state.get("analysis", {}), "maria": analysis}
            }
            
            # Add routing information if needed
            if needs_routing and route_to:
                state_update["next_agent"] = route_to
                state_update["routing_reason"] = f"Customer needs assistance with {route_to} specialty"
            
            return state_update
            
        except Exception as e:
            logger.error(f"Error in Maria agent: {str(e)}", exc_info=True)
            
            error_message = AIMessage(
                content="I apologize for the inconvenience. I'm having a technical issue, "
                        "but I'm here to help! What can I assist you with today?"
            )
            
            return {
                "messages": [error_message],
                "current_agent": "maria",
                "error": str(e)
            }
    
    def should_handle(self, state: ConversationState) -> bool:
        """
        Determine if Maria should handle this conversation
        
        Args:
            state: Current conversation state
            
        Returns:
            True if Maria should handle, False otherwise
        """
        # Maria is the default agent for general inquiries
        last_message = state["messages"][-1].content.lower() if state["messages"] else ""
        
        # Maria handles greetings and general queries
        general_keywords = [
            "hello", "hi", "hey", "good morning", "good afternoon",
            "help", "question", "information", "tell me", "what",
            "how", "why", "when", "where", "who", "services",
            "complaint", "issue", "problem", "concern", "feedback",
            "thank", "thanks", "appreciate"
        ]
        
        # Check for general inquiry keywords
        if any(keyword in last_message for keyword in general_keywords):
            # But not if it's clearly for another agent
            if not any(agent in ["appointment", "book", "schedule", "business needs", "qualify"] 
                      for agent in last_message.split()):
                return True
        
        # Default handler if no other agent claims it
        if not state.get("current_agent"):
            return True
            
        # Continue if already handling
        if state.get("current_agent") == "maria":
            return True
            
        return False


# Create agent node for LangGraph
async def maria_node(state: ConversationState) -> Dict[str, Any]:
    """Maria agent node for LangGraph"""
    agent = MariaAgent()
    return await agent.process(state)