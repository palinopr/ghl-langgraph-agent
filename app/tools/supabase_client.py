"""
Supabase client for message queue and conversation history
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import pytz
from supabase import create_client, Client
from app.config import get_settings
from app.utils.simple_logger import get_logger

logger = get_logger("supabase_client")


class SupabaseClient:
    """Supabase client for managing message queue and conversation history"""
    
    def __init__(self):
        settings = get_settings()
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_key
        )
        
    async def add_to_message_queue(self, message_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Add message to the processing queue
        
        Args:
            message_data: Message data including contact_id, message, etc.
            
        Returns:
            Created queue entry or None
        """
        try:
            data = {
                "contact_id": message_data["contact_id"],
                "message": message_data["message_body"],
                "sender": "user",
                "status": "pending",
                "location_id": message_data.get("location_id"),
                "conversation_id": message_data.get("conversation_id"),
                "whatsapp_message_id": message_data.get("whatsapp_message_id"),
                "created_at": datetime.now(pytz.UTC).isoformat()
            }
            
            result = self.client.table("message_queue").insert(data).execute()
            
            if result.data:
                logger.info(f"Added message to queue for contact {data['contact_id']}")
                return result.data[0]
            else:
                logger.error("Failed to add message to queue")
                return None
                
        except Exception as e:
            logger.error(f"Error adding to message queue: {str(e)}")
            return None
    
    async def get_pending_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending messages from the queue
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of pending messages
        """
        try:
            result = self.client.table("message_queue") \
                .select("*") \
                .eq("status", "pending") \
                .order("created_at", desc=False) \
                .limit(limit) \
                .execute()
                
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting pending messages: {str(e)}")
            return []
    
    async def update_message_status(
        self, 
        message_id: str, 
        status: str,
        agent_name: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update message processing status
        
        Args:
            message_id: Message ID
            status: New status (processing, completed, failed)
            agent_name: Name of the agent that processed the message
            error_message: Error message if failed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(pytz.UTC).isoformat()
            }
            
            if agent_name:
                update_data["processed_by_agent"] = agent_name
                update_data["agent_processed"] = True
                update_data["agent_processed_at"] = datetime.now(pytz.UTC).isoformat()
                
            if error_message:
                update_data["error_message"] = error_message
                
            result = self.client.table("message_queue") \
                .update(update_data) \
                .eq("id", message_id) \
                .execute()
                
            if result.data:
                logger.info(f"Updated message {message_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to update message {message_id} status")
                return False
                
        except Exception as e:
            logger.error(f"Error updating message status: {str(e)}")
            return False
    
    async def save_conversation_history(
        self,
        contact_id: str,
        messages: List[Dict[str, Any]]
    ) -> bool:
        """
        Save conversation history to database
        
        Args:
            contact_id: Contact ID
            messages: List of messages to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare messages for insertion
            records = []
            for msg in messages:
                records.append({
                    "contact_id": contact_id,
                    "message": msg.get("content", ""),
                    "sender": msg.get("sender", "user"),
                    "timestamp": msg.get("timestamp", datetime.now(pytz.UTC).isoformat()),
                    "metadata": msg.get("metadata", {})
                })
            
            result = self.client.table("conversation_history") \
                .insert(records) \
                .execute()
                
            if result.data:
                logger.info(f"Saved {len(records)} messages for contact {contact_id}")
                return True
            else:
                logger.error("Failed to save conversation history")
                return False
                
        except Exception as e:
            logger.error(f"Error saving conversation history: {str(e)}")
            return False
    
    async def get_conversation_history(
        self,
        contact_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a contact
        
        Args:
            contact_id: Contact ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of messages
        """
        try:
            result = self.client.table("conversation_history") \
                .select("*") \
                .eq("contact_id", contact_id) \
                .order("timestamp", desc=False) \
                .limit(limit) \
                .execute()
                
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {str(e)}")
            return []
    
    async def add_to_responder_queue(
        self,
        contact_id: str,
        message_id: str,
        agent: str,
        response: str,
        analysis: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        Add response to responder queue
        
        Args:
            contact_id: Contact ID
            message_id: Original message ID
            agent: Agent name
            response: Response text
            analysis: Agent analysis data
            
        Returns:
            Created queue entry or None
        """
        try:
            data = {
                "contact_id": contact_id,
                "message_id": message_id,
                "agent": agent,
                "response": response,
                "analysis": analysis,
                "status": "pending",
                "created_at": datetime.now(pytz.UTC).isoformat()
            }
            
            result = self.client.table("responder_queue") \
                .insert(data) \
                .execute()
                
            if result.data:
                logger.info(f"Added response to queue from {agent} for {contact_id}")
                return result.data[0]
            else:
                logger.error("Failed to add response to queue")
                return None
                
        except Exception as e:
            logger.error(f"Error adding to responder queue: {str(e)}")
            return None
    
    async def get_pending_responses(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending responses from the queue
        
        Args:
            limit: Maximum number of responses to retrieve
            
        Returns:
            List of pending responses
        """
        try:
            result = self.client.table("responder_queue") \
                .select("*") \
                .eq("status", "pending") \
                .order("created_at", desc=False) \
                .limit(limit) \
                .execute()
                
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting pending responses: {str(e)}")
            return []
    
    async def update_response_status(
        self,
        response_id: str,
        status: str,
        whatsapp_message_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update response status
        
        Args:
            response_id: Response ID
            status: New status (sent, failed)
            whatsapp_message_id: WhatsApp message ID if sent
            error_message: Error message if failed
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(pytz.UTC).isoformat()
            }
            
            if status == "sent":
                update_data["sent_at"] = datetime.now(pytz.UTC).isoformat()
                if whatsapp_message_id:
                    update_data["whatsapp_message_id"] = whatsapp_message_id
            elif status == "failed":
                update_data["failed_at"] = datetime.now(pytz.UTC).isoformat()
                if error_message:
                    update_data["error_message"] = error_message
                    
            result = self.client.table("responder_queue") \
                .update(update_data) \
                .eq("id", response_id) \
                .execute()
                
            if result.data:
                logger.info(f"Updated response {response_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to update response {response_id} status")
                return False
                
        except Exception as e:
            logger.error(f"Error updating response status: {str(e)}")
            return False
    
    async def mark_appointment_booked(
        self,
        message_id: str,
        appointment_id: str
    ) -> bool:
        """
        Mark that an appointment was booked from a message
        
        Args:
            message_id: Message ID
            appointment_id: Created appointment ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                "appointment_booked": True,
                "appointment_id": appointment_id,
                "booked_at": datetime.now(pytz.UTC).isoformat()
            }
            
            result = self.client.table("message_queue") \
                .update(update_data) \
                .eq("id", message_id) \
                .execute()
                
            if result.data:
                logger.info(f"Marked appointment {appointment_id} booked for message {message_id}")
                return True
            else:
                logger.error(f"Failed to mark appointment booked")
                return False
                
        except Exception as e:
            logger.error(f"Error marking appointment booked: {str(e)}")
            return False


# Note: Create instance when needed, not at module level
# This prevents initialization errors during imports