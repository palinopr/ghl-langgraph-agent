#!/usr/bin/env python3
"""Test all imports to find the issue"""
import sys
print(f"Python version: {sys.version}")
print(f"Python path: {sys.executable}")
print("-" * 50)

# Test each import step by step
tests = [
    ("FastAPI", "from fastapi import FastAPI"),
    ("Pydantic", "from pydantic import BaseModel"),
    ("Pydantic Settings", "from pydantic_settings import BaseSettings"),
    ("Dotenv", "from dotenv import load_dotenv"),
    ("Config", "from app.config import get_settings"),
    ("Simple Logger", "from app.utils.simple_logger import get_logger"),
    ("Webhook App", "from app.api.webhook import app"),
    ("Workflow", "from app.workflow import run_workflow"),
    ("Webhook Processor", "from app.tools.webhook_processor import webhook_processor"),
    ("Supabase Client", "from app.tools.supabase_client import supabase_client"),
    ("GHL Client", "from app.tools.ghl_client import ghl_client"),
]

for name, import_str in tests:
    print(f"\nTesting {name}...")
    try:
        exec(import_str)
        print(f"✓ {name} imported successfully")
    except Exception as e:
        print(f"✗ {name} failed: {type(e).__name__}: {e}")
        if "No module named" not in str(e):
            import traceback
            traceback.print_exc()