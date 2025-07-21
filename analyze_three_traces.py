#!/usr/bin/env python3
"""
Extensive debug analysis of three specific traces
"""
import os
from langsmith import Client
from datetime import datetime, timezone
import json
from typing import Dict, List, Any

# Set up the API key
os.environ["LANGSMITH_API_KEY"] = "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"

# Initialize client
client = Client()

# Traces to analyze
TRACE_IDS = [
    "1f066591-9d77-6367-9a7c-c8adf51eb60a",
    "1f066592-8528-6c8d-8bb9-f3081fd6e993", 
    "1f066593-5ae3-6ff0-bfed-dc5c173583cf"
]

def get_all_runs_for_trace(trace_id: str) -> List[Any]:
    """Get all runs including nested ones for a trace"""
    all_runs = []
    
    try:
        # Get main run
        main_run = client.read_run(trace_id)
        all_runs.append(main_run)
        
        # Get all child runs
        child_runs = list(client.list_runs(
            project_name="ghl-langgraph-agent",
            filter=f'eq(parent_run_id, "{trace_id}")'
        ))
        all_runs.extend(child_runs)
        
        # Get grandchildren
        for child in child_runs:
            grandchildren = list(client.list_runs(
                project_name="ghl-langgraph-agent",
                filter=f'eq(parent_run_id, "{child.id}")'
            ))
            all_runs.extend(grandchildren)
            
    except Exception as e:
        print(f"Error getting runs: {e}")
        
    return all_runs

