#!/usr/bin/env python3
"""
Simulate LangGraph Platform deployment environment
Tests all critical imports and configurations
"""
import sys
import os
import subprocess

# Simulate deployment path structure
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🚀 Simulating LangGraph Platform Deployment Environment")
print("=" * 60)

# Check Python version
print(f"\n📌 Python Version: {sys.version}")
if sys.version_info < (3, 11):
    print("⚠️  Warning: LangGraph Platform requires Python 3.11+")

errors = []

# Test 1: Critical imports
print("\n1️⃣  Testing critical imports...")
try:
    # This is what LangGraph Platform tries to import
    print("   - Importing app.workflow...")
    from app.workflow import workflow
    print("   ✅ workflow imported successfully")
    
    # Check if workflow is a StateGraph
    from langgraph.graph import StateGraph
    if isinstance(workflow, StateGraph):
        print("   ✅ workflow is a valid StateGraph")
    else:
        print(f"   ❌ workflow is {type(workflow)}, expected StateGraph")
        errors.append("workflow is not a StateGraph")
        
except Exception as e:
    print(f"   ❌ Failed to import workflow: {e}")
    errors.append(f"Import error: {e}")

# Test 2: Check for TypedDict compatibility
print("\n2️⃣  Testing TypedDict compatibility...")
try:
    from app.state.conversation_state import ConversationState
    print("   ✅ ConversationState imported successfully")
    
    # Check if it's using typing_extensions
    import inspect
    source = inspect.getsource(ConversationState.__module__)
    if "from typing_extensions import TypedDict" in source:
        print("   ✅ Using typing_extensions.TypedDict (Python < 3.12 compatible)")
    else:
        print("   ⚠️  Check TypedDict import source")
        
except Exception as e:
    print(f"   ❌ Failed to check TypedDict: {e}")
    errors.append(f"TypedDict error: {e}")

# Test 3: Check for Python 3.9 syntax issues
print("\n3️⃣  Checking for Python 3.9+ syntax compatibility...")
try:
    # Check for pipe union syntax
    import ast
    import glob
    
    files_with_issues = []
    for py_file in glob.glob("app/**/*.py", recursive=True):
        try:
            with open(py_file, 'r') as f:
                content = f.read()
                # Simple check for pipe syntax
                if " | None" in content or "| None" in content:
                    files_with_issues.append(py_file)
        except:
            pass
    
    if files_with_issues:
        print(f"   ❌ Found pipe syntax in: {files_with_issues}")
        errors.append(f"Pipe syntax found in {len(files_with_issues)} files")
    else:
        print("   ✅ No pipe union syntax found (Python 3.9 compatible)")
        
except Exception as e:
    print(f"   ❌ Failed to check syntax: {e}")

# Test 4: Check tool imports
print("\n4️⃣  Testing tool imports...")
try:
    from app.tools import (
        appointment_tools_v2,
        qualification_tools_v2,
        support_tools_v2,
        create_handoff_tool
    )
    print("   ✅ All tools imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import tools: {e}")
    errors.append(f"Tool import error: {e}")

# Test 5: Check agent imports
print("\n5️⃣  Testing agent imports...")
try:
    from app.agents.supervisor import supervisor_node
    from app.agents.sofia_agent_v2 import sofia_node_v2
    from app.agents.carlos_agent_v2 import carlos_node_v2
    from app.agents.maria_agent_v2 import maria_node_v2
    print("   ✅ All agents imported successfully")
except Exception as e:
    print(f"   ❌ Failed to import agents: {e}")
    errors.append(f"Agent import error: {e}")

# Test 6: Check for circular imports
print("\n6️⃣  Checking for circular imports...")
try:
    # Try importing in different orders
    import app
    import app.workflow
    import app.state.conversation_state
    print("   ✅ No circular import issues detected")
except Exception as e:
    print(f"   ❌ Circular import detected: {e}")
    errors.append(f"Circular import: {e}")

# Test 7: Environment variables
print("\n7️⃣  Checking environment variables...")
required_env_vars = [
    "OPENAI_API_KEY",
    "GHL_API_TOKEN", 
    "SUPABASE_URL",
    "SUPABASE_KEY"
]

missing_vars = []
for var in required_env_vars:
    if not os.getenv(var):
        missing_vars.append(var)

if missing_vars:
    print(f"   ⚠️  Missing environment variables: {missing_vars}")
    print("   💡 These will need to be set in LangGraph Platform")
else:
    print("   ✅ All required environment variables are set")

# Summary
print("\n" + "=" * 60)
print("📊 DEPLOYMENT READINESS SUMMARY")
print("=" * 60)

if errors:
    print(f"\n❌ Found {len(errors)} critical issues that will prevent deployment:\n")
    for i, error in enumerate(errors, 1):
        print(f"   {i}. {error}")
    print("\n⚠️  Fix these issues before deploying to LangGraph Platform!")
    sys.exit(1)
else:
    print("\n✅ All critical checks passed!")
    print("🎉 Your code should deploy successfully to LangGraph Platform")
    
    if missing_vars:
        print(f"\n💡 Remember to set these environment variables in LangGraph Platform:")
        for var in missing_vars:
            print(f"   - {var}")
    
    print("\n📝 Next steps:")
    print("   1. Commit and push your changes")
    print("   2. LangGraph Platform will automatically deploy")
    print("   3. Monitor the deployment logs for any runtime issues")
    
    sys.exit(0)