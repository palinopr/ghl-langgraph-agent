"""
Maria Agent - STRICT VERSION with Conversation Enforcement
This version makes it IMPOSSIBLE for Maria to deviate from conversation flow
"""
from typing import Dict, Any, List, Annotated, Optional, Union
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from app.tools.agent_tools_v2 import (
    get_contact_details_v2,
    escalate_to_supervisor
)
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model
from app.utils.state_utils import filter_agent_result
from app.utils.conversation_enforcer import get_conversation_analysis, get_next_response
from app.agents.prompts.maria_strict_prompt import get_maria_strict_prompt

logger = get_logger("maria_strict")


class MariaState(AgentState):
    """Extended state for Maria agent"""
    contact_id: str
    contact_name: Optional[str]
    support_category: Optional[str]
    issue_resolved: bool = False
    needs_escalation: bool = False
    
    # Conversation enforcement fields
    conversation_stage: Optional[str]
    collected_data: Optional[Dict[str, Any]]
    allowed_response: Optional[str]
    conversation_analysis: Optional[Dict[str, Any]]


def maria_strict_prompt(state: MariaState) -> list[AnyMessage]:
    """
    STRICT prompt function that enforces conversation rules
    """
    # STEP 1: Analyze conversation with enforcer
    messages = state.get("messages", [])
    analysis = get_conversation_analysis(messages)
    
    # Log the analysis for debugging
    logger.info(f"Conversation Analysis: {analysis}")
    
    # STEP 2: Get current lead score
    lead_score = state.get("lead_score", 0)
    
    # STEP 3: Check if Maria should handle this
    if lead_score >= 5:
        logger.warning(f"Lead score {lead_score} too high for Maria!")
        analysis["next_action"] = "ESCALATE"
        analysis["allowed_response"] = "ESCALATE:wrong_agent:Score is 5+, I only handle 1-4"
    
    # STEP 4: Build context for prompt
    context = {
        "conversation_summary": f"""
- Stage: {analysis['current_stage'].value}
- Name: {analysis['collected_data']['name'] or 'WAITING'}
- Business: {analysis['collected_data']['business'] or 'WAITING'}  
- Problem: {analysis['collected_data']['problem'] or 'WAITING'}
- Budget OK: {'YES' if analysis['collected_data']['budget_confirmed'] else 'NO'}
- Next Action: {analysis['next_action']}
- Lead Score: {lead_score}/10
""",
        "next_action": analysis["next_action"],
        "allowed_response": analysis["allowed_response"],
        "forbidden_actions": analysis["forbidden_actions"],
        "current_stage": analysis["current_stage"].value
    }
    
    # STEP 5: Generate strict prompt
    system_prompt = get_maria_strict_prompt(context)
    
    # STEP 6: Add enforcement instructions
    enforcement_prompt = f"""
🔴 ENFORCEMENT MODE ACTIVE 🔴

YOU MUST RESPOND WITH EXACTLY THIS:
"{analysis['allowed_response']}"

If the response starts with "ESCALATE:", use the escalate_to_supervisor tool:
- Split by ":" to get: ESCALATE : reason : details
- Use the reason and details for the escalation

OTHERWISE, send the exact message provided above.

Current conversation stage: {analysis['current_stage'].value}
Customer is expecting answer for: {analysis.get('expecting_answer_for', 'nothing')}
    """
    
    # Combine prompts
    full_prompt = system_prompt + "\n\n" + enforcement_prompt
    
    # Return system message plus conversation
    return [{"role": "system", "content": full_prompt}] + messages


def create_maria_strict_agent():
    """Factory function to create STRICT Maria agent with enforcement"""
    settings = get_settings()
    
    # Use explicit model initialization
    model = create_openai_model(temperature=0.0)  # Zero temp for consistency
    
    # Tools for Maria - minimal set
    maria_tools = [
        get_contact_details_v2,
        escalate_to_supervisor  # Only escalation allowed
    ]
    
    # Add conversation analysis tool
    @tool
    def analyze_conversation_state(
        state: Annotated[MariaState, InjectedState]
    ) -> str:
        """
        Analyze conversation to determine exact state and next action
        ALWAYS call this before responding!
        """
        messages = state.get("messages", [])
        analysis = get_conversation_analysis(messages)
        
        # Store in state for prompt access
        state["conversation_analysis"] = analysis
        state["allowed_response"] = analysis["allowed_response"]
        state["conversation_stage"] = analysis["current_stage"].value
        
        return f"""
CONVERSATION ANALYSIS COMPLETE:
- Current Stage: {analysis['current_stage'].value}
- Next Action: {analysis['next_action']}
- Allowed Response: {analysis['allowed_response']}

YOU MUST USE THIS EXACT RESPONSE!
"""
    
    # Add the analysis tool
    maria_tools.insert(0, analyze_conversation_state)
    
    agent = create_react_agent(
        model=model,
        tools=maria_tools,
        state_schema=MariaState,
        prompt=maria_strict_prompt,
        name="maria_strict"
    )
    
    logger.info("Created STRICT Maria agent with conversation enforcement")
    return agent


async def maria_strict_node(state: Dict[str, Any]) -> Union[Command, Dict[str, Any]]:
    """
    Maria node with STRICT conversation enforcement
    """
    try:
        # Pre-check: Should Maria handle this?
        lead_score = state.get("lead_score", 0)
        if lead_score >= 5:
            logger.info(f"Lead score {lead_score} too high, escalating immediately")
            return {
                "messages": state["messages"] + [
                    HumanMessage(content="[SYSTEM: Escalating due to high lead score]")
                ],
                "escalation_reason": "wrong_agent",
                "escalation_details": f"Lead score {lead_score} is too high for Maria (handles 1-4)",
                "escalation_from": "maria",
                "needs_rerouting": True
            }
        
        # Create and run the agent
        agent = create_maria_strict_agent()
        result = await agent.ainvoke(state)
        
        # Log the interaction
        logger.info(f"Maria processed message for contact {state.get('contact_id')}")
        
        # Check if escalation was triggered
        if result.get("needs_rerouting"):
            logger.info("Maria triggered escalation")
            
        # Filter and return result
        return filter_agent_result(result)
        
    except Exception as e:
        logger.error(f"Error in Maria strict agent: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "messages": state["messages"] + [{
                "role": "assistant",
                "content": "I apologize, but I'm experiencing technical difficulties. Please try again."
            }],
            "needs_escalation": True,
            "escalation_reason": "error",
            "escalation_details": str(e)
        }


# Export
__all__ = ["maria_strict_node", "create_maria_strict_agent", "MariaState"]