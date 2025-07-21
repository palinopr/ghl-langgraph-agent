# Streaming and Real-Time Improvements for Human-like Conversations

## Overview
Based on LangGraph best practices for streaming and real-time interactions, here are additional improvements to make conversations even more natural and engaging.

## 🚀 Streaming Capabilities from LangGraph

### 1. Token-by-Token Streaming
```python
# Enable real-time token streaming
async for token, metadata in agent.astream(
    {"messages": [{"role": "user", "content": "Hola, necesito ayuda"}]},
    stream_mode="messages"
):
    # Send each token as it's generated
    await send_to_ghl(contact_id, token)
```

### 2. Custom Stream Writers for Typing Indicators
```python
from langgraph.config import get_stream_writer

async def agent_with_typing(state):
    """Agent that streams typing indicators"""
    writer = get_stream_writer()
    
    # Start typing indicator
    writer({"typing": True, "agent": state.get("current_agent")})
    
    # Generate response
    response = await generate_response(state)
    
    # Stop typing and send message
    writer({"typing": False})
    writer({"message": response})
    
    return {"messages": [response]}
```

### 3. Multi-Message Streaming
```python
# Stream multiple related messages naturally
messages = [
    "Ah, un restaurante...",
    "Conozco bien ese sector 😊",
    "Dime, ¿qué es lo más difícil de manejar en WhatsApp?"
]

for msg in messages:
    writer({"typing": True})
    await asyncio.sleep(calculate_typing_duration(msg))
    writer({"typing": False})
    writer({"message": msg})
    await asyncio.sleep(0.5)  # Natural pause between messages
```

## 📋 Implementation Plan

### Phase 1: Streaming Infrastructure
```python
# app/utils/streaming_responder.py
class StreamingResponder:
    """Handles streaming responses with typing indicators"""
    
    async def stream_with_typing(
        self,
        contact_id: str,
        agent_name: str,
        message_generator: AsyncGenerator[str, None]
    ):
        # Show typing indicator
        await self.send_typing_status(contact_id, True)
        
        # Stream tokens
        buffer = ""
        async for token in message_generator:
            buffer += token
            
            # Send complete words/phrases
            if token in [" ", ".", ",", "!", "?"]:
                await self.send_partial(contact_id, buffer)
                buffer = ""
        
        # Send remaining buffer
        if buffer:
            await self.send_partial(contact_id, buffer)
        
        # Stop typing
        await self.send_typing_status(contact_id, False)
```

### Phase 2: Natural Message Patterns
```python
# app/utils/message_patterns.py
class NaturalMessagePatterns:
    """Patterns for human-like message sequences"""
    
    @staticmethod
    async def thinking_pattern(writer, agent_name: str):
        """Shows agent thinking before complex responses"""
        # Quick typing indicator
        writer({"typing": True, "duration": 1.5})
        await asyncio.sleep(1.5)
        
        # Thinking message
        thinking = random.choice([
            "Déjame ver...",
            "A ver...",
            "Mmm, déjame pensar..."
        ])
        writer({"message": thinking})
        
        # Longer typing for main response
        writer({"typing": True, "duration": 3.0})
    
    @staticmethod
    async def excitement_pattern(writer, message: str):
        """Shows excitement with quick messages"""
        # Fast typing
        writer({"typing": True, "duration": 0.8})
        await asyncio.sleep(0.8)
        
        # Excited opener
        opener = random.choice([
            "¡Qué bien!",
            "¡Excelente!",
            "¡Me encanta!"
        ])
        writer({"message": opener})
        
        # Quick follow-up
        await asyncio.sleep(0.3)
        writer({"typing": True, "duration": 1.5})
        await asyncio.sleep(1.5)
        writer({"message": message})
```

### Phase 3: Enhanced Pre-Model Hooks with Streaming
```python
def streaming_maria_hook(state: Dict[str, Any]) -> Dict[str, Any]:
    """Enhanced hook that prepares streaming responses"""
    result = maria_context_hook(state)
    
    # Add streaming instructions
    streaming_guidance = """
🎥 STREAMING BEHAVIOR:
1. For short responses (<50 chars): Send immediately
2. For medium responses (50-150 chars): Show typing 2-3 seconds
3. For long responses (>150 chars): 
   - Show typing indicator
   - Send in 2-3 natural chunks
   - Pause 0.5s between chunks

🎬 MULTI-MESSAGE PATTERNS:
- Acknowledgment → Pause → Main response
- Thinking indicator → Insight → Question
- Excitement → Context → Call to action

Example flow:
[typing 1.5s] "Ya veo..."
[pause 0.5s]
[typing 3s] "Para un restaurante como el tuyo, el mayor reto suele ser responder rápido durante las horas pico."
[pause 0.3s]
[typing 2s] "¿Es ese tu caso también?"
"""
    
    if result["llm_input_messages"]:
        result["llm_input_messages"][0].content += "\n\n" + streaming_guidance
    
    return result
```

## 🎯 Real-Time Conversation Examples

### Before (All at Once):
```
User: Tengo un restaurante y pierdo muchos clientes
Bot: [instant] Entiendo perfectamente tu situación. Para restaurantes, la respuesta rápida es crucial. Mis soluciones empiezan en $300/mes y pueden automatizar todas tus respuestas. ¿Te funciona ese presupuesto?
```

### After (Natural Streaming):
```
User: Tengo un restaurante y pierdo muchos clientes
Bot: [typing... 1.5s]
Bot: Uf, lo entiendo perfectamente...
Bot: [typing... 3s]
Bot: Los restaurantes pierden hasta 30% de reservas por no responder rápido 😔
Bot: [typing... 2.5s]
Bot: Pero tengo buenas noticias - puedo automatizar todas tus respuestas por $300/mes
Bot: [typing... 1s]
Bot: ¿Te funciona ese presupuesto?
```

