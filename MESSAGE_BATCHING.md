# Message Batching for Human-Like Responses

## Overview
The system now waits for customers to finish typing before responding, preventing bot-like behavior where each message gets an individual response.

## How It Works

### Example Scenario
```
4:00 PM - Customer: "Hi"
4:00:01 PM - Customer: "My name is Jaime"
4:00:02 PM - Customer: "I have a restaurant"
```

**Without Batching (Bot-like):**
- Response 1: "Hello! How can I help you?"
- Response 2: "Nice to meet you Jaime!"
- Response 3: "Great! Tell me more about your restaurant."

**With Batching (Human-like):**
- Waits 15 seconds after "Hi"
- Receives all 3 messages
- Merges them: "Hi, my name is Jaime. I have a restaurant"
- Single Response: "Hello Jaime! Nice to meet you. I'd love to learn more about your restaurant and how we can help with your marketing needs."

## Configuration

### Default Settings
- **Batch Window**: 15 seconds (waits for more messages)
- **Max Batch Size**: 10 messages (processes immediately if reached)
- **Redis**: Optional (falls back to in-memory if not available)

### Smart Message Merging
The system intelligently merges messages:
- "Hi" + "My name is John" → "Hi, my name is John"
- "I have a restaurant" + "Italian food" → "I have a restaurant, Italian food"
- "300" + "per month" → "300 per month"
- "Mi nombre es" + "Jaime" → "Mi nombre es Jaime"

## Implementation Details

### 1. Message Reception
When a webhook arrives, instead of immediate processing:
```python
batch_result = await process_with_batching(
    contact_id=message_data.get("id"),
    message=message_data,
    process_callback=process_batched_message
)
```

### 2. Batching Logic
- First message starts a 15-second timer
- Additional messages are added to the batch
- Processing triggers when:
  - Timer expires (15 seconds)
  - Max messages reached (10)
  - No more messages arrive

### 3. Message Processing
- All batched messages are merged into one
- Intelligence analyzer sees the complete thought
- Single, coherent response is generated

## Benefits

1. **More Human-Like**: Responds to complete thoughts, not fragments
2. **Better Context**: AI sees the full message intent
3. **Reduced Spam**: One thoughtful response instead of many
4. **Better Scoring**: Complete information for lead analysis
5. **Cost Efficient**: Fewer API calls and responses

## Edge Cases Handled

### Continuation Detection
The system recognizes when messages continue previous ones:
- "Mi nombre es" → waits for name
- "$300" → waits for "al mes" or context
- "Tengo un" → waits for what they have

### Quick Messages
If customer sends many messages quickly:
- All captured in one batch
- Properly ordered and merged
- Analyzed as complete context

### Long Pauses
If customer pauses mid-conversation:
- 15-second timer ensures reasonable response time
- New message after response starts new batch

## Redis Integration (Optional)

### With Redis
- Distributed batching across multiple servers
- Survives server restarts
- Handles high volume

### Without Redis
- In-memory batching (single server)
- Works perfectly for most deployments
- No additional infrastructure needed

## Configuration Options

### Environment Variables
```bash
# Optional Redis for distributed batching
REDIS_URL=redis://localhost:6379/0
```

### Customization
In `message_batcher.py`:
```python
MessageBatcher(
    batch_window_seconds=15,  # Adjust wait time
    max_batch_size=10,       # Adjust max messages
)
```

## Monitoring

With LangSmith tracing, you can see:
- Batch formation (how messages were grouped)
- Merge quality (how well messages combined)
- Response timing (customer experience)
- Cost savings (fewer API calls)

## Result

Customers experience natural, thoughtful responses that consider their complete message, making the interaction feel more like chatting with a human consultant rather than a bot.