"""
Agent modules for LangGraph messaging system
Using modernized v2 implementations with latest patterns
"""
from app.agents.supervisor import supervisor_node, create_supervisor_agent
from app.agents.sofia_agent_v2 import sofia_node_v2, create_sofia_agent
from app.agents.carlos_agent_v2 import carlos_node_v2, create_carlos_agent
from app.agents.maria_agent_v2 import maria_node_v2, create_maria_agent

__all__ = [
    "supervisor_node",
    "create_supervisor_agent",
    "sofia_node_v2",
    "create_sofia_agent",
    "carlos_node_v2", 
    "create_carlos_agent",
    "maria_node_v2",
    "create_maria_agent"
]