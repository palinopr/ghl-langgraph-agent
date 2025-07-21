"""
Supervisor Brain - The Complete Decision Maker
This supervisor does EVERYTHING:
1. Receives data from Receptionist
2. Analyzes what changed
3. Calculates new score
4. Updates GHL (score, tags, notes)
5. Routes to appropriate agent
"""
from typing import Dict, Any, List, Optional, Union, Literal
from datetime import datetime
import re
from langchain_core.messages import AnyMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState
from langchain_core.tools import InjectedToolCallId

from app.tools.ghl_client import GHLClient
from app.state.conversation_state import ConversationState
from app.constants import FIELD_MAPPINGS
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model

logger = get_logger("supervisor_brain")


# Tool 1: Analyze and Score Lead
@tool
async def analyze_and_score_lead(
    state: Annotated[ConversationState, InjectedState]
) -> str:
    """
    Analyze the lead based on all available data and calculate score
    """
    # Get current message and context
    current_message = state.get("messages", [])[-1].content if state.get("messages") else ""
    contact_info = state.get("contact_info", {})
    previous_fields = state.get("previous_custom_fields", {})
    conversation_history = state.get("conversation_history", [])
    
    # Previous values
    previous_score = int(previous_fields.get("score", "0"))
    previous_name = previous_fields.get("name", "") or contact_info.get("firstName", "")
    previous_business = previous_fields.get("business_type", "NO_MENCIONADO")
    previous_budget = previous_fields.get("budget", "")
    
    # Extract new information using patterns
    extracted = {
        "name": None,
        "business_type": None,
        "budget": None,
        "email": contact_info.get("email"),
        "goal": None
    }
    
    # Spanish name patterns
    name_patterns = [
        r'\b(?:soy|me llamo|mi nombre es)\s+([A-Za-zÀ-ÿ]+)',
        r'\b([A-Za-zÀ-ÿ]+)\s+y\s+tengo',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, current_message, re.IGNORECASE)
        if match:
            extracted["name"] = match.group(1)
            break
    
    # Business patterns
    business_patterns = [
        r'\b(?:tengo un|tengo una|mi)\s+([A-Za-zÀ-ÿ]+(?:\s+[A-Za-zÀ-ÿ]+){0,2})',
        r'\b(restaurante|negocio|empresa|tienda|local|clínica)\b',
    ]
    for pattern in business_patterns:
        match = re.search(pattern, current_message, re.IGNORECASE)
        if match:
            extracted["business_type"] = match.group(1)
            break
    
    # Budget patterns and confirmation
    if current_message.lower() in ["si", "sí", "yes", "claro", "ok", "perfecto"]:
        # Check if last AI message mentioned $300
        for msg in conversation_history[-3:]:
            if msg.get("direction") == "outbound" and "$300" in msg.get("body", ""):
                extracted["budget"] = "300+"
                break
    
    # Budget amount patterns
    budget_patterns = [
        (r'como unos?\s*\$?\s*(\d+)', '{0}'),
        (r'aproximadamente\s*\$?\s*(\d+)', '{0}'),
        (r'\$?\s*(\d+)\s*(?:al mes|mensuales)', '{0}/month'),
    ]
    for pattern, format_str in budget_patterns:
        match = re.search(pattern, current_message, re.IGNORECASE)
        if match:
            extracted["budget"] = format_str.format(match.group(1))
            break
    
    # Calculate new score
    score_breakdown = {
        "base": 1,
        "has_name": 0,
        "has_business": 0,
        "has_budget": 0,
        "has_goal": 0,
        "budget_qualified": 0
    }
    
    # Use extracted or previous values
    final_name = extracted["name"] or previous_name
    final_business = extracted["business_type"] or previous_business
    final_budget = extracted["budget"] or previous_budget
    
    if final_name:
        score_breakdown["has_name"] = 2
    if final_business and final_business != "NO_MENCIONADO":
        score_breakdown["has_business"] = 1
    if final_budget:
        score_breakdown["has_budget"] = 2
        if "300" in str(final_budget):
            score_breakdown["budget_qualified"] = 1
            
    # Calculate total
    new_score = sum(score_breakdown.values())
    
    # Never decrease score
    final_score = max(new_score, previous_score)
    
    # Build analysis
    changes = []
    if extracted["name"] and not previous_name:
        changes.append(f"NEW: Name discovered - {extracted['name']}")
    if extracted["business_type"]:
        changes.append(f"NEW: Business - {extracted['business_type']}")
    if extracted["budget"]:
        changes.append(f"NEW: Budget - {extracted['budget']}")
    if final_score > previous_score:
        changes.append(f"SCORE: {previous_score} → {final_score}")
        
    analysis = f"""
LEAD ANALYSIS:
- Previous Score: {previous_score}
- New Score: {final_score}
- Name: {final_name or 'Unknown'}
- Business: {final_business}
- Budget: {final_budget or 'Not confirmed'}
- Email: {extracted['email'] or 'None'}

CHANGES DETECTED:
{chr(10).join(changes) if changes else 'No significant changes'}

QUALIFICATION CHECK:
- Has Name: {'YES' if final_name else 'NO'}
- Has Email: {'YES' if extracted['email'] else 'NO'}
- Budget $300+: {'YES' if '300' in str(final_budget) else 'NO'}
- Ready for appointment: {'YES' if all([final_name, extracted['email'], '300' in str(final_budget)]) else 'NO'}
"""
    
    # Store analysis in state
    state["lead_score"] = final_score
    state["extracted_data"] = {
        "name": final_name,
        "business_type": final_business,
        "budget": final_budget,
        "email": extracted["email"],
        "goal": extracted.get("goal")
    }
    state["score_reasoning"] = f"Score {final_score}: " + ", ".join([k for k, v in score_breakdown.items() if v > 0])
    
    return analysis


