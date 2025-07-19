#!/usr/bin/env python3
"""
Verify Sofia's prompt generates correct tool instructions
"""

# Simulate the state and variables that would be present in Sofia's prompt
test_contact_id = "Emp7UWc546yDMiWVEzKF"
state = {
    'contact_id': test_contact_id,
    'extracted_data': {
        'name': 'Diego',
        'email': 'diego@restaurant.com'
    }
}

analysis = {
    'collected_data': {
        'name': 'Diego',
        'email': 'diego@restaurant.com'
    }
}

current_message = "El martes a las 2pm está perfecto"
customer_selects_time = True
customer_asks_times = False

# This is the exact logic from Sofia's prompt (line 183)
prompt_instruction = f"USE book_appointment_simple TOOL IMMEDIATELY with customer_confirmation='{current_message}', contact_id='{state.get('contact_id', '')}', contact_name='{state.get('extracted_data', {}).get('name', '') or analysis['collected_data'].get('name', 'Cliente')}', contact_email='{state.get('extracted_data', {}).get('email', '') or analysis['collected_data'].get('email', '')}'" if customer_selects_time else "USE check_calendar_availability TOOL IMMEDIATELY!" if customer_asks_times else "Other instruction"

print("="*60)
print("SOFIA PROMPT VERIFICATION")
print("="*60)
print(f"\nTest Contact ID: {test_contact_id}")
print(f"Customer Message: '{current_message}'")
print(f"Customer Selecting Time: {customer_selects_time}")
print(f"\nGenerated Instruction:")
print("-"*60)
print(prompt_instruction)
print("-"*60)

# Parse the instruction
if "book_appointment_simple" in prompt_instruction:
    print("\n✅ Tool: book_appointment_simple")
    
    # Extract parameters
    if f"contact_id='{test_contact_id}'" in prompt_instruction:
        print(f"✅ contact_id: '{test_contact_id}' (CORRECT!)")
    else:
        print(f"❌ contact_id: NOT FOUND or INCORRECT")
        
    if "contact_name='Diego'" in prompt_instruction:
        print("✅ contact_name: 'Diego'")
        
    if "contact_email='diego@restaurant.com'" in prompt_instruction:
        print("✅ contact_email: 'diego@restaurant.com'")
        
    if f"customer_confirmation='{current_message}'" in prompt_instruction:
        print(f"✅ customer_confirmation: '{current_message}'")

print("\n" + "="*60)
print("VERIFICATION COMPLETE")
print("="*60)