#!/usr/bin/env python3
"""
Run the workflow directly without app imports to avoid pydantic issues
"""
import os
import asyncio
import sys
from datetime import datetime

# Set environment variables BEFORE any imports
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "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"
os.environ["LANGCHAIN_PROJECT"] = "ghl-agent-direct-test"
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
os.environ["GHL_API_KEY"] = "pit-21cee867-6a57-4eea-b6fa-2bd4462934d0"
os.environ["GHL_LOCATION_ID"] = "sHFG9Rw6BdGh6d6bfMqG"

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_workflow():
    """Test workflow with different scenarios"""
    
    # Import here after env vars are set
    from app.workflow_production_ready import workflow
    
    print("🚀 Direct Workflow Testing")
    print("=" * 50)
    
    # Test scenarios
    test_cases = [
        {
            "name": "New Contact - Low Intent",
            "message": "Hola, qué es esto?",
            "expected_score": 2,
            "expected_agent": "maria"
        },
        {
            "name": "Business Owner - Medium Intent", 
            "message": "Tengo un restaurante con 15 empleados y necesito mejorar mis ventas",
            "expected_score": 6,
            "expected_agent": "carlos"
        },
        {
            "name": "Ready to Buy - High Intent",
            "message": "Necesito agendar una cita urgente, mi presupuesto es $500/mes",
            "expected_score": 9,
            "expected_agent": "sofia"
        }
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*50}")
        print(f"Test {i+1}: {test_case['name']}")
        print(f"Message: {test_case['message']}")
        print("-" * 50)
        
        # Create unique IDs
        contact_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}"
        conversation_id = f"conv-{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}"
        thread_id = f"thread-{conversation_id}"
        
        # Create state
        state = {
            "webhook_data": {
                "contactId": contact_id,
                "conversationId": conversation_id,
                "locationId": "sHFG9Rw6BdGh6d6bfMqG",
                "body": test_case["message"]
            },
            "messages": [],
            "thread_id": thread_id,
            "contact_id": contact_id,
            "conversation_id": conversation_id,
            "location_id": "sHFG9Rw6BdGh6d6bfMqG"
        }
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            # Run workflow
            result = await workflow.ainvoke(state, config=config)
            
            # Check results
            lead_score = result.get("lead_score", 0)
            current_agent = result.get("current_agent", "unknown")
            message_sent = result.get("message_sent", False)
            
            print(f"✅ Workflow completed successfully!")
            print(f"   Lead Score: {lead_score} (expected: {test_case['expected_score']})")
            print(f"   Agent: {current_agent} (expected: {test_case['expected_agent']})")
            print(f"   Message Sent: {message_sent}")
            
            # Show the agent's response
            messages = result.get("messages", [])
            if messages:
                last_ai_msg = None
                for msg in reversed(messages):
                    if hasattr(msg, "name") and msg.name in ["maria", "carlos", "sofia"]:
                        last_ai_msg = msg
                        break
                
                if last_ai_msg:
                    print(f"\n📤 Agent Response:")
                    print(f"   {last_ai_msg.content[:200]}...")
            
            # Check if expectations met
            score_match = abs(lead_score - test_case["expected_score"]) <= 2
            agent_match = current_agent == test_case["expected_agent"] or current_agent == "responder"
            
            if score_match and agent_match:
                print(f"\n✅ Test PASSED!")
            else:
                print(f"\n⚠️  Test expectations not fully met")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Wait between tests
        if i < len(test_cases) - 1:
            await asyncio.sleep(1)
    
    print("\n" + "="*50)
    print("✅ All tests completed!")
    print(f"View traces at: https://smith.langchain.com/o/anthropic/projects/p/ghl-agent-direct-test")

async def test_conversation_continuity():
    """Test that conversation context is maintained"""
    
    from app.workflow_production_ready import workflow
    
    print("\n🧪 Testing Conversation Continuity")
    print("=" * 50)
    
    contact_id = f"continuity-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    conversation_id = f"conv-continuity-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    thread_id = f"thread-{conversation_id}"
    
    messages = [
        "Hola, me llamo Juan",
        "Tengo un restaurante llamado El Buen Sabor",
        "¿Cuál es mi nombre?"  # This tests if context is maintained
    ]
    
    config = {"configurable": {"thread_id": thread_id}}
    
    for i, message in enumerate(messages):
        print(f"\n--- Message {i+1}: {message} ---")
        
        state = {
            "webhook_data": {
                "contactId": contact_id,
                "conversationId": conversation_id,
                "locationId": "sHFG9Rw6BdGh6d6bfMqG",
                "body": message
            },
            "thread_id": thread_id
        }
        
        try:
            result = await workflow.ainvoke(state, config=config)
            
            # Get the response
            messages_list = result.get("messages", [])
            if messages_list:
                last_msg = messages_list[-1]
                if hasattr(last_msg, "content"):
                    response = last_msg.content
                    print(f"Response: {response[:200]}...")
                    
                    # Check if context is maintained
                    if i == 2:  # The "what's my name" question
                        if "Juan" in response:
                            print("✅ Context maintained! Agent remembered the name.")
                        else:
                            print("❌ Context lost! Agent didn't remember the name.")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test_workflow())
    asyncio.run(test_conversation_continuity())