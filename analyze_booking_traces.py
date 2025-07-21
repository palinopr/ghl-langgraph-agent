#!/usr/bin/env python3
"""
Analyze the booking flow traces using LangSmith SDK
"""
import os
from langsmith import Client
from datetime import datetime, timezone
import json
import sys

# Set up the client
os.environ["LANGSMITH_API_KEY"] = "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"
client = Client()

def format_timestamp(ts):
    """Format timestamp for readability"""
    if isinstance(ts, str):
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
    else:
        dt = ts
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def analyze_trace(trace_id):
    """Analyze a single trace"""
    print(f"\n{'='*80}")
    print(f"📊 Analyzing Trace: {trace_id}")
    print(f"{'='*80}")
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        # Basic info
        print(f"\n📌 Basic Information:")
        print(f"  - Name: {run.name}")
        print(f"  - Status: {run.status}")
        print(f"  - Start: {format_timestamp(run.start_time)}")
        if run.end_time:
            print(f"  - End: {format_timestamp(run.end_time)}")
            duration = (run.end_time - run.start_time).total_seconds()
            print(f"  - Duration: {duration:.2f}s")
        
        # Input analysis
        print(f"\n📥 Input Analysis:")
        if run.inputs:
            if 'messages' in run.inputs:
                messages = run.inputs['messages']
                if messages:
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict):
                        print(f"  - Last Message: {last_msg.get('content', 'N/A')}")
            if 'contact_id' in run.inputs:
                print(f"  - Contact ID: {run.inputs['contact_id']}")
        
        # Output analysis
        print(f"\n📤 Output Analysis:")
        if run.outputs:
            if 'messages' in run.outputs:
                output_messages = run.outputs['messages']
                if output_messages:
                    last_output = output_messages[-1]
                    if isinstance(last_output, dict):
                        print(f"  - Response: {last_output.get('content', 'N/A')[:100]}...")
            
            # Check extracted data
            if 'extracted_data' in run.outputs:
                print(f"  - Extracted Data: {json.dumps(run.outputs['extracted_data'], indent=4)}")
            
            # Check lead score
            if 'lead_score' in run.outputs:
                print(f"  - Lead Score: {run.outputs['lead_score']}")
            
            # Check current agent
            if 'current_agent' in run.outputs:
                print(f"  - Current Agent: {run.outputs['current_agent']}")
        
        # Error analysis
        if run.error:
            print(f"\n❌ Error Found:")
            print(f"  - Error: {run.error}")
        
        # Get child runs for detailed flow
        print(f"\n🔍 Execution Flow:")
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{trace_id}")',
            limit=50
        ))
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        # Show the flow
        for i, child in enumerate(child_runs[:20], 1):  # Limit to first 20
            indent = "  "
            status_emoji = "✅" if child.status == "success" else "❌"
            print(f"{indent}{i}. {status_emoji} {child.name}")
            
            # Show key details for important nodes
            if "supervisor" in child.name.lower():
                if child.outputs:
                    if 'current_agent' in child.outputs:
                        print(f"{indent}    → Routed to: {child.outputs['current_agent']}")
                    if 'lead_score' in child.outputs:
                        print(f"{indent}    → Score: {child.outputs['lead_score']}")
            
            elif "intelligence" in child.name.lower():
                if child.outputs:
                    if 'lead_score' in child.outputs:
                        print(f"{indent}    → Calculated Score: {child.outputs['lead_score']}")
                    if 'extracted_data' in child.outputs:
                        extracted = child.outputs['extracted_data']
                        if extracted:
                            print(f"{indent}    → Extracted: {json.dumps(extracted, ensure_ascii=False)}")
            
            elif any(agent in child.name.lower() for agent in ["maria", "carlos", "sofia"]):
                if child.outputs and 'messages' in child.outputs:
                    msgs = child.outputs['messages']
                    if msgs and isinstance(msgs[-1], dict):
                        response = msgs[-1].get('content', '')[:80]
                        print(f"{indent}    → Response: {response}...")
            
            # Show errors
            if child.error:
                print(f"{indent}    ❌ ERROR: {child.error}")
        
        # Look for specific issues
        print(f"\n🔎 Issue Detection:")
        
        # Check for appointment booking
        appointment_found = False
        for child in child_runs:
            if "appointment" in str(child.name).lower() or "book" in str(child.name).lower():
                appointment_found = True
                print(f"  - Appointment Tool Called: {child.name}")
                if child.outputs:
                    print(f"    Result: {json.dumps(child.outputs, indent=4)}")
        
        if not appointment_found:
            print("  - ⚠️  No appointment booking detected")
        
        # Check for Sofia involvement
        sofia_found = any("sofia" in child.name.lower() for child in child_runs)
        if sofia_found:
            print("  - ✅ Sofia agent was activated")
        else:
            print("  - ⚠️  Sofia agent was NOT activated (needed for appointments)")
        
        return run
        
    except Exception as e:
        print(f"❌ Error analyzing trace {trace_id}: {str(e)}")
        return None

def main():
    """Main analysis function"""
    trace_ids = [
        "1f0666ce-dd6e-602b-9a98-381d8a6d73e4",
        "1f0666cf-d7c4-6f3f-b89f-d384ff4c6ba0"
    ]
    
    print("🔍 TRACE ANALYSIS - Appointment Booking Flow")
    print("="*80)
    print(f"Project: ghl-langgraph-agent")
    print(f"Analyzing {len(trace_ids)} traces")
    
    runs = []
    for trace_id in trace_ids:
        run = analyze_trace(trace_id)
        if run:
            runs.append(run)
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY")
    print(f"{'='*80}")
    
    if runs:
        # Check for patterns
        print("\n🎯 Key Findings:")
        
        # Check scores
        scores = []
        for run in runs:
            if run.outputs and 'lead_score' in run.outputs:
                scores.append(run.outputs['lead_score'])
        
        if scores:
            print(f"  - Lead Scores: {scores}")
            print(f"  - Score Progression: {' → '.join(map(str, scores))}")
        
        # Check agents
        agents = []
        for run in runs:
            if run.outputs and 'current_agent' in run.outputs:
                agents.append(run.outputs['current_agent'])
        
        if agents:
            print(f"  - Agent Routing: {' → '.join(agents)}")
        
        # Check for appointment success
        appointment_traces = [r for r in runs if r.outputs and 'appointment' in str(r.outputs).lower()]
        if appointment_traces:
            print(f"  - ✅ Appointment booking attempted in {len(appointment_traces)} trace(s)")
        else:
            print(f"  - ❌ No appointment booking detected in any trace")

if __name__ == "__main__":
    main()