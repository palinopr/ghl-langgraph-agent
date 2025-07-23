#!/usr/bin/env python3
"""
Diagnostic tool to identify why messages aren't being sent
"""
import asyncio
from app.workflow import run_workflow
from app.utils.simple_logger import get_logger
import json

logger = get_logger("diagnose")

# Test cases that should trigger responses
TEST_CASES = [
    {
        "name": "Simple greeting",
        "body": "Hola",
        "expected": "Should respond with greeting"
    },
    {
        "name": "Business inquiry",
        "body": "Necesito información sobre sus servicios de marketing",
        "expected": "Should respond with service information"
    },
    {
        "name": "Direct question",
        "body": "¿Cuánto cuesta?",
        "expected": "Should respond with pricing inquiry"
    }
]


async def diagnose_response_issue(webhook_data: Dict[str, Any]):
    """Run workflow and diagnose why no response is sent"""
    
    print(f"\n🔍 Diagnosing: {webhook_data.get('body', 'NO MESSAGE')}")
    print("=" * 60)
    
    try:
        # Run the workflow
        result = await run_workflow(webhook_data)
        
        # Check results
        print("\n📊 Workflow Result:")
        print(f"Success: {result.get('success')}")
        print(f"Message Sent: {result.get('message_sent')}")
        print(f"Agent: {result.get('agent')}")
        print(f"Lead Score: {result.get('lead_score')}")
        
        # Check response
        response = result.get('response', '')
        if response:
            print(f"\n✅ Response Generated:")
            print(f"'{response[:200]}...'" if len(response) > 200 else f"'{response}'")
        else:
            print("\n❌ NO RESPONSE GENERATED!")
            
        # Diagnose issues
        if not result.get('message_sent'):
            print("\n🚨 DIAGNOSIS - Message NOT sent:")
            print("Possible reasons:")
            print("1. Responder didn't find an AI message to send")
            print("2. Agent didn't generate a response")
            print("3. Message was filtered out as duplicate")
            print("4. Error in responder node")
            
            # Check which agent handled it
            agent = result.get('agent', 'unknown')
            print(f"\n🤖 Last Agent: {agent}")
            if agent in ['maria', 'carlos', 'sofia']:
                print(f"→ {agent} should have generated a response")
                print("→ Check if agent's prompt is working correctly")
                print("→ Check if agent's tools are being called")
            
        return result
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


async def run_diagnostics():
    """Run diagnostic tests"""
    
    print("🏥 Message Response Diagnostic Tool")
    print("=" * 60)
    
    # Base webhook template
    base_webhook = {
        "id": "test-123",
        "contactId": "test-contact",
        "conversationId": "test-conv",
        "locationId": "test-location",
        "type": "SMS",
        "contact": {
            "id": "test-contact",
            "firstName": "Test",
            "lastName": "User",
            "email": "test@example.com",
            "phone": "+1234567890"
        }
    }
    
    # Run each test case
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n\n🧪 Test {i}: {test_case['name']}")
        print("-" * 40)
        
        # Create webhook data
        webhook_data = {**base_webhook, "body": test_case["body"]}
        
        # Run diagnosis
        result = await diagnose_response_issue(webhook_data)
        
        # Check expectation
        if result and result.get('message_sent'):
            print(f"\n✅ PASSED: {test_case['expected']}")
        else:
            print(f"\n❌ FAILED: {test_case['expected']}")
            print("→ No message was sent!")
    
    print("\n\n📋 Common Issues & Solutions:")
    print("-" * 40)
    print("1. Agent not generating response:")
    print("   → Check agent prompts include clear instructions to respond")
    print("   → Verify create_react_agent is working properly")
    print("   → Check for tool call errors")
    print("\n2. Responder not finding message:")
    print("   → Check message filtering in responder_agent.py")
    print("   → Verify AIMessage is being added to state")
    print("   → Check for name attribute on messages")
    print("\n3. Message marked as duplicate:")
    print("   → Check MessageManager deduplication logic")
    print("   → Verify state message handling")
    print("\n4. Routing issues:")
    print("   → Check smart_router scoring and routing logic")
    print("   → Verify agent boundaries in base_agent.py")


def main():
    """Run the diagnostic tool"""
    import os
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set!")
        return
        
    print("🚀 Starting Message Response Diagnostics")
    asyncio.run(run_diagnostics())


if __name__ == "__main__":
    main()