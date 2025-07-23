#!/usr/bin/env python3
"""
Verify all conversational agents have conversation tracking
"""

import os
import sys
import ast

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_agent_file(filepath, agent_name):
    """Check if an agent file has conversation tracking"""
    with open(filepath, 'r') as f:
        content = f.read()
    
    checks = {
        "imports analyzer": "from app.utils.conversation_analyzer import analyze_conversation_state" in content,
        "calls analyzer": f"analyze_conversation_state(messages, agent_name=\"{agent_name}\")" in content,
        "uses analysis": "conversation_analysis[" in content or "conversation_analysis.get(" in content,
        "stage-based logic": "conversation_analysis['stage']" in content,
        "tracks topics": "topics_discussed" in content,
        "tracks pending": "pending_info" in content
    }
    
    return checks

def main():
    print("\n" + "="*80)
    print("Verifying Conversation Tracking in All Agents")
    print("="*80 + "\n")
    
    agents = {
        "maria": "app/agents/maria_agent.py",
        "carlos": "app/agents/carlos_agent.py", 
        "sofia": "app/agents/sofia_agent.py"
    }
    
    all_good = True
    
    for agent_name, filepath in agents.items():
        print(f"\n{agent_name.upper()} Agent ({filepath}):")
        print("-" * 50)
        
        checks = check_agent_file(filepath, agent_name)
        
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check_name}")
            if not passed:
                all_good = False
        
        # Verify the agent is using the analysis properly
        if all(checks.values()):
            print(f"✅ {agent_name.upper()} has complete conversation tracking!")
        else:
            print(f"❌ {agent_name.upper()} is missing some tracking features")
    
    print("\n" + "="*80)
    if all_good:
        print("✅ ALL AGENTS HAVE CONVERSATION TRACKING!")
    else:
        print("❌ Some agents need conversation tracking updates")
    print("="*80)

if __name__ == "__main__":
    main()