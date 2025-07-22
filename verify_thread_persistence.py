#!/usr/bin/env python3
"""
Verify thread persistence is working after webhook handler deployment
"""
import sqlite3
import asyncio
from datetime import datetime
import httpx
import os
import json

async def test_thread_persistence():
    """Test that conversations maintain context"""
    
    # Test configuration
    WEBHOOK_URL = os.getenv("WEBHOOK_HANDLER_URL", "http://localhost:8000")
    TEST_CONTACT_ID = "test-contact-12345"
    TEST_CONVERSATION_ID = "test-conv-67890"
    
    print("🧪 Testing Thread Persistence Fix\n")
    
    # Message 1: Introduction
    message1 = {
        "contactId": TEST_CONTACT_ID,
        "conversationId": TEST_CONVERSATION_ID,
        "body": "Hola, mi nombre es Carlos y tengo un restaurante",
        "type": "Contact",
        "locationId": "test-location",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Message 2: Context check
    message2 = {
        "contactId": TEST_CONTACT_ID,
        "conversationId": TEST_CONVERSATION_ID,
        "body": "¿Recuerdas mi nombre y negocio?",
        "type": "Contact",
        "locationId": "test-location",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Send first message
        print("📤 Sending message 1: Introduction")
        print(f"   Payload: {json.dumps(message1, indent=2)}")
        try:
            response1 = await client.post(f"{WEBHOOK_URL}/webhook/message", json=message1)
            print(f"   Response: {response1.status_code}")
            print(f"   Body: {response1.json()}")
            
            if response1.status_code == 200:
                thread_id = response1.json().get("thread_id")
                print(f"   ✅ Thread ID: {thread_id}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Wait for processing
        print("\n⏳ Waiting 5 seconds for processing...")
        await asyncio.sleep(5)
        
        # Send second message
        print("\n📤 Sending message 2: Context check")
        print(f"   Payload: {json.dumps(message2, indent=2)}")
        try:
            response2 = await client.post(f"{WEBHOOK_URL}/webhook/message", json=message2)
            print(f"   Response: {response2.status_code}")
            print(f"   Body: {response2.json()}")
            
            if response2.status_code == 200:
                thread_id = response2.json().get("thread_id")
                print(f"   ✅ Thread ID: {thread_id}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # Expected thread_id
        expected_thread_id = f"conv-{TEST_CONVERSATION_ID}"
        print(f"\n✅ Expected thread_id: {expected_thread_id}")
        
        # Test health endpoint
        print("\n🏥 Checking health endpoint...")
        try:
            health_response = await client.get(f"{WEBHOOK_URL}/health")
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"   Status: {health_data.get('status')}")
                print(f"   LangGraph Client: {health_data.get('langgraph_client')}")
                print(f"   API URL: {health_data.get('api_url')}")
                print(f"   Assistant ID: {health_data.get('assistant_id')}")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
    
    # Check database
    print("\n🔍 Checking SQLite database...")
    check_database_threads()


def check_database_threads():
    """Check thread patterns in database"""
    db_path = "app/checkpoints.db"
    
    if not os.path.exists(db_path):
        print("❌ Database not found at app/checkpoints.db")
        # Try alternative path
        alt_db_path = "checkpoints.db"
        if os.path.exists(alt_db_path):
            db_path = alt_db_path
            print(f"✅ Found database at {db_path}")
        else:
            return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get thread patterns
    cursor.execute("""
        SELECT DISTINCT thread_id, COUNT(*) as checkpoints
        FROM checkpoints
        WHERE thread_id LIKE 'conv-%' OR thread_id LIKE 'contact-%'
        GROUP BY thread_id
        ORDER BY checkpoints DESC
        LIMIT 10
    """)
    
    results = cursor.fetchall()
    
    if results:
        print("\n📊 Thread Patterns Found:")
        for thread_id, count in results:
            print(f"  ✅ {thread_id}: {count} checkpoints")
    else:
        print("\n⚠️  No conv-* or contact-* threads found yet")
    
    # Check for UUIDs (bad)
    cursor.execute("""
        SELECT COUNT(DISTINCT thread_id)
        FROM checkpoints
        WHERE thread_id NOT LIKE 'conv-%' 
        AND thread_id NOT LIKE 'contact-%'
    """)
    
    uuid_count = cursor.fetchone()[0]
    if uuid_count > 0:
        print(f"\n⚠️  Warning: Found {uuid_count} UUID-based threads (should be 0)")
        
        # Show sample UUIDs
        cursor.execute("""
            SELECT DISTINCT thread_id
            FROM checkpoints
            WHERE thread_id NOT LIKE 'conv-%' 
            AND thread_id NOT LIKE 'contact-%'
            LIMIT 5
        """)
        uuid_samples = cursor.fetchall()
        print("   Sample UUID threads:")
        for (uuid_thread,) in uuid_samples:
            print(f"   - {uuid_thread}")
    else:
        print("\n🎉 Success: No UUID threads found!")
    
    # Show recent checkpoints
    cursor.execute("""
        SELECT thread_id, created_at, checkpoint
        FROM checkpoints
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    recent = cursor.fetchall()
    if recent:
        print("\n📅 Recent Checkpoints:")
        for thread_id, created_at, checkpoint in recent:
            # Parse checkpoint data safely
            try:
                checkpoint_data = json.loads(checkpoint) if isinstance(checkpoint, str) else checkpoint
                checkpoint_info = f"(type: {type(checkpoint_data).__name__})"
            except:
                checkpoint_info = "(binary data)"
            
            print(f"  - {thread_id} at {created_at} {checkpoint_info}")
    
    conn.close()


async def test_direct_invocation():
    """Test direct invocation endpoint"""
    WEBHOOK_URL = os.getenv("WEBHOOK_HANDLER_URL", "http://localhost:8000")
    TEST_THREAD_ID = "test-direct-thread-123"
    
    print("\n🎯 Testing Direct Invocation Endpoint")
    
    test_input = {
        "message": "Test direct invocation",
        "metadata": {
            "test": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{WEBHOOK_URL}/invoke/{TEST_THREAD_ID}",
                json=test_input
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Thread Persistence Verification Script")
    print("=" * 60)
    
    # Run tests
    asyncio.run(test_thread_persistence())
    
    # Optional: Test direct invocation
    if os.getenv("TEST_DIRECT", "false").lower() == "true":
        asyncio.run(test_direct_invocation())
    
    print("\n" + "=" * 60)
    print("Verification Complete")
    print("=" * 60)