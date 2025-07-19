#!/usr/bin/env python3
"""
Analyze a specific trace to understand what's happening
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

def analyze_trace(trace_id: str):
    """Analyze a specific trace from LangSmith"""
    
    print(f"\n🔍 ANALYZING TRACE: {trace_id}")
    print("="*60)
    
    # Check if we have LangSmith credentials
    api_key = os.getenv('LANGCHAIN_API_KEY') or os.getenv('LANGSMITH_API_KEY')
    if not api_key:
        print("❌ No LangSmith API key found")
        print("\nTo analyze traces, you need to:")
        print("1. Go to https://smith.langchain.com")
        print("2. Find the trace ID: " + trace_id)
        print("3. Look for:")
        print("   - Input messages")
        print("   - State at each step")
        print("   - Tool calls made")
        print("   - Final output")
        return
    
    print("\n📊 What to look for in the trace:")
    print("\n1. RECEPTIONIST NODE:")
    print("   - Is conversation history loaded?")
    print("   - Are custom fields populated?")
    print("   - What's the initial state?")
    
    print("\n2. SUPERVISOR NODE:")
    print("   - What's the lead score?")
    print("   - Which agent is selected?")
    print("   - Is data extracted correctly?")
    
    print("\n3. AGENT NODE (Sofia/Carlos/Maria):")
    print("   - What tools are called?")
    print("   - Is conversation context used?")
    print("   - What's the response?")
    
    print("\n4. SPECIFIC CHECKS:")
    print("   - Is budget being extracted from time (10:00 AM → $10)?")
    print("   - Is appointment tool being called?")
    print("   - Are available slots loaded?")
    print("   - Is conversation enforcer working?")
    
    print("\n5. ERROR SIGNS:")
    print("   - 'Unknown node' errors")
    print("   - Missing state keys")
    print("   - Tool failures")
    print("   - Routing loops")

if __name__ == "__main__":
    trace_id = "1f064cd1-554a-6fd6-b196-9d317c823332"
    
    print("🧪 TRACE ANALYSIS GUIDE")
    print(f"Trace ID: {trace_id}")
    print("\nSince we can't access LangSmith programmatically,")
    print("here's what to check manually:")
    
    analyze_trace(trace_id)
    
    print("\n\n📝 COMMON ISSUES IN PRODUCTION:")
    print("\n1. Environment differences:")
    print("   - Different LLM model versions")
    print("   - Missing environment variables")
    print("   - Different Python versions")
    
    print("\n2. Data differences:")
    print("   - Contact has existing conversation history")
    print("   - Custom fields already populated")
    print("   - Different GHL configuration")
    
    print("\n3. Deployment issues:")
    print("   - Old code cached")
    print("   - Imports not working")
    print("   - Memory/timeout limits")
    
    print("\n\n🔧 TO REPLICATE LOCALLY:")
    print("1. Get the exact input from the trace")
    print("2. Check the contact's existing data in GHL")
    print("3. Set up the same initial state")
    print("4. Run with the same message")
    
    print("\n\nPlease share:")
    print("1. The error message from the trace")
    print("2. Which node failed")
    print("3. The input/output at that step")
    print("4. Any tool call results")