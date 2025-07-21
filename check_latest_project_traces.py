#!/usr/bin/env python3
"""
Check latest traces for project: a807d9fb-2c58-4d09-a4b2-4037e0668fcc
"""
import os
import json
from datetime import datetime, timezone, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

# LangSmith API configuration
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "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")
PROJECT_ID = "a807d9fb-2c58-4d09-a4b2-4037e0668fcc"

def get_latest_traces(limit=10):
    """Fetch latest traces from the project"""
    url = f"https://api.smith.langchain.com/api/v1/runs"
    
    # Get traces from last 24 hours
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=24)
    
    headers = {
        "x-api-key": LANGSMITH_API_KEY,
        "Content-Type": "application/json"
    }
    
    params = {
        "project_id": PROJECT_ID,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "limit": limit,
        "order": "desc"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            runs = data.get("runs", [])
            
            print(f"🔍 Found {len(runs)} recent traces in project")
            print("=" * 80)
            
            for i, run in enumerate(runs):
                print(f"\n📊 Trace {i+1}:")
                print(f"ID: {run.get('id')}")
                print(f"Name: {run.get('name')}")
                print(f"Status: {run.get('status')}")
                print(f"Start Time: {run.get('start_time')}")
                
                # Check for errors
                if run.get('error'):
                    print(f"❌ ERROR: {run.get('error')}")
                
                # Show input message
                inputs = run.get('inputs', {})
                if isinstance(inputs, dict):
                    messages = inputs.get('messages', [])
                    if messages and isinstance(messages, list) and len(messages) > 0:
                        last_msg = messages[-1]
                        if isinstance(last_msg, dict):
                            content = last_msg.get('content', '')
                            print(f"📥 Input: {content[:100]}...")
                
                # Show output
                outputs = run.get('outputs', {})
                if outputs:
                    print(f"📤 Output preview: {str(outputs)[:100]}...")
                
                # Execution metadata
                if run.get('execution_metadata'):
                    meta = run.get('execution_metadata', {})
                    if 'deployment' in str(meta):
                        print(f"🚀 Deployment: Yes")
                
                print("-" * 40)
            
            # Summary
            print(f"\n📈 SUMMARY:")
            successful = sum(1 for r in runs if r.get('status') == 'success')
            failed = sum(1 for r in runs if r.get('status') == 'error')
            pending = sum(1 for r in runs if r.get('status') in ['pending', 'running'])
            
            print(f"✅ Successful: {successful}")
            print(f"❌ Failed: {failed}")
            print(f"⏳ Pending/Running: {pending}")
            
            # Check for patterns in errors
            if failed > 0:
                print(f"\n⚠️  ERROR ANALYSIS:")
                error_types = {}
                for run in runs:
                    if run.get('error'):
                        error_msg = str(run.get('error'))
                        # Categorize errors
                        if 'language' in error_msg.lower():
                            error_types['Language Detection'] = error_types.get('Language Detection', 0) + 1
                        elif 'routing' in error_msg.lower():
                            error_types['Routing'] = error_types.get('Routing', 0) + 1
                        elif 'supervisor' in error_msg.lower():
                            error_types['Supervisor'] = error_types.get('Supervisor', 0) + 1
                        else:
                            error_types['Other'] = error_types.get('Other', 0) + 1
                
                for error_type, count in error_types.items():
                    print(f"  - {error_type}: {count} errors")
            
            return runs
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"Response: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching traces: {str(e)}")
        return []

if __name__ == "__main__":
    print(f"🔍 Checking latest traces for project: {PROJECT_ID}")
    print(f"Time: {datetime.now()}")
    print("=" * 80)
    
    traces = get_latest_traces(limit=20)
    
    if traces:
        print(f"\n💡 INSIGHTS:")
        
        # Check deployment status
        latest = traces[0] if traces else None
        if latest:
            latest_time = datetime.fromisoformat(latest.get('start_time', '').replace('Z', '+00:00'))
            deployment_time = datetime(2025, 7, 21, 15, 4, 0, tzinfo=timezone.utc)  # Approximate deployment time
            
            if latest_time > deployment_time:
                print("✅ Traces are POST-DEPLOYMENT")
                print("🔍 Language detection fix should be active")
            else:
                print("⚠️  Traces are pre-deployment")
        
        # Language analysis
        spanish_count = 0
        english_count = 0
        
        for run in traces:
            inputs = run.get('inputs', {})
            if isinstance(inputs, dict):
                messages = inputs.get('messages', [])
                if messages and isinstance(messages, list):
                    for msg in messages:
                        if isinstance(msg, dict):
                            content = msg.get('content', '')
                            # Simple language detection
                            spanish_words = ['hola', 'gracias', 'necesito', 'quiero', 'tengo', 'estoy']
                            english_words = ['hello', 'hi', 'thanks', 'need', 'want', 'have']
                            
                            if any(word in content.lower() for word in spanish_words):
                                spanish_count += 1
                            elif any(word in content.lower() for word in english_words):
                                english_count += 1
        
        print(f"\n🌐 LANGUAGE DISTRIBUTION:")
        print(f"  - Spanish messages: {spanish_count}")
        print(f"  - English messages: {english_count}")