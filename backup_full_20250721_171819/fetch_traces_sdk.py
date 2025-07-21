#!/usr/bin/env python3
"""
Fetch and analyze LangSmith traces using SDK
Trace IDs: 
- 1f0664ec-cd74-6708-92b6-ea19cc76f13e
- 1f0664ee-dc28-6a93-ac39-b4cbe41bd294
"""

import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

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

# First check if langsmith is installed
try:
    import langsmith
    from langsmith import Client
    print("✅ LangSmith SDK is installed")
except ImportError:
    print("❌ LangSmith SDK not installed. Installing...")
    os.system(f"{sys.executable} -m pip install langsmith")
    try:
        import langsmith
        from langsmith import Client
        print("✅ LangSmith SDK installed successfully")
    except:
        print("❌ Failed to install LangSmith SDK")
        sys.exit(1)

def format_timestamp(ts):
    """Format timestamp for readability"""
    if isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return ts
    return str(ts)

def analyze_run_details(run: Any) -> Dict[str, Any]:
    """Analyze a run in detail"""
    analysis = {
        "run_id": str(run.id),
        "name": run.name,
        "run_type": run.run_type,
        "status": run.status,
        "start_time": format_timestamp(run.start_time),
        "end_time": format_timestamp(run.end_time) if hasattr(run, 'end_time') else None,
        "error": run.error if hasattr(run, 'error') else None,
        "total_tokens": getattr(run, 'total_tokens', 0),
        "total_cost": getattr(run, 'total_cost', 0),
        "feedback_stats": getattr(run, 'feedback_stats', {}),
        "tags": getattr(run, 'tags', []),
        "metadata": {},
        "inputs": {},
        "outputs": {},
        "events": []
    }
    
    # Extract metadata
    if hasattr(run, 'extra') and run.extra:
        analysis["metadata"] = run.extra.get('metadata', {})
    
    # Extract inputs
    if hasattr(run, 'inputs') and run.inputs:
        analysis["inputs"] = run.inputs
    
    # Extract outputs
    if hasattr(run, 'outputs') and run.outputs:
        analysis["outputs"] = run.outputs
    
    # Extract events (if available)
    if hasattr(run, 'events') and run.events:
        for event in run.events:
            analysis["events"].append({
                "name": event.get('name'),
                "time": format_timestamp(event.get('time')),
                "data": event.get('data', {})
            })
    
    return analysis

def fetch_child_runs(client: Client, parent_id: str, limit: int = 10) -> List[Any]:
    """Fetch child runs for a parent run"""
    try:
        child_runs = list(client.list_runs(
            filter=f'eq(parent_run_id, "{parent_id}")',
            limit=limit
        ))
        return child_runs
    except Exception as e:
        print(f"Error fetching child runs: {e}")
        return []

