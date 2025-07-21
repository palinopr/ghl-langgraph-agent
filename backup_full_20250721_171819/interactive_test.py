#!/usr/bin/env python3
"""
Interactive testing - type messages and see responses immediately
"""
import asyncio
import sys
sys.path.append('.')

from app.workflow import app
from langchain_core.messages import HumanMessage

async def interactive_test():
    """Run interactive test session"""
    print("🤖 Local Test Environment")
    print("Type 'quit' to exit, 'reset' to start new conversation")
    print("Commands: 'state' - show current state, 'help' - show commands")
    print("="*60)
    
    state = {
        "messages": [],
        "contact_id": "interactive_test",
        "webhook_data": {
            "contactId": "interactive_test",
            "locationId": "test_location",
            "type": "SMS"
        }
    }
    
    while True:
        # Get user input
        message = input("\nYou: ").strip()
        
        if message.lower() == 'quit':
            break
        elif message.lower() == 'reset':
            state = {
                "messages": [],
                "contact_id": "interactive_test",
                "webhook_data": {
                    "contactId": "interactive_test",
                    "locationId": "test_location",
                    "type": "SMS"
                }
            }
            print("🔄 Conversation reset")
            continue
        elif message.lower() == 'state':
            print(f"\n📊 Current State:")
            print(f"  Extracted: {state.get('extracted_data', {})}")
            print(f"  Score: {state.get('lead_score', 0)}")
            print(f"  Agent: {state.get('current_agent', 'none')}")
            print(f"  Messages: {len(state.get('messages', []))}")
            continue
        elif message.lower() == 'help':
            print("\n📋 Commands:")
            print("  quit - Exit the program")
            print("  reset - Start new conversation")
            print("  state - Show current state")
            print("  help - Show this help")
            continue
        
        # Add message to state
        state["messages"].append(HumanMessage(content=message))
        
        # Run workflow
        print("🔄 Processing...")
        try:
            result = await app.ainvoke(state)
            
            # Show response
            if result.get("messages"):
                last_msg = result["messages"][-1]
                if hasattr(last_msg, 'content'):
                    print(f"\n🤖 AI: {last_msg.content}")
            
            # Show key state changes
            if result.get('extracted_data') != state.get('extracted_data'):
                print(f"\n📊 Extracted: {result.get('extracted_data')}")
            if result.get('lead_score') != state.get('lead_score'):
                print(f"🎯 Score: {result.get('lead_score')}")
            if result.get('current_agent') != state.get('current_agent'):
                print(f"👤 Agent: {result.get('current_agent')}")
            
            # Update state
            state = result
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Try 'reset' to start over")

if __name__ == "__main__":
    try:
        asyncio.run(interactive_test())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")