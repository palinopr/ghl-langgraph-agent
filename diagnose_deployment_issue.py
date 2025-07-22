#!/usr/bin/env python3
"""
Diagnose potential deployment issues with the LangGraph agent
"""
import sys
import importlib
import subprocess
from pathlib import Path

def check_python_version():
    """Check Python version compatibility"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    print(f"   Current: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("   ❌ Python 3.11+ required!")
        return False
    else:
        print("   ✅ Python version OK")
        return True


def check_imports():
    """Check if critical imports work"""
    print("\n📦 Checking critical imports...")
    
    critical_imports = [
        ("langgraph.types", "Command"),
        ("langgraph.prebuilt", "InjectedState"),
        ("langgraph.prebuilt", "create_react_agent"),
        ("langchain_core.tools", "tool"),
        ("typing_extensions", "Annotated"),
    ]
    
    all_good = True
    for module_name, attr_name in critical_imports:
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, attr_name):
                print(f"   ✅ {module_name}.{attr_name}")
            else:
                print(f"   ❌ {module_name}.{attr_name} - attribute not found")
                all_good = False
        except ImportError as e:
            print(f"   ❌ {module_name} - {str(e)}")
            all_good = False
    
    return all_good


def check_langgraph_version():
    """Check LangGraph version"""
    print("\n📊 Checking LangGraph version...")
    
    try:
        import langgraph
        version = getattr(langgraph, "__version__", "unknown")
        print(f"   Current version: {version}")
        
        # Parse version
        if version != "unknown":
            parts = version.split(".")
            major = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            
            if major == 0 and minor >= 5 and patch >= 3:
                print("   ✅ LangGraph version OK (>=0.5.3)")
                return True
            else:
                print(f"   ❌ LangGraph version too old (need >=0.5.3, have {version})")
                return False
    except ImportError:
        print("   ❌ LangGraph not installed!")
        return False


def check_supervisor_syntax():
    """Check if supervisor.py compiles"""
    print("\n🔍 Checking supervisor.py syntax...")
    
    try:
        supervisor_path = Path("app/agents/supervisor.py")
        if supervisor_path.exists():
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(supervisor_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("   ✅ supervisor.py compiles successfully")
                return True
            else:
                print(f"   ❌ supervisor.py compilation error: {result.stderr}")
                return False
        else:
            print("   ❌ supervisor.py not found!")
            return False
    except Exception as e:
        print(f"   ❌ Error checking supervisor.py: {e}")
        return False


def check_command_import_location():
    """Try different import locations for Command"""
    print("\n🔍 Checking Command import locations...")
    
    possible_imports = [
        "from langgraph.types import Command",
        "from langgraph.pregel import Command",
        "from langgraph.graph import Command",
        "from langgraph import Command",
    ]
    
    for import_stmt in possible_imports:
        try:
            exec(import_stmt)
            print(f"   ✅ Works: {import_stmt}")
            return import_stmt
        except ImportError:
            print(f"   ❌ Failed: {import_stmt}")
    
    return None


def suggest_fixes():
    """Suggest fixes based on diagnostics"""
    print("\n💡 Suggested Fixes:")
    print("=" * 60)
    
    # Check if Command needs different import
    correct_import = check_command_import_location()
    if correct_import and correct_import != "from langgraph.types import Command":
        print(f"\n1. Update Command import in supervisor.py:")
        print(f"   Replace: from langgraph.types import Command")
        print(f"   With: {correct_import}")
    
    # Check if we need to update requirements
    print("\n2. Ensure requirements.txt has latest versions:")
    print("   langgraph>=0.5.3")
    print("   langchain-core>=0.3.42")
    print("   typing-extensions>=4.12.0")
    
    # Alternative approach if Command doesn't work
    print("\n3. If Command objects don't work, use alternative pattern:")
    print("   Instead of returning Command objects from tools,")
    print("   return dict with routing information and handle in supervisor_node")


def main():
    """Run all diagnostics"""
    print("🔍 LangGraph Deployment Diagnostics")
    print("=" * 60)
    
    checks = [
        check_python_version(),
        check_imports(),
        check_langgraph_version(),
        check_supervisor_syntax(),
    ]
    
    if all(checks):
        print("\n✅ All checks passed!")
        print("   The issue might be in the deployment environment.")
        print("   Check GitHub Actions logs for specific errors.")
    else:
        print("\n❌ Some checks failed!")
        suggest_fixes()


if __name__ == "__main__":
    main()