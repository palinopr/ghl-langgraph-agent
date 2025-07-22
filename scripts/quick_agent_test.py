#!/usr/bin/env python3
"""
Quick Agent Test
A simple script to quickly test agent routing and responses
"""

import asyncio
from app.workflow import workflow
from langchain_core.messages import HumanMessage

async def test():
    """Quick test to see agent routing"""
    # Test different messages
    test_messages = [
        "Hola",
        "Tengo un restaurante", 
        "Mi nombre es Juan, tengo una barbería y mi presupuesto es $300",
        "Quiero agendar una cita para mañana"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}: {message}")
        print('='*60)
        
        # Create state
        state = {
            "messages": [HumanMessage(content=message)],
            "contact_id": f"quick-test-{i}",
            "thread_id": f"thread-quick-{i}",
            "webhook_data": {
                "body": message,
                "contactId": f"quick-test-{i}",
                "type": "SMS"
            },
            "lead_score": 0,
            "lead_category": "cold",
            "extracted_data": {},
            "current_agent": None,
            "next_agent": None,
            "agent_task": None,
            "should_end": False,
            "needs_rerouting": False,
            "needs_escalation": False,
            "response_to_send": None,
            "conversation_stage": None,
            "messages_to_send": [],
            "appointment_status": None,
            "available_slots": None,
            "appointment_details": None,
            "contact_name": None,
            "custom_fields": {},
            "agent_handoff": None,
            "error": None
        }
        
        try:
            # Run workflow with config
            config = {"configurable": {"thread_id": f"thread-quick-{i}"}}
            result = await workflow.ainvoke(state, config)
            
            # Show results
            print(f"Score: {result.get('lead_score', 0)}")
            print(f"Agent: {result.get('current_agent', 'none')}")
            print(f"Extracted: {result.get('extracted_data', {})}")
            
            # Get response
            response = None
            for msg in reversed(result.get('messages', [])):
                if hasattr(msg, 'content') and msg.content and msg.__class__.__name__ == 'AIMessage':
                    response = msg.content
                    break
            
            print(f"Response: {response[:100]}..." if response else "No response")
            
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    print("🚀 Quick Agent Test")
    print("This will test basic routing and responses\n")
    
    asyncio.run(test())