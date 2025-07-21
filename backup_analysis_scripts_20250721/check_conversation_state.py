#!/usr/bin/env python3
"""
Check the current conversation state for contact
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tools.ghl_client import GHLClient
from app.constants import FIELD_MAPPINGS

CONTACT_ID = "z49hFQn0DxOX5sInJg60"

async def check_contact_state():
    """Check current state of contact in GHL"""
    
    print(f"🔍 CHECKING CONTACT STATE: {CONTACT_ID}")
    print("="*60)
    
    ghl = GHLClient()
    
    # Get contact info
    endpoint = f"/contacts/{CONTACT_ID}"
    contact_response = await ghl._make_request("GET", endpoint)
    
    if contact_response and contact_response.get("contact"):
        contact = contact_response["contact"]
        
        print(f"📋 CONTACT INFO:")
        print(f"  Name: {contact.get('firstName', '')} {contact.get('lastName', '')}")
        print(f"  Phone: {contact.get('phone', 'Not set')}")
        print(f"  Email: {contact.get('email', 'Not set')}")
        print(f"  Tags: {', '.join(contact.get('tags', [])) or 'None'}")
        
        # Check custom fields
        print(f"\n📊 CUSTOM FIELDS:")
        custom_fields = contact.get("customFields", [])
        field_values = {}
        for field in custom_fields:
            field_values[field.get("id")] = field.get("value")
        
        for field_name, field_id in FIELD_MAPPINGS.items():
            value = field_values.get(field_id, "NOT SET")
            print(f"  {field_name}: {value}")
            
            # Highlight issues
            if field_name == "score" and value != "NOT SET":
                try:
                    score_int = int(value)
                    if score_int > 10:
                        print(f"    ⚠️  Score should be 1-10, not {score_int}!")
                except:
                    pass
            elif field_name == "budget" and value == "10/month":
                print(f"    ⚠️  Budget was extracted from time '10:00 AM'!")
    
    # Get conversation history
    print(f"\n💬 RECENT MESSAGES:")
    search_response = await ghl._make_request("GET", "/conversations/search", params={
        "contactId": CONTACT_ID,
        "limit": 1
    })
    
    if search_response and search_response.get("conversations"):
        conversations = search_response["conversations"]
        if conversations:
            conv_id = conversations[0]["id"]
            
            # Get messages
            messages_response = await ghl._make_request("GET", f"/conversations/{conv_id}/messages", params={
                "limit": 10
            })
            
            if messages_response and messages_response.get("messages"):
                messages = messages_response["messages"]
                for i, msg in enumerate(messages[:5]):  # Show last 5
                    direction = "👤" if msg.get("direction") == "inbound" else "🤖"
                    content = msg.get("body", "")[:100] + "..." if len(msg.get("body", "")) > 100 else msg.get("body", "")
                    print(f"  {direction} {content}")

async def reset_contact_fields():
    """Reset the contact fields to clean state"""
    
    print(f"\n\n🔧 RESETTING CONTACT FIELDS")
    print("="*60)
    
    ghl = GHLClient()
    
    # Reset custom fields
    custom_fields = [
        {"id": FIELD_MAPPINGS["score"], "value": "1"},  # Reset to 1
        {"id": FIELD_MAPPINGS["budget"], "value": ""},  # Clear budget
    ]
    
    updates = {"customFields": custom_fields}
    
    response = await ghl.update_contact(CONTACT_ID, updates)
    
    if response:
        print("✅ Reset complete!")
        print("  - Score reset to 1")
        print("  - Budget cleared")
    else:
        print("❌ Reset failed")

if __name__ == "__main__":
    asyncio.run(check_contact_state())
    
    # Ask if user wants to reset
    reset = input("\n❓ Do you want to reset the contact fields? (y/n): ")
    if reset.lower() == 'y':
        asyncio.run(reset_contact_fields())