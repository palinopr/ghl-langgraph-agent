#!/usr/bin/env python3
"""
Analyze LangSmith trace 1f064efb-c2bb-6489-b171-714cf92ca332
"""
import os
import json
from datetime import datetime
from langsmith import Client

# The trace ID to analyze
TRACE_ID = "1f064efb-c2bb-6489-b171-714cf92ca332"

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
        try:
            run = client.read_run(TRACE_ID)
        except Exception as e:
            print(f"Error reading trace: {e}")
            print("\nTrying alternative approach...")
            # Try fetching via project
            return
        
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
                limit=500
            ))
        except:
            child_runs = []
        
        # Sort by start time
        child_runs.sort(key=lambda x: x.start_time)
        
        print(f"\n{'='*60}")
        print(f"TOTAL CHILD RUNS: {len(child_runs)}")
        print(f"{'='*60}")
        
        # Analyze conversation flow
        print(f"\n{'='*60}")
        print("CONVERSATION FLOW ANALYSIS:")
        print(f"{'='*60}")
        
        messages_found = []
        for child in child_runs:
            # Look for messages in inputs/outputs
            if child.inputs and "messages" in child.inputs:
                for msg in child.inputs["messages"]:
                    if isinstance(msg, dict) and "content" in msg:
                        messages_found.append({
                            "role": msg.get("type", "unknown"),
                            "content": msg.get("content", ""),
                            "source": "input",
                            "node": child.name
                        })
            
            if child.outputs and "messages" in child.outputs:
                for msg in child.outputs["messages"]:
                    if isinstance(msg, dict) and "content" in msg:
                        messages_found.append({
                            "role": msg.get("type", "unknown"),
                            "content": msg.get("content", ""),
                            "source": "output",
                            "node": child.name
                        })
        
        # Print messages in order
        print("\nMessages Found:")
        for i, msg in enumerate(messages_found):
            print(f"\n{i+1}. [{msg['role'].upper()}] from {msg['node']} ({msg['source']}):")
            print(f"   {msg['content'][:200]}...")
        
        # Look for specific issues
        print(f"\n{'='*60}")
        print("ISSUE DETECTION:")
        print(f"{'='*60}")
        
        # Check for repeated questions
        questions_asked = []
        for msg in messages_found:
            if msg["role"] == "ai" and "?" in msg["content"]:
                questions_asked.append(msg["content"])
        
        print(f"\nQuestions asked by AI ({len(questions_asked)} total):")
        for q in questions_asked:
            print(f"- {q[:100]}...")
        
        # Check for duplicate questions
        if len(questions_asked) != len(set(questions_asked)):
            print("\n⚠️  DUPLICATE QUESTIONS DETECTED!")
            
        # Check for conversation history loading
        history_loaded = False
        for child in child_runs:
            if "load_conversation_history" in str(child.name) or \
               "conversation_history" in str(child.inputs):
                history_loaded = True
                print(f"\n✓ Conversation history loaded in: {child.name}")
        
        if not history_loaded:
            print("\n⚠️  NO CONVERSATION HISTORY LOADING DETECTED!")
        
        # Check for supervisor analysis
        supervisor_found = False
        for child in child_runs:
            if "supervisor" in child.name.lower():
                supervisor_found = True
                print(f"\n✓ Supervisor analysis found: {child.name}")
                if child.outputs:
                    print(f"  Output: {str(child.outputs)[:200]}...")
        
        if not supervisor_found:
            print("\n⚠️  NO SUPERVISOR ANALYSIS FOUND!")
        
        # Pattern analysis
        print(f"\n{'='*60}")
        print("PATTERN ANALYSIS:")
        print(f"{'='*60}")
        
        # Look for the repeating pattern mentioned in docs
        pattern_indicators = {
            "greeting_repeated": False,
            "question_repeated": False,
            "business_type_missed": False,
            "context_ignored": False
        }
        
        ai_messages = [msg for msg in messages_found if msg["role"] == "ai"]
        user_messages = [msg for msg in messages_found if msg["role"] == "human"]
        
        # Check for repeated greetings
        greetings = [msg for msg in ai_messages if "hola" in msg["content"].lower() or "👋" in msg["content"]]
        if len(greetings) > 1:
            pattern_indicators["greeting_repeated"] = True
            print("\n⚠️  REPEATED GREETINGS DETECTED!")
        
        # Check for business type handling
        business_mentions = [msg for msg in user_messages if "restaurante" in msg["content"].lower()]
        if business_mentions:
            # Check if AI recognized it
            recognition = [msg for msg in ai_messages if "restaurante" in msg["content"].lower()]
            if not recognition:
                pattern_indicators["business_type_missed"] = True
                print("\n⚠️  BUSINESS TYPE NOT RECOGNIZED!")
        
        print(f"\nPattern Summary:")
        for pattern, detected in pattern_indicators.items():
            status = "✓ DETECTED" if detected else "✗ Not found"
            print(f"- {pattern}: {status}")
        
        # Save analysis results
        analysis_results = {
            "trace_id": TRACE_ID,
            "timestamp": datetime.now().isoformat(),
            "run_details": {
                "name": run.name,
                "status": run.status,
                "start_time": str(run.start_time),
                "end_time": str(run.end_time)
            },
            "child_runs_count": len(child_runs),
            "messages_found": len(messages_found),
            "issues_detected": {
                "duplicate_questions": len(questions_asked) != len(set(questions_asked)),
                "history_loaded": history_loaded,
                "supervisor_found": supervisor_found,
                "patterns": pattern_indicators
            },
            "questions_asked": questions_asked,
            "conversation_flow": [
                {
                    "role": msg["role"],
                    "content": msg["content"][:100] + "...",
                    "node": msg["node"]
                }
                for msg in messages_found[:10]  # First 10 messages
            ]
        }
        
        # Save to file
        output_file = f"trace_analysis_{TRACE_ID[:8]}.json"
        with open(output_file, "w") as f:
            json.dump(analysis_results, f, indent=2)
        
        print(f"\n\nAnalysis saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_trace()