#!/usr/bin/env python3
"""
Export a LangSmith trace to JSON with all details
"""
import json
import os
from datetime import datetime
from langsmith import Client

def export_trace_to_json(trace_id: str, api_key: str, output_file: str):
    """Export a complete trace to JSON"""
    
    # Initialize client
    client = Client(api_key=api_key)
    
    print(f"🔍 Fetching trace: {trace_id}")
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        
        # Build the trace data
        trace_data = {
            "trace_id": str(run.id),
            "name": run.name,
            "status": run.status,
            "start_time": run.start_time.isoformat() if run.start_time else None,
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "duration_seconds": (run.end_time - run.start_time).total_seconds() if run.end_time and run.start_time else None,
            "inputs": run.inputs if run.inputs else {},
            "outputs": run.outputs if run.outputs else {},
            "error": run.error if run.error else None,
            "metadata": {},
            "child_runs": []
        }
        
        # Extract metadata
        if hasattr(run, 'extra') and run.extra:
            metadata = run.extra.get('metadata', {})
            trace_data['metadata'] = {
                "thread_id": metadata.get('thread_id'),
                "user_id": metadata.get('user_id'),
                "assistant_id": metadata.get('assistant_id'),
                "langgraph_version": metadata.get('langgraph_version'),
                "graph_id": metadata.get('graph_id'),
                "run_attempt": metadata.get('run_attempt'),
                "x_real_ip": metadata.get('x-real-ip'),
                "x_request_id": metadata.get('x-request-id'),
                "revision_id": metadata.get('revision_id'),
                "created_by": metadata.get('created_by'),
                "all_metadata": metadata  # Include all metadata
            }
        
        # Try to get child runs using different approaches
        print("📊 Fetching child runs...")
        child_runs = []
        
        # Method 1: Try using session_id
        if hasattr(run, 'session_id') and run.session_id:
            try:
                session_runs = list(client.list_runs(
                    project_name="ghl-langgraph-agent",
                    execution_order=1,
                    start_time=run.start_time,
                    limit=100
                ))
                
                # Filter runs that are likely children based on timing
                for r in session_runs:
                    if (r.id != trace_id and 
                        r.start_time >= run.start_time and 
                        r.end_time <= run.end_time):
                        child_runs.append(r)
                        
            except Exception as e:
                print(f"  Method 1 failed: {e}")
        
        # Method 2: Try direct parent_run filter
        try:
            direct_children = list(client.list_runs(
                project_name="ghl-langgraph-agent",
                filter=f'eq(parent_run_id, "{trace_id}")',
                limit=100
            ))
            child_runs.extend(direct_children)
        except Exception as e:
            print(f"  Method 2 failed: {e}")
        
        # Deduplicate child runs
        seen_ids = set()
        unique_children = []
        for child in child_runs:
            if child.id not in seen_ids:
                seen_ids.add(child.id)
                unique_children.append(child)
        
        print(f"  Found {len(unique_children)} child runs")
        
        # Process child runs
        for child in unique_children:
            child_data = {
                "id": str(child.id),
                "name": child.name,
                "status": child.status,
                "start_time": child.start_time.isoformat() if child.start_time else None,
                "end_time": child.end_time.isoformat() if child.end_time else None,
                "duration_seconds": (child.end_time - child.start_time).total_seconds() if child.end_time and child.start_time else None,
                "inputs": child.inputs if child.inputs else {},
                "outputs": child.outputs if child.outputs else {},
                "error": child.error if child.error else None,
                "node_type": None
            }
            
            # Determine node type
            if child.name:
                if "supervisor" in child.name.lower():
                    child_data["node_type"] = "supervisor"
                elif "intelligence" in child.name.lower():
                    child_data["node_type"] = "intelligence"
                elif "maria" in child.name.lower():
                    child_data["node_type"] = "maria_agent"
                elif "carlos" in child.name.lower():
                    child_data["node_type"] = "carlos_agent"
                elif "sofia" in child.name.lower():
                    child_data["node_type"] = "sofia_agent"
                elif "webhook" in child.name.lower():
                    child_data["node_type"] = "webhook_handler"
                else:
                    child_data["node_type"] = "unknown"
            
            trace_data["child_runs"].append(child_data)
        
        # Sort child runs by start time
        trace_data["child_runs"].sort(key=lambda x: x["start_time"] or "")
        
        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(trace_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Trace exported to: {output_file}")
        print(f"   Total size: {os.path.getsize(output_file):,} bytes")
        print(f"   Child runs: {len(trace_data['child_runs'])}")
        
        # Print summary
        print("\n📋 SUMMARY:")
        print(f"   Status: {trace_data['status']}")
        print(f"   Duration: {trace_data['duration_seconds']:.2f}s")
        print(f"   Thread ID: {trace_data['metadata'].get('thread_id', 'N/A')}")
        
        if trace_data['error']:
            print(f"   ❌ Error: {trace_data['error']}")
        
        if trace_data['outputs']:
            if 'next_agent' in trace_data['outputs']:
                print(f"   Routed to: {trace_data['outputs']['next_agent']}")
            if 'messages' in trace_data['outputs']:
                for msg in trace_data['outputs']['messages']:
                    if isinstance(msg, dict) and msg.get('type') == 'ai' and msg.get('content'):
                        content = msg['content']
                        if not content.startswith('[Task from supervisor:'):
                            print(f"   Response: {content[:100]}...")
                            break
        
    except Exception as e:
        print(f"❌ Error exporting trace: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    
    # Get trace ID from command line or use default
    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
    else:
        trace_id = "1f0672fb-ff3b-6d80-b9da-df83a5eeb845"
    
    api_key = "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"
    output_file = f"trace_export_{trace_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    export_trace_to_json(trace_id, api_key, output_file)