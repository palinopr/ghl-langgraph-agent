#!/usr/bin/env python3
"""
Debug why appointments aren't being created in GHL
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
import pytz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tools.ghl_client import GHLClient
from app.tools.calendar_slots import generate_available_slots
from app.utils.simple_logger import get_logger

logger = get_logger("debug_appointment")

async def test_direct_appointment_creation():
    """Test creating appointment directly through GHL API"""
    
    print("="*70)
    print("🔍 DEBUGGING APPOINTMENT CREATION")
    print("="*70)
    
    # Initialize GHL client
    ghl_client = GHLClient()
    
    # Test contact ID from user
    contact_id = "z49hFQn0DxOX5sInJg60"
    
    print(f"\n📱 Contact ID: {contact_id}")
    
    # Step 1: Check if we can get contact details
    print("\n1️⃣ Testing contact fetch...")
    contact = await ghl_client.get_contact_details(contact_id)
    if contact:
        print(f"✅ Contact found: {contact.get('firstName', 'Unknown')} {contact.get('lastName', '')}")
        print(f"   Email: {contact.get('email', 'N/A')}")
        print(f"   Phone: {contact.get('phone', 'N/A')}")
    else:
        print("❌ Could not fetch contact details")
        return
    
    # Step 2: Generate appointment slot
    print("\n2️⃣ Generating appointment slot...")
    slots = generate_available_slots(num_slots=1)
    slot = slots[0]
    
    start_time = slot["startTime"]
    end_time = slot["endTime"]
    
    print(f"📅 Appointment time: {start_time.strftime('%Y-%m-%d %H:%M %Z')}")
    
    # Step 3: Try to create appointment
    print("\n3️⃣ Attempting to create appointment...")
    print(f"   Calendar ID: {ghl_client.calendar_id}")
    print(f"   Location ID: {ghl_client.location_id}")
    print(f"   Assigned User ID: {ghl_client.assigned_user_id}")
    
    try:
        result = await ghl_client.create_appointment(
            contact_id=contact_id,
            start_time=start_time,
            end_time=end_time,
            title=f"Test Appointment - {contact.get('firstName', 'Customer')}",
            timezone="America/New_York"
        )
        
        if result:
            print("\n✅ APPOINTMENT CREATED SUCCESSFULLY!")
            print(f"   Appointment ID: {result.get('id')}")
            print(f"   Status: {result.get('appointmentStatus')}")
            print(f"   Start: {result.get('startTime')}")
            print(f"   Full response: {result}")
        else:
            print("\n❌ APPOINTMENT CREATION FAILED - No result returned")
            
    except Exception as e:
        print(f"\n❌ ERROR creating appointment: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Step 4: Check calendar slots
    print("\n4️⃣ Checking calendar availability...")
    try:
        calendar_slots = await ghl_client.get_calendar_slots(
            start_date=datetime.now(pytz.timezone("America/New_York")),
            end_date=datetime.now(pytz.timezone("America/New_York")) + timedelta(days=7)
        )
        
        if calendar_slots:
            print(f"✅ Found {len(calendar_slots)} available slots")
            for i, slot in enumerate(calendar_slots[:3]):
                print(f"   Slot {i+1}: {slot.get('startTime')} - {slot.get('endTime')}")
        else:
            print("⚠️  No calendar slots returned from GHL")
            
    except Exception as e:
        print(f"❌ Error checking calendar: {str(e)}")
    
    print("\n" + "="*70)
    print("DEBUG COMPLETE")
    print("="*70)

async def test_appointment_tool():
    """Test the book_appointment_from_confirmation tool"""
    
    print("\n\n🔧 TESTING APPOINTMENT TOOL")
    print("="*70)
    
    from app.tools.agent_tools_v2 import book_appointment_from_confirmation
    from app.state.conversation_state import ConversationState
    from langchain_core.messages import HumanMessage, AIMessage
    
    # Create test state
    state = {
        "messages": [
            AIMessage(content="¡Excelente! Tengo estos horarios disponibles:\n\n📅 Mañana:\n• 10:00 AM\n• 2:00 PM\n• 4:00 PM\n\n¿Cuál prefieres?"),
            HumanMessage(content="10:00 AM")
        ],
        "contact_id": "z49hFQn0DxOX5sInJg60",
        "contact_info": {"firstName": "Test", "lastName": "User"},
        "available_slots": generate_available_slots(num_slots=3)
    }
    
    print("📝 Test scenario: Customer selected '10:00 AM'")
    
    try:
        # Call the tool
        result = await book_appointment_from_confirmation.ainvoke({
            "customer_confirmation": "10:00 AM",
            "contact_id": "z49hFQn0DxOX5sInJg60",
            "contact_name": "Test User",
            "state": state,
            "tool_call_id": "test_123"
        })
        
        print("\n📊 Tool Result:")
        if hasattr(result, 'update'):
            update = result.update
            print(f"   appointment_status: {update.get('appointment_status')}")
            print(f"   appointment_id: {update.get('appointment_id')}")
            print(f"   appointment_datetime: {update.get('appointment_datetime')}")
            
            # Check message
            if 'messages' in update:
                last_msg = update['messages'][-1]
                if hasattr(last_msg, 'content'):
                    print(f"\n   Tool message: {last_msg.content}")
        else:
            print(f"   Unexpected result type: {type(result)}")
            print(f"   Result: {result}")
            
    except Exception as e:
        print(f"\n❌ Tool error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n🚀 STARTING APPOINTMENT CREATION DEBUG\n")
    
    # Run tests
    asyncio.run(test_direct_appointment_creation())
    asyncio.run(test_appointment_tool())