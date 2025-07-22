"""
Minimal workflow for production testing
No complex imports that could fail
"""
from typing import Dict, Any, Literal, TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_openai import ChatOpenAI
import os

# Simple state definition
class SimpleState(TypedDict):
    messages: Annotated[List[BaseMessage], lambda x, y: x + y]
    current_agent: str
    lead_score: int
    contact_id: str
    conversation_id: str
    next_agent: str
    agent_complete: bool


def analyze_and_route(state: SimpleState) -> Dict[str, Any]:
    """Analyze message and determine routing"""
    messages = state.get("messages", [])
    if not messages:
        return {"lead_score": 0, "next_agent": "maria", "current_agent": "analyzer"}
    
    # Get last human message
    last_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break
        elif isinstance(msg, dict) and msg.get("role") == "human":
            last_message = msg.get("content", "")
            break
    
    # Simple scoring
    last_message_lower = last_message.lower()
    
    if any(word in last_message_lower for word in ["agendar", "cita", "presupuesto", "$", "appointment", "budget"]):
        return {
            "lead_score": 9,
            "next_agent": "sofia",
            "current_agent": "analyzer"
        }
    elif any(word in last_message_lower for word in ["restaurante", "negocio", "empleados", "clientes", "business"]):
        return {
            "lead_score": 6,
            "next_agent": "carlos",
            "current_agent": "analyzer"
        }
    else:
        return {
            "lead_score": 2,
            "next_agent": "maria",
            "current_agent": "analyzer"
        }


def maria_agent(state: SimpleState) -> Dict[str, Any]:
    """Maria agent - handles low score leads"""
    messages = state.get("messages", [])
    
    # Use OpenAI to generate response
    model = ChatOpenAI(temperature=0.7, model="gpt-4o-mini")
    
    system_prompt = """Eres María, una asistente virtual amigable para un servicio de marketing digital.
Tu trabajo es dar la bienvenida a nuevos contactos y entender sus necesidades básicas.
Mantén las respuestas cortas y amigables. Pregunta sobre su negocio."""

    response = model.invoke([
        {"role": "system", "content": system_prompt},
        *[{"role": m.type if hasattr(m, 'type') else m.get('role', 'human'), 
           "content": m.content if hasattr(m, 'content') else m.get('content', '')} 
          for m in messages]
    ])
    
    return {
        "messages": messages + [AIMessage(content=response.content, name="maria")],
        "current_agent": "maria",
        "lead_score": state.get("lead_score", 2),
        "agent_complete": True
    }


def carlos_agent(state: SimpleState) -> Dict[str, Any]:
    """Carlos agent - handles medium score leads"""
    messages = state.get("messages", [])
    
    model = ChatOpenAI(temperature=0.7, model="gpt-4o-mini")
    
    system_prompt = """Eres Carlos, un especialista en marketing para negocios.
Tu trabajo es calificar prospectos que ya tienen un negocio establecido.
Haz preguntas sobre su negocio, empleados, y objetivos de crecimiento."""

    response = model.invoke([
        {"role": "system", "content": system_prompt},
        *[{"role": m.type if hasattr(m, 'type') else m.get('role', 'human'), 
           "content": m.content if hasattr(m, 'content') else m.get('content', '')} 
          for m in messages]
    ])
    
    return {
        "messages": messages + [AIMessage(content=response.content, name="carlos")],
        "current_agent": "carlos",
        "lead_score": state.get("lead_score", 6),
        "agent_complete": True
    }


def sofia_agent(state: SimpleState) -> Dict[str, Any]:
    """Sofia agent - handles high score leads ready to book"""
    messages = state.get("messages", [])
    
    model = ChatOpenAI(temperature=0.7, model="gpt-4o-mini")
    
    system_prompt = """Eres Sofía, una especialista en cerrar citas.
Tu trabajo es agendar citas con prospectos calificados que tienen presupuesto.
Ofrece horarios específicos y confirma la cita. Sé profesional pero amigable."""

    response = model.invoke([
        {"role": "system", "content": system_prompt},
        *[{"role": m.type if hasattr(m, 'type') else m.get('role', 'human'), 
           "content": m.content if hasattr(m, 'content') else m.get('content', '')} 
          for m in messages]
    ])
    
    return {
        "messages": messages + [AIMessage(content=response.content, name="sofia")],
        "current_agent": "sofia",
        "lead_score": state.get("lead_score", 9),
        "agent_complete": True
    }


def route_after_analysis(state: SimpleState) -> Literal["maria", "carlos", "sofia", "end"]:
    """Route based on analysis"""
    next_agent = state.get("next_agent", "maria")
    
    if next_agent in ["maria", "carlos", "sofia"]:
        return next_agent
    
    return "maria"  # Default


# Create workflow
workflow_graph = StateGraph(SimpleState)

# Add nodes
workflow_graph.add_node("analyzer", analyze_and_route)
workflow_graph.add_node("maria", maria_agent)
workflow_graph.add_node("carlos", carlos_agent)
workflow_graph.add_node("sofia", sofia_agent)

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

# Compile
workflow = workflow_graph.compile()

# Export
__all__ = ["workflow"]