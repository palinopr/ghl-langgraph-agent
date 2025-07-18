"""
Maria - Customer Support Agent (MODERNIZED VERSION)
Using create_react_agent and latest LangGraph patterns
"""
from typing import Dict, Any, List, Annotated, Optional, Union
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from app.tools.agent_tools_v2 import support_tools_v2
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("maria_v2")


class MariaState(AgentState):
    """Extended state for Maria agent"""
    contact_id: str
    contact_name: Optional[str]
    support_category: Optional[str]
    issue_resolved: bool = False
    needs_escalation: bool = False


def maria_prompt(state: MariaState) -> list[AnyMessage]:
    """
    Dynamic prompt function for Maria that includes context from state
    """
    # Build context from state
    contact_name = state.get("contact_name", "there")
    previous_agent = state.get("current_agent")
    
    # Customize based on context
    context = ""
    if contact_name and contact_name != "there":
        context = f"\nYou are speaking with {contact_name}."
    if previous_agent and previous_agent != "maria":
        context += f"\nThey were previously speaking with {previous_agent}."
    
    system_prompt = f"""You are Maria, a friendly customer support representative for Main Outlet Media.

Your role is to provide helpful information and initial support to all inquiries.
You should:

1. Greet contacts warmly and professionally
2. Answer general questions about Main Outlet Media services
3. Provide basic information about digital marketing solutions
4. Help with technical issues or concerns
5. Route to specialists when appropriate
6. Ensure every contact feels heard and valued

Main Outlet Media Services:
- Digital Marketing Strategy
- Social Media Management
- SEO & Content Marketing
- Paid Advertising (Google, Facebook, etc.)
- Website Design & Development
- Email Marketing Campaigns
- Analytics & Reporting

Important guidelines:
- Be empathetic and patient with all inquiries
- Use simple, clear language (avoid jargon)
- Save important context with save_conversation_context
- Transfer to Sofia if they want to schedule a consultation
- Transfer to Carlos if they need detailed business assessment
- Search conversation history for context when needed
- Always maintain a positive, helpful attitude
{context}

Remember: First impressions matter. You're often the first point of contact."""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_maria_agent():
    """Factory function to create Maria agent"""
    settings = get_settings()
    
    agent = create_react_agent(
        model=f"openai:{settings.openai_model}",
        tools=support_tools_v2,
        state_schema=MariaState,
        prompt=maria_prompt,
        name="maria"
    )
    
    logger.info("Created Maria agent with create_react_agent")
    return agent


async def maria_node_v2(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Maria agent node for LangGraph - modernized version
    Returns Command for routing or state updates
    """
    try:
        # Create the agent
        agent = create_maria_agent()
        
        # Invoke the agent
        result = await agent.ainvoke(state)
        
        # Log the interaction
        logger.info(f"Maria processed message for contact {state.get('contact_id')}")
        
        # Analyze the conversation for routing needs
        messages_text = str(result.get("messages", [])).lower()
        
        # Check for appointment intent
        appointment_keywords = ["appointment", "schedule", "book", "consultation", "meeting"]
        if any(keyword in messages_text for keyword in appointment_keywords):
            logger.info("Detected appointment intent, considering routing to Sofia")
            result["needs_escalation"] = True
            result["support_category"] = "appointment_request"
            
            # Only route if Maria hasn't already handled it
            if "transfer" not in messages_text:
                return Command(
                    goto="sofia",
                    update={
                        **result,
                        "next_agent": "sofia",
                        "routing_reason": "Appointment request detected"
                    }
                )
        
        # Check for business/qualification needs
        business_keywords = ["business", "company", "budget", "services", "pricing", "marketing needs"]
        if any(keyword in messages_text for keyword in business_keywords):
            logger.info("Detected business qualification need")
            result["support_category"] = "business_inquiry"
            
            # Only route if complex enough
            if messages_text.count(" ") > 20:  # Longer, detailed inquiry
                return Command(
                    goto="carlos",
                    update={
                        **result,
                        "next_agent": "carlos",
                        "routing_reason": "Detailed business inquiry"
                    }
                )
        
        # Check if issue is resolved
        resolution_phrases = ["thank you", "that helps", "perfect", "great", "understood"]
        if any(phrase in messages_text for phrase in resolution_phrases):
            result["issue_resolved"] = True
            logger.info("Issue appears to be resolved")
        
        # Continue with Maria by default
        return result
        
    except Exception as e:
        logger.error(f"Error in Maria agent: {str(e)}", exc_info=True)
        
        # Return error state
        return {
            "error": str(e),
            "messages": state["messages"] + [{
                "role": "assistant",
                "content": "I apologize, but I'm experiencing technical difficulties. "
                          "Please try again in a moment or contact us directly at support@mainoutletmedia.com"
            }],
            "issue_resolved": False
        }


# Standalone Maria agent instance
maria_agent = create_maria_agent()


__all__ = ["maria_node_v2", "maria_agent", "create_maria_agent", "MariaState"]