#!/usr/bin/env python3
"""
Test critical imports that are failing in deployment
This simulates what LangGraph Platform is trying to import
"""
import sys
import os

# Add the current directory to Python path like deployment does
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing deployment imports...")
print("=" * 60)

try:
    print("1. Testing app.workflow import...")
    from app.workflow import workflow
    print("✓ Successfully imported workflow")
except Exception as e:
    print(f"✗ Failed to import workflow: {e}")
    import traceback
    traceback.print_exc()

print("\nDone!")