"""
Main LangGraph workflow with Python 3.13 parallel processing
Uses TaskGroup for concurrent agent execution when possible
"""
from typing import Dict, Any, Literal, List
import asyncio
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from app.state.conversation_state import ConversationState
from app.intelligence.analyzer import intelligence_node
from app.intelligence.ghl_updater import ghl_update_node
from app.agents.supervisor import supervisor_node

# Import enhanced agents
from app.agents.sofia_agent_v2_enhanced import sofia_node_v2, create_sofia_agent
from app.agents.carlos_agent_v2_enhanced import carlos_node_v2, create_carlos_agent
from app.agents.maria_agent_v2 import maria_node_v2, create_maria_agent

# Import error recovery
from app.utils.error_recovery import error_recovery_middleware, handle_graph_recursion
from app.utils.simple_logger import get_logger
from app.config import get_settings

logger = get_logger("workflow_parallel")


# Parallel supervisor node that can run multiple agents concurrently
async def parallel_supervisor_node(state: ConversationState) -> Command:
    """
    Enhanced supervisor that can run multiple agents in parallel
    when appropriate (e.g., getting multiple perspectives)
    """
    settings = get_settings()
    
    # Get the last message for analysis
    last_message = state["messages"][-1] if state.get("messages") else None
    if not last_message:
        return Command(goto="maria", update={})
    
    # Check if we should run agents in parallel
    lead_score = state.get("lead_score", 0)
    message_content = last_message.content.lower()
    
    # Scenarios for parallel execution
    should_run_parallel = False
    parallel_agents = []
    
    # 1. Complex qualification - run Carlos + Maria for different perspectives
    if lead_score >= 5 and any(word in message_content for word in [
        "necesito", "quiero", "busco", "ayuda", "información"
    ]):
        should_run_parallel = True
        parallel_agents = ["carlos", "maria"]
        logger.info("Running Carlos and Maria in parallel for qualification")
    
    # 2. High-value lead - run Sofia + Carlos for comprehensive service
    elif lead_score >= 8 and any(word in message_content for word in [
        "cita", "appointment", "disponibilidad", "horario"
    ]):
        should_run_parallel = True
        parallel_agents = ["sofia", "carlos"]
        logger.info("Running Sofia and Carlos in parallel for hot lead")
    
    # 3. Research phase - multiple agents for information gathering
    elif lead_score <= 4 and len(message_content) > 50:
        should_run_parallel = True
        parallel_agents = ["maria", "carlos"]
        logger.info("Running multiple agents for research phase")
    
    if should_run_parallel and settings.enable_parallel_agents:
        # Run agents in parallel using TaskGroup
        return await run_agents_parallel(state, parallel_agents)
    else:
        # Standard single-agent routing
        return await supervisor_node(state)


async def run_agents_parallel(
    state: ConversationState, 
    agents: List[str]
) -> Command:
    """
    Run multiple agents in parallel using Python 3.13 TaskGroup
    
    Args:
        state: Current conversation state
        agents: List of agent names to run in parallel
        
    Returns:
        Command with combined results
    """
    agent_functions = {
        "sofia": sofia_node_v2,
        "carlos": carlos_node_v2,
        "maria": maria_node_v2
    }
    
    results = []
    errors = []
    
    try:
        # Use TaskGroup for true parallel execution
        async with asyncio.TaskGroup() as tg:
            tasks = []
            for agent_name in agents:
                if agent_name in agent_functions:
                    # Create task for each agent
                    task = tg.create_task(
                        _run_agent_safe(
                            agent_functions[agent_name],
                            state,
                            agent_name
                        )
                    )
                    tasks.append((agent_name, task))
        
        # Collect results
        for agent_name, task in tasks:
            try:
                result = task.result()
                results.append({
                    "agent": agent_name,
                    "result": result
                })
            except Exception as e:
                errors.append({
                    "agent": agent_name,
                    "error": str(e)
                })
        
        # Merge results intelligently
        merged_result = _merge_agent_results(results, errors)
        
        # Determine next step based on merged results
        if merged_result.get("appointment_confirmed"):
            # Sofia confirmed appointment
            return Command(goto=END, update=merged_result)
        elif merged_result.get("needs_qualification"):
            # Need more qualification
            return Command(goto="carlos", update=merged_result)
        else:
            # Continue conversation
            return Command(goto="supervisor", update=merged_result)
            
    except Exception as e:
        logger.error(f"Parallel agent execution failed: {e}")
        # Fallback to single agent
        return Command(goto="maria", update={"error": str(e)})


