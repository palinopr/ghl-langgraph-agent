#!/bin/bash
# Setup EXACT environment to match LangGraph deployment

echo "🚀 Setting up EXACT LangGraph environment locally"
echo "================================================="

# 1. Check Python version
echo "📍 Step 1: Checking Python version..."
REQUIRED_PYTHON="3.13"
CURRENT_PYTHON=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)

if [ "$CURRENT_PYTHON" != "$REQUIRED_PYTHON" ]; then
    echo "❌ Python $REQUIRED_PYTHON required, but you have Python $CURRENT_PYTHON"
    echo "Please install Python 3.13:"
    echo "  brew install python@3.13"
    exit 1
else
    echo "✅ Python $REQUIRED_PYTHON found"
fi

# 2. Create virtual environment with Python 3.13
echo -e "\n📍 Step 2: Creating virtual environment..."
python3.13 -m venv venv_langgraph
source venv_langgraph/bin/activate

# 3. Upgrade pip and install wheel
echo -e "\n📍 Step 3: Upgrading pip..."
pip install --upgrade pip wheel setuptools

# 4. Install EXACT dependencies from requirements.txt
echo -e "\n📍 Step 4: Installing exact dependencies..."
pip install -r requirements.txt

# 5. Install additional dependencies that might be missing
echo -e "\n📍 Step 5: Installing additional dependencies..."
pip install \
    langsmith \
    httpx \
    python-dotenv \
    aiohttp \
    tenacity \
    orjson

# 6. Setup environment variables
echo -e "\n📍 Step 6: Setting up environment variables..."
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Copy .env.example and fill in your values:"
    echo "  cp .env.example .env"
    exit 1
else
    echo "✅ .env file found"
fi

# 7. Create test script
echo -e "\n📍 Step 7: Creating test script..."
cat > test_environment.py << 'EOF'
#!/usr/bin/env python3
"""Test if environment matches LangGraph deployment"""
import sys
import os
from importlib import import_module

print("🔍 Testing Environment Setup")
print("="*50)

# Check Python version
print(f"Python Version: {sys.version}")
if not sys.version.startswith("3.13"):
    print("❌ Wrong Python version! Need 3.13.x")
else:
    print("✅ Python version correct")

# Check critical imports
modules_to_check = [
    "langchain",
    "langgraph", 
    "langsmith",
    "httpx",
    "dotenv",
    "app.workflow",
    "app.agents.supervisor_brain_simple",
    "app.tools.ghl_client"
]

print("\nChecking imports:")
for module in modules_to_check:
    try:
        if module.startswith("app."):
            # Add current directory to path
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import_module(module)
        print(f"✅ {module}")
    except ImportError as e:
        print(f"❌ {module}: {str(e)}")

# Check environment variables
print("\nChecking environment variables:")
env_vars = [
    "OPENAI_API_KEY",
    "GHL_API_TOKEN",
    "GHL_LOCATION_ID",
    "GHL_CALENDAR_ID",
    "SUPABASE_URL"
]

from dotenv import load_dotenv
load_dotenv()

for var in env_vars:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {'*' * 8}{value[-4:]}")
    else:
        print(f"❌ {var}: Not set")

print("\n✅ Environment setup complete!")
EOF

# 8. Run the test
echo -e "\n📍 Step 8: Testing environment..."
python test_environment.py

echo -e "\n✅ Setup complete!"
echo ""
echo "To activate this environment in the future:"
echo "  source venv_langgraph/bin/activate"
echo ""
echo "To run the workflow:"
echo "  python app.py"