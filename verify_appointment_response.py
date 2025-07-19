#!/usr/bin/env python3
"""
Verify the appointment response was sent correctly
"""
import asyncio
from datetime import datetime
from app.workflow_runner import run_workflow_safe

TEST_CONTACT_ID = "z49hFQn0DxOX5sInJg60"

async def verify_appointment_response():
    """Verify appointment response"""
    
    print("🗓️ VERIFYING APPOINTMENT RESPONSE")
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
    
    try:
        result = await run_workflow_safe(webhook_data)
        
        if result.get('status') == 'completed':
            print("\n✅ Workflow completed successfully")
            
            # Check the state for messages
            if 'state' in result:
                state = result['state']
                messages = state.get('messages', [])
                
                # Find the last AI message
                for msg in reversed(messages):
                    if hasattr(msg, '__class__'):
                        class_name = msg.__class__.__name__
                        if class_name == 'AIMessage' or (hasattr(msg, 'role') and msg.role == 'assistant'):
                            content = msg.content if hasattr(msg, 'content') else str(msg)
                            
                            print(f"\n🤖 Sofia's Response:")
                            print("-" * 60)
                            print(content)
                            print("-" * 60)
                            
                            # Check if it contains appointment times
                            if "10:00 AM" in content or "2:00 PM" in content or "4:00 PM" in content:
                                print("\n✅ SUCCESS: Sofia offered specific appointment times!")
                            else:
                                print("\n❌ FAIL: Sofia didn't offer appointment times")
                            break
                            
        else:
            print(f"\n❌ Workflow failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_appointment_response())