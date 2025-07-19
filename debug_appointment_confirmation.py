#!/usr/bin/env python3
"""
Debug appointment confirmation issue
"""
import asyncio
from datetime import datetime
from app.workflow_runner import run_workflow_safe

TEST_CONTACT_ID = "z49hFQn0DxOX5sInJg60"

async def test_appointment_confirmation():
    """Test appointment confirmation with debugging"""
    
    print("🗓️ TESTING APPOINTMENT CONFIRMATION")
    print("="*60)
    
    # Customer says yes
    webhook_data = {
        "id": TEST_CONTACT_ID,
        "contactId": TEST_CONTACT_ID,
        "message": "Sí",
        "body": "Sí",
        "type": "SMS",
        "locationId": "sHFG9Rw6BdGh6d6bfMqG",
        "direction": "inbound",
        "dateAdded": datetime.now().isoformat()
    }
    
    print(f"📱 Customer responds: '{webhook_data['message']}'")
    
    # Patch sofia to debug
    import app.agents.sofia_agent_v2
    from app.utils.smart_responder import get_smart_response
    
    original_node = app.agents.sofia_agent_v2.sofia_node_v2
    
    async def debug_sofia_node(state):
        print("\n=== SOFIA DEBUG ===")
        
        # Check last few messages
        messages = state.get('messages', [])
        print(f"Total messages: {len(messages)}")
        
        # Find last AI message
        last_ai_msg = None
        for msg in reversed(messages[-5:]):
            if isinstance(msg, dict) and msg.get('role') == 'assistant':
                last_ai_msg = msg.get('content', '')
                break
            elif hasattr(msg, 'role') and msg.role == 'assistant':
                last_ai_msg = msg.content
                break
        
        print(f"Last AI message: '{last_ai_msg[:100] if last_ai_msg else 'NOT FOUND'}...'")
        
        # Check if it contains appointment question
        if last_ai_msg:
            has_agendar = 'agendar' in last_ai_msg.lower()
            has_llamada = 'llamada' in last_ai_msg.lower()
            print(f"Contains 'agendar': {has_agendar}")
            print(f"Contains 'llamada': {has_llamada}")
        
        # Test smart responder directly
        response = get_smart_response(state, "sofia")
        print(f"Smart response: {response}")
        
        print("=== END DEBUG ===\n")
        
        return await original_node(state)
    
    # Replace temporarily
    app.agents.sofia_agent_v2.sofia_node_v2 = debug_sofia_node
    
    try:
        result = await run_workflow_safe(webhook_data)
        
        if result.get('status') == 'completed':
            print("✅ Workflow completed")
            
            # Check what was sent
            if 'state' in result:
                state = result['state']
                messages = state.get('messages', [])
                
                # Find Sofia's response
                for msg in reversed(messages):
                    if hasattr(msg, 'role') and msg.role == 'assistant':
                        print(f"\n🤖 Sofia's Response:")
                        print(f"'{msg.content}'")
                        
                        # Check if it's appointment slots
                        if "10:00 AM" in msg.content or "horarios disponibles" in msg.content:
                            print("\n✅ SUCCESS: Sofia offered appointment times!")
                        else:
                            print("\n❌ FAIL: Sofia didn't offer appointment times")
                        break
                        
        else:
            print(f"❌ Workflow failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        # Restore
        app.agents.sofia_agent_v2.sofia_node_v2 = original_node

if __name__ == "__main__":
    asyncio.run(test_appointment_confirmation())