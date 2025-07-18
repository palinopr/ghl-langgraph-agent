#!/usr/bin/env python3
"""
Comprehensive import test to catch all errors before deployment
Tests all imports and checks for compatibility issues
"""
import sys
import traceback
from typing import List, Tuple

def test_import(module_path: str) -> Tuple[bool, str]:
    """Test a single import and return success status and error message"""
    try:
        exec(f"import {module_path}")
        return True, f"✓ {module_path}"
    except Exception as e:
        return False, f"✗ {module_path}: {str(e)}"

def test_from_import(module_path: str, items: List[str]) -> Tuple[bool, str]:
    """Test from X import Y statements"""
    try:
        import_stmt = f"from {module_path} import {', '.join(items)}"
        exec(import_stmt)
        return True, f"✓ {import_stmt}"
    except Exception as e:
        return False, f"✗ {import_stmt}: {str(e)}"

def main():
    print("Testing all imports for LangGraph GHL Agent...")
    print("=" * 60)
    
    errors = []
    
    # Test basic dependencies
    basic_imports = [
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langgraph",
        "langgraph.graph",
        "langgraph.graph.message",
        "langgraph.checkpoint",
        "langgraph.store",
        "pydantic",
        "typing_extensions",
        "fastapi",
        "supabase",
    ]
    
    print("\n1. Testing basic dependencies:")
    for module in basic_imports:
        success, msg = test_import(module)
        print(msg)
        if not success:
            errors.append(msg)
    
    # Test specific imports that are causing issues
    print("\n2. Testing specific imports:")
    specific_tests = [
        ("langgraph.graph.message", ["add_messages"]),
        ("typing_extensions", ["TypedDict"]),
        ("langgraph.graph", ["StateGraph", "END", "START"]),
        ("langgraph.checkpoint.memory", ["MemorySaver"]),
        ("langgraph.store.memory", ["InMemoryStore"]),
        ("langgraph.types", ["Command"]),
        ("langgraph.prebuilt", ["create_react_agent"]),
        ("langchain_core.tools", ["InjectedState", "InjectedToolCallId", "tool"]),
    ]
    
    for module, items in specific_tests:
        success, msg = test_from_import(module, items)
        print(msg)
        if not success:
            errors.append(msg)
    
    # Test our app modules
    print("\n3. Testing app modules:")
    app_modules = [
        "app",
        "app.config",
        "app.state.conversation_state",
        "app.utils.tracing",
        "app.utils.simple_logger",
        "app.utils.message_batcher",
        "app.utils.message_utils",
        "app.tools.ghl_client",
        "app.tools.supabase_client",
        "app.tools.webhook_processor",
        "app.tools.webhook_enricher",
        "app.tools.conversation_loader",
        "app.tools.agent_tools_v2",
        "app.intelligence.analyzer",
        "app.intelligence.ghl_updater",
        "app.agents.supervisor",
        "app.agents.sofia_agent_v2",
        "app.agents.carlos_agent_v2",
        "app.agents.maria_agent_v2",
        "app.workflow_v2",
        "app.workflow",
        "app.api.webhook",
    ]
    
    for module in app_modules:
        success, msg = test_import(module)
        print(msg)
        if not success:
            errors.append(msg)
    
    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"\n❌ Found {len(errors)} import errors:\n")
        for error in errors:
            print(error)
        print("\nThese errors need to be fixed before deployment!")
        sys.exit(1)
    else:
        print("\n✅ All imports successful! Ready for deployment.")
        sys.exit(0)

if __name__ == "__main__":
    main()