## 🔧 Technical Integration with LangGraph

### 1. Update Agent Creation
```python
def create_streaming_agent(agent_name: str):
    """Create agent with streaming capabilities"""
    
    # Get base agent
    if agent_name == "maria":
        base_agent = create_maria_agent()
        hook = streaming_maria_hook
    # ... other agents
    
    # Wrap with streaming
    return create_react_agent(
        model=model,
        tools=tools,
        state_schema=State,
        prompt=prompt,
        pre_model_hook=hook,
        # Enable streaming
        stream=True,
        stream_options={
            "include_partial": True,
            "chunk_size": 10  # Tokens per chunk
        }
    )
```

### 2. Update Responder for Streaming
```python
async def streaming_responder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Responder that handles streaming messages"""
    
    messages = state.get("messages", [])
    contact_id = state.get("contact_id")
    
    for msg in messages:
        if should_send_message(msg):
            # Get agent personality
            agent = detect_agent_from_message(msg)
            
            # Stream with appropriate style
            async with StreamingResponder() as responder:
                await responder.stream_with_personality(
                    contact_id=contact_id,
                    agent_name=agent,
                    message=msg.content,
                    style=get_agent_style(agent)
                )
    
    return {"response_sent": True}
```

### 3. GHL Webhook Integration
```python
# app/api/webhook_streaming.py
async def handle_streaming_webhook(webhook_data: Dict):
    """Process webhook with streaming responses"""
    
    # Create streaming config
    config = {
        "configurable": {
            "thread_id": webhook_data["contactId"],
            "stream_mode": ["messages", "custom"],
            "stream_handler": GHLStreamHandler(webhook_data["contactId"])
        }
    }
    
    # Stream workflow execution
    async for chunk in workflow.astream(
        {"messages": [webhook_data["message"]]},
        config,
        stream_mode=["messages", "custom"]
    ):
        # Handle different chunk types
        if "typing" in chunk:
            await handle_typing_indicator(chunk)
        elif "message" in chunk:
            await handle_message_chunk(chunk)
        elif "custom" in chunk:
            await handle_custom_event(chunk)
```

## 📊 Benefits of Streaming

### User Experience
- **Immediate Feedback**: Users see typing indicators instantly
- **Natural Pacing**: Messages arrive at human-like speeds
- **Engagement**: Multi-message patterns keep attention
- **Less Robotic**: Thinking pauses and corrections feel human

### Technical Benefits
- **Lower Latency**: First token arrives faster
- **Better Error Handling**: Can stop mid-stream if needed
- **Memory Efficient**: Don't buffer entire responses
- **Real-time Analytics**: Track engagement as it happens

## 🎨 Personality-Specific Streaming Styles

### Maria (Warm & Thoughtful)
```python
maria_streaming_style = {
    "typing_speed": 2.5,  # Chars per second
    "thinking_probability": 0.4,
    "multi_message_probability": 0.3,
    "emoji_in_stream": True,
    "patterns": ["acknowledge_think_respond", "empathy_solution"]
}
```

### Carlos (Professional & Engaging)
```python
carlos_streaming_style = {
    "typing_speed": 3.0,
    "thinking_probability": 0.5,
    "multi_message_probability": 0.4,
    "emoji_in_stream": False,
    "patterns": ["insight_question", "value_then_ask"]
}
```

### Sofia (Efficient & Exciting)
```python
sofia_streaming_style = {
    "typing_speed": 4.0,
    "thinking_probability": 0.2,
    "multi_message_probability": 0.5,
    "emoji_in_stream": True,
    "patterns": ["excitement_urgency", "benefit_action"]
}
```

## 🚦 Implementation Priority

### High Priority (Do First)
1. Basic typing indicators via GHL API
2. Message chunking for long responses
3. Natural pauses between messages
4. Personality-based timing

### Medium Priority
1. Token streaming integration
2. Thinking patterns
3. Multi-message sequences
4. Real-time analytics

### Future Enhancements
1. Adaptive timing based on user response speed
2. Emotion detection and response adjustment
3. A/B testing streaming patterns
4. Voice message support with realistic delays

## 📝 Testing Streaming Features

```python
# test_streaming_conversation.py
async def test_natural_streaming():
    """Test streaming conversation flow"""
    
    # Simulate user message
    user_msg = "Hola, tengo un restaurante"
    
    # Track timing
    timings = []
    
    async for event in agent.astream(
        {"messages": [{"role": "user", "content": user_msg}]},
        stream_mode="custom"
    ):
        timings.append({
            "timestamp": time.time(),
            "event": event
        })
    
    # Verify natural timing
    assert_typing_indicators_shown(timings)
    assert_natural_pauses_between_messages(timings)
    assert_total_time_realistic(timings)
```

## 🎯 Success Metrics

### Conversation Metrics
- **Response Time**: Time to first token (target: <1s)
- **Typing Realism**: Duration matches message length
- **Engagement Rate**: Users wait for full response
- **Completion Rate**: Conversations reach booking

### Technical Metrics
- **Stream Latency**: Time between tokens
- **Error Rate**: Failed streams or timeouts
- **Throughput**: Concurrent conversations supported
- **Resource Usage**: Memory/CPU per stream

## 🔄 Migration Path

1. **Phase 1**: Add typing indicators (no streaming yet)
2. **Phase 2**: Stream long messages in chunks
3. **Phase 3**: Full token streaming with LangGraph
4. **Phase 4**: Advanced patterns and personalization

This gradual approach ensures stability while progressively enhancing the human-like experience.