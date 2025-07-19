"""
Analyze LangSmith trace specifically for receptionist contact ID and conversation loading
"""
import os
from langsmith import Client
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize LangSmith client with API key
api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
if not api_key:
    print("Error: No API key found in environment")
    exit(1)
    
client = Client(api_key=api_key)

# Trace ID to analyze
trace_id = "1f0649dd-8dac-6802-9b24-a91f9943836c"

def analyze_receptionist_trace(trace_id):
    """Analyze a trace focusing on receptionist behavior"""
    print(f"\n{'='*80}")
    print(f"ANALYZING RECEPTIONIST TRACE: {trace_id}")
    print('='*80)
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        # Basic info
        print(f"\nMain Run: {run.name}")
        print(f"Type: {run.run_type}")
        print(f"Status: {run.status}")
        print(f"Start Time: {run.start_time}")
        if hasattr(run, 'session_id') and run.session_id:
            print(f"Project/Session ID: {run.session_id}")
        
        # Show full inputs to check contact_id
        print(f"\n{'='*60}")
        print("MAIN RUN INPUTS (checking for contact_id):")
        print('='*60)
        if run.inputs:
            inputs_str = json.dumps(run.inputs, indent=2, default=str)
            print(inputs_str[:1000])
            
            # Check for contact_id
            if "contact_id" in inputs_str:
                print("\n✅ CONTACT_ID FOUND IN MAIN INPUTS")
            else:
                print("\n❌ NO CONTACT_ID IN MAIN INPUTS")
        
        # Get ALL child runs
        print(f"\n{'='*60}")
        print("ANALYZING CHILD RUNS FOR RECEPTIONIST AND CONVERSATION LOADING:")
        print('='*60)
        
        # Try to get child runs without specifying project
        try:
            child_runs = list(client.list_runs(
                filter=f'eq(parent_run_id, "{trace_id}")',
                limit=200
            ))
        except:
            # If that fails, try with the session_id from the main run
            project_name = run.session_id if hasattr(run, 'session_id') else os.getenv("LANGCHAIN_PROJECT", "ghl-langgraph-migration")
            print(f"Using project: {project_name}")
            child_runs = list(client.list_runs(
                project_name=project_name,
                filter=f'eq(parent_run_id, "{trace_id}")',
                limit=200
            ))
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        # Track important findings
        receptionist_runs = []
        get_conversations_calls = []
        contact_id_usage = []
        error_runs = []
        
        for i, child in enumerate(child_runs):
            # Look for receptionist nodes
            if "receptionist" in child.name.lower():
                receptionist_runs.append({
                    "name": child.name,
                    "time": child.start_time,
                    "status": child.status,
                    "inputs": child.inputs,
                    "outputs": child.outputs,
                    "error": child.error
                })
                print(f"\n📍 RECEPTIONIST NODE: {child.name}")
                print(f"   Status: {child.status}")
                if child.inputs:
                    print(f"   Inputs: {json.dumps(child.inputs, indent=2, default=str)[:500]}")
                if child.error:
                    print(f"   ❌ ERROR: {child.error}")
                    
            # Look for get_conversations calls
            if "get_conversations" in child.name.lower() or "conversation" in child.name.lower():
                get_conversations_calls.append({
                    "name": child.name,
                    "time": child.start_time,
                    "status": child.status,
                    "inputs": child.inputs,
                    "outputs": child.outputs
                })
                print(f"\n📞 CONVERSATION LOADING: {child.name}")
                print(f"   Status: {child.status}")
                if child.inputs:
                    inputs_str = json.dumps(child.inputs, indent=2, default=str)
                    print(f"   Inputs: {inputs_str[:500]}")
                    if "contact_id" in inputs_str:
                        print(f"   ✅ Contact ID present in inputs")
                    else:
                        print(f"   ❌ No contact ID in inputs")
                        
            # Track any usage of contact_id
            if child.inputs and "contact_id" in str(child.inputs):
                contact_id_usage.append({
                    "node": child.name,
                    "time": child.start_time,
                    "context": str(child.inputs)[:200]
                })
                
            # Track errors
            if child.error:
                error_runs.append({
                    "name": child.name,
                    "time": child.start_time,
                    "error": child.error
                })
                
            # Show all runs briefly
            status_emoji = "✅" if child.status == "success" else "❌"
            print(f"\n{i+1}. {status_emoji} {child.name} ({child.run_type})")
            
        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY:")
        print('='*60)
        
        print(f"\n1. RECEPTIONIST NODES FOUND: {len(receptionist_runs)}")
        for r in receptionist_runs:
            print(f"   - {r['name']} at {r['time'].strftime('%H:%M:%S')} - Status: {r['status']}")
            
        print(f"\n2. GET_CONVERSATIONS CALLS: {len(get_conversations_calls)}")
        for call in get_conversations_calls:
            print(f"   - {call['name']} at {call['time'].strftime('%H:%M:%S')}")
            
        print(f"\n3. CONTACT_ID USAGE: {len(contact_id_usage)} occurrences")
        for usage in contact_id_usage[:5]:  # Show first 5
            print(f"   - In {usage['node']}: {usage['context']}")
            
        print(f"\n4. ERRORS: {len(error_runs)}")
        for error in error_runs:
            print(f"   - {error['name']}: {error['error']}")
            
        # Look for specific flow issues
        print(f"\n{'='*60}")
        print("FLOW ANALYSIS:")
        print('='*60)
        
        # Check if receptionist came before conversation loading
        receptionist_times = [r['time'] for r in receptionist_runs]
        conversation_times = [c['time'] for c in get_conversations_calls]
        
        if receptionist_times and conversation_times:
            if min(receptionist_times) < min(conversation_times):
                print("✅ Receptionist ran before conversation loading (correct order)")
            else:
                print("❌ Conversation loading happened before receptionist (wrong order)")
        elif not conversation_times:
            print("❌ No conversation loading calls found!")
        elif not receptionist_times:
            print("❌ No receptionist nodes found!")
            
    except Exception as e:
        print(f"Error analyzing trace: {str(e)}")
        import traceback
        traceback.print_exc()

# Run the analysis
analyze_receptionist_trace(trace_id)

print("\n\n🎯 KEY QUESTIONS TO ANSWER:")
print("-" * 40)
print("1. Is contact_id being passed to the receptionist?")
print("2. Is the receptionist calling get_conversations?")
print("3. Are there any errors in conversation loading?")
print("4. What is the exact flow from webhook to receptionist?")