def analyze_trace_extensively(trace_id: str) -> Dict[str, Any]:
    """Perform extensive analysis of a single trace"""
    print(f"\n{'='*100}")
    print(f"🔍 EXTENSIVE ANALYSIS OF TRACE: {trace_id}")
    print(f"{'='*100}")
    
    analysis = {
        "trace_id": trace_id,
        "issues": [],
        "warnings": [],
        "successes": [],
        "details": {}
    }
    
    try:
        # Get all runs
        all_runs = get_all_runs_for_trace(trace_id)
        print(f"\n📊 Found {len(all_runs)} total runs")
        
        # Get main run
        main_run = all_runs[0]
        print(f"\nMain Run Status: {main_run.status}")
        print(f"Start Time: {main_run.start_time}")
        
        # Extract input message
        input_message = None
        if main_run.inputs and 'messages' in main_run.inputs:
            msgs = main_run.inputs['messages']
            if msgs and len(msgs) > 0:
                last_msg = msgs[-1]
                if isinstance(last_msg, dict) and 'content' in last_msg:
                    input_message = last_msg['content']
                    print(f"Input Message: '{input_message}'")
                    analysis["details"]["input_message"] = input_message
        
        # Analyze each node in detail
        print(f"\n🔄 NODE-BY-NODE ANALYSIS:")
        print("-" * 80)
        
        for run in all_runs[1:]:  # Skip main run
            run_name = run.name.lower()
            
            # RECEPTIONIST NODE
            if "receptionist" in run_name:
                print(f"\n📋 RECEPTIONIST NODE:")
                if run.outputs:
                    # Check conversation history
                    history = run.outputs.get("conversation_history", [])
                    print(f"  - Conversation history: {len(history)} messages")
                    if len(history) > 10:
                        analysis["warnings"].append(f"Loading {len(history)} historical messages (should be filtered)")
                    
                    # Check if loading from correct thread
                    if history:
                        print(f"  - First message: {history[0].get('body', '')[:50] if history[0] else 'None'}...")
                        print(f"  - Last message: {history[-1].get('body', '')[:50] if history[-1] else 'None'}...")
                    
                    # Check custom fields
                    fields = run.outputs.get("previous_custom_fields", {})
                    if fields:
                        print(f"  - Previous score: {fields.get('score', 'None')}")
                        print(f"  - Previous business: {fields.get('business_type', 'None')}")
            
            # INTELLIGENCE NODE
            elif "intelligence" in run_name:
                print(f"\n🧠 INTELLIGENCE NODE:")
                if run.outputs:
                    score = run.outputs.get("lead_score")
                    extracted = run.outputs.get("extracted_data", {})
                    reasoning = run.outputs.get("score_reasoning", "")
                    
                    print(f"  - Lead score: {score}")
                    print(f"  - Score reasoning: {reasoning}")
                    
                    # Check extraction quality
                    if extracted:
                        print(f"  - Extracted data:")
                        for key, value in extracted.items():
                            if value and key != "extraction_confidence":
                                print(f"    • {key}: {value}")
                                
                                # Check for bad extractions
                                if key == "business_type" and value and "hola" in str(value).lower():
                                    analysis["issues"].append(f"Bad business extraction: '{value}'")
                                
                                if key == "budget" and input_message and ":" in input_message and "AM" in input_message.upper():
                                    analysis["issues"].append(f"Time extracted as budget: '{value}'")
                    
                    # Check score appropriateness
                    if input_message and input_message.lower() == "hola" and score and score > 3:
                        analysis["issues"].append(f"Score too high ({score}) for simple 'hola'")
                    
                    analysis["details"]["intelligence_score"] = score
                    analysis["details"]["extracted_data"] = extracted
            
            # SUPERVISOR NODE
            elif "supervisor" in run_name:
                print(f"\n🎯 SUPERVISOR NODE:")
                if run.outputs:
                    supervisor_score = run.outputs.get("lead_score")
                    next_agent = run.outputs.get("next_agent")
                    route = run.outputs.get("lead_category")
                    
                    print(f"  - Score: {supervisor_score}")
                    print(f"  - Next agent: {next_agent}")
                    print(f"  - Route: {route}")
                    
                    # Check for score changes
                    if "intelligence_score" in analysis["details"] and supervisor_score:
                        intel_score = analysis["details"]["intelligence_score"]
                        if intel_score and supervisor_score != intel_score:
                            score_change = supervisor_score - intel_score
                            print(f"  - ⚠️  Score changed: {intel_score} → {supervisor_score} (diff: {score_change})")
                            
                            # Check if this is our historical boost issue
                            if input_message and input_message.lower() == "hola" and score_change > 2:
                                analysis["issues"].append(f"Supervisor boosted 'hola' score by {score_change} (historical context issue)")
                            elif score_change > 0:
                                analysis["warnings"].append(f"Supervisor increased score by {score_change}")
                    
                    analysis["details"]["supervisor_score"] = supervisor_score
                    analysis["details"]["routed_to"] = next_agent
            
            # AGENT NODES (Maria, Carlos, Sofia)
            elif any(agent in run_name for agent in ["maria", "carlos", "sofia"]):
                agent_name = next((a for a in ["maria", "carlos", "sofia"] if a in run_name), "agent")
                print(f"\n💬 {agent_name.upper()} AGENT:")
                
                if run.outputs and 'messages' in run.outputs:
                    messages = run.outputs['messages']
                    agent_messages = []
                    
                    for msg in messages:
                        if hasattr(msg, 'content') and msg.content:
                            if hasattr(msg, 'name') and msg.name not in ['receptionist', 'supervisor', 'intelligence']:
                                content = msg.content
                                agent_messages.append(content)
                                print(f"  - Response: {content[:100]}...")
                                
                                # Check for debug messages
                                debug_patterns = ['lead scored', 'routing to', 'debug:', 'error:', 'data loaded', 'analysis complete']
                                for pattern in debug_patterns:
                                    if pattern in content.lower():
                                        analysis["issues"].append(f"Debug message in {agent_name} response: '{pattern}'")
                    
                    analysis["details"][f"{agent_name}_response"] = agent_messages
            
            # RESPONDER NODE
            elif "responder" in run_name:
                print(f"\n📤 RESPONDER NODE:")
                if run.outputs:
                    sent = run.outputs.get("response_sent", False)
                    status = run.outputs.get("responder_status", "")
                    print(f"  - Message sent: {'Yes' if sent else 'No'}")
                    print(f"  - Status: {status}")
                    
                    if not sent:
                        analysis["warnings"].append("Responder did not send message")
        
        # CHECK OUR SPECIFIC FIXES
        print(f"\n{'='*80}")
        print("🔍 CHECKING OUR SPECIFIC FIXES:")
        print("-" * 80)
        
        # 1. Historical Context Boost Fix
        if input_message and input_message.lower() == "hola":
            intel_score = analysis["details"].get("intelligence_score", 0)
            final_score = analysis["details"].get("supervisor_score", intel_score)
            
            print(f"\n1. Historical Context Boost Fix:")
            print(f"   Input: 'hola'")
            print(f"   Intelligence score: {intel_score}")
            print(f"   Final score: {final_score}")
            
            if final_score and final_score > 3:
                print(f"   ❌ FAILED: Score {final_score} too high for 'hola'")
                analysis["issues"].append(f"Historical boost fix not working: 'hola' got score {final_score}")
            else:
                print(f"   ✅ PASSED: Score appropriate for 'hola'")
                analysis["successes"].append("Historical boost fix working correctly")
        
        # 2. Debug Message Filtering
        print(f"\n2. Debug Message Filtering:")
        debug_found = any("Debug message" in issue for issue in analysis["issues"])
        if debug_found:
            print(f"   ❌ FAILED: Debug messages found in output")
        else:
            print(f"   ✅ PASSED: No debug messages in output")
            analysis["successes"].append("Debug message filtering working")
        
        # 3. Conversation History Loading
        print(f"\n3. Conversation History Loading:")
        history_warning = any("historical messages" in warning for warning in analysis["warnings"])
        if history_warning:
            print(f"   ⚠️  WARNING: Still loading too many historical messages")
        else:
            print(f"   ✅ PASSED: Conversation history properly filtered")
            analysis["successes"].append("Conversation history filtering working")
        
        # 4. Data Extraction Quality
        print(f"\n4. Data Extraction Quality:")
        bad_extraction = any("Bad business extraction" in issue for issue in analysis["issues"])
        if bad_extraction:
            print(f"   ❌ FAILED: Poor quality extractions found")
        else:
            print(f"   ✅ PASSED: Extractions are clean")
            analysis["successes"].append("Data extraction quality good")
        
        # Final Summary
        print(f"\n{'='*80}")
        print("📊 ANALYSIS SUMMARY:")
        print("-" * 80)
        print(f"✅ Successes: {len(analysis['successes'])}")
        for success in analysis['successes']:
            print(f"   - {success}")
        
        print(f"\n⚠️  Warnings: {len(analysis['warnings'])}")
        for warning in analysis['warnings']:
            print(f"   - {warning}")
        
        print(f"\n❌ Issues: {len(analysis['issues'])}")
        for issue in analysis['issues']:
            print(f"   - {issue}")
        
        return analysis
        
    except Exception as e:
        print(f"\n❌ Error analyzing trace: {e}")
        import traceback
        traceback.print_exc()
        analysis["issues"].append(f"Analysis error: {e}")
        return analysis

