"""
Receptionist Agent - The Data Gatherer
Like n8n's "Get Contact from GHL" + "Edit Fields" nodes
This agent's ONLY job is to gather ALL data before processing
"""
from typing import Dict, Any, List, Optional
from langchain_core.messages import AnyMessage, AIMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from typing_extensions import Annotated
from langgraph.prebuilt import InjectedState

from app.tools.ghl_client import GHLClient
from app.state.conversation_state import ConversationState
from app.constants import FIELD_MAPPINGS
from app.utils.simple_logger import get_logger
from app.config import get_settings
from app.utils.model_factory import create_openai_model

logger = get_logger("receptionist_agent")


# Tool 1: Get full contact data
@tool
async def get_full_contact_data(
    state: Annotated[ConversationState, InjectedState]
) -> str:
    """
    Get complete contact information from GHL including all custom fields
    """
    # Get contact_id from state
    contact_id = state.get("contact_id")
    if not contact_id:
        return "Error: No contact_id found in state"
    try:
        ghl_client = GHLClient()
        contact = await ghl_client.get_contact_details(contact_id)
        
        if not contact:
            return "Failed to load contact data"
            
        # Extract all data
        info = f"""
CONTACT LOADED:
- ID: {contact_id}
- Name: {contact.get('firstName', '')} {contact.get('lastName', '')}
- Phone: {contact.get('phone', '')}
- Email: {contact.get('email', 'none')}
- Type: {contact.get('type', 'lead')}
- Tags: {', '.join(contact.get('tags', []))}
- Date Added: {contact.get('dateAdded', '')}

CUSTOM FIELDS:"""
        
        # Extract custom fields
        custom_fields = {}
        for field in contact.get('customFields', []):
            field_id = field.get('id')
            field_value = field.get('value', '')
            
            # Map to readable names
            field_name = field_id
            for name, mapped_id in FIELD_MAPPINGS.items():
                if mapped_id == field_id:
                    field_name = name
                    custom_fields[name] = field_value
                    break
                    
            info += f"\n- {field_name}: {field_value}"
        
        # Update state with loaded data
        state["contact_info"] = contact
        state["previous_custom_fields"] = custom_fields
        
        return info
        
    except Exception as e:
        logger.error(f"Error loading contact: {e}")
        return f"Error: {str(e)}"


# Tool 2: Get conversation history
@tool
async def get_conversation_history(
    state: Annotated[ConversationState, InjectedState]
) -> str:
    """
    Load conversation history from GHL
    """
    # Get contact_id from state
    contact_id = state.get("contact_id")
    if not contact_id:
        return "Error: No contact_id found in state"
    try:
        ghl_client = GHLClient()
        
        # Get conversations
        conversations = await ghl_client.get_conversations(contact_id)
        if not conversations:
            return "No conversation history found"
            
        # Get messages from most recent conversation
        conv_id = conversations[0].get('id')
        messages = await ghl_client.get_conversation_messages(conv_id)
        
        if not messages:
            return "No messages in conversation"
            
        # Format recent messages
        history = f"CONVERSATION HISTORY ({len(messages)} messages):\n"
        history += "Last 10 messages:\n"
        
        for msg in messages[-10:]:
            sender = "Customer" if msg.get('direction') == 'inbound' else 'AI'
            timestamp = msg.get('dateAdded', '')
            body = msg.get('body', '')[:100]
            history += f"\n[{timestamp}] {sender}: {body}..."
            
        # Store in state
        state["conversation_history"] = messages
        
        return history
        
    except Exception as e:
        logger.error(f"Error loading history: {e}")
        return f"Error loading history: {str(e)}"


