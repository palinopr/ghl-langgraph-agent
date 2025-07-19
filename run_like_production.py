#!/usr/bin/env python3
"""
Run EXACTLY like production LangGraph environment
"""
import os
import sys
import asyncio
from datetime import datetime

# Add current directory to path FIRST
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv()

# Set production-like environment
os.environ['LANGSMITH_TRACING'] = 'true'
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGSMITH_PROJECT'] = os.getenv('LANGCHAIN_PROJECT', 'ghl-langgraph-agent')
os.environ['LOG_LEVEL'] = 'INFO'  # Production uses INFO, not DEBUG

async def run_like_production(contact_id: str, message: str):
    """Run exactly like production environment"""
    
    print("\n🚀 RUNNING LIKE PRODUCTION")
    print("="*60)
    print(f"Contact: {contact_id}")
    print(f"Message: '{message}'")
    
    # Import AFTER environment setup (like production)
    from app.workflow import workflow  # This is the EXACT workflow used in production
    from app.tools.ghl_client import GHLClient
    
    # 1. Load real contact data from GHL (like production does)
    print("\n📊 Loading contact data from GHL...")
    ghl_client = GHLClient()
    
    try:
        # Get contact details
        contact = await ghl_client.get_contact_details(contact_id)
        if not contact:
            print("❌ Contact not found in GHL!")
            return
            
        print(f"✅ Contact loaded: {contact.get('firstName', '')} {contact.get('lastName', '')}")
        
        # Get conversation history
        history = await ghl_client.get_messages(contact_id, limit=50)
        print(f"✅ Conversation history: {len(history)} messages")
        
        # Get custom fields
        custom_fields = contact.get('customFields', {})
        print(f"✅ Custom fields loaded:")
        for key, value in custom_fields.items():
            if value:
                print(f"   - {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error loading GHL data: {str(e)}")
        contact = {"id": contact_id}
        history = []
        custom_fields = {}
    
    # 2. Create webhook data EXACTLY like production
    webhook_data = {
        "id": contact_id,
        "contactId": contact_id,
        "message": message,
        "body": message,
        "type": "SMS",
        "locationId": os.getenv('GHL_LOCATION_ID', 'sHFG9Rw6BdGh6d6bfMqG'),
        "direction": "inbound",
        "dateAdded": datetime.now().isoformat(),
        # Production webhook includes these
        "contactName": contact.get('firstName', ''),
        "contactEmail": contact.get('email', ''),
        "contactPhone": contact.get('phone', '')
    }
    
    print("\n📥 Webhook data created")
    
    # 3. Create initial state like production
    initial_state = {
        "webhook_data": webhook_data,
        "contact_id": contact_id,
        # These are populated by receptionist in production
        "contact_info": {},
        "conversation_history": [],
        "previous_custom_fields": {},
        "messages": []
    }
    
    # 4. Run through production workflow
    print("\n🔄 Running workflow...")
    print("-"*60)
    
    try:
        # Invoke with production configuration
        config = {
            "configurable": {
                "thread_id": f"production-test-{contact_id}",
                "checkpoint_ns": ""
            },
            "metadata": {
                "source": "local_production_test",
                "contact_id": contact_id
            }
        }
        
        result = await workflow.ainvoke(initial_state, config)
        
        print("-"*60)
        print("✅ Workflow completed")
        
        # Analyze results
        print("\n📊 RESULTS:")
        print(f"  - Lead Score: {result.get('lead_score', 'N/A')}")
        
        extracted = result.get('extracted_data', {})
        print(f"  - Extracted Data:")
        for key, value in extracted.items():
            print(f"    • {key}: {value if value else 'Not set'}")
        
        # Find AI response
        messages = result.get('messages', [])
        for msg in reversed(messages):
            if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                print(f"\n🤖 AI Response: '{msg.content}'")
                break
        
        return result
        
    except Exception as e:
        print(f"\n❌ Workflow error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

async def test_full_conversation():
    """Test a full conversation flow like production"""
    
    contact_id = "XinFGydeogXoZamVtZly"
    
    messages = [
        "Hola",
        "Jaime", 
        "Restaurante",
        "No puedo responder rápido a los clientes",
        "Sí",
        "jaime@restaurant.com",
        "10:00 AM"
    ]
    
    print("\n🔄 TESTING FULL CONVERSATION FLOW")
    print("="*60)
    
    for i, message in enumerate(messages):
        print(f"\n\n{'#'*60}")
        print(f"# Message {i+1}/{len(messages)}: '{message}'")
        print("#"*60)
        
        result = await run_like_production(contact_id, message)
        
        if not result:
            print("❌ Stopping due to error")
            break
            
        # Wait between messages like a real conversation
        if i < len(messages) - 1:
            print("\n⏳ Waiting 3 seconds...")
            await asyncio.sleep(3)

def main():
    """Main entry point"""
    
    print("🏭 PRODUCTION-LIKE EXECUTION")
    print("This runs the EXACT same way as LangGraph deployment")
    
    # Check environment
    print("\n📋 Environment Check:")
    print(f"  - Python: {sys.version.split()[0]}")
    print(f"  - OPENAI_API_KEY: {'✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing'}")
    print(f"  - GHL_API_TOKEN: {'✅ Set' if os.getenv('GHL_API_TOKEN') else '❌ Missing'}")
    print(f"  - LANGSMITH_API_KEY: {'✅ Set' if os.getenv('LANGSMITH_API_KEY') or os.getenv('LANGCHAIN_API_KEY') else '❌ Missing'}")
    
    # Menu
    print("\n📱 Choose test mode:")
    print("1. Single message test")
    print("2. Full conversation test")
    print("3. Custom contact and message")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        # Single message test
        asyncio.run(run_like_production("XinFGydeogXoZamVtZly", "Restaurante"))
        
    elif choice == "2":
        # Full conversation
        asyncio.run(test_full_conversation())
        
    elif choice == "3":
        # Custom
        contact_id = input("Enter contact ID: ").strip()
        message = input("Enter message: ").strip()
        asyncio.run(run_like_production(contact_id, message))
        
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()