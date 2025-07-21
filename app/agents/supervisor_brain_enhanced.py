"""
Enhanced supervisor that uses AI analysis as fallback
"""
from typing import Dict, Any, Optional
import re
from app.utils.simple_logger import get_logger
from app.agents.ai_analyzer import analyze_customer_intent, calculate_smart_score
from app.constants import FIELD_MAPPINGS

logger = get_logger("supervisor_brain_enhanced")


async def extract_and_update_lead_enhanced(
    state: Dict[str, Any],
    ghl_updater = None
) -> Dict[str, Any]:
    """
    Enhanced extraction that uses pattern matching first,
    then falls back to AI analysis for complex cases
    """
    
    # Get current message and context
    webhook_data = state.get("webhook_data", {})
    current_message = webhook_data.get("message", "").strip()
    
    # Get conversation history
    messages = state.get("messages", [])
    previous_fields = state.get("previous_custom_fields", {})
    
    # Try pattern extraction first (fast)
    pattern_result = try_pattern_extraction(current_message, previous_fields)
    
    # If pattern extraction fails or is incomplete, use AI
    if should_use_ai_analysis(pattern_result, current_message):
        logger.info("🤖 Using AI analyzer for complex message understanding")
        
        # Prepare context
        conversation_history = [
            {"type": msg.type, "content": msg.content} 
            for msg in messages[-10:] if hasattr(msg, 'type')
        ]
        
        previous_context = {
            "name": previous_fields.get("name"),
            "business_type": previous_fields.get("business_type"),
            "budget": previous_fields.get("budget"),
            "score": previous_fields.get("score", "0")
        }
        
        # Get AI analysis
        ai_analysis = await analyze_customer_intent(
            current_message,
            conversation_history,
            previous_context
        )
        
        # Merge results
        final_result = merge_results(pattern_result, ai_analysis, previous_fields)
        
        # Calculate score
        final_result["lead_score"] = calculate_smart_score(
            ai_analysis,
            int(previous_fields.get("score", "0"))
        )
        
        # Log decision
        logger.info(f"AI Analysis Result: {final_result}")
        
        # Determine routing based on AI recommendation
        if ai_analysis.get("recommended_action") == "QUALIFY_BUSINESS":
            final_result["next_agent"] = "carlos"
        elif ai_analysis.get("recommended_action") == "OFFER_APPOINTMENT":
            final_result["next_agent"] = "sofia"
        else:
            # Use score-based routing
            score = final_result["lead_score"]
            if score >= 8:
                final_result["next_agent"] = "sofia"
            elif score >= 5:
                final_result["next_agent"] = "carlos"
            else:
                final_result["next_agent"] = "maria"
        
        return final_result
    
    # Use pattern result if sufficient
    return pattern_result


def should_use_ai_analysis(pattern_result: Dict, message: str) -> bool:
    """
    Decide if we need AI analysis
    """
    # Use AI if:
    # 1. No business type detected but message seems business-related
    business_indicators = ["perdiendo", "negocio", "ayuda", "cliente", "reserva", "venta"]
    has_business_indicator = any(word in message.lower() for word in business_indicators)
    
    # 2. Message is complex (multiple sentences, questions)
    is_complex = len(message.split()) > 10 or "?" in message
    
    # 3. Previous patterns failed
    no_extraction = not pattern_result.get("extracted_data", {}).get("business_type")
    
    return (has_business_indicator and no_extraction) or is_complex


def try_pattern_extraction(message: str, previous_fields: Dict) -> Dict[str, Any]:
    """
    Original pattern-based extraction (fast for simple cases)
    """
    # ... existing pattern extraction logic ...
    # This is a simplified version
    
    extracted = {
        "name": previous_fields.get("name"),
        "business_type": previous_fields.get("business_type"),
        "budget": previous_fields.get("budget")
    }
    
    # Simple patterns
    if "restaurante" in message.lower():
        extracted["business_type"] = "restaurante"
    
    # Return result
    return {
        "extracted_data": extracted,
        "lead_score": int(previous_fields.get("score", "0")),
        "next_agent": "maria"  # Default
    }


def merge_results(pattern_result: Dict, ai_analysis: Dict, previous_fields: Dict) -> Dict[str, Any]:
    """
    Merge pattern and AI results intelligently
    """
    merged = pattern_result.copy()
    
    # Update with AI findings
    if ai_analysis.get("business_type"):
        merged["extracted_data"]["business_type"] = ai_analysis["business_type"]
    
    # Add AI insights
    merged["ai_insights"] = {
        "intent": ai_analysis.get("intent"),
        "urgency": ai_analysis.get("urgency"),
        "sentiment": ai_analysis.get("sentiment")
    }
    
    # Update with any new key info
    for key, value in ai_analysis.get("key_info", {}).items():
        if value and key in ["name", "email", "budget"]:
            merged["extracted_data"][key] = value
    
    return merged