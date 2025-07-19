"""
Analyze LangSmith traces to debug double message issue
"""
import os
from langsmith import Client
from datetime import datetime
import json

# Initialize LangSmith client
client = Client()

# Trace IDs to analyze
trace_ids = [
    "1f064982-efbc-6aba-9b85-f3b5227b2c2b",
    "1f064974-3f93-6d5e-a756-1dd912bc6798"
]

def analyze_trace(trace_id):
    """Analyze a single trace"""
    print(f"\n{'='*60}")
    print(f"ANALYZING TRACE: {trace_id}")
    print('='*60)
    
    try:
        # Get the run
        run = client.read_run(trace_id)
        
        # Basic info
        print(f"\nName: {run.name}")
        print(f"Run Type: {run.run_type}")
        print(f"Status: {run.status}")
        print(f"Start Time: {run.start_time}")
        print(f"End Time: {run.end_time}")
        print(f"Total Tokens: {run.total_tokens if hasattr(run, 'total_tokens') else 'N/A'}")
        
        # Inputs
        print(f"\n📥 INPUTS:")
        if run.inputs:
            print(json.dumps(run.inputs, indent=2, default=str)[:500] + "...")
        
        # Outputs
        print(f"\n📤 OUTPUTS:")
        if run.outputs:
            print(json.dumps(run.outputs, indent=2, default=str)[:500] + "...")
        
        # Check for errors
        if run.error:
            print(f"\n❌ ERROR: {run.error}")
        
        # Get child runs to see the flow
        print(f"\n🔄 CHILD RUNS:")
        child_runs = list(client.list_runs(
            project_name=os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent"),
            filter=f'eq(parent_run_id, "{trace_id}")',
            limit=10
        ))
        
        for i, child in enumerate(child_runs):
            print(f"  {i+1}. {child.name} ({child.run_type}) - {child.status}")
            if child.name == "ChatOpenAI" and child.outputs:
                # Show the AI response
                try:
                    content = child.outputs.get("generations", [[{}]])[0][0].get("text", "")
                    if not content and "message" in child.outputs.get("generations", [[{}]])[0][0]:
                        content = child.outputs["generations"][0][0]["message"].get("content", "")
                    if content:
                        print(f"     Response: {content[:100]}...")
                except:
                    pass
        
        # Look for specific patterns
        print(f"\n🔍 ANALYSIS:")
        
        # Check if it's a webhook run
        if "webhook" in run.name.lower():
            print("  - This is a webhook processing run")
            
        # Check for language in inputs
        if run.inputs:
            inputs_str = json.dumps(run.inputs, default=str).lower()
            if "hola" in inputs_str:
                print("  - Spanish input detected ('Hola')")
            if "jaime" in inputs_str:
                print("  - Name 'Jaime' found in input")
                
        # Check for Maria agent
        if "maria" in run.name.lower():
            print("  - Maria agent was involved")
            
        # Check outputs for both languages
        if run.outputs:
            outputs_str = json.dumps(run.outputs, default=str)
            has_spanish = "¡Hola!" in outputs_str or "Ayudo a las empresas" in outputs_str
            has_english = "Hi!" in outputs_str or "I help businesses" in outputs_str
            
            if has_spanish and has_english:
                print("  - ⚠️ BOTH Spanish AND English responses found!")
            elif has_spanish:
                print("  - Spanish response found")
            elif has_english:
                print("  - English response found")
                
    except Exception as e:
        print(f"Error analyzing trace {trace_id}: {str(e)}")

def compare_traces(trace_ids):
    """Compare the two traces to find differences"""
    print(f"\n\n{'='*60}")
    print("COMPARING TRACES")
    print('='*60)
    
    runs = []
    for trace_id in trace_ids:
        try:
            run = client.read_run(trace_id)
            runs.append(run)
        except:
            print(f"Could not load trace {trace_id}")
            
    if len(runs) == 2:
        # Compare timing
        time_diff = abs((runs[0].start_time - runs[1].start_time).total_seconds())
        print(f"\nTime difference between runs: {time_diff} seconds")
        
        if time_diff < 5:
            print("⚠️ Runs started within 5 seconds - possible duplicate processing!")
            
        # Compare inputs
        if runs[0].inputs == runs[1].inputs:
            print("⚠️ Both runs have IDENTICAL inputs - likely duplicate webhook!")
        else:
            print("✓ Runs have different inputs")
            
        # Check which agents were used
        print("\nAgent usage:")
        for i, run in enumerate(runs):
            agent = "Unknown"
            if "maria" in str(run.name).lower():
                agent = "Maria"
            elif "carlos" in str(run.name).lower():
                agent = "Carlos"
            elif "sofia" in str(run.name).lower():
                agent = "Sofia"
            print(f"  Trace {i+1}: {agent}")

# Analyze each trace
for trace_id in trace_ids:
    analyze_trace(trace_id)

# Compare traces
compare_traces(trace_ids)

print("\n\n🎯 CONCLUSION:")
print("-" * 40)
print("Check the analysis above to see:")
print("1. If both traces processed the same message")
print("2. If responses were in different languages")
print("3. If there's duplicate webhook processing")
print("4. The time gap between executions")