def debug_trace_complete(client: Client, trace_id: str):
    """Complete debugging of a trace"""
    print(f"\n{'='*80}")
    print(f"🔍 DEBUGGING TRACE: {trace_id}")
    print(f"{'='*80}\n")
    
    try:
        # Get the main run
        run = client.read_run(trace_id)
        analysis = analyze_run_details(run)
        
        # Basic Information
        print("📊 BASIC INFORMATION:")
        print(f"  - Name: {analysis['name']}")
        print(f"  - Type: {analysis['run_type']}")
        print(f"  - Status: {analysis['status']}")
        print(f"  - Start: {analysis['start_time']}")
        print(f"  - End: {analysis['end_time']}")
        print(f"  - Total Tokens: {analysis['total_tokens']}")
        print(f"  - Total Cost: ${analysis['total_cost']:.4f}" if analysis['total_cost'] else "  - Total Cost: N/A")
        
        # Error Information
        if analysis['error']:
            print(f"\n❌ ERROR:")
            print(f"  {analysis['error']}")
        
        # Tags
        if analysis['tags']:
            print(f"\n🏷️ TAGS: {', '.join(analysis['tags'])}")
        
        # Metadata
        if analysis['metadata']:
            print(f"\n📋 METADATA:")
            for key, value in analysis['metadata'].items():
                print(f"  - {key}: {value}")
        
        # Inputs
        print(f"\n📥 INPUTS:")
        if 'messages' in analysis['inputs']:
            messages = analysis['inputs']['messages']
            print(f"  Total Messages: {len(messages)}")
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    print(f"  [{i+1}] {role}: {content[:100]}{'...' if len(content) > 100 else ''}")
        
        if 'contact_id' in analysis['inputs']:
            print(f"  Contact ID: {analysis['inputs']['contact_id']}")
        
        if 'webhook_data' in analysis['inputs']:
            print(f"  Webhook Data: {json.dumps(analysis['inputs']['webhook_data'], indent=4)}")
        
        # Outputs
        if analysis['outputs']:
            print(f"\n📤 OUTPUTS:")
            output_str = json.dumps(analysis['outputs'], indent=2)
            if len(output_str) > 500:
                print(output_str[:500] + "...")
            else:
                print(output_str)
        
        # Child Runs (Execution Flow)
        print(f"\n🔄 EXECUTION FLOW:")
        child_runs = fetch_child_runs(client, trace_id, limit=20)
        
        if child_runs:
            print(f"  Total Steps: {len(child_runs)}")
            
            for i, child in enumerate(child_runs):
                child_analysis = analyze_run_details(child)
                print(f"\n  Step {i+1}: {child_analysis['name']}")
                print(f"    - Type: {child_analysis['run_type']}")
                print(f"    - Status: {child_analysis['status']}")
                
                # Special handling for specific nodes
                if 'supervisor' in child_analysis['name'].lower():
                    if child_analysis['outputs']:
                        print(f"    - Routing Decision: {json.dumps(child_analysis['outputs'], indent=6)}")
                
                if 'intelligence' in child_analysis['name'].lower():
                    if child_analysis['outputs']:
                        outputs = child_analysis['outputs']
                        if isinstance(outputs, dict):
                            print(f"    - Lead Score: {outputs.get('lead_score', 'N/A')}")
                            print(f"    - Extracted: {outputs.get('extracted_data', {})}")
                
                if child_analysis['error']:
                    print(f"    - ❌ Error: {child_analysis['error']}")
        
        # Analyze for common issues
        print(f"\n🔍 ANALYSIS:")
        issues = []
        
        # Check for language switching
        if 'messages' in analysis['inputs']:
            for msg in analysis['inputs']['messages']:
                if isinstance(msg, dict) and msg.get('role') == 'user':
                    content = msg.get('content', '').lower()
                    if any(word in content for word in ['hola', 'necesito', 'quiero']):
                        # Spanish input detected
                        if analysis['outputs']:
                            output_text = str(analysis['outputs']).lower()
                            if any(eng in output_text for eng in ['hello', 'how can i help', 'thank you']):
                                issues.append("⚠️ Language Switch: Spanish input → English output")
        
        # Check for invalid lead scores
        if analysis['metadata'].get('lead_score'):
            score = analysis['metadata']['lead_score']
            if isinstance(score, (int, float)) and score > 10:
                issues.append(f"⚠️ Invalid lead score: {score} (should be 1-10)")
        
        # Check for missing data collection
        if 'sofia' in analysis['name'].lower() or 'appointment' in analysis['name'].lower():
            if analysis['outputs']:
                output_text = str(analysis['outputs']).lower()
                if '¿qué tipo de negocio' in output_text or 'what type of business' in output_text:
                    issues.append("⚠️ Sofia asking basic questions instead of booking appointment")
        
        if issues:
            print("\n⚠️ ISSUES DETECTED:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("  ✅ No major issues detected")
        
        return analysis
        
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
        print("Please ensure LANGCHAIN_API_KEY is set in your .env file")
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
    analyses = []
    for trace_id in trace_ids:
        analysis = debug_trace_complete(client, trace_id)
        if analysis:
            analyses.append(analysis)
    
    # Compare traces
    if len(analyses) == 2:
        print("\n" + "="*80)
        print("📊 TRACE COMPARISON")
        print("="*80)
        
        trace1, trace2 = analyses[0], analyses[1]
        
        print(f"\nTrace 1: {trace1['run_id'][:8]}...")
        print(f"  - Status: {trace1['status']}")
        print(f"  - Name: {trace1['name']}")
        
        print(f"\nTrace 2: {trace2['run_id'][:8]}...")
        print(f"  - Status: {trace2['status']}")
        print(f"  - Name: {trace2['name']}")
        
        # Compare inputs
        print("\n📥 Input Comparison:")
        if 'messages' in trace1['inputs'] and 'messages' in trace2['inputs']:
            msgs1 = trace1['inputs']['messages']
            msgs2 = trace2['inputs']['messages']
            
            if len(msgs1) == len(msgs2):
                print(f"  ✅ Same number of messages: {len(msgs1)}")
            else:
                print(f"  ❌ Different message counts: {len(msgs1)} vs {len(msgs2)}")
        
        # Compare metadata
        print("\n📋 Metadata Comparison:")
        meta1 = trace1['metadata']
        meta2 = trace2['metadata']
        
        common_keys = set(meta1.keys()) & set(meta2.keys())
        if common_keys:
            for key in common_keys:
                if meta1[key] == meta2[key]:
                    print(f"  ✅ {key}: {meta1[key]} (same)")
                else:
                    print(f"  ❌ {key}: {meta1[key]} vs {meta2[key]} (different)")
    
    print("\n" + "="*80)
    print("🎯 DEBUGGING COMPLETE")
    print("="*80)
    
    # Additional debugging tips
    print("\n💡 DEBUGGING TIPS:")
    print("1. Check the LangSmith UI for visual trace analysis:")
    print(f"   https://smith.langchain.com/public/{trace_ids[0]}/r")
    print(f"   https://smith.langchain.com/public/{trace_ids[1]}/r")
    print("\n2. Use filters to find similar traces:")
    print("   - By metadata: filter='has(metadata, \"lead_score\")'")
    print("   - By error: filter='eq(error, true)'")
    print("   - By date: filter='gt(start_time, \"2025-07-21T00:00:00Z\")'")
    print("\n3. Export traces for offline analysis:")
    print("   - client.download_run(run_id)")
    print("   - client.export_runs(project_name='ghl-langgraph-agent')")

if __name__ == "__main__":
    main()