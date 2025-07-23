"""
Agent modules for LangGraph messaging system
Production agents with simplified imports
"""
# from app.agents.supervisor import supervisor_node  # Obsolete - using smart_router instead
from app.agents.smart_router import smart_router_node
from app.agents.receptionist_agent import receptionist_node
from app.agents.maria_agent import maria_node
from app.agents.carlos_agent import carlos_node
from app.agents.sofia_agent import sofia_node
from app.agents.responder_agent import responder_node

__all__ = [
    "smart_router_node",
    "receptionist_node",
    "maria_node",
    "carlos_node",
    "sofia_node",
    "responder_node"
]