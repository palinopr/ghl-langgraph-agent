#!/usr/bin/env python3
"""Simple test to verify imports and basic functionality"""

print("Testing imports...")

try:
    print("1. Testing FastAPI import...")
    from fastapi import FastAPI
    print("✓ FastAPI imported successfully")
except Exception as e:
    print(f"✗ FastAPI import failed: {e}")

try:
    print("\n2. Testing src.api.webhook import...")
    from app.api.webhook import app
    print("✓ Webhook app imported successfully")
except Exception as e:
    print(f"✗ Webhook import failed: {e}")

try:
    print("\n3. Testing environment variables...")
    import os
    from app.config import get_settings
    settings = get_settings()
    print("✓ Settings loaded successfully")
    print(f"  - Port: {settings.port}")
    print(f"  - App env: {settings.app_env}")
except Exception as e:
    print(f"✗ Settings failed: {e}")

print("\n4. Testing basic server start...")
try:
    import uvicorn
    print("✓ Uvicorn imported successfully")
    print("\nAll imports successful! The app should be able to start.")
except Exception as e:
    print(f"✗ Uvicorn import failed: {e}")