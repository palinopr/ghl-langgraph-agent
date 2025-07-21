"""
Simplified Workflow with <15 State Fields
Uses MessagesState base and official patterns
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Import simplified state
from app.state.simplified_state import (
    SimplifiedState, 
    get_lead_category,
    determine_agent_from_score,
    is_qualified_for_appointment
)

# Import nodes
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_simplified")


# Simplified Receptionist Node
async def receptionist_simplified(state: SimplifiedState) -> Dict[str, Any]:
    """Load essential contact data only"""
    from app.tools.ghl_client import ghl_client
    
    contact_id = state["contact_id"]
    logger.info(f"Loading contact data for {contact_id}")
    
    try:
        # Load contact info
        contact = await ghl_client.get_contact(contact_id)
        
        if contact:
            # Extract only essential data
            extracted = {}
            
            # Get custom fields
            custom_fields = contact.get("customFields", {})
            if custom_fields.get("name"):
                extracted["name"] = custom_fields["name"]
            if custom_fields.get("business_type"):
                extracted["business_type"] = custom_fields["business_type"]
            if custom_fields.get("budget"):
                extracted["budget"] = custom_fields["budget"]
            if custom_fields.get("email"):
                extracted["email"] = custom_fields["email"]
            
            # Also check main contact fields
            if not extracted.get("name"):
                extracted["name"] = contact.get("name") or contact.get("firstName")
            if not extracted.get("email"):
                extracted["email"] = contact.get("email")
            
            return {
                "contact_info": contact,
                "extracted_data": extracted
            }
    except Exception as e:
        logger.error(f"Error loading contact: {str(e)}")
    
    return {}


# Simplified Intelligence Node
async def intelligence_simplified(state: SimplifiedState) -> Dict[str, Any]:
    """Score lead based on available information"""
    from app.intelligence.analyzer import SpanishPatternExtractor, LeadScorer
    
    # Get current message
    if not state["messages"]:
        return {"lead_score": 0}
    
    current_msg = state["messages"][-1].content
    
    # Extract patterns
    extractor = SpanishPatternExtractor()
    new_extractions = extractor.extract_all(current_msg)
    
    # Merge with existing data
    extracted_data = state.get("extracted_data", {})
    for key, value in new_extractions.items():
        if value and key not in extracted_data:
            extracted_data[key] = value
    
    # Score the lead
    scorer = LeadScorer()
    score = scorer.calculate_score(
        name=extracted_data.get("name"),
        business=extracted_data.get("business_type"),
        budget=extracted_data.get("budget"),
        goal=extracted_data.get("goal"),
        current_message=current_msg
    )
    
    logger.info(f"Lead score: {score}/10")
    
    return {
        "lead_score": score,
        "extracted_data": extracted_data
    }


# Simplified Supervisor Node
async def supervisor_simplified(state: SimplifiedState) -> Dict[str, Any]:
    """Route based on score and qualifications"""
    score = state.get("lead_score", 0)
    
    # Check if qualified for appointment
    if score >= 8 and is_qualified_for_appointment(state):
        logger.info("Routing to Sofia for appointment")
        return {
            "next_agent": "sofia",
            "agent_task": "Help customer book their appointment"
        }
    
    # Determine agent by score
    agent = determine_agent_from_score(score)
    
    # Set appropriate task
    tasks = {
        "maria": "Gather initial information about their business",
        "carlos": "Qualify their budget and needs",
        "sofia": "Complete qualification and book appointment"
    }
    
    logger.info(f"Routing to {agent} (score: {score})")
    
    return {
        "next_agent": agent,
        "agent_task": tasks.get(agent, "Help the customer")
    }


# Simplified Agent Nodes
async def maria_simplified(state: SimplifiedState) -> Dict[str, Any]:
    """Maria - Basic support"""
    from langchain_core.messages import AIMessage
    
    name = state.get("extracted_data", {}).get("name", "")
    greeting = f"¡Hola{' ' + name if name else ''}! Soy María de Main Outlet Media. "
    
    if not name:
        response = greeting + "¿Cuál es tu nombre?"
    elif not state.get("extracted_data", {}).get("business_type"):
        response = f"{greeting}¿Qué tipo de negocio tienes?"
    else:
        response = f"{greeting}¿En qué puedo ayudarte hoy?"
    
    return {
        "messages": [AIMessage(content=response)],
        "current_agent": "maria"
    }


async def carlos_simplified(state: SimplifiedState) -> Dict[str, Any]:
    """Carlos - Qualification"""
    from langchain_core.messages import AIMessage
    
    extracted = state.get("extracted_data", {})
    name = extracted.get("name", "")
    business = extracted.get("business_type", "")
    
    greeting = f"¡Hola{' ' + name if name else ''}! Soy Carlos, especialista en automatización de WhatsApp. "
    
    if not extracted.get("budget"):
        response = greeting + f"Veo que tienes un {business}. ¿Cuál es tu presupuesto mensual para marketing?"
    else:
        response = greeting + f"Excelente, con tu presupuesto podemos hacer mucho para tu {business}. ¿Cuál es tu email para enviarte más información?"
    
    return {
        "messages": [AIMessage(content=response)],
        "current_agent": "carlos"
    }


async def sofia_simplified(state: SimplifiedState) -> Dict[str, Any]:
    """Sofia - Appointments"""
    from langchain_core.messages import AIMessage
    
    name = state.get("extracted_data", {}).get("name", "")
    
    response = f"""¡Perfecto {name}! Tengo estos horarios disponibles para tu consulta gratuita:

📅 Martes a las 10:00 AM
📅 Miércoles a las 2:00 PM
📅 Jueves a las 4:00 PM

¿Cuál prefieres?"""
    
    return {
        "messages": [AIMessage(content=response)],
        "current_agent": "sofia"
    }


# Simplified Responder
async def responder_simplified(state: SimplifiedState) -> Dict[str, Any]:
    """Send the last AI message"""
    from app.tools.ghl_client import ghl_client
    
    # Find last AI message
    for msg in reversed(state["messages"]):
        if msg.type == "ai" and not msg.content.startswith("["):
            logger.info(f"Sending: {msg.content[:50]}...")
            
            # Send via GHL
            await ghl_client.send_message(
                state["contact_id"],
                msg.content,
                state["webhook_data"].get("type", "WhatsApp")
            )
            
            return {"should_end": True}
    
    return {}


# Routing functions
def route_after_supervisor(state: SimplifiedState) -> str:
    """Route from supervisor"""
    if state.get("should_end"):
        return "end"
    
    next_agent = state.get("next_agent")
    if next_agent in ["maria", "carlos", "sofia"]:
        return next_agent
    
    return "end"


def route_after_agent(state: SimplifiedState) -> str:
    """Route from agent"""
    if state.get("needs_rerouting"):
        return "supervisor"
    return "responder"


def create_simplified_workflow():
    """
    Create workflow with simplified state (<15 fields)
    """
    logger.info("Creating simplified workflow")
    
    # Create workflow
    workflow = StateGraph(SimplifiedState)
    
    # Add nodes
    workflow.add_node("receptionist", receptionist_simplified)
    workflow.add_node("intelligence", intelligence_simplified)
    workflow.add_node("supervisor", supervisor_simplified)
    workflow.add_node("maria", maria_simplified)
    workflow.add_node("carlos", carlos_simplified)
    workflow.add_node("sofia", sofia_simplified)
    workflow.add_node("responder", responder_simplified)
    
    # Set entry point
    workflow.set_entry_point("receptionist")
    
    # Add edges
    workflow.add_edge("receptionist", "intelligence")
    workflow.add_edge("intelligence", "supervisor")
    
    # Conditional routing
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "maria": "maria",
            "carlos": "carlos", 
            "sofia": "sofia",
            "end": END
        }
    )
    
    # Agent routing
    for agent in ["maria", "carlos", "sofia"]:
        workflow.add_conditional_edges(
            agent,
            route_after_agent,
            {
                "supervisor": "supervisor",
                "responder": "responder"
            }
        )
    
    # Responder ends
    workflow.add_edge("responder", END)
    
    # Compile
    memory = MemorySaver()
    compiled = workflow.compile(checkpointer=memory)
    
    logger.info("Simplified workflow compiled successfully")
    
    return compiled


# Create workflow instance
simplified_workflow = create_simplified_workflow()

# Export
__all__ = ["simplified_workflow", "create_simplified_workflow"]