# Tool 2: Update GHL with Everything
@tool
async def update_ghl_complete(
    contact_id: str,
    state: Annotated[ConversationState, InjectedState]
) -> str:
    """
    Update GHL with score, tags, custom fields, and notes
    """
    try:
        ghl_client = GHLClient()
        
        # Get analysis results
        score = state.get("lead_score", 0)
        extracted = state.get("extracted_data", {})
        changes = state.get("what_changed", {}).get("changes", [])
        
        # 1. Prepare custom fields
        custom_fields = []
        
        # Always update score
        custom_fields.append({
            "id": FIELD_MAPPINGS["score"],
            "value": str(score)
        })
        
        # Update other fields if we have data
        if extracted.get("business_type"):
            custom_fields.append({
                "id": FIELD_MAPPINGS["business_type"],
                "value": extracted["business_type"]
            })
            
        if extracted.get("budget"):
            custom_fields.append({
                "id": FIELD_MAPPINGS["budget"],
                "value": extracted["budget"]
            })
            
        if extracted.get("name"):
            custom_fields.append({
                "id": FIELD_MAPPINGS.get("name", "TjB0I5iNfVwx3zyxZ9sW"),
                "value": extracted["name"]
            })
            
        # Set intent based on score
        intent = "LISTO_COMPRAR" if score >= 8 else "EVALUANDO" if score >= 5 else "EXPLORANDO"
        custom_fields.append({
            "id": FIELD_MAPPINGS["intent"],
            "value": intent
        })
        
        # Set urgency
        urgency = "ALTA" if score >= 8 else "NO_EXPRESADO"
        custom_fields.append({
            "id": FIELD_MAPPINGS["urgency_level"],
            "value": urgency
        })
        
        # 2. Update contact
        contact_updates = {"customFields": custom_fields}
        
        if extracted.get("email"):
            contact_updates["email"] = extracted["email"]
        if extracted.get("name") and not state.get("contact_info", {}).get("firstName"):
            contact_updates["firstName"] = extracted["name"]
            
        await ghl_client.update_contact(contact_id, contact_updates)
        
        # 3. Update tags based on score
        tags = []
        if score >= 8:
            tags = ["hot-lead", "ready-to-buy", "qualified"]
        elif score >= 5:
            tags = ["warm-lead", "needs-qualification"]
        else:
            tags = ["cold-lead", "needs-nurturing"]
            
        if extracted.get("budget") and "300" in str(extracted["budget"]):
            tags.append("budget-confirmed")
            
        await ghl_client.add_tags(contact_id, tags)
        
        # 4. Create note with analysis
        note = f"""Lead Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M')}
Score: {score}/10
Changes: {', '.join(changes) if changes else 'No changes'}
Current Status:
- Name: {extracted.get('name', 'Unknown')}
- Business: {extracted.get('business_type', 'Not specified')}
- Budget: {extracted.get('budget', 'Not confirmed')}
- Intent: {intent}
"""
        await ghl_client.create_note(contact_id, note)
        
        return f"""✅ GHL UPDATED:
- Score: {score}/10
- Tags: {', '.join(tags)}
- Fields: {len(custom_fields)} updated
- Note: Added analysis"""
        
    except Exception as e:
        logger.error(f"GHL update error: {e}")
        return f"❌ GHL Update failed: {str(e)}"


