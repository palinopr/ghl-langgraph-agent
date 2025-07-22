"""
Verify LangGraph agent deployment is working correctly
Tests routing to Maria, Carlos, and Sofia based on lead scores
"""
import httpx
import asyncio
import json
from datetime import datetime

# Update this with your actual deployment URL
DEPLOYMENT_URL = "https://YOUR-DEPLOYMENT-URL"  # e.g., https://abc123.us.langgraph.app


async def test_deployment():
    """Run comprehensive deployment tests"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"🚀 Testing deployment at: {DEPLOYMENT_URL}")
        print(f"🕐 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Test 1: Health check
        print("\n📋 Test 1: Health Check")
        try:
            health = await client.get(f"{DEPLOYMENT_URL}/health")
            print(f"✅ Health endpoint status: {health.status_code}")
            if health.status_code == 200:
                print(f"   Response: {health.json()}")
        except Exception as e:
            print(f"❌ Health check failed: {str(e)}")
        
        # Test 2: Simple message (should route to Maria - score 0-4)
        print("\n📋 Test 2: Maria Routing (Cold Lead - Score 0-4)")
        try:
            maria_test = await client.post(
                f"{DEPLOYMENT_URL}/webhook/message",
                json={
                    "contactId": "test-maria-001",
                    "body": "Hola, ¿qué servicios ofrecen?",
                    "conversationId": "test-conv-maria-001",
                    "type": "IncomingMessage",
                    "locationId": "test-location"
                }
            )
            print(f"✅ Maria test status: {maria_test.status_code}")
            if maria_test.status_code == 200:
                result = maria_test.json()
                print(f"   Agent routed to: {result.get('agent', 'unknown')}")
                print(f"   Lead score: {result.get('lead_score', 'N/A')}")
        except Exception as e:
            print(f"❌ Maria routing test failed: {str(e)}")
        
        # Test 3: Business message (should route to Carlos - score 5-7)
        print("\n📋 Test 3: Carlos Routing (Warm Lead - Score 5-7)")
        try:
            carlos_test = await client.post(
                f"{DEPLOYMENT_URL}/webhook/message",
                json={
                    "contactId": "test-carlos-001",
                    "body": "Tengo un restaurante y necesito ayuda con WhatsApp para mis clientes",
                    "conversationId": "test-conv-carlos-001",
                    "type": "IncomingMessage",
                    "locationId": "test-location"
                }
            )
            print(f"✅ Carlos test status: {carlos_test.status_code}")
            if carlos_test.status_code == 200:
                result = carlos_test.json()
                print(f"   Agent routed to: {result.get('agent', 'unknown')}")
                print(f"   Lead score: {result.get('lead_score', 'N/A')}")
        except Exception as e:
            print(f"❌ Carlos routing test failed: {str(e)}")
        
        # Test 4: Complete info (should route to Sofia - score 8-10)
        print("\n📋 Test 4: Sofia Routing (Hot Lead - Score 8-10)")
        try:
            sofia_test = await client.post(
                f"{DEPLOYMENT_URL}/webhook/message",
                json={
                    "contactId": "test-sofia-001",
                    "body": "Soy Juan Pérez, tengo un restaurante llamado La Cocina, mi email es juan@lacocina.com, tengo un presupuesto de $500 mensuales para marketing",
                    "conversationId": "test-conv-sofia-001",
                    "type": "IncomingMessage",
                    "locationId": "test-location"
                }
            )
            print(f"✅ Sofia test status: {sofia_test.status_code}")
            if sofia_test.status_code == 200:
                result = sofia_test.json()
                print(f"   Agent routed to: {result.get('agent', 'unknown')}")
                print(f"   Lead score: {result.get('lead_score', 'N/A')}")
        except Exception as e:
            print(f"❌ Sofia routing test failed: {str(e)}")
        
        # Test 5: Supervisor handoff (test Command routing)
        print("\n📋 Test 5: Supervisor Command Routing")
        try:
            handoff_test = await client.post(
                f"{DEPLOYMENT_URL}/webhook/message",
                json={
                    "contactId": "test-handoff-001",
                    "body": "Mi nombre es Ana, tengo una tienda de ropa",
                    "conversationId": "test-conv-handoff-001",
                    "type": "IncomingMessage",
                    "locationId": "test-location"
                }
            )
            print(f"✅ Handoff test status: {handoff_test.status_code}")
            if handoff_test.status_code == 200:
                result = handoff_test.json()
                print(f"   Initial agent: {result.get('agent', 'unknown')}")
                print(f"   Lead score: {result.get('lead_score', 'N/A')}")
                print(f"   Next agent: {result.get('next_agent', 'N/A')}")
        except Exception as e:
            print(f"❌ Handoff routing test failed: {str(e)}")
        
        print("\n" + "=" * 60)
        print("✅ Deployment verification complete!")
        print(f"🕐 Test finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n⚠️  Remember to update DEPLOYMENT_URL with your actual deployment URL!")


async def test_streaming():
    """Test streaming responses"""
    print("\n📋 Testing Streaming Responses")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{DEPLOYMENT_URL}/webhook/message",
                json={
                    "contactId": "test-stream-001",
                    "body": "Hola, necesito información",
                    "conversationId": "test-conv-stream-001",
                    "type": "IncomingMessage",
                    "locationId": "test-location"
                }
            ) as response:
                print(f"Stream status: {response.status_code}")
                async for chunk in response.aiter_text():
                    if chunk:
                        print(f"   Chunk: {chunk[:100]}...")
        except Exception as e:
            print(f"❌ Streaming test failed: {str(e)}")


if __name__ == "__main__":
    print("🚀 LangGraph Agent Deployment Verification")
    print("=" * 60)
    
    if DEPLOYMENT_URL == "https://YOUR-DEPLOYMENT-URL":
        print("❌ ERROR: Please update DEPLOYMENT_URL with your actual deployment URL!")
        print("   Example: https://abc123.us.langgraph.app")
        exit(1)
    
    # Run main tests
    asyncio.run(test_deployment())
    
    # Optional: test streaming
    # asyncio.run(test_streaming())