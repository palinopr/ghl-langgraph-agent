#!/usr/bin/env python3
"""
Analyze LangSmith traces to understand why the agent repeats the challenge question
"""
import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import langsmith
try:
    from langsmith import Client
except ImportError:
    print("Error: langsmith package not installed")
    print("Please install it with: pip install langsmith")
    sys.exit(1)

def analyze_challenge_repeat(trace_id):
    """Analyze a trace to understand challenge question repetition"""
    
    # Check for API key
    api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("Error: LANGSMITH_API_KEY or LANGCHAIN_API_KEY not set in environment")
        return
    
    try:
        client = Client()
        run = client.read_run(trace_id)
        
        print(f"\n{'='*60}")
        print(f"TRACE ANALYSIS: {trace_id}")
        print(f"{'='*60}")
        print(f"Name: {run.name}")
        print(f"Status: {run.status}")
        print(f"Start Time: {run.start_time}")
        
        # Look for conversation analyzer output
        print(f"\n{'='*40}")
        print("CHECKING CONVERSATION ANALYZER OUTPUT:")
        print(f"{'='*40}")
        
        # Get child runs
        child_runs = list(client.list_runs(
            project_name=os.getenv("LANGSMITH_PROJECT", "ghl-langgraph-agent"),
            filter=f'eq(parent_run_id, "{trace_id}")',
            limit=100
        ))
        
        # Track conversation flow
        conversation_flow = []
        challenge_mentions = []
        
        for child in child_runs:
            # Look for conversation analyzer
            if "conversation_analyzer" in child.name.lower() or "analyze" in child.name.lower():
                print(f"\nFound Conversation Analyzer: {child.name}")
                if child.outputs:
                    print("Analyzer Output:")
                    print(json.dumps(child.outputs, indent=2, default=str)[:1000])
                    
            # Look for agent responses
            if child.run_type == "llm" and child.outputs:
                try:
                    # Extract the actual message content
                    content = ""
                    if "generations" in child.outputs:
                        gen = child.outputs["generations"][0][0]
                        if "text" in gen:
                            content = gen["text"]
                        elif "message" in gen and "content" in gen["message"]:
                            content = gen["message"]["content"]
                    
                    if content:
                        conversation_flow.append({
                            "time": child.start_time,
                            "agent": child.name,
                            "content": content[:200]
                        })
                        
                        # Check for challenge question mentions
                        if "challenge" in content.lower() or "question" in content.lower():
                            challenge_mentions.append({
                                "time": child.start_time,
                                "agent": child.name,
                                "content": content[:300]
                            })
                except:
                    pass
        
        # Show conversation flow
        print(f"\n{'='*40}")
        print("CONVERSATION FLOW:")
        print(f"{'='*40}")
        for i, msg in enumerate(sorted(conversation_flow, key=lambda x: x["time"])):
            print(f"\n{i+1}. [{msg['time'].strftime('%H:%M:%S')}] {msg['agent']}")
            print(f"   {msg['content']}...")
            
        # Show challenge mentions
        if challenge_mentions:
            print(f"\n{'='*40}")
            print("CHALLENGE QUESTION MENTIONS:")
            print(f"{'='*40}")
            for i, mention in enumerate(challenge_mentions):
                print(f"\n{i+1}. [{mention['time'].strftime('%H:%M:%S')}] {mention['agent']}")
                print(f"   {mention['content']}...")
        
        # Look for state information
        print(f"\n{'='*40}")
        print("STATE INFORMATION:")
        print(f"{'='*40}")
        
        if run.inputs:
            inputs_str = json.dumps(run.inputs, indent=2, default=str)
            
            # Look for conversation history
            if "conversation_history" in inputs_str:
                print("\nConversation History Found in Inputs")
                
            # Look for challenge-related state
            if "challenge" in inputs_str.lower():
                print("\nChallenge-related content in inputs:")
                # Extract relevant parts
                for line in inputs_str.split('\n'):
                    if "challenge" in line.lower():
                        print(f"  {line.strip()}")
                        
        # Final analysis
        print(f"\n{'='*40}")
        print("ANALYSIS SUMMARY:")
        print(f"{'='*40}")
        print(f"- Total conversation steps: {len(conversation_flow)}")
        print(f"- Challenge mentions: {len(challenge_mentions)}")
        
        if len(challenge_mentions) > 1:
            print("\n⚠️  ISSUE FOUND: Challenge question mentioned multiple times!")
            print("This suggests the agent may not be tracking that the challenge was already answered.")
            
    except Exception as e:
        print(f"Error analyzing trace: {e}")

# Analyze both traces
trace_ids = [
    "1f064982-efbc-6aba-9b85-f3b5227b2c2b",
    "1f064974-3f93-6d5e-a756-1dd912bc6798"
]

for trace_id in trace_ids:
    analyze_challenge_repeat(trace_id)
    
print(f"\n{'='*60}")
print("RECOMMENDATION:")
print(f"{'='*60}")
print("Check the conversation analyzer logic to ensure it:")
print("1. Properly tracks when challenge questions have been answered")
print("2. Updates the conversation state to reflect completed challenges")
print("3. Prevents agents from re-asking already answered questions")