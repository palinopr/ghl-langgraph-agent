#!/usr/bin/env python3
"""
Fetch and analyze trace 1f065ab7-af0c-6b8f-b629-457ad5e5145c
"""
import os
import json
import urllib.request
import urllib.error
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def format_timestamp(ts):
    """Format timestamp for readability"""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime('%H:%M:%S.%f')[:-3]
        except:
            return ts
    return str(ts)

def fetch_trace():
    trace_id = '1f065ab7-af0c-6b8f-b629-457ad5e5145c'
    
    # Try both possible env var names
    api_key = os.getenv('LANGSMITH_API_KEY') or os.getenv('LANGCHAIN_API_KEY')
    
    if not api_key:
        print('❌ No API key found')
        return
    
    print(f'🔍 Fetching trace: {trace_id}')
    print('=' * 80)
    
    url = f'https://api.smith.langchain.com/runs/{trace_id}'
    headers = {
        'x-api-key': api_key,
        'Content-Type': 'application/json'
    }
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            # Basic info
            print(f"Name: {data.get('name', 'N/A')}")
            print(f"Status: {data.get('status', 'N/A')}")
            print(f"Run Type: {data.get('run_type', 'N/A')}")
            print(f"Start Time: {format_timestamp(data.get('start_time'))}")
            print(f"End Time: {format_timestamp(data.get('end_time'))}")
            
            # Save full trace
            with open(f'trace_{trace_id[:8]}.json', 'w') as f:
                json.dump(data, f, indent=2)
            
            # Inputs
            print('\n📥 INPUTS:')
            inputs = data.get('inputs', {})
            
            # Check for webhook data
            if 'webhook_data' in inputs:
                wd = inputs['webhook_data']
                print(f"  Contact ID: {wd.get('contactId', 'N/A')}")
                print(f"  Message: {wd.get('message', 'N/A')}")
                print(f"  Type: {wd.get('type', 'N/A')}")
            
            # Check for messages
            if 'messages' in inputs:
                msgs = inputs['messages']
                print(f"  Messages: {len(msgs)} total")
                if msgs:
                    last_msg = msgs[-1]
                    print(f"  Last message: {last_msg.get('content', 'N/A')[:100]}...")
            
            # Outputs
            print('\n📤 OUTPUTS:')
            outputs = data.get('outputs', {})
            
            # Look for key output fields
            if 'lead_score' in outputs:
                print(f"  Lead Score: {outputs['lead_score']}")
            if 'next_agent' in outputs:
                print(f"  Next Agent: {outputs['next_agent']}")
            if 'messages' in outputs:
                out_msgs = outputs['messages']
                if out_msgs and isinstance(out_msgs, list) and len(out_msgs) > 0:
                    last_out = out_msgs[-1]
                    if isinstance(last_out, dict):
                        print(f"  Response: {last_out.get('content', 'N/A')[:100]}...")
            
            # Errors
            if data.get('error'):
                print('\n❌ ERROR:')
                print(data['error'])
            
            # Check for child runs (to see which nodes executed)
            print('\n🔄 EXECUTION FLOW:')
            
            # Fetch child runs
            child_url = f'https://api.smith.langchain.com/runs?filter=eq(parent_run_id, "{trace_id}")&limit=50'
            child_req = urllib.request.Request(child_url, headers=headers)
            
            try:
                with urllib.request.urlopen(child_req) as child_response:
                    child_data = json.loads(child_response.read().decode())
                    runs = child_data.get('runs', [])
                    
                    # Sort by start time
                    runs.sort(key=lambda x: x.get('start_time', ''))
                    
                    for run in runs:
                        name = run.get('name', 'Unknown')
                        status = run.get('status', 'unknown')
                        run_type = run.get('run_type', '')
                        
                        # Skip certain types
                        if run_type in ['llm', 'parser']:
                            continue
                            
                        time = format_timestamp(run.get('start_time'))
                        
                        # Show status emoji
                        emoji = '✅' if status == 'success' else '❌' if status == 'error' else '🔄'
                        
                        print(f"  {time} {emoji} {name}")
                        
                        # Check for specific important nodes
                        if 'receptionist' in name.lower():
                            if run.get('outputs'):
                                score = run['outputs'].get('lead_score', 'N/A')
                                print(f"       → Score: {score}")
                        
                        if 'supervisor' in name.lower():
                            if run.get('outputs'):
                                next_agent = run['outputs'].get('next_agent', 'N/A')
                                print(f"       → Routes to: {next_agent}")
                        
                        if 'sofia' in name.lower() or 'carlos' in name.lower() or 'maria' in name.lower():
                            if run.get('inputs'):
                                print(f"       → Agent: {name}")
                        
                        if run.get('error'):
                            print(f"       → Error: {run['error'][:100]}...")
            
            except Exception as e:
                print(f"Could not fetch child runs: {e}")
            
            print(f'\n💾 Full trace saved to: trace_{trace_id[:8]}.json')
            print('\n📋 ANALYSIS SUMMARY:')
            
            # Analyze what happened
            if 'error' in data:
                print("❌ The workflow failed with an error")
            elif outputs.get('messages'):
                print("✅ The workflow completed and sent a response")
            else:
                print("⚠️ The workflow completed but may not have sent a response")
                
    except urllib.error.HTTPError as e:
        print(f'❌ HTTP Error {e.code}: {e.reason}')
        try:
            error_body = e.read().decode()
            print(f'Response: {error_body}')
        except:
            pass
    except Exception as e:
        print(f'❌ Error: {str(e)}')

if __name__ == '__main__':
    fetch_trace()