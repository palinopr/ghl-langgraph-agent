#!/usr/bin/env python3
"""
Comprehensive trace analyzer
"""
import os
import json
from langsmith import Client

# The trace ID to analyze
TRACE_ID = "1f0649dd-8dac-6802-9b24-a91f9943836c"

# Set API key
os.environ["LANGSMITH_API_KEY"] = "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"

def analyze_trace():
    """Analyze the trace comprehensively"""
    
    try:
        client = Client()
        
        print(f"\n{'='*80}")
        print(f"COMPREHENSIVE TRACE ANALYSIS: {TRACE_ID}")
        print(f"{'='*80}")
        
        # Get the main run
        run = client.read_run(TRACE_ID)
        
        print(f"\nMain Run Details:")
        print(f"- Name: {run.name}")
        print(f"- Type: {run.run_type}")
        print(f"- Status: {run.status}")
        print(f"- Start: {run.start_time}")
        print(f"- End: {run.end_time}")
        print(f"- Total tokens: {run.total_tokens if hasattr(run, 'total_tokens') else 'N/A'}")
        
        # Show full inputs
        print(f"\n{'='*60}")
        print("FULL INPUTS:")
        print(f"{'='*60}")
        if run.inputs:
            print(json.dumps(run.inputs, indent=2, default=str))
        
        # Show full outputs
        print(f"\n{'='*60}")
        print("FULL OUTPUTS:")
        print(f"{'='*60}")
        if run.outputs:
            output_str = json.dumps(run.outputs, indent=2, default=str)
            if len(output_str) > 2000:
                print(output_str[:2000] + "... [truncated]")
            else:
                print(output_str)
        
        # Get child runs
        try:
            project_id = run.session_id
            child_runs = list(client.list_runs(
                project_id=project_id,
                filter=f'eq(parent_run_id, "{TRACE_ID}")',
                limit=500  # Get more runs
            ))
        except:
            child_runs = []
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        print(f"\n{'='*60}")
        print(f"TOTAL CHILD RUNS: {len(child_runs)}")
        print(f"{'='*60}")
        
        # Categorize runs
        categories = {
            "receptionist": [],
            "tools": [],
            "llm_calls": [],
            "conversation_related": [],
            "ghl_related": [],
            "other": []
        }
        
        for child in child_runs:
            if "receptionist" in child.name.lower():
                categories["receptionist"].append(child)
            elif child.run_type == "tool":
                categories["tools"].append(child)
                # Also check if it's GHL related
                if any(term in str(child.name).lower() or term in str(child.inputs).lower() 
                       for term in ["ghl", "goHighLevel", "conversation", "history", "messages"]):
                    categories["ghl_related"].append(child)
            elif child.run_type == "llm":
                categories["llm_calls"].append(child)
            elif any(term in child.name.lower() for term in ["conversation", "history", "message"]):
                categories["conversation_related"].append(child)
            else:
                categories["other"].append(child)
        
        # Print receptionist details
        print(f"\n{'='*60}")
        print(f"RECEPTIONIST RUNS ({len(categories['receptionist'])} found):")
        print(f"{'='*60}")
        for r in categories["receptionist"]:
            print(f"\n{r.name}")
            print(f"- Start: {r.start_time}")
            print(f"- Status: {r.status}")
            if r.outputs and "messages" in r.outputs:
                # Look for the system message
                for msg in r.outputs.get("messages", []):
                    if msg.get("type") == "system" or "DATA LOADED" in str(msg.get("content", "")):
                        print(f"- System Message Found:")
                        print(f"  {msg.get('content', '')[:500]}...")
        
        # Print all tool calls with details
        print(f"\n{'='*60}")
        print(f"ALL TOOL CALLS ({len(categories['tools'])} found):")
        print(f"{'='*60}")
        for i, tool in enumerate(categories["tools"]):
            print(f"\n{i+1}. {tool.name}")
            print(f"   Start: {tool.start_time}")
            print(f"   Status: {tool.status}")
            
            # Show inputs
            if tool.inputs:
                input_str = json.dumps(tool.inputs, indent=2, default=str)
                if len(input_str) > 300:
                    print(f"   Inputs: {input_str[:300]}...")
                else:
                    print(f"   Inputs: {input_str}")
            
            # Show outputs
            if tool.outputs:
                output_str = json.dumps(tool.outputs, indent=2, default=str)
                if len(output_str) > 300:
                    print(f"   Outputs: {output_str[:300]}...")
                else:
                    print(f"   Outputs: {output_str}")
        
        # Print GHL-related runs
        print(f"\n{'='*60}")
        print(f"GHL/CONVERSATION RELATED ({len(categories['ghl_related'])} found):")
        print(f"{'='*60}")
        for g in categories["ghl_related"]:
            print(f"\n{g.name}")
            if g.inputs:
                print(f"Inputs: {json.dumps(g.inputs, indent=2, default=str)[:500]}...")
            if g.outputs:
                print(f"Outputs: {json.dumps(g.outputs, indent=2, default=str)[:500]}...")
        
        # Look for specific patterns
        print(f"\n{'='*60}")
        print("SEARCHING FOR SPECIFIC PATTERNS:")
        print(f"{'='*60}")
        
        # Check for load_conversation_history
        load_history_found = False
        for child in child_runs:
            if "load_conversation_history" in str(child.name) or \
               "load_conversation_history" in str(child.inputs):
                load_history_found = True
                print(f"\nFOUND load_conversation_history call:")
                print(f"- Name: {child.name}")
                print(f"- Inputs: {child.inputs}")
                print(f"- Outputs: {child.outputs}")
        
        if not load_history_found:
            print("\nNO load_conversation_history calls found!")
            
        # Check for any GHL API endpoints
        print(f"\n{'='*60}")
        print("CHECKING FOR API ENDPOINTS:")
        print(f"{'='*60}")
        for child in child_runs:
            # Convert to string for searching
            child_str = str(child.inputs) + str(child.outputs) if child.outputs else str(child.inputs)
            if any(endpoint in child_str for endpoint in 
                   ["contacts/", "conversations/", "/messages", "custom-values", "api.msgsndr.com"]):
                print(f"\nFound API endpoint reference in: {child.name}")
                print(f"Details: {child_str[:500]}...")
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_trace()