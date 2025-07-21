#!/usr/bin/env python3
"""
Analyze post-deployment traces to verify fixes are working
"""
import os
from datetime import datetime
from langsmith import Client
import json
from typing import Dict, Any, List

# Set API key
os.environ["LANGSMITH_API_KEY"] = "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"

def extract_messages(run) -> List[Dict[str, str]]:
    """Extract messages from run inputs"""
    messages = []
    if run.inputs and 'messages' in run.inputs:
        for msg in run.inputs['messages']:
            if isinstance(msg, dict):
                role = msg.get('type', msg.get('role', 'unknown'))
                content = msg.get('content', '')
                messages.append({"role": role, "content": content})
    return messages

def analyze_state(run) -> Dict[str, Any]:
    """Analyze state data from run"""
    state_info = {
        "extracted_data": None,
        "lead_score": None,
        "current_agent": None,
        "response_sent": None,
        "collected_data": None
    }
    
    if run.outputs:
        # Check different possible state locations
        if isinstance(run.outputs, dict):
            state_info["extracted_data"] = run.outputs.get("extracted_data")
            state_info["lead_score"] = run.outputs.get("lead_score")
            state_info["current_agent"] = run.outputs.get("current_agent")
            state_info["response_sent"] = run.outputs.get("response_sent")
            
            # Check if collected_data exists (from conversation analysis)
            if "collected_data" in str(run.outputs):
                state_info["collected_data"] = "Present in output"
    
    return state_info

def check_agent_behavior(run) -> Dict[str, Any]:
    """Check if agents are using extracted_data correctly"""
    behavior = {
        "asked_for_name": False,
        "asked_for_business": False,
        "used_extracted_data": False,
        "repeated_question": False,
        "agent_response": None
    }
    
    if run.outputs:
        output_str = str(run.outputs).lower()
        
        # Check for name questions
        name_questions = ["¿cuál es tu nombre?", "what's your name", "cómo te llamas"]
        for q in name_questions:
            if q in output_str:
                behavior["asked_for_name"] = True
                break
        
        # Check for business questions
        business_questions = ["¿qué tipo de negocio", "what type of business", "tipo de empresa"]
        for q in business_questions:
            if q in output_str:
                behavior["asked_for_business"] = True
                break
        
        # Check if extracted_data was referenced
        if "extracted_data" in str(run.outputs):
            behavior["used_extracted_data"] = True
        
        # Extract agent response if available
        if isinstance(run.outputs, dict) and "messages" in run.outputs:
            msgs = run.outputs["messages"]
            if isinstance(msgs, list) and len(msgs) > 0:
                last_msg = msgs[-1]
                if isinstance(last_msg, dict):
                    behavior["agent_response"] = last_msg.get("content", "")
    
    return behavior

def check_fuzzy_matching(run) -> Dict[str, Any]:
    """Check if fuzzy matching is working"""
    fuzzy_info = {
        "fuzzy_extractor_loaded": False,
        "typo_detected": False,
        "fuzzy_match_found": False,
        "business_extracted": None
    }
    
    # Check logs and outputs for fuzzy matching evidence
    if run.outputs:
        output_str = str(run.outputs)
        
        # Check if fuzzy extractor is mentioned
        if "fuzzy" in output_str.lower():
            fuzzy_info["fuzzy_extractor_loaded"] = True
        
        # Check for common typos
        typos = ["reaturante", "resturante", "gimansio", "peluqeria"]
        for typo in typos:
            if typo in output_str.lower():
                fuzzy_info["typo_detected"] = True
                break
        
        # Check if business was extracted
        if "business_type" in output_str:
            fuzzy_info["business_extracted"] = "Found in output"
    
    return fuzzy_info

def analyze_trace_comprehensive(trace_id: str) -> Dict[str, Any]:
    """Perform comprehensive analysis of a single trace"""
    client = Client()
    
    try:
        # Get the run
        run = client.read_run(trace_id)
        
        # Extract basic info
        messages = extract_messages(run)
        state_info = analyze_state(run)
        behavior = check_agent_behavior(run)
        fuzzy_info = check_fuzzy_matching(run)
        
        # Get child runs for detailed analysis
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{trace_id}")',
            limit=50
        ))
        
        # Analyze each node
        nodes_executed = []
        intelligence_found = False
        agents_executed = []
        errors = []
        
        for child in child_runs:
            node_name = child.name
            nodes_executed.append(node_name)
            
            if "intelligence" in node_name.lower():
                intelligence_found = True
                # Check intelligence output
                if child.outputs:
                    print(f"\n🧠 Intelligence Node Output:")
                    print(f"   Extracted: {child.outputs.get('extracted_data', {})}")
                    print(f"   Score: {child.outputs.get('lead_score', 'N/A')}")
            
            if node_name in ["maria", "carlos", "sofia"]:
                agents_executed.append(node_name)
                # Check if agent used extracted_data
                if child.inputs and "extracted_data" in str(child.inputs):
                    print(f"\n✅ {node_name.upper()} received extracted_data")
                else:
                    print(f"\n❌ {node_name.upper()} did NOT receive extracted_data")
            
            if child.error:
                errors.append({
                    "node": node_name,
                    "error": child.error
                })
        
        return {
            "trace_id": trace_id,
            "status": run.status,
            "start_time": run.start_time,
            "messages": messages,
            "state_info": state_info,
            "behavior": behavior,
            "fuzzy_info": fuzzy_info,
            "nodes_executed": nodes_executed,
            "intelligence_found": intelligence_found,
            "agents_executed": agents_executed,
            "errors": errors
        }
        
    except Exception as e:
        return {
            "trace_id": trace_id,
            "error": str(e)
        }

