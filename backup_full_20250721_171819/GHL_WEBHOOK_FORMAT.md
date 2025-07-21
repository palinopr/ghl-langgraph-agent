# GHL Webhook Format Documentation

## Expected Webhook Format from GHL

When setting up your GHL workflow webhook, you need to send the data in this format:

```json
{
  "assistant_id": "agent",
  "input": {
    "messages": [
      {
        "role": "user", 
        "content": "{{message.body}}"
      }
    ],
    "contact_id": "{{contact.id}}",
    "contact_name": "{{contact.name}}",
    "contact_email": "{{contact.email}}", 
    "contact_phone": "{{contact.phone}}"
  },
  "stream_mode": "updates"
}
```

## GHL Workflow Configuration

In your GHL workflow:

1. **Trigger**: Inbound Message (WhatsApp/SMS)
2. **Action**: Custom Webhook
3. **Method**: POST
4. **URL**: `https://YOUR-DEPLOYMENT.us.langgraph.app/runs/stream`
5. **Headers**:
   - `Content-Type`: `application/json`
   - `x-api-key`: Your LangSmith API key

## Important Dynamic Fields

These must use GHL's dynamic placeholders:

- `{{contact.id}}` - The contact's unique ID (changes for each contact)
- `{{contact.name}}` - Full name of the contact
- `{{contact.email}}` - Contact's email
- `{{contact.phone}}` - Contact's phone number
- `{{message.body}}` - The actual message content

## Example with Real Values

When GHL processes the webhook, it replaces the placeholders:

```json
{
  "assistant_id": "agent",
  "input": {
    "messages": [
      {
        "role": "user",
        "content": "Hola"
      }
    ],
    "contact_id": "28bBMnRmUVNWW8pM4rxA",
    "contact_name": "Jaime Ortiz",
    "contact_email": "",
    "contact_phone": "+13054870475"
  },
  "stream_mode": "updates"
}
```

## Troubleshooting

If contact ID is not being passed correctly:

1. Check your GHL webhook configuration
2. Make sure you're using `{{contact.id}}` not a hardcoded value
3. Test the webhook to see what data GHL is actually sending
4. Check LangSmith traces for the received webhook data