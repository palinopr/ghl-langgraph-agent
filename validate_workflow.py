#!/usr/bin/env python
"""
Quick workflow validation - Run this before git push!
Takes ~5 seconds to validate your workflow will deploy correctly
"""
import sys

def quick_check():
    """Quick validation of workflow structure"""
    print("⚡ Quick Workflow Validation\n")
    
    errors = []
    
    # 1. Try to import and compile workflow
    try:
        from app.workflow import get_optimized_workflow
        workflow = get_optimized_workflow()
        print("✅ Workflow imports successfully")
    except Exception as e:
        print(f"❌ Workflow import failed: {e}")
        errors.append(str(e))
        return errors
    
    # 2. Check for common edge errors
    try:
        # For parallel workflow
        from app.workflow_parallel import create_parallel_workflow
        from langgraph.checkpoint.memory import MemorySaver
        from langgraph.store.memory import InMemoryStore
        
        wf = create_parallel_workflow()
        
        # This is where deployment usually fails - during compilation
        compiled = wf.compile(
            checkpointer=MemorySaver(),
            store=InMemoryStore()
        )
        print("✅ Workflow compiles without errors")
        
        # Check graph structure
        if hasattr(wf, '_edges'):
            print(f"✅ Workflow has {len(wf._edges)} edges defined")
        
    except ValueError as e:
        if "unknown node" in str(e):
            print(f"❌ Edge error: {e}")
            print("   This is the error that breaks deployment!")
            errors.append(str(e))
        else:
            raise
    except Exception as e:
        print(f"❌ Compilation error: {e}")
        errors.append(str(e))
    
    # 3. Quick circular import check
    try:
        from app.constants import FIELD_MAPPINGS
        from app.tools.webhook_enricher import WebhookEnricher
        from app.intelligence.ghl_updater import GHLUpdater
        print("✅ No circular imports")
    except ImportError as e:
        print(f"❌ Circular import: {e}")
        errors.append(str(e))
    
    return errors

if __name__ == "__main__":
    errors = quick_check()
    
    print("\n" + "="*40)
    if errors:
        print("❌ VALIDATION FAILED")
        print("Do NOT deploy - fix these issues first!")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED")
        print("Safe to deploy! 🚀")
        sys.exit(0)