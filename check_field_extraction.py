#!/usr/bin/env python3
"""
Check if GHL is properly extracting and saving custom fields
"""
import asyncio
from app.tools.ghl_client import GHLClient
from app.constants import FIELD_MAPPINGS

# Jaime Ortiz's contact
CONTACT_ID = "S0VUJbKWrwSpmHtKHlFH"

async def check_contact_fields():
    """Check all custom fields and tags for the contact"""
    ghl = GHLClient()
    
    print("🔍 CHECKING GHL FIELD EXTRACTION")
    print("="*60)
    print(f"Contact ID: {CONTACT_ID}")
    print()
    
    try:
        # Get contact details
        endpoint = f"/contacts/{CONTACT_ID}"
        result = await ghl._make_request("GET", endpoint)
        
        if result and result.get("contact"):
            contact = result["contact"]
            
            print("📋 CONTACT DETAILS:")
            print(f"Name: {contact.get('firstName')} {contact.get('lastName')}")
            print(f"Email: {contact.get('email', 'Not set')}")
            print(f"Phone: {contact.get('phone')}")
            print()
            
            # Check tags
            tags = contact.get("tags", [])
            print(f"🏷️ TAGS: {len(tags)} total")
            for tag in tags:
                print(f"   - {tag}")
            print()
            
            # Check custom fields
            custom_fields = contact.get("customField", {})
            print("📊 CUSTOM FIELDS:")
            
            # Map field IDs to readable names
            for field_name, field_id in FIELD_MAPPINGS.items():
                value = custom_fields.get(field_id, "NOT SET")
                status = "✅" if value != "NOT SET" and value != "" else "❌"
                print(f"   {status} {field_name}: {value}")
            
            # Check for any additional custom fields not in our mapping
            print("\n🔍 OTHER CUSTOM FIELDS:")
            for field_id, value in custom_fields.items():
                if field_id not in FIELD_MAPPINGS.values() and value:
                    print(f"   - {field_id}: {value}")
                    
            # Check notes
            print("\n📝 RECENT NOTES:")
            notes_endpoint = f"/contacts/{CONTACT_ID}/notes"
            notes_result = await ghl._make_request("GET", notes_endpoint, params={"limit": 5})
            
            if notes_result and notes_result.get("notes"):
                for i, note in enumerate(notes_result["notes"][:5], 1):
                    print(f"\n   Note {i}:")
                    print(f"   {note.get('body', '')[:150]}...")
                    print(f"   Created: {note.get('dateAdded', 'Unknown')}")
                    
        else:
            print("❌ Failed to retrieve contact")
            
    except Exception as e:
        print(f"❌ Error: {e}")

async def main():
    await check_contact_fields()

if __name__ == "__main__":
    asyncio.run(main())