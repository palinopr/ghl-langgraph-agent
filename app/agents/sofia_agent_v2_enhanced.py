"""
Sofia - Appointment Setting Agent (ENHANCED VERSION)
With streaming responses and better error handling
"""
from typing import Dict, Any, List, Annotated, Optional, Union, AsyncIterator
from langchain_core.messages import AnyMessage, AIMessageChunk
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from langchain_core.messages.utils import trim_messages
from app.tools.agent_tools_v2 import appointment_tools_v2
from app.utils.simple_logger import get_logger
from app.config import get_settings
import asyncio

logger = get_logger("sofia_v2_enhanced")


class SofiaState(AgentState):
    """Extended state for Sofia agent with streaming support"""
    contact_id: str
    contact_name: Optional[str]
    appointment_status: Optional[str]
    appointment_id: Optional[str]
    appointment_datetime: Optional[str]
    should_continue: bool = True
    # New fields for enhanced features
    stream_response: bool = False
    conversation_token_count: int = 0


def sofia_prompt(state: SofiaState) -> list[AnyMessage]:
    """
    Dynamic prompt function for Sofia with context window management
    """
    # Trim messages if approaching token limit
    messages = state.get("messages", [])
    if messages and len(messages) > 10:
        try:
            # Keep system message and trim conversation history
            trimmed_messages = trim_messages(
                messages[1:],  # Skip system message
                max_tokens=3000,
                strategy="last",
                allow_partial=True
            )
            messages = messages[:1] + trimmed_messages
            logger.info(f"Trimmed conversation from {len(state['messages'])} to {len(messages)} messages")
        except Exception as e:
            logger.warning(f"Failed to trim messages: {e}")
    
    # Build context from state
    contact_name = state.get("contact_name", "there")
    appointment_status = state.get("appointment_status")
    
    # Customize prompt based on state
    context = ""
    if appointment_status == "booked":
        context = "\nIMPORTANT: An appointment has already been booked. Focus on confirming details and wrapping up."
    elif contact_name and contact_name != "there":
        context = f"\nYou are speaking with {contact_name}."
    
    system_prompt = f"""You are Sofia, a professional appointment setter for Main Outlet Media.

Your primary goal is to book appointments for consultations while maintaining a professional, 
friendly tone. You should:

1. Warmly greet new contacts and introduce yourself
2. Gather necessary information (name, business type, main challenges)
3. Check calendar availability
4. Book appointments efficiently
5. Confirm appointment details clearly
6. Handle objections professionally
7. Always be helpful and accommodating

Language: Respond in the same language as the customer (Spanish/English).
{context}

Remember: You have access to tools for checking availability and booking appointments.
Use them when appropriate."""

    return [{"role": "system", "content": system_prompt}] + messages


# Create the enhanced Sofia agent
def create_sofia_agent():
    """Create Sofia agent with enhanced features"""
    settings = get_settings()
    
    agent = create_react_agent(
        model=f"openai:{getattr(settings, 'openai_model', 'gpt-4-turbo')}",
        tools=appointment_tools_v2,
        state_schema=SofiaState,
        prompt=sofia_prompt,
        name="sofia_enhanced"
    )
    
    return agent


# Streaming response handler
async def stream_sofia_response(
    agent,
    state: SofiaState,
    config: Optional[Dict[str, Any]] = None
) -> AsyncIterator[Dict[str, Any]]:
    """
    Stream Sofia's responses for better UX, especially during appointment confirmation
    """
    try:
        # Stream events from the agent
        async for event in agent.astream_events(
            state,
            config=config or {},
            version="v2",
            include_types=["llm", "tool", "messages"]
        ):
            # Handle different event types
            if event["event"] == "on_llm_stream":
                # Stream LLM tokens as they're generated
                chunk = event.get("data", {}).get("chunk")
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    yield {
                        "type": "token",
                        "content": chunk.content,
                        "timestamp": event.get("timestamp")
                    }
            
            elif event["event"] == "on_tool_start":
                # Notify when tools are being used
                tool_name = event.get("metadata", {}).get("tool_name", "tool")
                yield {
                    "type": "tool_start",
                    "tool": tool_name,
                    "message": f"🔧 {tool_name.replace('_', ' ').title()}..."
                }
            
            elif event["event"] == "on_tool_end":
                # Notify when tools complete
                tool_name = event.get("metadata", {}).get("tool_name", "tool")
                yield {
                    "type": "tool_end",
                    "tool": tool_name,
                    "message": "✓ Complete"
                }
                
    except Exception as e:
        logger.error(f"Error during streaming: {e}")
        yield {
            "type": "error",
            "message": "I apologize, but I encountered an issue. Let me try again."
        }


# Error-resilient node function
async def sofia_node_v2_enhanced(state: SofiaState) -> Union[Dict[str, Any], Command]:
    """
    Enhanced Sofia node with streaming support and error recovery
    """
    agent = create_sofia_agent()
    
    try:
        # Check if streaming is requested
        if state.get("stream_response", False):
            # Return streaming configuration
            return {
                "streaming_enabled": True,
                "agent": agent,
                "handler": stream_sofia_response
            }
        
        # Regular (non-streaming) execution with retry logic
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                result = await agent.ainvoke(state)
                
                # Check for successful appointment booking
                if "appointment_id" in result:
                    logger.info(f"Successfully booked appointment: {result['appointment_id']}")
                
                return result
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Attempt {retry_count} failed: {e}")
                
                if retry_count >= max_retries:
                    # Return graceful error message
                    return {
                        "messages": [{
                            "role": "assistant",
                            "content": "I apologize, but I'm having technical difficulties booking your appointment. "
                                     "Please try again in a moment, or contact us directly at (555) 123-4567."
                        }],
                        "error": str(e),
                        "should_continue": False
                    }
                
                # Wait before retry
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                
    except Exception as e:
        logger.error(f"Critical error in Sofia node: {e}", exc_info=True)
        return {
            "messages": [{
                "role": "assistant",
                "content": "I apologize for the inconvenience. Let me transfer you to someone who can help."
            }],
            "error": str(e),
            "next_agent": "maria",  # Fallback to Maria
            "should_continue": True
        }


# Convenience function for appointment confirmation streaming
async def stream_appointment_confirmation(
    contact_id: str,
    appointment_details: Dict[str, Any],
    config: Optional[Dict[str, Any]] = None
) -> AsyncIterator[str]:
    """
    Stream appointment confirmation message for better UX
    """
    agent = create_sofia_agent()
    
    # Prepare confirmation state
    state = SofiaState(
        contact_id=contact_id,
        messages=[{
            "role": "user",
            "content": f"Please confirm my appointment for {appointment_details.get('date')} at {appointment_details.get('time')}"
        }],
        appointment_status="booked",
        appointment_id=appointment_details.get("id"),
        appointment_datetime=f"{appointment_details.get('date')} {appointment_details.get('time')}",
        stream_response=True
    )
    
    # Stream the response
    async for event in stream_sofia_response(agent, state, config):
        if event["type"] == "token":
            yield event["content"]


# Export enhanced components
sofia_node_v2 = sofia_node_v2_enhanced  # Use enhanced version
__all__ = [
    "SofiaState",
    "create_sofia_agent",
    "sofia_node_v2",
    "stream_sofia_response",
    "stream_appointment_confirmation"
]