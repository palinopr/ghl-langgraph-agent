"""
State utilities for filtering agent results
"""
from typing import Dict, Any


def filter_agent_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter agent result to only include fields defined in ConversationState.
    This prevents internal fields like 'remaining_steps' from being included.
    """
    # Define allowed fields that can be returned by agents
    allowed_fields = {
        "messages",
        "contact_id", "contact_name", "contact_email", "contact_phone",
        "lead_score", "previous_score", "route", "intent",
        "business_type", "goal", "budget", "preferred_day", "preferred_time",
        "current_agent", "agent_history",
        "appointment_booked", "appointment_id", "appointment_datetime",
        "current_step", "next_action",
        "pending_response", "last_response_sent", "response_sent",
        "error", "retry_count",
        "conversation_started_at", "last_updated_at", "language",
        "webhook_data", "ai_analysis", "extracted_data",
        "score_history", "lead_category", "suggested_agent", 
        "analysis_metadata", "score_reasoning",
        "interaction_count", "should_end",
        # Workflow coordination fields
        "next_agent", "supervisor_complete", "data_loaded", "receptionist_complete",
        # Responder tracking fields
        "responder_status", "messages_sent_count", "messages_failed_count", "failed_messages",
        # Custom fields that agents might add
        "qualification_status", "qualification_score", "needs_escalation", "support_category",
        "issue_resolved", "routing_reason", "should_continue"
    }
    
    # Filter the result
    filtered = {}
    for key, value in result.items():
        if key in allowed_fields:
            filtered[key] = value
    
    return filtered