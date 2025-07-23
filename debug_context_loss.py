#!/usr/bin/env python3
"""
Debug Context Loss Issue - Why is conversation history not being loaded?
"""
import asyncio
import json
from typing import Dict, Any
from app.tools.ghl_client_simple import SimpleGHLClient
from app.tools.conversation_loader import ConversationLoader
from app.utils.simple_logger import get_logger
from app.agents.receptionist_agent import receptionist_node
from langchain_core.messages import HumanMessage

logger = get_logger("debug_context")


async def test_ghl_conversation_loading():
    """Test if GHL conversation loading works"""
    print("="*80)
    print("TESTING GHL CONVERSATION LOADING")
    print("="*80)
    
    # Test data from the trace
    contact_id = "0ZCqYBRX57Q2xLNUHvzu"
    conversation_id = None  # Not shown in trace
    
    print(f"\nContact ID: {contact_id}")
    
    # Initialize GHL client
    ghl_client = SimpleGHLClient()
    loader = ConversationLoader(ghl_client)
    
    # Try to load conversation history
    try:
        messages = await loader.load_conversation_history(
            contact_id=contact_id,
            conversation_id=conversation_id,
            limit=50
        )
        
        print(f"\nLoaded {len(messages)} messages from GHL")
        for i, msg in enumerate(messages[:5]):  # Show first 5
            print(f"  {i+1}. {msg}")
            
    except Exception as e:
        print(f"\n❌ Failed to load from GHL: {str(e)}")
        print("This might be why receptionist returned 0 messages!")


async def test_receptionist_with_context():
    """Test receptionist node with the actual state"""
    print("\n" + "="*80)
    print("TESTING RECEPTIONIST NODE")
    print("="*80)
    
    # Create state similar to the trace
    state = {
        "messages": [HumanMessage(content="si")],  # What LangGraph Cloud provides
        "contact_id": "0ZCqYBRX57Q2xLNUHvzu",
        "conversation_id": "",  # Empty in trace
        "webhook_data": {"body": "si"},
        "thread_id": "contact-0ZCqYBRX57Q2xLNUHvzu"
    }
    
    print(f"\nInput state:")
    print(f"  Messages: {len(state['messages'])}")
    print(f"  Contact ID: {state['contact_id']}")
    print(f"  Thread ID: {state['thread_id']}")
    
    try:
        # Call receptionist
        result = await receptionist_node(state)
        
        print(f"\nReceptionist output:")
        print(f"  Messages returned: {len(result.get('messages', []))}")
        print(f"  Is first contact: {result.get('is_first_contact')}")
        print(f"  Thread message count: {result.get('thread_message_count')}")
        
        if len(result.get('messages', [])) == 0:
            print("\n⚠️ PROBLEM: Receptionist returned 0 messages!")
            print("This explains why Maria has no context!")
            
    except Exception as e:
        print(f"\n❌ Receptionist error: {str(e)}")


def analyze_context_loss_pattern():
    """Analyze why context is lost"""
    print("\n" + "="*80)
    print("CONTEXT LOSS ANALYSIS")
    print("="*80)
    
    print("\nPossible reasons for context loss:")
    print("\n1. GHL API Issues:")
    print("   - No conversation_id in state (might be required)")
    print("   - Contact might not have conversation history")
    print("   - API credentials might be incorrect")
    
    print("\n2. Receptionist Logic Issues:")
    print("   - Error in conversation loading")
    print("   - MessageManager deduplication too aggressive")
    print("   - Exception caught and returning empty messages")
    
    print("\n3. State Flow Issues:")
    print("   - Thread ID not matching GHL's expectations")
    print("   - Missing required fields for GHL API")
    
    print("\n4. Message Duplication Separate Issue:")
    print("   - Agent node receiving 1 message but outputting 4 copies")
    print("   - This happens BEFORE Maria even runs")
    print("   - Likely the create_react_agent internal behavior")


async def main():
    """Run all debug tests"""
    await test_ghl_conversation_loading()
    await test_receptionist_with_context()
    analyze_context_loss_pattern()
    
    print("\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)
    
    print("\n1. Check GHL API response:")
    print("   - Add more logging to conversation_loader.py")
    print("   - Verify conversation_id is being passed correctly")
    
    print("\n2. Fix receptionist error handling:")
    print("   - Log the exact error when loading fails")
    print("   - Don't silently return empty messages")
    
    print("\n3. Fix message duplication:")
    print("   - The 'agent' node is duplicating input 4x")
    print("   - This is separate from context loss but compounds the problem")


if __name__ == "__main__":
    import os
    # Use the API key from env
    if not os.environ.get("GHL_API_KEY"):
        print("❌ GHL_API_KEY not set. Context loading will fail!")
    
    asyncio.run(main())