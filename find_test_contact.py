#!/usr/bin/env python3
"""
Find a valid contact in GHL for testing
"""
import asyncio
import sys
sys.path.append('.')

from app.tools.ghl_client import GHLClient
from app.config import get_settings

async def find_contacts():
    """Find available contacts in GHL"""
    settings = get_settings()
    client = GHLClient()
    
    print("🔍 Searching for contacts in GHL...")
    print(f"Location ID: {settings.ghl_location_id}")
    
    try:
        # Search for contacts
        contacts = await client.search_contacts(
            location_id=settings.ghl_location_id,
            limit=10
        )
        
        if not contacts:
            print("❌ No contacts found")
            return
        
        print(f"\n✅ Found {len(contacts)} contacts:\n")
        
        for i, contact in enumerate(contacts, 1):
            name = contact.get("contactName", contact.get("firstName", "Unknown"))
            phone = contact.get("phone", "N/A")
            email = contact.get("email", "N/A")
            contact_id = contact.get("id")
            
            print(f"{i}. {name}")
            print(f"   ID: {contact_id}")
            print(f"   Phone: {phone}")
            print(f"   Email: {email}")
            print()
        
        # Show first contact ID for easy copying
        if contacts:
            first_id = contacts[0].get("id")
            print(f"\n📋 Test command with first contact:")
            print(f'python test_with_real_ghl.py "{first_id}" "Hola, tengo un negocio"')
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(find_contacts())