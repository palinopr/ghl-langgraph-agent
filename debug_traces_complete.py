#!/usr/bin/env python3
"""
Complete Trace Debugging Script
Trace IDs: 
- 1f0664ec-cd74-6708-92b6-ea19cc76f13e
- 1f0664ee-dc28-6a93-ac39-b4cbe41bd294
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List

# Read API key from .env
def get_api_key():
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('LANGCHAIN_API_KEY='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return None

def format_timestamp(ts):
    """Format timestamp for readability"""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return ts
    return str(ts)

def analyze_messages(messages: List[Dict]) -> Dict[str, Any]:
    """Analyze conversation messages"""
    analysis = {
        "total_messages": len(messages),
        "user_messages": [],
        "ai_messages": [],
        "language_detected": None,
        "topics": []
    }
    
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get('role', '')
            content = msg.get('content', '')
            
            if role == 'user':
                analysis["user_messages"].append(content)
                # Detect language
                if any(word in content.lower() for word in ['hola', 'necesito', 'quiero', 'gracias']):
                    analysis["language_detected"] = "Spanish"
                elif any(word in content.lower() for word in ['hello', 'need', 'want', 'thanks']):
                    analysis["language_detected"] = "English"
            
            elif role == 'assistant':
                analysis["ai_messages"].append(content)
    
    return analysis

def analyze_trace_flow(run_data: Dict) -> Dict[str, Any]:
    """Analyze the complete flow of a trace"""
    flow_analysis = {
        "trace_id": run_data.get('id'),
        "status": run_data.get('status'),
        "start_time": format_timestamp(run_data.get('start_time')),
        "end_time": format_timestamp(run_data.get('end_time')),
        "total_tokens": run_data.get('total_tokens', 0),
        "error": run_data.get('error'),
        "tags": run_data.get('tags', []),
        "metadata": run_data.get('extra', {}).get('metadata', {}),
        "flow_steps": [],
        "issues_found": []
    }
    
    # Analyze inputs
    inputs = run_data.get('inputs', {})
    if 'messages' in inputs:
        msg_analysis = analyze_messages(inputs['messages'])
        flow_analysis["input_analysis"] = msg_analysis
        
        # Check for language switching
        if msg_analysis["language_detected"] == "Spanish":
            # Check if AI responded in English
            outputs = run_data.get('outputs', {})
            if outputs:
                output_text = str(outputs).lower()
                if any(eng in output_text for eng in ['hello', 'how can i help', 'thank you']):
                    flow_analysis["issues_found"].append("⚠️ Language Switch: Spanish input → English output")
    
    # Analyze child runs (execution steps)
    child_runs = run_data.get('child_runs', [])
    for i, child in enumerate(child_runs):
        step = {
            "order": i + 1,
            "name": child.get('name', 'Unknown'),
            "start_time": format_timestamp(child.get('start_time')),
            "duration_ms": child.get('dotted_order', '').split('.')[-1] if child.get('dotted_order') else 'N/A',
            "status": child.get('status'),
            "type": child.get('run_type')
        }
        flow_analysis["flow_steps"].append(step)
    
    # Check for specific issues
    if flow_analysis["status"] == "error":
        flow_analysis["issues_found"].append(f"❌ Error: {flow_analysis['error']}")
    
    # Check metadata for routing info
    if 'lead_score' in flow_analysis["metadata"]:
        score = flow_analysis["metadata"]["lead_score"]
        if score > 10:
            flow_analysis["issues_found"].append(f"⚠️ Invalid lead score: {score} (should be 1-10)")
    
    return flow_analysis

def debug_trace_with_langsmith(trace_id: str, api_key: str):
    """Debug a specific trace using LangSmith"""
    try:
        import langsmith
        client = langsmith.Client(api_key=api_key)
        
        print(f"\n{'='*60}")
        print(f"🔍 DEBUGGING TRACE: {trace_id}")
        print(f"{'='*60}\n")
        
        # Get the run
        run = client.read_run(trace_id)
        
        # Basic info
        print("📊 BASIC INFORMATION:")
        print(f"  - Status: {run.status}")
        print(f"  - Start: {format_timestamp(run.start_time)}")
        print(f"  - End: {format_timestamp(run.end_time)}")
        print(f"  - Total Tokens: {getattr(run, 'total_tokens', 'N/A')}")
        print(f"  - Project: {getattr(run, 'project_name', 'N/A')}")
        
        # Inputs
        print("\n📥 INPUTS:")
        if hasattr(run, 'inputs') and run.inputs:
            inputs = run.inputs
            if 'messages' in inputs:
                print("  Messages:")
                for msg in inputs['messages']:
                    if isinstance(msg, dict):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        print(f"    [{role}]: {content[:100]}...")
            
            if 'contact_id' in inputs:
                print(f"  Contact ID: {inputs['contact_id']}")
            
            if 'webhook_data' in inputs:
                print(f"  Webhook Data: {json.dumps(inputs['webhook_data'], indent=4)}")
        
        # Outputs
        print("\n📤 OUTPUTS:")
        if hasattr(run, 'outputs') and run.outputs:
            outputs = run.outputs
            print(json.dumps(outputs, indent=2)[:500] + "...")
        
        # Error details
        if hasattr(run, 'error') and run.error:
            print("\n❌ ERROR DETAILS:")
            print(f"  {run.error}")
        
        # Metadata
        print("\n🏷️ METADATA:")
        if hasattr(run, 'extra') and run.extra:
            metadata = run.extra.get('metadata', {})
            for key, value in metadata.items():
                print(f"  - {key}: {value}")
        
        # Tags
        if hasattr(run, 'tags') and run.tags:
            print(f"\n🏷️ TAGS: {', '.join(run.tags)}")
        
        # Child runs (execution flow)
        print("\n🔄 EXECUTION FLOW:")
        if hasattr(run, 'child_run_ids') and run.child_run_ids:
            print(f"  Total Steps: {len(run.child_run_ids)}")
            
            # Get child runs
            for i, child_id in enumerate(run.child_run_ids[:10]):  # First 10
                try:
                    child = client.read_run(child_id)
                    print(f"\n  Step {i+1}: {child.name}")
                    print(f"    - Type: {child.run_type}")
                    print(f"    - Status: {child.status}")
                    print(f"    - Duration: {getattr(child, 'dotted_order', 'N/A')}")
                    
                    # Check for specific nodes
                    if 'supervisor' in child.name.lower():
                        if hasattr(child, 'outputs') and child.outputs:
                            print(f"    - Routing Decision: {child.outputs}")
                    
                    if 'intelligence' in child.name.lower():
                        if hasattr(child, 'outputs') and child.outputs:
                            outputs = child.outputs
                            if isinstance(outputs, dict):
                                score = outputs.get('lead_score', 'N/A')
                                print(f"    - Lead Score: {score}")
                                print(f"    - Extracted: {outputs.get('extracted_data', {})}")
                    
                except Exception as e:
                    print(f"    - Error reading child: {e}")
        
        # Full flow analysis
        print("\n📈 FLOW ANALYSIS:")
        run_dict = run.dict() if hasattr(run, 'dict') else {}
        flow_analysis = analyze_trace_flow(run_dict)
        
        if flow_analysis["issues_found"]:
            print("\n⚠️ ISSUES DETECTED:")
            for issue in flow_analysis["issues_found"]:
                print(f"  {issue}")
        else:
            print("  ✅ No major issues detected")
        
        return flow_analysis
        
    except Exception as e:
        print(f"❌ Error debugging trace: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_traces(trace1_analysis: Dict, trace2_analysis: Dict):
    """Compare two traces to find patterns"""
    print("\n" + "="*60)
    print("📊 TRACE COMPARISON")
    print("="*60)
    
    # Compare basic info
    print("\n🔍 Basic Comparison:")
    print(f"  Trace 1: {trace1_analysis['trace_id'][:8]}... - Status: {trace1_analysis['status']}")
    print(f"  Trace 2: {trace2_analysis['trace_id'][:8]}... - Status: {trace2_analysis['status']}")
    
    # Compare issues
    print("\n⚠️ Issues Comparison:")
    issues1 = set(trace1_analysis.get('issues_found', []))
    issues2 = set(trace2_analysis.get('issues_found', []))
    
    common_issues = issues1.intersection(issues2)
    if common_issues:
        print("  Common Issues:")
        for issue in common_issues:
            print(f"    - {issue}")
    
    unique_1 = issues1 - issues2
    if unique_1:
        print("  Issues only in Trace 1:")
        for issue in unique_1:
            print(f"    - {issue}")
    
    unique_2 = issues2 - issues1
    if unique_2:
        print("  Issues only in Trace 2:")
        for issue in unique_2:
            print(f"    - {issue}")
    
    # Compare flow steps
    print("\n🔄 Flow Comparison:")
    steps1 = [s['name'] for s in trace1_analysis.get('flow_steps', [])]
    steps2 = [s['name'] for s in trace2_analysis.get('flow_steps', [])]
    
    if steps1 == steps2:
        print("  ✅ Same execution flow")
    else:
        print("  ❌ Different execution flows")
        print(f"    Trace 1: {' → '.join(steps1[:5])}...")
        print(f"    Trace 2: {' → '.join(steps2[:5])}...")

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
    
    # Try to import langsmith
    try:
        import langsmith
        print("✅ LangSmith SDK available")
    except ImportError:
        print("❌ LangSmith SDK not installed")
        print("Install with: pip install langsmith")
        return
    
    # Debug each trace
    analyses = []
    for trace_id in trace_ids:
        analysis = debug_trace_with_langsmith(trace_id, api_key)
        if analysis:
            analyses.append(analysis)
    
    # Compare traces if we have both
    if len(analyses) == 2:
        compare_traces(analyses[0], analyses[1])
    
    print("\n" + "="*60)
    print("🎯 DEBUGGING COMPLETE")
    print("="*60)
    
    # Provide Context7 MCP info
    print("\n📚 For more detailed analysis, use Context7 MCP:")
    print("  1. Check the LangSmith docs for trace analysis")
    print("  2. Use the API to get child run details")
    print("  3. Export traces for offline analysis")

if __name__ == "__main__":
    main()