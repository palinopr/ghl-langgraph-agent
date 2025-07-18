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
        ("Config", "from src.config import get_settings"),
        ("Simple Logger", "from src.utils.simple_logger import get_logger"),
        ("Conversation State", "from src.state.conversation_state import ConversationState"),
        ("Webhook Processor", "from src.tools.webhook_processor import webhook_processor"),
        ("GHL Client", "from src.tools.ghl_client import ghl_client"),
        ("Supabase Client", "from src.tools.supabase_client import supabase_client"),
        ("Agent Tools", "from src.tools.agent_tools import agent_tools"),
        ("Workflow", "from src.workflow import run_workflow"),
        ("Maria Agent", "from src.agents.maria_agent import maria_node"),
        ("Carlos Agent", "from src.agents.carlos_agent import carlos_node"),
        ("Sofia Agent", "from src.agents.sofia_agent import sofia_node"),
        ("Orchestrator", "from src.agents.orchestrator import orchestrator_node"),
        ("Webhook API", "from src.api.webhook import app"),
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