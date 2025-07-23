#!/usr/bin/env python3
"""
Analyze Trace - Quick CLI tool to debug specific LangSmith traces
"""
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from langsmith import Client
from app.utils.debug_helpers import trace_message_flow, validate_state
from app.state.message_manager import MessageManager


def analyze_trace_details(trace_id: str, verbose: bool = False) -> Dict[str, Any]:
    """Analyze a trace in detail"""
    client = Client()
    
    print(f"\n{'='*80}")
    print(f"ANALYZING TRACE: {trace_id}")
    print(f"{'='*80}\n")
    
    try:
        # Get main run
        run = client.read_run(trace_id)
        print(f"Start Time: {run.start_time}")
        print(f"End Time: {run.end_time}")
        print(f"Status: {run.status}")
        
        if run.error:
            print(f"❌ ERROR: {run.error}")
        
        # Get child runs - use project_name and trace_id
        try:
            child_runs = list(client.list_runs(
                project_name="ghl-langgraph-agent",
                trace_id=trace_id,
                limit=100
            ))
        except Exception as e:
            # Fallback to using the run's project
            child_runs = list(client.list_runs(
                project_id=run.session_id,
                trace_id=trace_id,
                limit=100
            ))
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        print(f"\nTotal Nodes: {len(child_runs)}")
        print("\n" + "-"*80)
        
        # Analyze each node
        all_messages = []
        node_data = []
        
        for i, child in enumerate(child_runs):
            print(f"\n[{i+1}] {child.name}")
            print(f"    Start: {child.start_time.strftime('%H:%M:%S.%f')[:-3]}")
            
            # Get message counts
            input_msgs = []
            output_msgs = []
            
            if child.inputs:
                if "messages" in child.inputs:
                    input_msgs = child.inputs["messages"]
                    print(f"    Input Messages: {len(input_msgs)}")
                
                if verbose and "contact_id" in child.inputs:
                    print(f"    Contact ID: {child.inputs['contact_id']}")
                if verbose and "thread_id" in child.inputs:
                    print(f"    Thread ID: {child.inputs['thread_id']}")
            
            if child.outputs:
                if "messages" in child.outputs:
                    output_msgs = child.outputs["messages"]
                    print(f"    Output Messages: {len(output_msgs)}")
                    
                    # Check for duplicates
                    unique_msgs = MessageManager.deduplicate_messages(output_msgs)
                    if len(unique_msgs) < len(output_msgs):
                        print(f"    ⚠️  DUPLICATES: {len(output_msgs) - len(unique_msgs)} duplicate messages!")
                    
                    # Store for overall analysis
                    all_messages.extend(output_msgs)
            
            # Check for errors
            if child.error:
                print(f"    ❌ ERROR: {child.error}")
            elif child.outputs and "Error" in str(child.outputs):
                print(f"    ⚠️  Contains Error message")
            
            # Duration
            if child.end_time:
                duration = (child.end_time - child.start_time).total_seconds()
                print(f"    Duration: {duration:.2f}s")
                if duration > 1.0:
                    print(f"    ⚠️  SLOW: Took more than 1 second")
            
            # Store node data
            node_data.append({
                "name": child.name,
                "input_messages": len(input_msgs),
                "output_messages": len(output_msgs),
                "error": bool(child.error)
            })
            
            # Show message content if verbose
            if verbose and output_msgs:
                print(f"    Last Message:")
                last_msg = output_msgs[-1]
                if isinstance(last_msg, dict):
                    content = last_msg.get("content", "")
                elif hasattr(last_msg, "content"):
                    content = last_msg.content
                else:
                    content = str(last_msg)
                print(f"    > {content[:100]}...")
        
        # Overall analysis
        print("\n" + "="*80)
        print("OVERALL ANALYSIS")
        print("="*80)
        
        # Message flow visualization
        trace_message_flow({"nodes": node_data})
        
        # Check total message accumulation
        total_unique = len(MessageManager.deduplicate_messages(all_messages))
        total_messages = len(all_messages)
        
        print(f"\nTotal Messages: {total_messages}")
        print(f"Unique Messages: {total_unique}")
        print(f"Duplicates: {total_messages - total_unique}")
        
        if total_messages > len(child_runs) * 3:
            print("\n🚨 WARNING: Excessive message accumulation detected!")
        
        # Pattern detection
        message_counts = [n["output_messages"] for n in node_data if n["output_messages"] > 0]
        if len(message_counts) >= 3:
            # Calculate growth rate
            growth_rates = []
            for i in range(1, len(message_counts)):
                if message_counts[i-1] > 0:
                    rate = message_counts[i] / message_counts[i-1]
                    growth_rates.append(rate)
            
            if growth_rates and all(r >= 1.5 for r in growth_rates):
                avg_rate = sum(growth_rates) / len(growth_rates)
                print(f"\n📈 Exponential growth detected! Average rate: {avg_rate:.1f}x per node")
        
        # Find problem nodes
        problem_nodes = []
        for node in node_data:
            if node["output_messages"] > node["input_messages"] * 2:
                problem_nodes.append(node["name"])
        
        if problem_nodes:
            print(f"\n🔍 Problem nodes (doubling messages): {', '.join(problem_nodes)}")
        
        return {
            "trace_id": trace_id,
            "total_nodes": len(child_runs),
            "total_messages": total_messages,
            "unique_messages": total_unique,
            "duplicates": total_messages - total_unique,
            "problem_nodes": problem_nodes
        }
        
    except Exception as e:
        print(f"\n❌ Failed to analyze trace: {e}")
        return {"error": str(e)}


def main():
    """Main CLI function"""
    if len(sys.argv) < 2:
        print("Usage: python analyze_trace.py <trace_id> [--verbose]")
        print("\nExample:")
        print("  python analyze_trace.py 1f067756-c282-640a-85ed-56c1478cd894")
        print("  python analyze_trace.py 1f067756-c282-640a-85ed-56c1478cd894 --verbose")
        sys.exit(1)
    
    trace_id = sys.argv[1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    # Analyze trace
    result = analyze_trace_details(trace_id, verbose)
    
    # Save result to file
    output_file = f"trace_analysis_{trace_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"\n💾 Analysis saved to: {output_file}")


if __name__ == "__main__":
    main()