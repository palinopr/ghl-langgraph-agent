# Message Identification Guide

## How the System Identifies Different Message Types

### 1. Human Messages (Customer)
**Identified by:**
- `direction: "inbound"` in GHL API
- `userId` matches the contact ID
- `sender: "user"` in some formats

**Examples:**
- "Hola"
- "Mi nombre es Jaime"
- "Tengo un restaurante"

### 2. AI Agent Messages (Maria, Carlos, Sofia)
**Identified by:**
- `direction: "outbound"` in GHL API
- Contains actual conversational content
- Not in the system message list

**Examples:**
- "¡Hola! 👋 Ayudo a las empresas a automatizar WhatsApp..."
- "Mucho gusto, Jaime. ¿Qué tipo de negocio tienes?"
- "¡Perfecto! Para coordinar nuestra videollamada..."

### 3. GHL System Messages (Ignored)
**Identified by:**
- Matches specific patterns
- Usually automated notifications
- No conversational value

**System messages we filter out:**
- "Opportunity created"
- "Appointment created"
- "Appointment scheduled"
- "Tag added"
- "Tag removed"
- "Contact created"
- "Task created"
- "Note added"

## How Filtering Works

```python
# The system checks each message:
system_messages = [
    "Opportunity created",
    "Appointment created",
    # ... etc
]

# Skip if it matches any system message
is_system_message = any(
    content.strip().lower() == sys_msg.lower() or 
    content.strip().startswith(sys_msg)
    for sys_msg in system_messages
)

if is_system_message:
    # This message is ignored
    continue
```

## Message Flow Example

```
GHL Conversation:
1. [HUMAN] "Hola" ✅ Included
2. [SYSTEM] "Opportunity created" ❌ Filtered out
3. [AI] "¡Hola! 👋 Ayudo a las empresas..." ✅ Included
4. [HUMAN] "Jaime" ✅ Included
5. [SYSTEM] "Tag added" ❌ Filtered out
6. [AI] "Mucho gusto, Jaime..." ✅ Included
```

## Benefits

1. **Cleaner Conversation History**: Agents only see relevant messages
2. **Better Context**: No confusion from system notifications
3. **Improved Responses**: Agents won't respond to "Opportunity created"
4. **Customer Experience**: No weird acknowledgments of system messages

## Adding New System Messages

If GHL adds new system messages that need filtering, add them to the `system_messages` list in:
- `/app/agents/receptionist_simple.py`
- `/app/tools/conversation_loader.py`

Example:
```python
system_messages = [
    "Opportunity created",
    "Appointment created",
    "New system message here",  # Add new ones
    # ...
]
```