async def _run_agent_safe(
    agent_func: Any,
    state: ConversationState,
    agent_name: str
) -> Dict[str, Any]:
    """Safely run an agent with error handling"""
    try:
        logger.info(f"Running {agent_name} agent in parallel")
        result = await error_recovery_middleware(agent_func, state)
        logger.info(f"{agent_name} completed successfully")
        return result
    except Exception as e:
        logger.error(f"{agent_name} failed: {e}")
        raise


def _merge_agent_results(
    results: List[Dict[str, Any]], 
    errors: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Intelligently merge results from multiple agents
    
    Priority:
    1. Appointment confirmations (Sofia)
    2. Qualification insights (Carlos)
    3. General responses (Maria)
    """
    merged = {
        "parallel_execution": True,
        "agents_run": [r["agent"] for r in results],
        "errors": errors
    }
    
    # Collect all messages
    all_messages = []
    
    for result in results:
        agent_name = result["agent"]
        agent_result = result["result"]
        
        # Extract messages
        if "messages" in agent_result:
            for msg in agent_result["messages"]:
                msg.metadata = msg.metadata or {}
                msg.metadata["agent"] = agent_name
                all_messages.append(msg)
        
        # Check for special states
        if agent_name == "sofia" and agent_result.get("appointment_status") == "booked":
            merged["appointment_confirmed"] = True
            merged["appointment_id"] = agent_result.get("appointment_id")
            
        if agent_name == "carlos" and agent_result.get("qualification_score"):
            merged["qualification_score"] = agent_result["qualification_score"]
            merged["needs_qualification"] = agent_result["qualification_score"] < 7
    
    # Use the best response (prioritize Sofia > Carlos > Maria)
    priority_order = ["sofia", "carlos", "maria"]
    for agent in priority_order:
        agent_results = [r for r in results if r["agent"] == agent]
        if agent_results and agent_results[0]["result"].get("messages"):
            merged["messages"] = agent_results[0]["result"]["messages"]
            merged["primary_agent"] = agent
            break
    
    # Add metadata about parallel execution
    if "messages" in merged and merged["messages"]:
        merged["messages"][-1].metadata = merged["messages"][-1].metadata or {}
        merged["messages"][-1].metadata["parallel_agents"] = [r["agent"] for r in results]
    
    return merged


def create_parallel_workflow() -> StateGraph:
    """
    Create workflow with parallel agent execution capabilities
    
    Flow: Message → Intelligence → GHL Update → Parallel Supervisor → Agents (parallel) → End
    """
    # Create the graph
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("intelligence", intelligence_node)
    workflow.add_node("ghl_update", ghl_update_node)
    workflow.add_node("parallel_supervisor", parallel_supervisor_node)
    workflow.add_node("supervisor", supervisor_node)  # Fallback
    workflow.add_node("sofia", sofia_node_v2)
    workflow.add_node("carlos", carlos_node_v2)
    workflow.add_node("maria", maria_node_v2)
    
    # Entry point
    workflow.add_edge(START, "intelligence")
    
    # Intelligence → GHL Update → Parallel Supervisor
    workflow.add_edge("intelligence", "ghl_update")
    workflow.add_edge("ghl_update", "parallel_supervisor")
    
    # Agents can go back to supervisor
    workflow.add_edge("sofia", "supervisor")
    workflow.add_edge("carlos", "supervisor")
    workflow.add_edge("maria", "supervisor")
    
    logger.info("Created parallel workflow with TaskGroup support")
    
    return workflow


def create_parallel_workflow_with_memory() -> StateGraph:
    """Create parallel workflow with persistence"""
    workflow = create_parallel_workflow()
    
    # Add memory and store
    checkpointer = MemorySaver()
    store = InMemoryStore()
    
    # Compile
    app = workflow.compile(
        checkpointer=checkpointer,
        store=store
    )
    
    logger.info("Created parallel workflow with memory")
    
    return app


# Export main components
__all__ = [
    "create_parallel_workflow",
    "create_parallel_workflow_with_memory",
    "parallel_supervisor_node",
    "run_agents_parallel"
]