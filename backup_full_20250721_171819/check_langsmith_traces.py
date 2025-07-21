#!/usr/bin/env python3
"""
Check latest traces using LangSmith Client API
Based on the Context7 documentation for LangSmith SDK
"""
import os
import sys
from datetime import datetime, timezone, timedelta

# Try to import langsmith - if not available, provide instructions
try:
    from langsmith import Client
except ImportError:
    print("❌ langsmith package not installed.")
    print("Please install it with: pip install langsmith")
    sys.exit(1)

def check_project_traces():
    """Fetch and analyze recent traces from LangSmith"""
    
    # Initialize client with API key from environment
    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        print("❌ No API key found. Please set LANGCHAIN_API_KEY or LANGSMITH_API_KEY")
        return
    
    try:
        client = Client(api_key=api_key)
        
        # The project name from your .env file
        project_name = "ghl-langgraph-migration"
        
        print(f"🔍 Fetching traces for project: {project_name}")
        print(f"API Key: {api_key[:10]}...")
        print("=" * 80)
        
        # List runs from the project
        runs = client.list_runs(
            project_name=project_name,
            execution_order=1,  # Top-level runs only
            error=False,  # Can change to None to see all runs
            limit=20
        )
        
        # Convert generator to list
        runs_list = list(runs)
        
        print(f"\n✅ Found {len(runs_list)} recent traces")
        
        # Analyze each run
        for i, run in enumerate(runs_list[:10]):  # Show first 10
            print(f"\n📊 Trace {i+1}:")
            print(f"ID: {run.id}")
            print(f"Name: {run.name}")
            print(f"Status: {run.status}")
            print(f"Start Time: {run.start_time}")
            
            # Check inputs
            if run.inputs:
                messages = run.inputs.get('messages', [])
                if messages and isinstance(messages, list) and len(messages) > 0:
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict):
                        content = last_msg.get('content', '')
                        print(f"📥 Message: {content[:100]}...")
                        
                        # Language detection
                        spanish_words = ['hola', 'necesito', 'quiero', 'tengo', 'estoy', 'perdiendo']
                        english_words = ['hello', 'hi', 'need', 'want', 'have', 'i am']
                        
                        content_lower = content.lower()
                        has_spanish = any(word in content_lower for word in spanish_words)
                        has_english = any(word in content_lower for word in english_words)
                        
                        if has_spanish:
                            print("🌐 Language: Spanish")
                        elif has_english:
                            print("🌐 Language: English")
            
            # Check outputs
            if run.outputs:
                print(f"📤 Has outputs: Yes")
                # Check if response is in correct language
                output_str = str(run.outputs)[:200]
                if 'es' in output_str or any(spanish in output_str.lower() for spanish in ['hola', 'gracias', 'perfecto']):
                    print("✅ Response appears to be in Spanish")
                elif any(english in output_str.lower() for english in ['hello', 'thank', 'perfect']):
                    print("⚠️  Response appears to be in English")
            
            # Check for errors
            if run.error:
                print(f"❌ ERROR: {run.error}")
            
            # Check run metadata
            if hasattr(run, 'extra') and run.extra:
                metadata = run.extra.get('metadata', {})
                if metadata:
                    print(f"📋 Metadata: {metadata}")
            
            print("-" * 40)
        
        # Summary analysis
        print(f"\n📈 SUMMARY:")
        
        # Count statuses
        status_counts = {}
        for run in runs_list:
            status = run.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        for status, count in status_counts.items():
            print(f"  {status}: {count}")
        
        # Check deployment timing
        if runs_list:
            latest_run = runs_list[0]
            if latest_run.start_time:
                # Your last deployment was around 10:04 AM CDT on July 21
                deployment_time = datetime(2025, 7, 21, 15, 4, 0, tzinfo=timezone.utc)  # 10:04 AM CDT = 15:04 UTC
                
                run_time = latest_run.start_time
                if isinstance(run_time, str):
                    run_time = datetime.fromisoformat(run_time.replace('Z', '+00:00'))
                
                if run_time > deployment_time:
                    print(f"\n✅ Latest traces are POST-DEPLOYMENT")
                    print("🔍 Language detection fix should be active")
                else:
                    print(f"\n⚠️  Latest traces are pre-deployment")
        
        # Look for specific issues
        print(f"\n🔍 ISSUE DETECTION:")
        
        language_switch_count = 0
        routing_issues = 0
        
        for run in runs_list[:20]:  # Check more runs
            # Check for language switching
            if run.inputs and run.outputs:
                input_msgs = run.inputs.get('messages', [])
                if input_msgs:
                    last_input = input_msgs[-1] if isinstance(input_msgs, list) else {}
                    input_content = last_input.get('content', '') if isinstance(last_input, dict) else ''
                    
                    # Simple Spanish detection
                    if any(word in input_content.lower() for word in ['hola', 'necesito', 'quiero', 'tengo']):
                        # Check if output is in English
                        output_str = str(run.outputs)
                        if any(eng in output_str.lower() for eng in ['hello', 'what', 'how can i help']):
                            language_switch_count += 1
        
        if language_switch_count > 0:
            print(f"⚠️  Found {language_switch_count} potential language switching issues")
        else:
            print(f"✅ No language switching detected")
        
        # Provide specific trace IDs for investigation
        print(f"\n📌 TRACES TO INVESTIGATE:")
        for i, run in enumerate(runs_list[:5]):
            print(f"{i+1}. {run.id} - {run.name} ({run.status})")
            
    except Exception as e:
        print(f"❌ Error accessing LangSmith: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        
        # Provide helpful debugging info
        print(f"\n🔧 Debugging Info:")
        print(f"API Key present: {'Yes' if api_key else 'No'}")
        print(f"API Key format: {'Correct' if api_key and api_key.startswith('lsv2_pt_') else 'Check format'}")

if __name__ == "__main__":
    check_project_traces()