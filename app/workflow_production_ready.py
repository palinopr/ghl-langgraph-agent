"""
Production-Ready Workflow for Deployment
Combines full functionality with clean imports
"""
from typing import Dict, Any, Literal, TypedDict, Annotated, List, Union
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_openai import ChatOpenAI
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Production State Definition
class ProductionState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    current_agent: str
    lead_score: int
    contact_id: str
    conversation_id: str
    location_id: str
    next_agent: str
    agent_task: str
    supervisor_complete: bool
    needs_escalation: bool
    escalation_reason: str
    routing_attempts: int
    should_end: bool
    contact_name: str
    email: str
    phone: str
    business_type: str
    goal: str
    urgency_level: str
    budget: str
    thread_id: str
    webhook_data: Dict[str, Any]  # For passing webhook data to receptionist


def thread_mapper_node(state: ProductionState) -> Dict[str, Any]:
    """Map conversation ID to thread ID for consistency"""
    conversation_id = state.get("conversation_id", "")
    thread_id = state.get("thread_id", "")
    
    if not thread_id and conversation_id:
        thread_id = f"thread-{conversation_id}"
        logger.info(f"Mapped conversation {conversation_id} to thread {thread_id}")
    
    return {"thread_id": thread_id}


# Receptionist node removed - using receptionist_checkpoint_aware_node from imports


def intelligence_analyzer_node(state: ProductionState) -> Dict[str, Any]:
    """Analyze message and determine lead score"""
    messages = state.get("messages", [])
    last_message = state.get("last_message", "")
    
    if not last_message:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage) or (isinstance(msg, dict) and msg.get("role") == "human"):
                last_message = msg.content if hasattr(msg, "content") else msg.get("content", "")
                break
    
    logger.info("Intelligence analyzer processing message...")
    
    # Enhanced scoring logic
    last_message_lower = last_message.lower()
    lead_score = state.get("lead_score", 0)
    
    # High intent signals (8-10)
    high_intent_keywords = ["agendar", "cita", "presupuesto", "$", "appointment", "budget", 
                           "comprar", "contratar", "necesito ya", "urgente"]
    
    # Medium intent signals (5-7)
    medium_intent_keywords = ["negocio", "empresa", "empleados", "restaurante", "tienda",
                             "clientes", "ventas", "marketing", "ayuda", "mejorar"]
    
    # Calculate score
    if any(keyword in last_message_lower for keyword in high_intent_keywords):
        lead_score = 9
        intent = "high_intent_booking"
    elif any(keyword in last_message_lower for keyword in medium_intent_keywords):
        lead_score = 6
        intent = "business_qualification"
    else:
        lead_score = 2
        intent = "information_gathering"
    
    # Extract business info
    business_type = ""
    if "restaurante" in last_message_lower:
        business_type = "restaurant"
    elif "tienda" in last_message_lower or "ropa" in last_message_lower:
        business_type = "retail"
    elif "gimnasio" in last_message_lower:
        business_type = "gym"
    elif "panadería" in last_message_lower or "cafetería" in last_message_lower:
        business_type = "food_service"
    
    logger.info(f"Intelligence result: score={lead_score}, intent={intent}")
    
    return {
        "lead_score": lead_score,
        "last_intent": intent,
        "business_type": business_type,
        "intelligence_complete": True
    }


def supervisor_node(state: ProductionState) -> Dict[str, Any]:
    """Supervisor that routes to appropriate agent"""
    lead_score = state.get("lead_score", 0)
    routing_attempts = state.get("routing_attempts", 0)
    
    logger.info(f"Supervisor routing with score: {lead_score}")
    
    # Determine routing
    if routing_attempts >= 3:
        logger.warning("Max routing attempts reached")
        return {
            "next_agent": "responder",
            "supervisor_complete": True,
            "should_end": False
        }
    
    # Route based on lead score
    if lead_score >= 8:
        next_agent = "sofia"
        task = "Help this high-intent lead book an appointment. They have budget and urgency."
    elif lead_score >= 5:
        next_agent = "carlos"
        task = "Qualify this business owner. Learn about their needs and pain points."
    else:
        next_agent = "maria"
        task = "Welcome this new contact and understand their basic needs."
    
    logger.info(f"Routing to {next_agent} with task: {task}")
    
    return {
        "next_agent": next_agent,
        "agent_task": task,
        "supervisor_complete": True,
        "should_end": False
    }