def main():
    """Main analysis function"""
    print("🔍 Post-Deployment Trace Analysis")
    print("=" * 80)
    
    # Deployment time
    deployment_time = datetime(2025, 7, 21, 17, 58, 0)  # 12:58 PM CDT in UTC
    print(f"Deployment Time: {deployment_time}")
    print("\n")
    
    # Analyze each trace
    trace_ids = [
        "1f0665dd-9068-66a3-84bb-26a8a0c201a5",
        "1f0665de-65c0-649d-88fc-17a24f9ca734",
        "1f0665df-46f9-6d57-889b-74d1726b4a41"
    ]
    
    all_results = []
    
    for i, trace_id in enumerate(trace_ids, 1):
        print(f"\n{'='*80}")
        print(f"TRACE {i}: {trace_id}")
        print(f"{'='*80}")
        
        result = analyze_trace_comprehensive(trace_id)
        all_results.append(result)
        
        if "error" in result and not "messages" in result:
            print(f"❌ Error analyzing trace: {result['error']}")
            continue
        
        # Print messages
        print("\n📨 MESSAGES:")
        for msg in result["messages"]:
            if msg["role"] == "human":
                print(f"   Customer: {msg['content']}")
            else:
                print(f"   AI: {msg['content'][:100]}...")
        
        # Print state info
        print("\n📊 STATE ANALYSIS:")
        print(f"   Extracted Data: {result['state_info']['extracted_data']}")
        print(f"   Lead Score: {result['state_info']['lead_score']}")
        print(f"   Current Agent: {result['state_info']['current_agent']}")
        print(f"   Response Sent: {result['state_info']['response_sent']}")
        
        # Print behavior analysis
        print("\n🤖 AGENT BEHAVIOR:")
        print(f"   Asked for name: {result['behavior']['asked_for_name']}")
        print(f"   Asked for business: {result['behavior']['asked_for_business']}")
        print(f"   Used extracted_data: {result['behavior']['used_extracted_data']}")
        if result['behavior']['agent_response']:
            print(f"   Response: {result['behavior']['agent_response'][:100]}...")
        
        # Print fuzzy matching info
        print("\n🔤 FUZZY MATCHING:")
        print(f"   Fuzzy extractor loaded: {result['fuzzy_info']['fuzzy_extractor_loaded']}")
        print(f"   Typo detected: {result['fuzzy_info']['typo_detected']}")
        print(f"   Business extracted: {result['fuzzy_info']['business_extracted']}")
        
        # Print workflow info
        print("\n🔄 WORKFLOW EXECUTION:")
        print(f"   Nodes: {' → '.join(result['nodes_executed'][:5])}...")
        print(f"   Intelligence Layer: {'✅' if result['intelligence_found'] else '❌'}")
        print(f"   Agents: {result['agents_executed']}")
        
        # Print errors if any
        if result['errors']:
            print("\n❌ ERRORS:")
            for err in result['errors']:
                print(f"   {err['node']}: {err['error']}")
    
    # Summary
    print(f"\n{'='*80}")
    print("📋 SUMMARY")
    print(f"{'='*80}")
    
    issues_found = []
    
    for i, result in enumerate(all_results, 1):
        if "error" in result and not "messages" in result:
            continue
            
        print(f"\nTrace {i}:")
        
        # Check for repeated questions
        if result['behavior']['asked_for_name'] and result['state_info']['extracted_data']:
            if isinstance(result['state_info']['extracted_data'], dict) and 'name' in result['state_info']['extracted_data']:
                issues_found.append(f"Trace {i}: Asked for name when already extracted")
                print("   ❌ Asked for name when already in extracted_data")
            else:
                print("   ✅ Correctly asked for name (not in extracted_data)")
        
        # Check if extracted_data was used
        if result['behavior']['used_extracted_data']:
            print("   ✅ Agent used extracted_data")
        else:
            print("   ⚠️  No evidence of using extracted_data")
        
        # Check fuzzy matching
        if result['fuzzy_info']['typo_detected']:
            if result['fuzzy_info']['business_extracted']:
                print("   ✅ Fuzzy matching handled typo")
            else:
                print("   ❌ Typo detected but not extracted")
                issues_found.append(f"Trace {i}: Typo not handled by fuzzy matching")
    
    # Final verdict
    print(f"\n{'='*80}")
    print("🎯 DEPLOYMENT VERIFICATION")
    print(f"{'='*80}")
    
    if not issues_found:
        print("✅ All fixes appear to be working correctly!")
    else:
        print("❌ Issues found:")
        for issue in issues_found:
            print(f"   - {issue}")
    
    # Save detailed results
    with open("post_deployment_analysis.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print("\n📄 Detailed results saved to post_deployment_analysis.json")

if __name__ == "__main__":
    main()