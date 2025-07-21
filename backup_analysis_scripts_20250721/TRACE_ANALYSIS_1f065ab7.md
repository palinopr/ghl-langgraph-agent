# Trace Analysis Guide for 1f065ab7-af0c-6b8f-b629-457ad5e5145c

## How to Access the Trace

Visit: https://smith.langchain.com/o/4c95e8d5-51d9-5c98-9f15-da9d8fd05782/projects/p/8f9e7a4f-5aad-4919-bd03-88f695c7c8cf/r/1f065ab7-af0c-6b8f-b629-457ad5e5145c

## What to Look For

### 1. Input Analysis
- **Contact ID**: Check if it's a real GHL contact or test ID
- **Message Content**: What did the customer say?
- **Webhook Data**: Is this from GHL webhook or direct API?
- **Existing State**: What custom fields were loaded?

### 2. Workflow Execution
Check the node execution order:
1. **Receptionist** - Did it load contact data correctly?
2. **Supervisor Brain** - What score was calculated?
3. **Agent Selection** - Which agent (Maria/Carlos/Sofia) was chosen?
4. **Agent Response** - What did the agent decide?
5. **Responder** - Was the message sent successfully?

### 3. Common Issues to Check

#### State Persistence Issues
- Is the lead score maintaining between messages?
- Are custom fields being updated in GHL?
- Is conversation history loaded correctly?

#### Routing Issues
- Score 1-4 → Maria
- Score 5-7 → Carlos  
- Score 8+ → Sofia
- Is the routing correct based on score?

#### Calendar/Appointment Issues
- If customer asked for "horarios disponibles" → Did Sofia use calendar tool?
- If customer selected time (e.g., "martes 2pm") → Did booking tool get called?
- Check for the log entries:
  - "📅 CHECK_CALENDAR_SIMPLE called"
  - "📅 BOOK_APPOINTMENT_SIMPLE called"

#### Response Issues
- Did the responder send a message?
- Any GHL API errors (400, 404)?
- Message formatting correct?

### 4. Error Patterns

#### "Contact not found"
```json
{"error":"Contact with id XXX not found"}
```
This means the contact ID doesn't exist in GHL.

#### "Recursion limit"
```
GraphRecursionError: Recursion limit of 25 reached
```
Agent is stuck in a loop, likely with tool usage.

#### Missing State
```
KeyError: 'contact_id'
```
State is not being passed correctly between nodes.

### 5. Expected Flow for Appointment Booking

1. Customer: "Quiero agendar una cita"
2. Receptionist: Loads contact data
3. Supervisor: Calculates score (should be 8+ for appointment intent)
4. Routes to Sofia
5. Sofia: Uses `check_calendar_simple` tool
6. Sofia: Returns available times
7. Customer: "Martes 2pm está bien"
8. Sofia: Uses `book_appointment_simple` tool
9. Sofia: Confirms appointment
10. Responder: Sends confirmation

### 6. Debug Information to Extract

From the trace, note:
- Total execution time
- Number of LLM calls
- Token usage
- Any retries or errors
- Final output/response

### 7. Quick Fixes Based on Common Issues

#### If Sofia isn't using tools:
- Check if prompt includes "USE_CALENDAR_TOOL" instruction
- Verify tools are in the agent's tool list
- Check for conversation enforcer interference

#### If score isn't persisting:
- Check supervisor_brain_simple.py is reading previous state
- Verify GHL custom field updates are working
- Check field mappings are correct

#### If wrong agent is selected:
- Verify score calculation in supervisor
- Check routing logic in workflow_linear.py
- Ensure score is being passed correctly

## Next Steps

1. Copy the full trace JSON from LangSmith
2. Look for the specific error or unexpected behavior
3. Check which node failed or behaved incorrectly
4. Compare with expected flow above
5. Apply relevant fix from the solutions provided

## Contact for Help

If you need help analyzing the trace, provide:
1. The input message
2. Expected behavior
3. Actual behavior
4. Any error messages
5. Which node failed