def create_agent_node(agent_name: str, system_prompt: str):
    """Factory function to create agent nodes"""
    def agent_node(state: ProductionState) -> Dict[str, Any]:
        messages = state.get("messages", [])
        agent_task = state.get("agent_task", "")
        
        logger.info(f"{agent_name} agent processing...")
        
        # Use OpenAI
        model = ChatOpenAI(temperature=0.7, model="gpt-4o-mini")
        
        # Build conversation for model
        conversation = [{"role": "system", "content": system_prompt}]
        
        if agent_task:
            conversation.append({"role": "system", "content": f"Task: {agent_task}"})
        
        # Add message history
        for msg in messages:
            if isinstance(msg, HumanMessage):
                conversation.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                conversation.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, dict):
                role = "user" if msg.get("role") == "human" else "assistant"
                conversation.append({"role": role, "content": msg.get("content", "")})
        
        # Get response
        response = model.invoke(conversation)
        
        # Update state
        return {
            "messages": messages + [AIMessage(content=response.content, name=agent_name)],
            "current_agent": agent_name,
            "agent_complete": True,
            "needs_escalation": False
        }
    
    return agent_node


# Create agent nodes
maria_node = create_agent_node(
    "maria",
    """Eres María, una asistente virtual amigable para un servicio de marketing digital.
    Tu trabajo es dar la bienvenida a nuevos contactos y entender sus necesidades básicas.
    Sé amigable, haz preguntas sobre su negocio, pero no seas muy técnica.
    Si mencionan presupuesto específico o quieren agendar, indícalo en tu respuesta."""
)

carlos_node = create_agent_node(
    "carlos",
    """Eres Carlos, un especialista en marketing para negocios establecidos.
    Tu trabajo es calificar prospectos que ya tienen un negocio.
    Haz preguntas sobre: tamaño del negocio, empleados, facturación, problemas actuales.
    Identifica sus puntos de dolor y cómo el marketing puede ayudarles."""
)

sofia_node = create_agent_node(
    "sofia",
    """Eres Sofía, una especialista en cerrar citas para prospectos calificados.
    Tu trabajo es agendar citas con personas que tienen presupuesto y urgencia.
    Ofrece horarios específicos (mañana 10am, 2pm, o 4pm).
    Sé profesional pero cálida. Confirma sus datos de contacto."""
)


# Responder node removed - using responder_streaming_node from imports


def route_from_supervisor(state: ProductionState) -> Literal["maria", "carlos", "sofia", "responder", "end"]:
    """Route based on supervisor decision"""
    if state.get("should_end", False):
        return "end"
    
    if not state.get("supervisor_complete"):
        return "end"
    
    next_agent = state.get("next_agent")
    
    if next_agent in ["maria", "carlos", "sofia"]:
        return next_agent
    elif next_agent == "responder":
        return "responder"
    else:
        return "end"


def route_from_agent(state: ProductionState) -> Literal["responder", "supervisor"]:
    """Route from agent - either to responder or back to supervisor"""
    if state.get("needs_escalation", False):
        logger.info("Escalating back to supervisor")
        return "supervisor"
    
    return "responder"


# Import the actual responder that sends to GHL
from app.agents.responder_streaming import responder_streaming_node
# Import the checkpoint-aware receptionist for conversation context
from app.agents.receptionist_checkpoint_aware import receptionist_checkpoint_aware_node

# Create the workflow
workflow_graph = StateGraph(ProductionState)

# Add all nodes
workflow_graph.add_node("thread_mapper", thread_mapper_node)
workflow_graph.add_node("receptionist", receptionist_checkpoint_aware_node)  # Use checkpoint-aware receptionist
workflow_graph.add_node("intelligence", intelligence_analyzer_node)
workflow_graph.add_node("supervisor", supervisor_node)
workflow_graph.add_node("maria", maria_node)
workflow_graph.add_node("carlos", carlos_node)
workflow_graph.add_node("sofia", sofia_node)
workflow_graph.add_node("responder", responder_streaming_node)  # Use the real responder that sends to GHL

# Set entry point
workflow_graph.set_entry_point("thread_mapper")

# Define edges
workflow_graph.add_edge("thread_mapper", "receptionist")
workflow_graph.add_edge("receptionist", "intelligence")
workflow_graph.add_edge("intelligence", "supervisor")

# Supervisor routing
workflow_graph.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "maria": "maria",
        "carlos": "carlos",
        "sofia": "sofia",
        "responder": "responder",
        "end": END
    }
)

# Agent routing
for agent in ["maria", "carlos", "sofia"]:
    workflow_graph.add_conditional_edges(
        agent,
        route_from_agent,
        {
            "responder": "responder",
            "supervisor": "supervisor"
        }
    )

# Responder ends
workflow_graph.add_edge("responder", END)

# Compile with memory checkpointer for conversation persistence
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
workflow = workflow_graph.compile(checkpointer=checkpointer)

logger.info("Production workflow compiled with memory checkpointer for conversation persistence")

# Export
__all__ = ["workflow"]