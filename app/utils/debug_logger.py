"""
Enhanced debug logging utilities for complete visibility
"""
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from functools import wraps
import traceback

from app.utils.simple_logger import get_logger

logger = get_logger("debug")


class DebugLogger:
    """Enhanced debugging logger with structured output"""
    
    @staticmethod
    def log_entry(component: str, state: Dict[str, Any]) -> None:
        """Log entry to a component with state snapshot"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🎯 ENTERING {component.upper()}")
        logger.info(f"⏰ Time: {datetime.now().isoformat()}")
        logger.info(f"📊 State Summary:")
        logger.info(f"  - Contact ID: {state.get('contact_id', 'N/A')}")
        logger.info(f"  - Messages: {len(state.get('messages', []))}")
        logger.info(f"  - Lead Score: {state.get('lead_score', 'N/A')}")
        
        # Log extracted data
        extracted = state.get('extracted_data', {})
        if extracted:
            logger.info(f"  - Extracted Data:")
            logger.info(f"    • Name: {extracted.get('name', 'Not set')}")
            logger.info(f"    • Business: {extracted.get('business_type', 'Not set')}")
            logger.info(f"    • Budget: {extracted.get('budget', 'Not set')}")
            logger.info(f"    • Goal: {extracted.get('goal', 'Not set')}")
    
    @staticmethod
    def log_exit(component: str, result: Any = None, error: Exception = None) -> None:
        """Log exit from a component"""
        if error:
            logger.error(f"❌ EXITING {component.upper()} WITH ERROR")
            logger.error(f"  - Error: {str(error)}")
            logger.error(f"  - Traceback: {traceback.format_exc()}")
        else:
            logger.info(f"✅ EXITING {component.upper()} SUCCESSFULLY")
            if result:
                logger.info(f"  - Result type: {type(result).__name__}")
    
    @staticmethod
    def log_message_flow(messages: List[Any]) -> None:
        """Log the conversation flow"""
        logger.info(f"\n💬 CONVERSATION FLOW ({len(messages)} messages):")
        for i, msg in enumerate(messages[-10:]):  # Last 10 messages
            if hasattr(msg, 'type'):
                role = "Human" if msg.type == "human" else "AI"
                content = getattr(msg, 'content', str(msg))
            elif isinstance(msg, dict):
                role = "Human" if msg.get('role') == 'user' else "AI"
                content = msg.get('content', str(msg))
            else:
                role = "Unknown"
                content = str(msg)
            
            logger.info(f"  {i+1}. [{role}]: {content[:100]}...")
    
    @staticmethod
    def log_extraction(current_message: str, extracted: Dict[str, Any]) -> None:
        """Log extraction results"""
        logger.info(f"\n🔍 EXTRACTION ANALYSIS:")
        logger.info(f"  - Current Message: '{current_message}'")
        logger.info(f"  - Message Length: {len(current_message.split())} words")
        logger.info(f"  - Extracted:")
        
        for key, value in extracted.items():
            if value:
                logger.info(f"    ✅ {key}: '{value}'")
            else:
                logger.info(f"    ❌ {key}: None")
    
    @staticmethod
    def log_routing_decision(state: Dict[str, Any], next_agent: str, reason: str) -> None:
        """Log routing decisions"""
        logger.info(f"\n🚦 ROUTING DECISION:")
        logger.info(f"  - Current Score: {state.get('lead_score', 'N/A')}")
        logger.info(f"  - Routing Count: {state.get('routing_count', 0)}")
        logger.info(f"  - Decision: Route to {next_agent.upper()}")
        logger.info(f"  - Reason: {reason}")
        
        # Log data completeness
        extracted = state.get('extracted_data', {})
        completeness = []
        if extracted.get('name'): completeness.append('name')
        if extracted.get('business_type'): completeness.append('business')
        if extracted.get('budget'): completeness.append('budget')
        if extracted.get('goal'): completeness.append('goal')
        
        logger.info(f"  - Data Completeness: {completeness}")
    
    @staticmethod
    def log_tool_call(tool_name: str, params: Dict[str, Any], result: Any = None) -> None:
        """Log tool calls"""
        logger.info(f"\n🔧 TOOL CALL: {tool_name}")
        logger.info(f"  - Parameters: {json.dumps(params, default=str)[:200]}...")
        if result:
            logger.info(f"  - Result: {json.dumps(result, default=str)[:200]}...")
    
    @staticmethod
    def log_ghl_api_call(method: str, endpoint: str, data: Any, response: Any = None, error: Exception = None) -> None:
        """Log GHL API calls"""
        logger.info(f"\n🌐 GHL API CALL:")
        logger.info(f"  - Method: {method}")
        logger.info(f"  - Endpoint: {endpoint}")
        logger.info(f"  - Data: {json.dumps(data, default=str)[:200]}...")
        
        if error:
            logger.error(f"  - Error: {str(error)}")
        elif response:
            logger.info(f"  - Response: {json.dumps(response, default=str)[:200]}...")
    
    @staticmethod
    def log_state_snapshot(state: Dict[str, Any], checkpoint: str) -> Dict[str, Any]:
        """Create and log a state snapshot"""
        snapshot = {
            "checkpoint": checkpoint,
            "timestamp": datetime.now().isoformat(),
            "contact_id": state.get("contact_id"),
            "lead_score": state.get("lead_score"),
            "extracted_data": state.get("extracted_data", {}),
            "messages_count": len(state.get("messages", [])),
            "appointment_booked": state.get("appointment_booked", False),
            "available_slots": len(state.get("available_slots", [])),
            "current_agent": state.get("current_agent"),
            "routing_count": state.get("routing_count", 0),
            "escalation_reason": state.get("escalation_reason"),
            "last_message": None
        }
        
        # Get last message safely
        messages = state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, 'content'):
                snapshot["last_message"] = last_msg.content[:100]
            elif isinstance(last_msg, dict):
                snapshot["last_message"] = last_msg.get('content', '')[:100]
        
        logger.info(f"\n📸 STATE SNAPSHOT @ {checkpoint}:")
        logger.info(json.dumps(snapshot, indent=2))
        
        return snapshot


class TimingContext:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        logger.info(f"⏱️ Starting: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type:
            logger.error(f"⏱️ {self.operation_name} FAILED after {elapsed:.3f}s")
        else:
            logger.info(f"⏱️ {self.operation_name} completed in {elapsed:.3f}s")


def debug_async(component_name: str):
    """Decorator for async functions with debug logging"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get state from args if available
            state = None
            if args and isinstance(args[0], dict):
                state = args[0]
            elif 'state' in kwargs:
                state = kwargs['state']
            
            if state:
                DebugLogger.log_entry(component_name, state)
            else:
                logger.info(f"➡️ Entering {component_name}: {func.__name__}")
            
            try:
                with TimingContext(f"{component_name}::{func.__name__}"):
                    result = await func(*args, **kwargs)
                
                DebugLogger.log_exit(component_name, result)
                return result
                
            except Exception as e:
                DebugLogger.log_exit(component_name, error=e)
                raise
        
        return wrapper
    return decorator


def debug_sync(component_name: str):
    """Decorator for sync functions with debug logging"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"➡️ Entering {component_name}: {func.__name__}")
            
            try:
                with TimingContext(f"{component_name}::{func.__name__}"):
                    result = func(*args, **kwargs)
                
                logger.info(f"✅ Exiting {component_name}: {func.__name__}")
                return result
                
            except Exception as e:
                logger.error(f"❌ Error in {component_name}: {str(e)}")
                raise
        
        return wrapper
    return decorator


# Export main components
__all__ = [
    "DebugLogger",
    "TimingContext", 
    "debug_async",
    "debug_sync"
]