"""
Simple workflow for testing LangGraph Studio
Focuses on basic agent routing without complex pipeline
"""
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
import os

# Import minimal state
from app.state.minimal_state import MinimalState

# Import logger
from app.utils.simple_logger import get_logger

logger = get_logger("workflow_studio_simple")


def analyze_message(state: MinimalState) -> Dict[str, Any]:
    """Simple analyzer to determine lead score and routing"""
    messages = state.get("messages", [])
    if not messages:
        return {"lead_score": 0, "next_agent": "maria", "current_agent": "analyzer"}
    
    # Get last human message
    last_message = ""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "human":
            last_message = msg.get("content", "")
            break
        elif hasattr(msg, "content"):
            if isinstance(msg, HumanMessage) or (hasattr(msg, "type") and msg.type == "human"):
                last_message = msg.content
                break
    
    logger.info(f"Analyzing message: {last_message[:100]}...")
    
    # Simple keyword-based scoring
    last_message_lower = last_message.lower()
    
    # High intent keywords (score 8-10) - Ready to buy/book
    if any(word in last_message_lower for word in ["agendar", "cita", "presupuesto", "$", "appointment", "budget"]):
        lead_score = 9
        next_agent = "sofia"
    # Medium intent keywords (score 5-7) - Business owner
    elif any(word in last_message_lower for word in ["restaurante", "negocio", "empleados", "clientes", "business", "employees"]):
        lead_score = 6
        next_agent = "carlos"
    # Low intent keywords (score 0-4) - Just inquiring
    else:
        lead_score = 2
        next_agent = "maria"
    
    logger.info(f"Lead score: {lead_score}, routing to: {next_agent}")
    
    return {
        "lead_score": lead_score,
        "next_agent": next_agent,
        "current_agent": "analyzer",
        "analysis_complete": True
    }


def maria_simple(state: MinimalState) -> Dict[str, Any]:
    """Simple Maria agent for testing"""
    logger.info("Maria agent processing...")
    
    messages = state.get("messages", [])
    lead_score = state.get("lead_score", 2)  # Get from state
    
    # Create response
    response = AIMessage(
        content="¡Hola! Soy María, tu asistente virtual. Veo que estás interesado en nuestros servicios. "
                "Ofrecemos soluciones de marketing digital para ayudar a tu negocio a crecer. "
                "¿Podrías contarme más sobre tu negocio?",
        name="maria"
    )
    
    return {
        "messages": messages + [response],
        "current_agent": "maria",
        "lead_score": lead_score,  # Pass through
        "agent_complete": True
    }


def carlos_simple(state: MinimalState) -> Dict[str, Any]:
    """Simple Carlos agent for testing"""
    logger.info("Carlos agent processing...")
    
    messages = state.get("messages", [])
    lead_score = state.get("lead_score", 6)  # Get from state
    
    # Create response
    response = AIMessage(
        content="¡Hola! Soy Carlos, especialista en marketing para negocios. "
                "Entiendo que tienes un restaurante y necesitas atraer más clientes. "
                "Tenemos estrategias específicas para el sector gastronómico que pueden ayudarte. "
                "¿Cuántos clientes atiendes actualmente al día?",
        name="carlos"
    )
    
    return {
        "messages": messages + [response],
        "current_agent": "carlos",
        "lead_score": lead_score,  # Pass through
        "agent_complete": True
    }


def sofia_simple(state: MinimalState) -> Dict[str, Any]:
    """Simple Sofia agent for testing"""
    logger.info("Sofia agent processing...")
    
    messages = state.get("messages", [])
    lead_score = state.get("lead_score", 9)  # Get from state
    
    # Create response
    response = AIMessage(
        content="¡Excelente! Soy Sofía y me encantaría ayudarte a agendar una cita. "
                "Con un presupuesto de $500 mensuales podemos crear una estrategia muy efectiva. "
                "¿Te gustaría agendar para mañana? Tengo disponibilidad a las 10am, 2pm o 4pm. "
                "¿Cuál horario te conviene más?",
        name="sofia"
    )
    
    return {
        "messages": messages + [response],
        "current_agent": "sofia",
        "lead_score": lead_score,  # Pass through
        "agent_complete": True
    }


def route_after_analysis(state: MinimalState) -> Literal["maria", "carlos", "sofia", "end"]:
    """Route based on analysis"""
    next_agent = state.get("next_agent")
    
    if next_agent in ["maria", "carlos", "sofia"]:
        logger.info(f"Routing to {next_agent}")
        return next_agent
    
    logger.warning(f"Unknown agent: {next_agent}, defaulting to maria")
    return "maria"


# Create simple workflow
logger.info("Creating simple workflow for LangGraph Studio")

workflow_graph = StateGraph(MinimalState)

# Add nodes
workflow_graph.add_node("analyzer", analyze_message)
workflow_graph.add_node("maria", maria_simple)
workflow_graph.add_node("carlos", carlos_simple)
workflow_graph.add_node("sofia", sofia_simple)

# Set entry point
workflow_graph.set_entry_point("analyzer")

# Add routing
workflow_graph.add_conditional_edges(
    "analyzer",
    route_after_analysis,
    {
        "maria": "maria",
        "carlos": "carlos",
        "sofia": "sofia",
        "end": END
    }
)

# All agents end
workflow_graph.add_edge("maria", END)
workflow_graph.add_edge("carlos", END)
workflow_graph.add_edge("sofia", END)

# Compile without checkpointer
workflow = workflow_graph.compile()

logger.info("Simple workflow compiled for LangGraph Studio")

# Export
__all__ = ["workflow"]