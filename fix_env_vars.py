#!/usr/bin/env python3
"""
Temporarily remove extra env vars that cause pydantic validation errors
"""
import os

# Remove the problematic extra env vars
problematic_vars = [
    'ANTHROPIC_API_KEY',
    'GHL_API_KEY',  # Settings expects GHL_API_TOKEN
    'SUPABASE_SERVICE_KEY',  # Settings expects SUPABASE_KEY
    'LANGSMITH_API_KEY'  # Settings expects LANGCHAIN_API_KEY
]

print("🔧 Fixing environment variables...")
for var in problematic_vars:
    if var in os.environ:
        del os.environ[var]
        print(f"   Removed: {var}")

print("\n✅ Environment cleaned!")

# Now import and test the workflow
if __name__ == "__main__":
    print("\n📊 Testing workflow import...")
    try:
        from app.workflow import workflow
        print("✅ Workflow imported successfully!")
        print(f"   Type: {type(workflow)}")
        if hasattr(workflow, 'nodes'):
            print(f"   Nodes: {list(workflow.nodes.keys())}")
    except Exception as e:
        print(f"❌ Import failed: {e}")