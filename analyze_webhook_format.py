#!/usr/bin/env python3
"""
Analyze the webhook format to understand contact ID structure
"""

# Based on the screenshot and trace, let's understand the webhook format
print("=== GHL Webhook Format Analysis ===")
print()

# From your screenshot, the contact details show:
print("1. Contact Information from Screenshot:")
print("   - Name: Jaime Ortiz")
print("   - Phone: (305) 487-0475")
print("   - Custom Field IDs visible:")
print("     - goal: r7jFiJBYHiEllsGn7jZC")
print("     - budget: 4Qe8P25JRLW0IcZc5iOs")
print("     - last_score: 6")
print("     - name_confirmed: true")
print()

print("2. Webhook Format (from webhook_handler.py):")
print("   Expected format from GHL through LangGraph:")
print("   {")
print('       "assistant_id": "agent",')
print('       "input": {')
print('           "messages": [{"role": "user", "content": "message"}],')
print('           "contact_id": "{{contact.id}}",  # <-- This is what we need')
print('           "contact_name": "{{contact.name}}",')
print('           "contact_email": "{{contact.email}}",')
print('           "contact_phone": "{{contact.phone}}"')
print("       }")
print("   }")
print()

print("3. Contact ID Format:")
print("   - The contact_id in the webhook should be the actual GHL contact ID")
print("   - NOT the custom field ID like 'TjB0I5iNfVwx3zyxZ9sW'")
print("   - GHL contact IDs are typically 24-char hex strings like '66a17f6b2ca1b4f91e90157f'")
print()

print("4. To Find Your Contact ID:")
print("   a) In GHL, go to the contact page for Jaime Ortiz")
print("   b) Look at the URL - it should contain the contact ID")
print("   c) Or check the webhook logs in GHL to see what contact_id is sent")
print()

print("5. Testing with Real Data:")
print("   Once you have the real contact ID, update the test to use it:")
print('   contact_id = "YOUR_ACTUAL_CONTACT_ID_HERE"')
print()

# Let's also check what the trace shows
print("6. From Trace Analysis:")
print("   - The trace ID 1f0649dd-8dac-6802-9b24-a91f9943836c shows:")
print("   - Receptionist is trying to load conversation history")
print("   - But the contact_id being used might be incorrect")
print("   - We need the actual GHL contact ID from the webhook")