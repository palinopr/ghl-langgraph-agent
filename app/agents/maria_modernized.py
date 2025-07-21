"""
Maria - Modernized Support Agent with Command Pattern
Uses enhanced tools with task descriptions
"""
from typing import Dict, Any, Optional
from langchain_core.messages import AnyMessage
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from app.tools.agent_tools_modernized import maria_tools
from app.utils.simple_logger import get_logger
from app.utils.model_factory import create_openai_model

logger = get_logger("maria_modernized")


class MariaState(AgentState):
    """State for Maria agent"""
    contact_id: str
    contact_name: Optional[str]
    lead_score: int
    extracted_data: Optional[Dict[str, Any]]
    agent_task: Optional[str]  # Task from supervisor


def maria_prompt_modernized(state: MariaState) -> list[AnyMessage]:
    """
    Dynamic prompt for Maria with task awareness
    """
    contact_name = state.get("contact_name", "")
    lead_score = state.get("lead_score", 0)
    extracted_data = state.get("extracted_data", {})
    agent_task = state.get("agent_task", "")
    
    # Build context
    known_info = []
    if extracted_data.get("name"):
        known_info.append(f"Nombre: {extracted_data['name']}")
    if extracted_data.get("business_type"):
        known_info.append(f"Negocio: {extracted_data['business_type']}")
    
    context_str = "\n".join(known_info) if known_info else "Sin información previa"
    
    system_prompt = f"""Eres Maria, representante de atención al cliente de Main Outlet Media.
Tu rol es ayudar con consultas generales y recopilar información inicial.

{"🎯 TAREA ESPECÍFICA: " + agent_task if agent_task else ""}

INFORMACIÓN DEL CLIENTE:
- Score: {lead_score}/10
- {context_str}

TU ENFOQUE:
1. Sé amable y profesional
2. Responde en español
3. Recopila nombre y tipo de negocio si no los tienes
4. Si el cliente muestra interés en automatización, escala a Carlos

HERRAMIENTAS DISPONIBLES:
- escalate_to_supervisor: Úsala cuando:
  * El cliente quiere información sobre precios (reason="needs_qualification", task="Calificar presupuesto del cliente")
  * El cliente tiene un negocio establecido (reason="qualification_complete", task="Cliente tiene [tipo de negocio], explorar necesidades")
  * El cliente está confundido (reason="customer_confused", task="Aclarar dudas sobre [tema]")
  
- get_contact_details_with_task: Para verificar información del contacto
- update_contact_with_context: Para guardar información recopilada
- save_important_context: Para recordar preferencias o restricciones

IMPORTANTE:
- Si el cliente menciona presupuesto o está listo para comprar, escala inmediatamente
- Incluye descripciones claras de tareas al escalar
- No hagas múltiples preguntas a la vez"""
    
    return [{"role": "system", "content": system_prompt}] + state["messages"]


def create_maria_modernized():
    """Create modernized Maria agent"""
    model = create_openai_model(temperature=0.7)
    
    agent = create_react_agent(
        model=model,
        tools=maria_tools,
        state_schema=MariaState,
        prompt=maria_prompt_modernized,
        name="maria_modernized"
    )
    
    logger.info("Created modernized Maria agent with Command pattern")
    return agent


async def maria_modernized_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Maria node with enhanced Command pattern support
    """
    try:
        # Check if this is the right agent for the score
        lead_score = state.get("lead_score", 0)
        
        if lead_score > 4 and state.get("extracted_data", {}).get("business_type"):
            # Should escalate to Carlos
            logger.info("Maria escalating to Carlos - lead score too high")
            return {
                "needs_rerouting": True,
                "escalation_reason": "qualification_complete",
                "agent_task": f"Cliente con score {lead_score} y negocio {state['extracted_data']['business_type']}",
                "current_agent": "maria"
            }
        
        # Create and run agent
        agent = create_maria_modernized()
        result = await agent.ainvoke(state)
        
        # Update state
        return {
            **result,
            "current_agent": "maria"
        }
        
    except Exception as e:
        logger.error(f"Maria error: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "current_agent": "maria"
        }


# Export
__all__ = ["maria_modernized_node", "create_maria_modernized", "MariaState"]