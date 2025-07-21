"""
Conversation Formatter Utility
Formats conversation history for agents to understand context
"""
from typing import List, Dict, Any, Optional
from app.utils.simple_logger import get_logger

logger = get_logger("conversation_formatter")


def format_conversation_for_agent(state: Dict[str, Any]) -> str:
    """
    Format conversation history into a clear, readable context for agents
    
    Args:
        state: The workflow state containing messages and extracted data
        
    Returns:
        Formatted string with conversation summary
    """
    messages = state.get("messages", [])
    extracted_data = state.get("extracted_data", {})
    lead_score = state.get("lead_score", 0)
    
    # Build conversation summary
    conversation_summary = "\n📝 CONVERSATION SUMMARY:\n"
    conversation_summary += "=" * 50 + "\n"
    
    # Current data collected
    conversation_summary += "\n✅ DATA COLLECTED:\n"
    if extracted_data.get("name"):
        conversation_summary += f"• Name: {extracted_data['name']}\n"
    if (extracted_data.get("business_type") and 
        extracted_data["business_type"] != "NO_MENCIONADO" and
        extracted_data["business_type"].lower() not in ["negocio", "business", "empresa", "local", "comercio"]):
        conversation_summary += f"• Business Type: {extracted_data['business_type']}\n"
    if extracted_data.get("budget"):
        conversation_summary += f"• Budget: {extracted_data['budget']}\n"
    if extracted_data.get("goal"):
        conversation_summary += f"• Goal: {extracted_data['goal']}\n"
        
    conversation_summary += f"\n📊 Current Lead Score: {lead_score}/10\n"
    
    # Conversation flow
    conversation_summary += "\n💬 CONVERSATION FLOW:\n"
    human_count = 0
    
    for msg in messages:
        # Skip system messages from receptionist/supervisor
        if hasattr(msg, 'name') and msg.name in ['receptionist', 'supervisor_brain']:
            continue
            
        if hasattr(msg, '__class__'):
            msg_type = msg.__class__.__name__
            if msg_type == 'HumanMessage':
                human_count += 1
                conversation_summary += f"\nCustomer #{human_count}: {msg.content}\n"
            elif msg_type == 'AIMessage' and hasattr(msg, 'content'):
                # Only show agent responses, not system messages
                if not any(skip in msg.content for skip in ['SUPERVISOR ANALYSIS', 'DATA LOADED']):
                    conversation_summary += f"Agent: {msg.content[:100]}...\n"
    
    # What's needed next
    conversation_summary += "\n🎯 NEXT STEPS:\n"
    if not extracted_data.get("name"):
        conversation_summary += "• Need to get customer's name\n"
    elif (not extracted_data.get("business_type") or 
          extracted_data["business_type"] == "NO_MENCIONADO" or
          extracted_data["business_type"].lower() in ["negocio", "business", "empresa", "local", "comercio"]):
        conversation_summary += "• Need to get business type\n"
    elif not extracted_data.get("budget"):
        conversation_summary += "• Need to get budget information\n"
    elif lead_score >= 8:
        conversation_summary += "• Ready for appointment booking!\n"
    else:
        conversation_summary += "• Continue qualification\n"
        
    conversation_summary += "\n" + "=" * 50
    
    return conversation_summary


def get_last_customer_message(state: Dict[str, Any]) -> Optional[str]:
    """
    Get the most recent customer message from state
    
    Args:
        state: The workflow state
        
    Returns:
        The last customer message or None
    """
    messages = state.get("messages", [])
    
    for msg in reversed(messages):
        if hasattr(msg, '__class__') and msg.__class__.__name__ == 'HumanMessage':
            return msg.content
            
    return None


def get_conversation_stage(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Determine what stage the conversation is at
    
    Returns dict with:
        - stage: Current conversation stage
        - next_question: What to ask next
        - context: Additional context
    """
    extracted_data = state.get("extracted_data", {})
    lead_score = state.get("lead_score", 0)
    
    has_name = bool(extracted_data.get("name"))
    has_business = bool(extracted_data.get("business_type") and 
                       extracted_data["business_type"] != "NO_MENCIONADO" and
                       extracted_data["business_type"].lower() not in ["negocio", "business", "empresa", "local", "comercio"])
    has_budget = bool(extracted_data.get("budget"))
    
    # Determine stage
    if not has_name:
        return {
            "stage": "greeting",
            "next_question": "ask_name",
            "context": "Customer hasn't provided name yet"
        }
    elif not has_business:
        return {
            "stage": "name_collected",
            "next_question": "ask_business",
            "context": f"Customer name is {extracted_data.get('name')}"
        }
    elif not has_budget:
        return {
            "stage": "business_collected",
            "next_question": "ask_budget",
            "context": f"Customer has {extracted_data.get('business_type')} business"
        }
    elif lead_score >= 8:
        return {
            "stage": "qualified_hot_lead",
            "next_question": "offer_appointment",
            "context": "Customer is fully qualified and ready for appointment"
        }
    else:
        return {
            "stage": "needs_more_qualification",
            "next_question": "ask_goals",
            "context": "Customer needs more qualification"
        }