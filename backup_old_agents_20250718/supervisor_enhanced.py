"""
Enhanced Supervisor - The Brain of the Operation
Like n8n, this supervisor:
1. Loads EVERYTHING from GHL first
2. Analyzes what changed
3. Updates GHL with new data
4. Routes with full context
"""
from typing import Dict, Any, List, Optional, Union, Literal
from datetime import datetime
from langchain_core.messages import AnyMessage, AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from typing_extensions import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langgraph.types import InjectedState, InjectedToolCallId

from app.tools.ghl_client import GHLClient
from app.state.conversation_state import ConversationState
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.constants import FIELD_MAPPINGS
from app.utils.model_factory import create_openai_model

logger = get_logger("supervisor_enhanced")


class SupervisorState(ConversationState):
    """Enhanced state with full GHL context"""
    # GHL loaded data
    ghl_contact_data: Optional[Dict[str, Any]]
    ghl_conversation_history: Optional[List[Dict[str, Any]]]
    ghl_notes: Optional[str]
    previous_custom_fields: Optional[Dict[str, Any]]
    
    # Analysis results
    what_changed: Optional[Dict[str, Any]]
    score_delta: Optional[int]
    new_information: Optional[Dict[str, Any]]
    
    # remaining_steps is managed internally by create_react_agent


# Tool 1: Load EVERYTHING from GHL
@tool
async def load_full_ghl_context(
    contact_id: str,
    state: Annotated[SupervisorState, InjectedState]
) -> str:
    """
    Load complete contact data, custom fields, conversation history, and notes from GHL
    """
    try:
        ghl_client = GHLClient()
        
        # 1. Get full contact details
        contact = await ghl_client.get_contact_details(contact_id)
        if not contact:
            return "Failed to load contact from GHL"
            
        # 2. Extract custom fields into a dict
        custom_fields = {}
        for field in contact.get("customFields", []):
            field_id = field.get("id")
            field_value = field.get("value")
            # Map to human-readable names
            for name, id in FIELD_MAPPINGS.items():
                if id == field_id:
                    custom_fields[name] = field_value
                    break
                    
        # 3. Get conversation history
        conversations = await ghl_client.get_conversations(contact_id)
        
        # 4. Get recent messages
        messages = []
        if conversations and len(conversations) > 0:
            # Get messages from the most recent conversation
            conv_id = conversations[0].get("id")
            conv_messages = await ghl_client.get_conversation_messages(conv_id)
            messages = conv_messages[-20:] if conv_messages else []  # Last 20 messages
            
        # 5. Build context summary
        context_summary = f"""
CONTACT LOADED FROM GHL:
- Name: {contact.get('firstName', '')} {contact.get('lastName', '')}
- Email: {contact.get('email', 'none')}
- Phone: {contact.get('phone', '')}
- Tags: {', '.join(contact.get('tags', []))}

CUSTOM FIELDS:
- Score: {custom_fields.get('score', '0')}
- Business: {custom_fields.get('business_type', 'unknown')}
- Budget: {custom_fields.get('budget', 'not confirmed')}
- Intent: {custom_fields.get('intent', 'EXPLORANDO')}
- Goal: {custom_fields.get('goal', 'not specified')}
- Urgency: {custom_fields.get('urgency_level', 'NO_EXPRESADO')}

RECENT CONVERSATION ({len(messages)} messages):
"""
        # Add recent messages
        for msg in messages[-5:]:  # Show last 5
            sender = "Customer" if msg.get("direction") == "inbound" else "AI"
            context_summary += f"\n{sender}: {msg.get('body', '')[:100]}..."
            
        # Update state with loaded data
        state["ghl_contact_data"] = contact
        state["previous_custom_fields"] = custom_fields
        state["ghl_conversation_history"] = messages
        
        return context_summary
        
    except Exception as e:
        logger.error(f"Error loading GHL context: {e}")
        return f"Error loading GHL data: {str(e)}"


# Tool 2: Analyze what changed
@tool
async def analyze_changes(
    current_message: str,
    state: Annotated[SupervisorState, InjectedState]
) -> str:
    """
    Analyze what changed compared to previous data
    """
    previous = state.get("previous_custom_fields", {})
    extracted = state.get("extracted_data", {})
    
    changes = []
    
    # Check for new information
    if extracted.get("name") and not previous.get("name"):
        changes.append(f"NEW: Name discovered - {extracted['name']}")
        
    if extracted.get("business_type") and extracted["business_type"] != previous.get("business_type", "NO_MENCIONADO"):
        changes.append(f"NEW: Business type - {extracted['business_type']}")
        
    if extracted.get("budget") and extracted["budget"] != previous.get("budget"):
        changes.append(f"NEW: Budget confirmed - {extracted['budget']}")
        
    if extracted.get("email") and not previous.get("email"):
        changes.append(f"NEW: Email provided - {extracted['email']}")
        
    # Check for score changes
    old_score = int(previous.get("score", "0"))
    new_score = state.get("lead_score", 0)
    if new_score > old_score:
        changes.append(f"SCORE UP: {old_score} → {new_score} (+{new_score - old_score})")
        
    # Build analysis
    if changes:
        analysis = "CHANGES DETECTED:\n" + "\n".join(changes)
    else:
        analysis = "NO SIGNIFICANT CHANGES"
        
    # Add reasoning for routing
    analysis += f"\n\nROUTING ANALYSIS:\n"
    analysis += f"- Current Score: {new_score}\n"
    analysis += f"- Has Email: {'YES' if extracted.get('email') or previous.get('email') else 'NO'}\n"
    analysis += f"- Budget $300+: {'CONFIRMED' if '$300' in str(extracted.get('budget', '')) or '300' in str(extracted.get('budget', '')) else 'NOT CONFIRMED'}\n"
    
    state["what_changed"] = {"changes": changes, "score_delta": new_score - old_score}
    
    return analysis