# Tool 3: Prepare complete context
@tool
async def prepare_complete_context(
    state: Annotated[ConversationState, InjectedState]
) -> str:
    """
    Prepare a complete context summary for the supervisor
    """
    contact = state.get("contact_info", {})
    custom_fields = state.get("previous_custom_fields", {})
    history = state.get("conversation_history", [])
    current_message = state.get("messages", [])[-1].content if state.get("messages") else ""
    
    context = f"""
COMPLETE CONTEXT PREPARED:

CURRENT MESSAGE: {current_message}

CONTACT SUMMARY:
- Name: {contact.get('firstName', 'Unknown')} {contact.get('lastName', '')}
- Score: {custom_fields.get('score', '0')}/10
- Business: {custom_fields.get('business_type', 'not specified')}
- Budget: {custom_fields.get('budget', 'not confirmed')}
- Intent: {custom_fields.get('intent', 'EXPLORANDO')}
- Email: {contact.get('email', 'none')}

QUALIFICATION STATUS:
- Has Name: {'YES' if contact.get('firstName') else 'NO'}
- Has Email: {'YES' if contact.get('email') else 'NO'}
- Budget $300+: {'YES' if '300' in str(custom_fields.get('budget', '')) else 'NO'}

RECENT ACTIVITY:
"""
    
    # Add last 3 messages for context
    for msg in history[-3:]:
        if msg.get('body'):
            sender = "Customer" if msg.get('direction') == 'inbound' else 'AI'
            context += f"\n{sender}: {msg['body'][:100]}..."
            
    context += f"\n\nREADY FOR PROCESSING: All data loaded successfully"
    
    # Mark as ready
    state["data_loaded"] = True
    state["receptionist_complete"] = True
    
    return context


def receptionist_prompt(state: Dict[str, Any]) -> list[AnyMessage]:
    """
    Simple prompt for receptionist - just gather data
    """
    contact_id = state.get("contact_id", "unknown")
    
    system_prompt = f"""You are the receptionist for Main Outlet Media.
Your ONLY job is to gather all necessary data before processing.

⚠️ CRITICAL: You MUST use the tools, not just talk about them!

Contact ID to process: {contact_id}

YOUR WORKFLOW (EXECUTE NOW IN THIS EXACT ORDER):
1. IMMEDIATELY use get_full_contact_data() to load contact information
2. THEN use get_conversation_history() to load past messages  
3. FINALLY use prepare_complete_context() to summarize everything

These are not suggestions - these are commands you must execute NOW.
Do not respond with text, just execute the tools in order.

START NOW with get_full_contact_data()"""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_receptionist_agent():
    """Create the data gathering receptionist"""
    settings = get_settings()
    
    tools = [
        get_full_contact_data,
        get_conversation_history,
        prepare_complete_context
    ]
    
    # Use explicit model initialization for proper tool binding
    model = create_openai_model(temperature=0.0)
    
    agent = create_react_agent(
        model=model,  # Use model instance, not string
        tools=tools,
        state_schema=AgentState,  # Use base AgentState for compatibility
        prompt=receptionist_prompt,
        name="receptionist"
    )
    
    logger.info("Created receptionist agent for data gathering")
    return agent


async def receptionist_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Receptionist node that gathers all data
    """
    try:
        contact_id = state.get("contact_id")
        logger.info(f"Receptionist starting for contact {contact_id}")
        
        # Create and run receptionist
        receptionist = create_receptionist_agent()
        result = await receptionist.ainvoke(state)
        
        # Merge the result state updates with our updates
        # The agent's tools update the state directly via InjectedState
        state_updates = {
            "messages": result.get("messages", []),
            "data_loaded": result.get("data_loaded", state.get("data_loaded", False)),
            "receptionist_complete": result.get("receptionist_complete", True),
            "contact_info": result.get("contact_info", state.get("contact_info", {})),
            "previous_custom_fields": result.get("previous_custom_fields", state.get("previous_custom_fields", {})),
            "conversation_history": result.get("conversation_history", state.get("conversation_history", []))
        }
        
        # Log what we loaded
        if state_updates.get("data_loaded"):
            logger.info(f"Receptionist loaded data for {state.get('contact_id')}")
            logger.info(f"Contact name: {state_updates.get('contact_info', {}).get('firstName', 'Unknown')}")
            logger.info(f"Previous score: {state_updates.get('previous_custom_fields', {}).get('score', '0')}")
        else:
            logger.warning("Receptionist didn't load all data")
            
        return state_updates
        
    except Exception as e:
        logger.error(f"Receptionist error: {e}")
        error_msg = AIMessage(
            content="I'm having trouble accessing the system. Please try again.",
            name="receptionist"
        )
        return {"messages": [error_msg], "error": str(e)}


# Export
__all__ = ["receptionist_node", "create_receptionist_agent"]