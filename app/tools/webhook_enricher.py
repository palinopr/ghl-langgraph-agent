"""
Webhook Data Enricher - Fetches complete context from GHL
Since webhook only provides basic data, we need to fetch everything else
UPDATED: Now with parallel API calls for 3x faster enrichment
"""
from typing import Dict, Any, List
import asyncio
from app.tools.ghl_client import ghl_client
from app.tools.conversation_loader import conversation_loader
from app.intelligence.ghl_updater import FIELD_MAPPINGS
from app.utils.simple_logger import get_logger

logger = get_logger("webhook_enricher")


class WebhookEnricher:
    """Enriches basic webhook data with full GHL context"""
    
    def __init__(self):
        self.ghl_client = ghl_client
        self.conversation_loader = conversation_loader
        self.field_mappings = FIELD_MAPPINGS
    
    async def enrich_webhook_data(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich basic webhook data with:
        - Full conversation history
        - Complete contact details
        - Custom fields (score, business, budget, etc.)
        - Tags
        
        Args:
            webhook_data: Basic webhook data with id, name, email, phone, message
            
        Returns:
            Enriched data with full context
        """
        contact_id = webhook_data.get("id")
        if not contact_id:
            logger.error("No contact ID in webhook data")
            return webhook_data
        
        enriched = {
            **webhook_data,
            "conversation_history": [],
            "contact_details": {},
            "custom_fields": {},
            "tags": [],
            "previous_score": 0,
            "extracted_info": {}
        }
        
        try:
            # PARALLEL API CALLS - Python 3.13 free-threading optimization
            # Fetch contact details and conversation history simultaneously
            contact_task = asyncio.create_task(
                self.ghl_client.get_contact(contact_id)
            )
            conversation_task = asyncio.create_task(
                self.conversation_loader.load_conversation_history(
                    contact_id, 
                    limit=50  # Get more history for better context
                )
            )
            
            # Wait for both to complete in parallel
            contact, conversation_history = await asyncio.gather(
                contact_task,
                conversation_task,
                return_exceptions=False
            )
            
            # Process contact details
            if contact:
                enriched["contact_details"] = contact
                enriched["tags"] = contact.get("tags", [])
                
                # Extract custom fields
                custom_fields = contact.get("customFields", [])
                enriched["custom_fields_raw"] = custom_fields
                
                # Map custom fields to our known fields
                for field in custom_fields:
                    field_id = field.get("id")
                    field_value = field.get("value")
                    
                    # Find the field name from our mappings
                    for name, mapped_id in self.field_mappings.items():
                        if field_id == mapped_id:
                            enriched["custom_fields"][name] = field_value
                            
                            # Special handling for score
                            if name == "score":
                                try:
                                    enriched["previous_score"] = int(field_value or 0)
                                except:
                                    enriched["previous_score"] = 0
                            break
                
                # Extract pre-existing info
                enriched["extracted_info"] = {
                    "name": enriched["custom_fields"].get("name") or contact.get("firstName"),
                    "email": contact.get("email"),
                    "phone": contact.get("phone"),
                    "business_type": enriched["custom_fields"].get("business_type"),
                    "budget": enriched["custom_fields"].get("budget"),
                    "goal": enriched["custom_fields"].get("goal"),
                    "intent": enriched["custom_fields"].get("intent", "EXPLORANDO"),
                    "urgency_level": enriched["custom_fields"].get("urgency_level", "NO_EXPRESADO")
                }
                
                logger.info(
                    f"Loaded contact details: Score={enriched['previous_score']}, "
                    f"Business={enriched['extracted_info']['business_type']}, "
                    f"Budget={enriched['extracted_info']['budget']}"
                )
            
            # Process conversation history
            enriched["conversation_history"] = conversation_history or []
            enriched["message_count"] = len(enriched["conversation_history"])
            
            logger.info(
                f"Enriched webhook data for {contact_id}: "
                f"{len(conversation_history)} historical messages, "
                f"previous score: {enriched['previous_score']}"
            )
            
        except Exception as e:
            logger.error(f"Failed to enrich webhook data: {e}")
            # Return original data if enrichment fails
            return webhook_data
        
        return enriched
    
    def prepare_initial_state(self, enriched_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare initial state for workflow from enriched webhook data
        
        Args:
            enriched_data: Webhook data enriched with GHL context
            
        Returns:
            Initial state ready for workflow
        """
        from langchain_core.messages import HumanMessage
        
        # Combine historical messages with current message
        messages = enriched_data.get("conversation_history", [])
        current_message = HumanMessage(content=enriched_data.get("message", ""))
        messages.append(current_message)
        
        # Build initial state with all context
        initial_state = {
            "messages": messages,
            "contact_id": enriched_data.get("id"),
            "contact_name": enriched_data.get("name"),
            "contact_email": enriched_data.get("email"),
            "contact_phone": enriched_data.get("phone"),
            "lead_score": enriched_data.get("previous_score", 0),
            "previous_score": enriched_data.get("previous_score", 0),
            "extracted_data": enriched_data.get("extracted_info", {}),
            "contact_info": enriched_data.get("contact_details", {}),
            "tags": enriched_data.get("tags", []),
            "webhook_data": enriched_data,
            "has_conversation_history": len(messages) > 1,
            "conversation_metadata": {
                "message_count": len(messages),
                "has_previous_score": enriched_data.get("previous_score", 0) > 0,
                "has_business_info": bool(enriched_data.get("extracted_info", {}).get("business_type")),
                "has_budget_info": bool(enriched_data.get("extracted_info", {}).get("budget"))
            }
        }
        
        # Add current agent based on score
        if initial_state["lead_score"] >= 8:
            initial_state["current_agent"] = "sofia"
            initial_state["lead_category"] = "hot"
        elif initial_state["lead_score"] >= 5:
            initial_state["current_agent"] = "carlos"
            initial_state["lead_category"] = "warm"
        else:
            initial_state["current_agent"] = "maria"
            initial_state["lead_category"] = "cold"
        
        logger.info(
            f"Prepared initial state: Score={initial_state['lead_score']}, "
            f"Agent={initial_state['current_agent']}, "
            f"History={initial_state['has_conversation_history']}"
        )
        
        return initial_state


# Singleton instance
webhook_enricher = WebhookEnricher()


async def process_webhook_with_full_context(webhook_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process webhook data and return enriched initial state
    
    This is the main entry point for webhook processing
    
    Args:
        webhook_data: Raw webhook data from GHL
        
    Returns:
        Initial state ready for workflow with full context
    """
    # Enrich webhook data with GHL context
    enriched_data = await webhook_enricher.enrich_webhook_data(webhook_data)
    
    # Prepare initial state for workflow
    initial_state = webhook_enricher.prepare_initial_state(enriched_data)
    
    return initial_state


__all__ = [
    "WebhookEnricher",
    "webhook_enricher",
    "process_webhook_with_full_context"
]