# Tool 3: Route to Agent with Context
@tool
async def route_to_agent(
    agent_name: Literal["sofia", "carlos", "maria"],
    reason: str,
    state: Annotated[ConversationState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Route to the appropriate agent with full context
    """
    # Build context for agent
    context = f"""
ROUTING TO {agent_name.upper()}
Reason: {reason}

LEAD SUMMARY:
- Name: {state.get('extracted_data', {}).get('name', 'Unknown')}
- Score: {state.get('lead_score', 0)}/10
- Business: {state.get('extracted_data', {}).get('business_type', 'Unknown')}
- Budget: {state.get('extracted_data', {}).get('budget', 'Not confirmed')}
- Email: {state.get('extracted_data', {}).get('email', 'None')}

CONVERSATION CONTEXT:
Last customer message: {state.get('messages', [])[-1].content if state.get('messages') else 'None'}
"""
    
    tool_msg = ToolMessage(
        content=context,
        tool_call_id=tool_call_id
    )
    
    return Command(
        goto=agent_name,
        update={
            "messages": state["messages"] + [tool_msg],
            "next_agent": agent_name,
            "supervisor_complete": True
        },
        graph=Command.PARENT
    )


def supervisor_brain_prompt(state: ConversationState) -> list[AnyMessage]:
    """
    Prompt for the all-in-one supervisor brain
    """
    contact_id = state.get("contact_id", "unknown")
    
    # Check if this is an escalation
    if state.get("needs_rerouting") and state.get("escalation_reason"):
        escalation_from = state.get("escalation_from", "unknown")
        escalation_reason = state.get("escalation_reason")
        escalation_details = state.get("escalation_details", "")
        routing_attempts = state.get("routing_attempts", 0)
        
        system_prompt = f"""You are the Supervisor Brain handling an ESCALATION.

🔴 ESCALATION RECEIVED:
- From Agent: {escalation_from}
- Reason: {escalation_reason}
- Details: {escalation_details}
- This is routing attempt {routing_attempts}/2

ESCALATION REASONS EXPLAINED:
- needs_appointment: Customer wants to schedule, route to Sofia
- needs_qualification: Customer needs business assessment, route to Carlos
- needs_support: Customer needs general help, route to Maria
- customer_confused: Re-analyze from scratch
- wrong_agent: Current agent can't help, find correct one

⚠️ You MUST use ALL THREE tools in this EXACT order:
1. analyze_and_score_lead() - Re-analyze the ENTIRE conversation
2. update_ghl_complete("{contact_id}") - Update any new information
3. route_to_agent() - Route to a DIFFERENT agent than {escalation_from}

IMPORTANT: 
- Do NOT route back to {escalation_from}
- If routing_attempts >= 2, this is the LAST chance
- Consider the escalation reason when choosing the new agent

START NOW with analyze_and_score_lead()"""
    else:
        # Normal first-time routing
        system_prompt = f"""You are the Supervisor Brain for Main Outlet Media.

⚠️ CRITICAL: You MUST use ALL THREE tools in this EXACT order:

1. FIRST: Use analyze_and_score_lead() to analyze the lead
2. SECOND: Use update_ghl_complete("{contact_id}") to save the score and data to GHL
3. THIRD: Use route_to_agent() to route to the appropriate agent

ROUTING LOGIC (use in step 3):
- Score 8-10 + Has Email + Budget $300+ → route_to_agent("sofia", "Qualified for appointment")
- Score 5-7 OR missing budget → route_to_agent("carlos", "Needs qualification")  
- Score 1-4 → route_to_agent("maria", "Cold lead support")

DO NOT skip any tools! DO NOT respond with text! Just execute the three tools in order.
The contact ID is: {contact_id}

START NOW with analyze_and_score_lead()"""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_supervisor_brain():
    """Create the all-in-one supervisor"""
    settings = get_settings()
    
    tools = [
        analyze_and_score_lead,
        update_ghl_complete,
        route_to_agent
    ]
    
    # Use explicit model initialization for proper tool binding
    model = create_openai_model(temperature=0.0)
    
    agent = create_react_agent(
        model=model,  # Use model instance, not string
        tools=tools,
        state_schema=ConversationState,
        prompt=supervisor_brain_prompt,
        name="supervisor_brain"
    )
    
    logger.info("Created Supervisor Brain - the complete decision maker")
    return agent


async def supervisor_brain_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Supervisor brain node that does everything
    """
    try:
        # Increment interaction counter to prevent loops
        interaction_count = state.get("interaction_count", 0) + 1
        if interaction_count > 3:
            logger.warning(f"Max interactions reached ({interaction_count}), ending workflow")
            return {
                "should_end": True,
                "interaction_count": interaction_count
            }
        
        # Create and run supervisor
        supervisor = create_supervisor_brain()
        result = await supervisor.ainvoke(state)
        
        # Extract the actual routing decision from the result
        # The create_react_agent returns a dict with messages
        messages = result.get("messages", [])
        
        # Check if a Command was executed by looking at state updates
        next_agent = result.get("next_agent")
        if not next_agent:
            # Look for it in the last message if it's a tool response
            last_message = messages[-1] if messages else None
            if hasattr(last_message, "content") and isinstance(last_message.content, str):
                # Extract agent name from routing context
                if "ROUTING TO SOFIA" in last_message.content:
                    next_agent = "sofia"
                elif "ROUTING TO CARLOS" in last_message.content:
                    next_agent = "carlos"
                elif "ROUTING TO MARIA" in last_message.content:
                    next_agent = "maria"
        
        # Return state updates for the workflow
        # Include all updates from the result (which has tool updates)
        return {
            "messages": messages,
            "supervisor_complete": True,
            "next_agent": next_agent or "maria",  # Default to maria if no routing found
            "lead_score": result.get("lead_score", state.get("lead_score", 0)),
            "extracted_data": result.get("extracted_data", state.get("extracted_data", {})),
            "score_reasoning": result.get("score_reasoning", ""),
            "interaction_count": interaction_count
        }
        
    except Exception as e:
        logger.error(f"Supervisor brain error: {e}")
        # Default to Maria on error
        return {
            "messages": [AIMessage(content="I encountered an error. Let me help you.", name="supervisor")],
            "error": str(e),
            "next_agent": "maria",
            "supervisor_complete": True,
            "interaction_count": state.get("interaction_count", 0) + 1
        }


# Export
__all__ = ["supervisor_brain_node", "create_supervisor_brain"]