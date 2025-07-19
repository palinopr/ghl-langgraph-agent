#!/usr/bin/env python3
"""
Fix for receptionist to properly load and format conversation history
"""

# The current receptionist code that needs to be fixed:
CURRENT_CODE = '''
# 3. Load conversation history (for context only, not for agent messages)
logger.info("Loading conversation history for context...")
messages = []
try:
    conversations = await ghl_client.get_conversations(contact_id)
    if conversations and isinstance(conversations, list) and len(conversations) > 0:
        conv_id = conversations[0].get('id')
        conv_messages = await ghl_client.get_conversation_messages(conv_id)
        if conv_messages and isinstance(conv_messages, list):
            messages = conv_messages[-50:] if len(conv_messages) > 50 else conv_messages
            logger.info(f"Loaded {len(messages)} historical messages for context")
except Exception as e:
    logger.warning(f"Could not load conversation history: {e}")

# Return updated state
return {
    "messages": state.get("messages", []) + [summary_msg],
    "contact_info": contact,
    "previous_custom_fields": custom_fields,
    "conversation_history": messages,  # <- This is just raw data, not formatted!
    "data_loaded": True,
    "receptionist_complete": True
}
'''

# The FIXED code should be:
FIXED_CODE = '''
# 3. Load conversation history and convert to LangChain messages
logger.info("Loading conversation history...")
conversation_messages = []
raw_messages = []
try:
    conversations = await ghl_client.get_conversations(contact_id)
    if conversations and isinstance(conversations, list) and len(conversations) > 0:
        conv_id = conversations[0].get('id')
        conv_messages = await ghl_client.get_conversation_messages(conv_id)
        if conv_messages and isinstance(conv_messages, list):
            raw_messages = conv_messages[-50:] if len(conv_messages) > 50 else conv_messages
            logger.info(f"Loaded {len(raw_messages)} historical messages")
            
            # Convert GHL messages to LangChain format
            for msg in raw_messages:
                content = msg.get('body', '') or msg.get('message', '')
                direction = msg.get('direction', '').lower()
                
                # Skip empty messages
                if not content:
                    continue
                
                # Create appropriate message type
                if direction == 'inbound' or msg.get('userId') == contact_id:
                    # Message from customer
                    conversation_messages.append(HumanMessage(
                        content=content,
                        additional_kwargs={
                            "timestamp": msg.get('dateAdded', ''),
                            "message_id": msg.get('id', ''),
                            "source": "ghl_history"
                        }
                    ))
                else:
                    # Message from agent/system
                    conversation_messages.append(AIMessage(
                        content=content,
                        additional_kwargs={
                            "timestamp": msg.get('dateAdded', ''),
                            "message_id": msg.get('id', ''),
                            "source": "ghl_history"
                        }
                    ))
            
            logger.info(f"Converted {len(conversation_messages)} messages to LangChain format")
            
except Exception as e:
    logger.warning(f"Could not load conversation history: {e}")

# 4. Create summary message
summary = f"""
DATA LOADED SUCCESSFULLY:
- Contact: {contact.get('firstName', '')} {contact.get('lastName', '')}
- Email: {contact.get('email', 'none')}
- Phone: {contact.get('phone', '')}
- Previous Score: {custom_fields.get('score', '0')}/10
- Business: {custom_fields.get('business_type', 'not specified')}
- Budget: {custom_fields.get('budget', 'not confirmed')}
- Messages in history: {len(conversation_messages)}
"""

# Add summary as AI message
summary_msg = AIMessage(
    content=summary,
    name="receptionist"
)

# Combine all messages: history + current + summary
all_messages = conversation_messages + state.get("messages", []) + [summary_msg]

# Return updated state with properly formatted messages
return {
    "messages": all_messages,  # <- Now includes full conversation history!
    "contact_info": contact,
    "previous_custom_fields": custom_fields,
    "conversation_history": raw_messages,  # Keep raw data for reference
    "formatted_history_count": len(conversation_messages),
    "data_loaded": True,
    "receptionist_complete": True
}
'''

print("RECEPTIONIST FIX NEEDED")
print("="*80)
print("\nThe receptionist is loading conversation history but not formatting it properly.")
print("\nKey issues:")
print("1. Raw GHL messages are stored in 'conversation_history' field")
print("2. These messages are NOT converted to LangChain HumanMessage/AIMessage format")
print("3. The messages are NOT added to the 'messages' array that agents actually read")
print("\nResult: Agents see empty conversation history and repeat questions!")
print("\nThe fix requires:")
print("1. Import HumanMessage from langchain_core.messages")
print("2. Convert GHL messages to proper format based on direction")
print("3. Prepend conversation history to the messages array")
print("4. Ensure agents see the full conversation context")