def main():
    """Analyze all three traces"""
    print("🚀 EXTENSIVE TRACE ANALYSIS")
    print("Analyzing 3 traces to verify our fixes are working")
    
    # Check deployment time
    deployment_time = datetime(2025, 7, 21, 17, 20, 0, tzinfo=timezone.utc)
    print(f"\nDeployment pushed at: {deployment_time}")
    print("Checking if these traces are post-deployment...")
    
    all_analyses = []
    
    for i, trace_id in enumerate(TRACE_IDS, 1):
        print(f"\n\n{'#'*100}")
        print(f"TRACE {i}/3")
        print(f"{'#'*100}")
        
        analysis = analyze_trace_extensively(trace_id)
        all_analyses.append(analysis)
        
        # Check timing
        try:
            run = client.read_run(trace_id)
            run_time = run.start_time
            if isinstance(run_time, str):
                run_time = datetime.fromisoformat(run_time.replace('Z', '+00:00'))
            elif run_time.tzinfo is None:
                run_time = run_time.replace(tzinfo=timezone.utc)
            
            if run_time > deployment_time:
                print(f"\n✅ This trace is POST-DEPLOYMENT")
            else:
                print(f"\n⚠️  This trace is PRE-DEPLOYMENT")
        except:
            pass
    
    # Overall summary
    print(f"\n\n{'='*100}")
    print("🎯 OVERALL SUMMARY")
    print("="*100)
    
    total_issues = sum(len(a["issues"]) for a in all_analyses)
    total_warnings = sum(len(a["warnings"]) for a in all_analyses)
    total_successes = sum(len(a["successes"]) for a in all_analyses)
    
    print(f"\nTotal Issues: {total_issues}")
    print(f"Total Warnings: {total_warnings}")
    print(f"Total Successes: {total_successes}")
    
    # Check specific fixes across all traces
    print(f"\n🔍 FIX VERIFICATION ACROSS ALL TRACES:")
    
    # Historical boost fix
    hola_traces = [a for a in all_analyses if a["details"].get("input_message", "").lower() == "hola"]
    if hola_traces:
        print(f"\n1. Historical Boost Fix ('hola' messages):")
        for analysis in hola_traces:
            score = analysis["details"].get("supervisor_score") or analysis["details"].get("intelligence_score")
            print(f"   - Trace {analysis['trace_id']}: Score {score}")
    
    # Debug messages
    debug_issues = sum(1 for a in all_analyses for issue in a["issues"] if "Debug message" in issue)
    print(f"\n2. Debug Message Filtering:")
    print(f"   - Debug messages found: {debug_issues}")
    
    # Save detailed report
    with open("trace_analysis_report.json", "w") as f:
        json.dump(all_analyses, f, indent=2, default=str)
    print(f"\n📄 Detailed report saved to: trace_analysis_report.json")

if __name__ == "__main__":
    main()