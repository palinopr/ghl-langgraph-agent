#!/usr/bin/env python3
"""
Full Access Trace Debugging with Complete Child Run Analysis
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import time

# Get API key from .env
def get_api_key():
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('LANGCHAIN_API_KEY='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return None

try:
    import langsmith
    from langsmith import Client
    print("✅ LangSmith SDK is installed")
except ImportError:
    print("❌ LangSmith SDK not installed")
    sys.exit(1)

def format_timestamp(ts):
    """Format timestamp for readability"""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime('%H:%M:%S.%f')[:-3]  # Show milliseconds
        except:
            return ts
    elif hasattr(ts, 'isoformat'):
        return ts.strftime('%H:%M:%S.%f')[:-3]
    return str(ts)

def extract_message_content(msg: Any) -> str:
    """Extract content from various message formats"""
    if isinstance(msg, dict):
        return msg.get('content', str(msg))
    elif hasattr(msg, 'content'):
        return msg.content
    return str(msg)

def analyze_node_execution(run: Any) -> Dict[str, Any]:
    """Analyze a single node execution"""
    analysis = {
        "name": run.name,
        "type": run.run_type,
        "status": run.status,
        "start": format_timestamp(run.start_time),
        "duration_ms": None,
        "inputs": {},
        "outputs": {},
        "error": None,
        "key_findings": []
    }
    
    # Calculate duration
    if hasattr(run, 'end_time') and run.end_time and run.start_time:
        try:
            if isinstance(run.start_time, str):
                start = datetime.fromisoformat(run.start_time.replace('Z', '+00:00'))
            else:
                start = run.start_time
            
            if isinstance(run.end_time, str):
                end = datetime.fromisoformat(run.end_time.replace('Z', '+00:00'))
            else:
                end = run.end_time
            
            duration = (end - start).total_seconds() * 1000
            analysis["duration_ms"] = f"{duration:.0f}ms"
        except:
            pass
    
    # Extract inputs
    if hasattr(run, 'inputs') and run.inputs:
        analysis["inputs"] = run.inputs
    
    # Extract outputs
    if hasattr(run, 'outputs') and run.outputs:
        analysis["outputs"] = run.outputs
    
    # Extract error
    if hasattr(run, 'error') and run.error:
        analysis["error"] = run.error
    
    # Analyze specific nodes
    if 'intelligence' in run.name.lower():
        if analysis["outputs"]:
            outputs = analysis["outputs"]
            if isinstance(outputs, dict):
                if 'lead_score' in outputs:
                    analysis["key_findings"].append(f"Lead Score: {outputs['lead_score']}")
                if 'extracted_data' in outputs:
                    analysis["key_findings"].append(f"Extracted: {outputs['extracted_data']}")
    
    elif 'supervisor' in run.name.lower():
        if analysis["outputs"]:
            outputs = analysis["outputs"]
            if isinstance(outputs, dict):
                if 'next_agent' in outputs:
                    analysis["key_findings"].append(f"Routing to: {outputs['next_agent']}")
                if 'lead_score' in outputs:
                    analysis["key_findings"].append(f"Score: {outputs['lead_score']}")
    
    elif any(agent in run.name.lower() for agent in ['maria', 'carlos', 'sofia']):
        if analysis["outputs"]:
            outputs = analysis["outputs"]
            if isinstance(outputs, dict) and 'messages' in outputs:
                msgs = outputs['messages']
                if msgs and len(msgs) > 0:
                    last_msg = msgs[-1]
                    content = extract_message_content(last_msg)[:100]
                    analysis["key_findings"].append(f"Response: {content}...")
    
    return analysis

def get_all_runs_in_trace(client: Client, trace_id: str) -> List[Any]:
    """Get all runs in a trace using the correct API"""
    all_runs = []
    
    try:
        # Method 1: Get main run and its children
        main_run = client.read_run(trace_id)
        all_runs.append(main_run)
        
        # Method 2: Use project filter with trace_id
        project_name = "ghl-langgraph-agent"
        
        # Get runs by trace
        trace_runs = list(client.list_runs(
            project_name=project_name,
            trace_id=trace_id,
            limit=100
        ))
        
        # Add unique runs
        run_ids = {str(main_run.id)}
        for run in trace_runs:
            if str(run.id) not in run_ids:
                all_runs.append(run)
                run_ids.add(str(run.id))
        
        # Sort by start time
        all_runs.sort(key=lambda r: r.start_time if hasattr(r, 'start_time') else '')
        
        return all_runs
        
    except Exception as e:
        print(f"Error getting runs: {e}")
        return [main_run] if 'main_run' in locals() else []

def build_execution_tree(runs: List[Any]) -> Dict[str, Any]:
    """Build execution tree from runs"""
    # Create lookup maps
    run_map = {str(run.id): run for run in runs}
    children_map = {}
    
    # Build parent-child relationships
    for run in runs:
        parent_id = getattr(run, 'parent_run_id', None)
        if parent_id:
            parent_id_str = str(parent_id)
            if parent_id_str not in children_map:
                children_map[parent_id_str] = []
            children_map[parent_id_str].append(run)
    
    # Find root run
    root_runs = [run for run in runs if not getattr(run, 'parent_run_id', None)]
    
    if not root_runs:
        return {"error": "No root run found"}
    
    root = root_runs[0]
    
    def build_node(run):
        node = {
            "id": str(run.id),
            "name": run.name,
            "type": run.run_type,
            "children": []
        }
        
        # Add children
        if str(run.id) in children_map:
            for child in children_map[str(run.id)]:
                node["children"].append(build_node(child))
        
        return node
    
    return build_node(root)

def debug_trace_complete(client: Client, trace_id: str):
    """Complete debugging of a trace with full access"""
    print(f"\n{'='*100}")
    print(f"🔍 COMPLETE TRACE ANALYSIS: {trace_id}")
    print(f"{'='*100}\n")
    
    try:
        # Get all runs in trace
        all_runs = get_all_runs_in_trace(client, trace_id)
        print(f"📊 Found {len(all_runs)} runs in trace\n")
        
        if not all_runs:
            print("❌ No runs found")
            return None
        
        # Analyze main run
        main_run = all_runs[0]
        print("🎯 MAIN RUN:")
        print(f"  - Name: {main_run.name}")
        print(f"  - Status: {main_run.status}")
        print(f"  - Start: {format_timestamp(main_run.start_time)}")
        print(f"  - Total Tokens: {getattr(main_run, 'total_tokens', 'N/A')}")
        print(f"  - Total Cost: ${getattr(main_run, 'total_cost', 0):.4f}")
        
        # Input analysis
        if hasattr(main_run, 'inputs') and main_run.inputs:
            print("\n📥 INPUT:")
            if 'messages' in main_run.inputs:
                messages = main_run.inputs['messages']
                for msg in messages:
                    if isinstance(msg, dict) and msg.get('type') == 'human':
                        content = msg.get('content', '')
                        print(f"  User: {content}")
                        
                        # Language detection
                        if any(word in content.lower() for word in ['hola', 'necesito', 'quiero', 'tengo']):
                            print(f"  Language: Spanish detected")
            
            if 'contact_id' in main_run.inputs:
                print(f"  Contact ID: {main_run.inputs['contact_id']}")
        
        # Build execution tree
        print("\n🌳 EXECUTION TREE:")
        tree = build_execution_tree(all_runs)
        
        def print_tree(node, indent=0):
            prefix = "  " * indent + "└─ " if indent > 0 else ""
            print(f"{prefix}{node['name']} ({node['type']})")
            for child in node.get('children', []):
                print_tree(child, indent + 1)
        
        print_tree(tree)
        
        # Detailed node analysis
        print("\n📋 DETAILED NODE EXECUTION:")
        print("-" * 100)
        
        # Group runs by type
        node_runs = [r for r in all_runs if r.run_type in ['chain', 'tool', 'llm']]
        
        for i, run in enumerate(node_runs):
            if i > 0:  # Skip main run
                analysis = analyze_node_execution(run)
                
                print(f"\n[{i}] {analysis['name']}")
                print(f"    Type: {analysis['type']}")
                print(f"    Start: {analysis['start']}")
                print(f"    Duration: {analysis['duration_ms'] or 'N/A'}")
                
                if analysis['key_findings']:
                    print(f"    Key Findings:")
                    for finding in analysis['key_findings']:
                        print(f"      - {finding}")
                
                if analysis['error']:
                    print(f"    ❌ Error: {analysis['error']}")
                
                # Special handling for specific nodes
                if 'intelligence' in analysis['name'].lower():
                    if analysis['outputs']:
                        print(f"    📊 Intelligence Analysis:")
                        outputs = analysis['outputs']
                        if isinstance(outputs, dict):
                            print(f"      - Lead Score: {outputs.get('lead_score', 'N/A')}")
                            print(f"      - Category: {outputs.get('lead_category', 'N/A')}")
                            extracted = outputs.get('extracted_data', {})
                            if extracted:
                                print(f"      - Extracted Data:")
                                for key, value in extracted.items():
                                    if value:
                                        print(f"        • {key}: {value}")
                
                elif 'supervisor' in analysis['name'].lower() and 'brain' in analysis['name'].lower():
                    if analysis['outputs']:
                        print(f"    🧠 Supervisor Decision:")
                        outputs = analysis['outputs']
                        if isinstance(outputs, dict):
                            print(f"      - Next Agent: {outputs.get('next_agent', 'N/A')}")
                            print(f"      - Lead Score: {outputs.get('lead_score', 'N/A')}")
                            if 'routing_reason' in outputs:
                                print(f"      - Reason: {outputs['routing_reason']}")
                
                elif any(agent in analysis['name'].lower() for agent in ['maria', 'carlos', 'sofia']):
                    agent_name = None
                    for agent in ['maria', 'carlos', 'sofia']:
                        if agent in analysis['name'].lower():
                            agent_name = agent.title()
                            break
                    
                    if agent_name and analysis['outputs']:
                        print(f"    💬 {agent_name}'s Response:")
                        outputs = analysis['outputs']
                        if isinstance(outputs, dict) and 'messages' in outputs:
                            msgs = outputs['messages']
                            for msg in msgs:
                                content = extract_message_content(msg)
                                if content and not content.startswith('System:'):
                                    print(f"      \"{content[:150]}{'...' if len(content) > 150 else ''}\"")
        
        # Final output analysis
        print("\n📤 FINAL OUTPUT:")
        if hasattr(main_run, 'outputs') and main_run.outputs:
            outputs = main_run.outputs
            if isinstance(outputs, dict) and 'messages' in outputs:
                msgs = outputs['messages']
                # Find last AI message
                for msg in reversed(msgs):
                    if isinstance(msg, dict):
                        msg_type = msg.get('type', '')
                        if msg_type in ['ai', 'assistant']:
                            content = msg.get('content', '')
                            print(f"  Response: {content}")
                            
                            # Check language consistency
                            if hasattr(main_run, 'inputs') and main_run.inputs:
                                input_msgs = main_run.inputs.get('messages', [])
                                for input_msg in input_msgs:
                                    if isinstance(input_msg, dict) and input_msg.get('type') == 'human':
                                        input_content = input_msg.get('content', '').lower()
                                        if any(w in input_content for w in ['hola', 'necesito', 'quiero']):
                                            # Spanish input
                                            if any(w in content.lower() for w in ['hello', 'help you', 'thank']):
                                                print("  ⚠️ WARNING: Language mismatch - Spanish input, English output!")
                            break
        
        # Performance summary
        print("\n⚡ PERFORMANCE SUMMARY:")
        total_duration = 0
        llm_calls = 0
        tool_calls = 0
        
        for run in all_runs:
            if hasattr(run, 'start_time') and hasattr(run, 'end_time') and run.end_time:
                try:
                    start = datetime.fromisoformat(str(run.start_time).replace('Z', '+00:00'))
                    end = datetime.fromisoformat(str(run.end_time).replace('Z', '+00:00'))
                    total_duration += (end - start).total_seconds() * 1000
                except:
                    pass
            
            if run.run_type == 'llm':
                llm_calls += 1
            elif run.run_type == 'tool':
                tool_calls += 1
        
        print(f"  - Total Duration: {total_duration:.0f}ms")
        print(f"  - LLM Calls: {llm_calls}")
        print(f"  - Tool Calls: {tool_calls}")
        print(f"  - Total Runs: {len(all_runs)}")
        
        return {
            "trace_id": trace_id,
            "status": main_run.status,
            "total_runs": len(all_runs),
            "total_duration_ms": total_duration,
            "tree": tree
        }
        
    except Exception as e:
        print(f"❌ Error debugging trace: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    trace_ids = [
        "1f0664ec-cd74-6708-92b6-ea19cc76f13e",
        "1f0664ee-dc28-6a93-ac39-b4cbe41bd294"
    ]
    
    api_key = get_api_key()
    if not api_key:
        print("❌ No API key found in .env file")
        return
    
    print(f"🔑 Using API key: {api_key[:20]}...")
    
    # Initialize client
    try:
        client = Client(api_key=api_key)
        print("✅ LangSmith client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return
    
    # Debug each trace
    results = []
    for trace_id in trace_ids:
        result = debug_trace_complete(client, trace_id)
        if result:
            results.append(result)
    
    # Summary
    if results:
        print("\n" + "="*100)
        print("📊 TRACE COMPARISON SUMMARY")
        print("="*100)
        
        for i, result in enumerate(results):
            print(f"\nTrace {i+1}: {result['trace_id'][:8]}...")
            print(f"  - Status: {result['status']}")
            print(f"  - Total Runs: {result['total_runs']}")
            print(f"  - Duration: {result['total_duration_ms']:.0f}ms")
    
    print("\n💡 ADDITIONAL ACCESS OPTIONS:")
    print("1. Direct API access for specific run details:")
    print("   run = client.read_run('run_id')")
    print("   print(run.dict())")
    print("\n2. Export full trace data:")
    print("   client.download_run('trace_id')")
    print("\n3. Query runs with complex filters:")
    print("   runs = client.list_runs(")
    print("       project_name='ghl-langgraph-agent',")
    print("       filter='and(eq(name, \"intelligence\"), has(outputs, \"lead_score\"))',")
    print("       limit=100")
    print("   )")

if __name__ == "__main__":
    main()