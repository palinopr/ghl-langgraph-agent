#!/usr/bin/env python3
"""Test all imports in the project to identify issues"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all module imports"""
    errors = []
    
    print("Testing imports...")
    
    # Test core modules
    imports_to_test = [
        ("Config", "from app.config import get_settings"),
        ("Simple Logger", "from app.utils.simple_logger import get_logger"),
        ("Conversation State", "from app.state.conversation_state import ConversationState"),
        ("Webhook Processor", "from app.tools.webhook_processor import webhook_processor"),
        ("GHL Client", "from app.tools.ghl_client import ghl_client"),
        ("Supabase Client", "from app.tools.supabase_client import supabase_client"),
        ("Agent Tools", "from app.tools.agent_tools import agent_tools"),
        ("Workflow", "from app.workflow import run_workflow"),
        ("Maria Agent", "from app.agents.maria_agent import maria_node"),
        ("Carlos Agent", "from app.agents.carlos_agent import carlos_node"),
        ("Sofia Agent", "from app.agents.sofia_agent import sofia_node"),
        ("Orchestrator", "from app.agents.orchestrator import orchestrator_node"),
        ("Webhook API", "from app.api.webhook import app"),
        ("Main App", "import main"),
    ]
    
    for name, import_stmt in imports_to_test:
        try:
            print(f"✓ {name}: ", end="")
            exec(import_stmt)
            print("OK")
        except Exception as e:
            error_msg = f"✗ {name}: {type(e).__name__}: {str(e)}"
            print(error_msg)
            errors.append(error_msg)
    
    print("\n" + "="*50)
    if errors:
        print(f"Found {len(errors)} import errors:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("All imports successful!")
        return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)