# Tool 3: Update GHL with analysis
@tool
async def update_ghl_with_analysis(
    contact_id: str,
    updates: Dict[str, Any],
    state: Annotated[SupervisorState, InjectedState]
) -> str:
    """
    Update GHL with new score, tags, notes, and custom fields
    """
    try:
        ghl_client = GHLClient()
        
        # 1. Prepare custom fields update
        custom_fields = []
        field_updates = updates.get("fields", {})
        
        for field_name, value in field_updates.items():
            if field_name in FIELD_MAPPINGS and value is not None:
                custom_fields.append({
                    "id": FIELD_MAPPINGS[field_name],
                    "value": str(value)
                })
                
        # 2. Update contact
        contact_updates = {}
        if custom_fields:
            contact_updates["customFields"] = custom_fields
            
        if updates.get("email"):
            contact_updates["email"] = updates["email"]
            
        if updates.get("firstName"):
            contact_updates["firstName"] = updates["firstName"]
            
        result = await ghl_client.update_contact(contact_id, contact_updates)
        
        # 3. Update tags
        if updates.get("tags"):
            await ghl_client.add_tags(contact_id, updates["tags"])
            
        # 4. Add note with analysis
        if updates.get("note"):
            await ghl_client.create_note(contact_id, updates["note"])
            
        return f"✅ GHL Updated: {len(custom_fields)} fields, {len(updates.get('tags', []))} tags"
        
    except Exception as e:
        logger.error(f"Error updating GHL: {e}")
        return f"❌ GHL Update failed: {str(e)}"


# Tool 4: Route with context
@tool
async def route_to_agent_with_context(
    agent_name: Literal["sofia", "carlos", "maria"],
    routing_reason: str,
    state: Annotated[SupervisorState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command:
    """
    Route to agent with full context loaded
    """
    # Build context message for agent
    context = state.get("ghl_contact_data", {})
    custom_fields = state.get("previous_custom_fields", {})
    
    context_message = f"""
ROUTING TO {agent_name.upper()}
Reason: {routing_reason}

FULL CONTEXT:
- Name: {context.get('firstName', 'Unknown')} {context.get('lastName', '')}
- Score: {state.get('lead_score', 0)}/10
- Business: {custom_fields.get('business_type', 'unknown')}
- Budget: {custom_fields.get('budget', 'not confirmed')}
- Email: {context.get('email', 'none')}
- Recent Activity: {state.get('what_changed', {}).get('changes', ['No changes'])[0] if state.get('what_changed', {}).get('changes') else 'No changes'}
"""
    
    # Create tool message
    tool_msg = ToolMessage(
        content=context_message,
        tool_call_id=tool_call_id
    )
    
    # Return command to route
    return Command(
        goto=agent_name,
        update={
            "messages": state["messages"] + [tool_msg],
            "context_loaded": True,
            "full_context": {
                "contact": context,
                "custom_fields": custom_fields,
                "conversation_history": state.get("ghl_conversation_history", [])
            }
        },
        graph=Command.PARENT
    )


def supervisor_enhanced_prompt(state: SupervisorState) -> list[AnyMessage]:
    """
    Enhanced supervisor prompt that knows to load data first
    """
    system_prompt = """You are the intelligent supervisor for Main Outlet Media.

YOUR WORKFLOW (MANDATORY ORDER):
1. FIRST: Use load_full_ghl_context to get ALL data from GHL
2. SECOND: Use analyze_changes to understand what's new
3. THIRD: Use update_ghl_with_analysis to save changes
4. FOURTH: Use route_to_agent_with_context to send to appropriate agent

ROUTING RULES (after loading context):
- Score 8-10 + Email + Budget $300+ → Sofia (appointments)
- Score 5-7 OR missing budget → Carlos (qualification)
- Score 1-4 → Maria (support)

IMPORTANT: You MUST load GHL context before making any decisions!"""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_enhanced_supervisor():
    """Create supervisor that loads context first"""
    settings = get_settings()
    
    tools = [
        load_full_ghl_context,
        analyze_changes,
        update_ghl_with_analysis,
        route_to_agent_with_context
    ]
    
    # Use explicit model initialization for proper tool binding
    model = create_openai_model(temperature=0.0)
    
    agent = create_react_agent(
        model=model,  # Use model instance, not string
        tools=tools,
        state_schema=SupervisorState,
        prompt=supervisor_enhanced_prompt,
        name="supervisor_enhanced"
    )
    
    logger.info("Created ENHANCED supervisor with GHL loading")
    return agent


# Export
__all__ = ["create_enhanced_supervisor", "SupervisorState"]