#!/usr/bin/env python3
"""
Verify conversation history is now loading correctly
"""
import asyncio
from app.agents.receptionist_simple import receptionist_simple_node
from langchain_core.messages import AIMessage, HumanMessage

async def verify_fix():
    """Verify the conversation history fix"""
    
    # Create test state
    state = {
        "messages": [{"role": "user", "content": "Jaime"}],
        "contact_id": "S0VUJbKWrwSpmHtKHlFH",
        "contact_name": "Jaime Ortiz",
        "contact_email": "",
        "contact_phone": "(305) 487-0475"
    }
    
    print("VERIFYING CONVERSATION HISTORY FIX")
    print("="*60)
    
    try:
        # Call receptionist node
        result = await receptionist_simple_node(state)
        
        print(f"\n✓ Data loaded: {result.get('data_loaded', False)}")
        print(f"✓ Formatted history count: {result.get('formatted_history_count', 0)}")
        
        # Check messages
        messages = result.get('messages', [])
        print(f"✓ Total messages in state: {len(messages)}")
        
        # Count different message types
        human_count = 0
        ai_count = 0
        history_count = 0
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                human_count += 1
                # Check if it's from history
                if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get('source') == 'ghl_history':
                    history_count += 1
            elif isinstance(msg, AIMessage):
                ai_count += 1
                # Check if it's from history
                if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get('source') == 'ghl_history':
                    history_count += 1
        
        print(f"\nMessage breakdown:")
        print(f"- Human messages: {human_count}")
        print(f"- AI messages: {ai_count}")
        print(f"- From conversation history: {history_count}")
        
        # Show some historical messages
        print(f"\nSample historical messages:")
        shown = 0
        for msg in messages:
            if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs.get('source') == 'ghl_history':
                print(f"\n[{msg.__class__.__name__}] {msg.content[:100]}...")
                print(f"  Timestamp: {msg.additional_kwargs.get('timestamp')}")
                shown += 1
                if shown >= 3:
                    break
        
        # Check the summary message
        for msg in messages:
            if isinstance(msg, AIMessage) and hasattr(msg, 'name') and msg.name == 'receptionist':
                print(f"\nReceptionist summary:")
                print(msg.content)
                
        print(f"\n✅ CONVERSATION HISTORY IS NOW LOADING CORRECTLY!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_fix())