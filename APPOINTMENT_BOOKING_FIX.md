# Appointment Booking Fix - Dynamic Contact ID

## Problem
When Sofia attempted to book an appointment after a customer selected a time (e.g., "El martes a las 2pm está perfecto"), she was using a hardcoded contact ID "12345" instead of the actual contact ID from the webhook data.

## Root Cause
In `app/agents/sofia_agent_v2.py`, line 183, the prompt instruction for when `customer_selects_time` is True was not including the tool parameters dynamically. It only included the customer_confirmation parameter but not the other required parameters (contact_id, contact_name, contact_email).

## Solution
Updated line 183 to use an f-string that dynamically includes all required parameters:

```python
# Before (missing parameters):
"USE book_appointment_simple TOOL IMMEDIATELY with customer_confirmation='" + current_message + "'" if customer_selects_time

# After (with all parameters):
f"USE book_appointment_simple TOOL IMMEDIATELY with customer_confirmation='{current_message}', contact_id='{state.get('contact_id', '')}', contact_name='{state.get('extracted_data', {}).get('name', '') or analysis['collected_data'].get('name', 'Cliente')}', contact_email='{state.get('extracted_data', {}).get('email', '') or analysis['collected_data'].get('email', '')}'" if customer_selects_time
```

## Verification
Created `verify_sofia_prompt.py` which confirms the prompt now generates:
```
USE book_appointment_simple TOOL IMMEDIATELY with customer_confirmation='El martes a las 2pm está perfecto', contact_id='Emp7UWc546yDMiWVEzKF', contact_name='Diego', contact_email='diego@restaurant.com'
```

## Testing
To test this fix in production-like environment:

1. Use `run_like_production.py` with option 3 (custom contact and message)
2. Enter contact ID: `Emp7UWc546yDMiWVEzKF`
3. Enter message: `El martes a las 2pm está perfecto`
4. Sofia should now book the appointment with the correct contact ID

## Expected Logs
When the appointment is created, you should see:
```
📞 GHL CREATE_APPOINTMENT API CALLED!
  - contact_id: Emp7UWc546yDMiWVEzKF  ← This should be the real contact ID, not "12345"
  - start_time: [selected time]
  - end_time: [selected time + 1 hour]
```

## Files Modified
- `app/agents/sofia_agent_v2.py` - Line 183: Added dynamic contact_id, contact_name, and contact_email parameters

## Status
✅ Fixed - Sofia now uses the actual contact ID from the state when booking appointments