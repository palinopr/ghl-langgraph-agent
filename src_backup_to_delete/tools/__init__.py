"""
Tool modules for agents
Production tools with modernized patterns
"""
from app.tools.agent_tools_modernized import (
    get_contact_details_with_task,
    escalate_to_supervisor,
    update_contact_with_context,
    save_important_context,
    book_appointment_with_instructions
)
from app.tools.ghl_client import GHLClient
from app.tools.webhook_processor import WebhookProcessor
from app.tools.webhook_enricher import WebhookEnricher
from app.tools.conversation_loader import ConversationLoader
from app.tools.calendar_slots import (
    generate_available_slots,
    format_slots_for_customer,
    parse_spanish_datetime,
    find_matching_slot
)
from app.tools.ghl_streaming import HumanLikeResponder, send_human_like_response

__all__ = [
    # Core tools
    "get_contact_details_with_task",
    "escalate_to_supervisor",
    "update_contact_with_context",
    "save_important_context",
    "book_appointment_with_instructions",
    # Clients
    "GHLClient",
    "HumanLikeResponder",
    "send_human_like_response",
    # Processors
    "WebhookProcessor",
    "WebhookEnricher",
    "ConversationLoader",
    # Calendar utilities
    "generate_available_slots",
    "format_slots_for_customer",
    "parse_spanish_datetime",
    "find_matching_slot"
]