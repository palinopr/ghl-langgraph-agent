"""
Conversation history loader for enriching workflow context
Retrieves full conversation history from GHL or Supabase
"""
from typing import Dict, Any, List, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.tools.ghl_client import ghl_client
# from app.tools.supabase_client import SupabaseClient  # Optional - not needed for core workflow
from app.utils.simple_logger import get_logger
from datetime import datetime

logger = get_logger("conversation_loader")


class ConversationLoader:
    """Loads conversation history from multiple sources with fallback"""
    
    def __init__(self):
        self.ghl_client = ghl_client
        self.supabase_client = None  # Optional - not needed for core workflow
    
    async def load_conversation_history(
        self, 
        contact_id: str, 
        limit: int = 20
    ) -> List[BaseMessage]:
        """
        Load conversation history from available sources
        
        Priority:
        1. Try GHL API for real-time data
        2. Fallback to Supabase for stored history
        3. Return empty list if both fail
        
        Args:
            contact_id: Contact ID to load history for
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of LangChain message objects
        """
        messages = []
        
        # Try GHL API first
        try:
            ghl_history = await self.ghl_client.get_conversation_history(contact_id)
            if ghl_history:
                logger.info(f"Loaded {len(ghl_history)} messages from GHL API")
                messages = self._convert_ghl_to_langchain(ghl_history)
        except Exception as e:
            logger.warning(f"Failed to load from GHL API: {e}")
        
        # If no messages from GHL, try Supabase (if configured)
        # Note: Supabase is optional - not required for core workflow
        # if not messages and self.supabase_client:
        #     try:
        #         supabase_history = await self.supabase_client.get_conversation_history(
        #             contact_id, 
        #             limit=limit
        #         )
        #         if supabase_history:
        #             logger.info(f"Loaded {len(supabase_history)} messages from Supabase")
        #             messages = self._convert_supabase_to_langchain(supabase_history)
        #     except Exception as e:
        #         logger.warning(f"Failed to load from Supabase: {e}")
        
        # Limit messages to requested amount
        if len(messages) > limit:
            messages = messages[-limit:]  # Keep most recent
            
        logger.info(f"Total messages loaded for contact {contact_id}: {len(messages)}")
        return messages
    
    def _convert_ghl_to_langchain(self, ghl_messages: List[Dict]) -> List[BaseMessage]:
        """Convert GHL message format to LangChain messages"""
        messages = []
        
        for msg in ghl_messages:
            content = msg.get("message", "")
            sender = msg.get("sender", "").lower()
            timestamp = msg.get("timestamp", "")
            
            # Create appropriate message type
            if sender == "user":
                message = HumanMessage(
                    content=content,
                    additional_kwargs={
                        "message_id": msg.get("id"),
                        "timestamp": timestamp,
                        "source": "ghl_api"
                    }
                )
            else:
                message = AIMessage(
                    content=content,
                    additional_kwargs={
                        "message_id": msg.get("id"),
                        "timestamp": timestamp,
                        "source": "ghl_api"
                    }
                )
            
            messages.append(message)
        
        return messages
    
    def _convert_supabase_to_langchain(self, supabase_messages: List[Dict]) -> List[BaseMessage]:
        """Convert Supabase message format to LangChain messages"""
        messages = []
        
        for msg in supabase_messages:
            content = msg.get("message", "")
            sender_type = msg.get("sender_type", "").lower()
            created_at = msg.get("created_at", "")
            
            # Create appropriate message type
            if sender_type == "user":
                message = HumanMessage(
                    content=content,
                    additional_kwargs={
                        "message_id": msg.get("id"),
                        "timestamp": created_at,
                        "contact_id": msg.get("contact_id"),
                        "source": "supabase"
                    }
                )
            else:
                message = AIMessage(
                    content=content,
                    additional_kwargs={
                        "message_id": msg.get("id"),
                        "timestamp": created_at,
                        "contact_id": msg.get("contact_id"),
                        "source": "supabase"
                    }
                )
            
            messages.append(message)
        
        return messages
    
    async def get_enhanced_context(self, contact_id: str) -> Dict[str, Any]:
        """
        Get enhanced context including conversation history and metadata
        
        Returns a dictionary with:
        - conversation_history: List of messages
        - contact_info: Contact details from GHL
        - conversation_metadata: Stats and summary
        """
        context = {
            "conversation_history": [],
            "contact_info": {},
            "conversation_metadata": {}
        }
        
        # Load conversation history
        context["conversation_history"] = await self.load_conversation_history(contact_id)
        
        # Try to get contact info from GHL
        try:
            contact_info = await self.ghl_client.get_contact(contact_id)
            if contact_info:
                context["contact_info"] = {
                    "name": contact_info.get("name"),
                    "email": contact_info.get("email"),
                    "phone": contact_info.get("phone"),
                    "tags": contact_info.get("tags", []),
                    "custom_fields": contact_info.get("custom_fields", {})
                }
        except Exception as e:
            logger.warning(f"Failed to get contact info: {e}")
        
        # Add metadata
        if context["conversation_history"]:
            context["conversation_metadata"] = {
                "message_count": len(context["conversation_history"]),
                "has_history": True,
                "oldest_message": context["conversation_history"][0].additional_kwargs.get("timestamp"),
                "newest_message": context["conversation_history"][-1].additional_kwargs.get("timestamp")
            }
        else:
            context["conversation_metadata"] = {
                "message_count": 0,
                "has_history": False
            }
        
        return context


# Create singleton instance
conversation_loader = ConversationLoader()


async def enrich_workflow_state_with_history(
    initial_state: Dict[str, Any],
    contact_id: str
) -> Dict[str, Any]:
    """
    Enrich the workflow initial state with conversation history
    
    This function should be called before running the workflow to ensure
    the full conversation context is available to agents.
    
    Args:
        initial_state: The basic initial state
        contact_id: Contact ID to load history for
        
    Returns:
        Enriched state with conversation history
    """
    # Get enhanced context
    context = await conversation_loader.get_enhanced_context(contact_id)
    
    # Get existing messages (current message)
    current_messages = initial_state.get("messages", [])
    
    # Combine history with current message
    all_messages = context["conversation_history"] + current_messages
    
    # Update state
    enriched_state = {
        **initial_state,
        "messages": all_messages,
        "contact_info": {
            **initial_state.get("contact_info", {}),
            **context["contact_info"]
        },
        "conversation_metadata": context["conversation_metadata"],
        "has_conversation_history": context["conversation_metadata"]["has_history"]
    }
    
    logger.info(
        f"Enriched state with {len(context['conversation_history'])} historical messages "
        f"for contact {contact_id}"
    )
    
    return enriched_state


__all__ = [
    "ConversationLoader",
    "conversation_loader", 
    "enrich_workflow_state_with_history"
]