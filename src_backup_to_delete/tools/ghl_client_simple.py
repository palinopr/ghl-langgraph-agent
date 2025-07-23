"""
Simplified GoHighLevel API Client
Only includes methods actually used in production
"""
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio
from app.config import get_settings, get_ghl_headers
from app.utils.simple_logger import get_logger

logger = get_logger("ghl_client_simple")


class SimpleGHLClient:
    """Simplified GHL API client with only production-used methods"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ghl_api_base_url
        self.headers = get_ghl_headers()
        self.location_id = self.settings.ghl_location_id
        self.calendar_id = self.settings.ghl_calendar_id
        self.assigned_user_id = self.settings.ghl_assigned_user_id
    
    async def api_call(
        self, 
        method: str, 
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 30
    ) -> Optional[Dict]:
        """
        Generic API caller with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., /contacts/{id})
            json: Request body data
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Response data or None if error
        """
        url = f"{self.base_url}{endpoint}"
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self.headers,
                        json=json,
                        params=params,
                        timeout=timeout
                    )
                    
                    # Log the request
                    logger.info(
                        f"GHL API: {method} {endpoint} - Status: {response.status_code}"
                    )
                    
                    # Handle success
                    if response.status_code in [200, 201]:
                        return response.json()
                    
                    # Handle rate limit
                    elif response.status_code == 429:
                        retry_after = int(response.headers.get("Retry-After", "60"))
                        logger.warning(f"Rate limited. Waiting {retry_after}s...")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    # Handle auth errors (don't retry)
                    elif response.status_code in [401, 403]:
                        logger.error(f"Auth error: {response.status_code} - {response.text}")
                        return None
                    
                    # Handle server errors (retry)
                    elif response.status_code >= 500:
                        logger.warning(f"Server error: {response.status_code}. Retrying...")
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    
                    # Other errors
                    else:
                        logger.error(f"API error: {response.status_code} - {response.text}")
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                return None
                
            except Exception as e:
                logger.error(f"API request failed: {str(e)}")
                return None
        
        return None
    
    # Contact Methods
    async def get_contact(self, contact_id: str) -> Optional[Dict]:
        """Get contact details"""
        result = await self.api_call("GET", f"/contacts/{contact_id}")
        # Handle nested response format
        if result and "contact" in result:
            return result["contact"]
        return result
    
    async def update_contact(self, contact_id: str, updates: Dict[str, Any]) -> Optional[Dict]:
        """Update contact information"""
        return await self.api_call("PUT", f"/contacts/{contact_id}", json=updates)
    
    async def update_contact_field(self, contact_id: str, field_id: str, value: str) -> Optional[Dict]:
        """Update a single custom field"""
        data = {"customFields": {field_id: value}}
        return await self.update_contact(contact_id, data)
    
    async def update_custom_fields(self, contact_id: str, custom_fields: Dict[str, Any]) -> Optional[Dict]:
        """Update multiple custom fields"""
        # Convert to GHL format
        custom_field_list = [
            {"id": field_id, "value": str(value) if value is not None else ""}
            for field_id, value in custom_fields.items()
        ]
        return await self.update_contact(contact_id, {"customFields": custom_field_list})
    
    async def add_tags(self, contact_id: str, tags: List[str]) -> Optional[Dict]:
        """Add tags to contact"""
        return await self.update_contact(contact_id, {"tags": tags})
    
    # Messaging Methods
    async def send_message(self, contact_id: str, message: str, message_type: str = "WhatsApp") -> Optional[Dict]:
        """Send message to contact"""
        # Split long messages
        messages = self._split_message(message)
        results = []
        
        for msg in messages:
            data = {
                "type": message_type,
                "contactId": contact_id,
                "message": msg
            }
            result = await self.api_call("POST", "/conversations/messages", json=data)
            if result:
                results.append(result)
                logger.info(f"Message sent: {msg[:50]}...")
            else:
                logger.error("Failed to send message")
                
        return results[0] if results else None
    
    def _split_message(self, message: str, max_length: int = 300) -> List[str]:
        """Split message into chunks"""
        if len(message) <= max_length:
            return [message]
            
        chunks = []
        current = ""
        
        for sentence in message.split(". "):
            if len(current) + len(sentence) + 2 <= max_length:
                current += sentence + ". "
            else:
                if current:
                    chunks.append(current.strip())
                current = sentence + ". "
                
        if current:
            chunks.append(current.strip())
            
        return chunks
    
    # Conversation Methods
    async def get_conversation_history(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get conversation history (legacy method for compatibility)"""
        params = {"contactId": contact_id, "limit": 50}
        result = await self.api_call("GET", "/conversations/search", params=params)
        
        if result and "conversations" in result:
            messages = []
            for conv in result["conversations"]:
                if "messages" in conv:
                    for msg in conv["messages"]:
                        messages.append({
                            "id": msg.get("id"),
                            "message": msg.get("body", ""),
                            "sender": "user" if msg.get("direction") == "inbound" else "assistant",
                            "timestamp": msg.get("dateAdded"),
                            "type": msg.get("type")
                        })
            messages.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "")
            return messages
        return []
    
    async def get_conversations(self, contact_id: str) -> List[Dict]:
        """Get conversations for a contact"""
        params = {"locationId": self.location_id, "contactId": contact_id}
        result = await self.api_call("GET", "/conversations/search", params=params)
        return result.get("conversations", []) if result else []
    
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Get messages from a conversation"""
        result = await self.api_call("GET", f"/conversations/{conversation_id}/messages")
        
        # Handle nested structure
        if result and "messages" in result:
            messages_data = result["messages"]
            if isinstance(messages_data, dict) and "messages" in messages_data:
                return messages_data["messages"]
            elif isinstance(messages_data, list):
                return messages_data
        return []
    
    async def get_conversation_messages_for_thread(
        self, contact_id: str, thread_id: str = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get messages for current thread only"""
        if not thread_id:
            conversations = await self.get_conversations(contact_id)
            if not conversations:
                return []
            thread_id = conversations[0].get('id')
        
        messages = await self.get_conversation_messages(thread_id)
        return messages[-limit:] if messages else []
    
    # Calendar Methods
    async def check_calendar_availability(
        self, start_date: datetime = None, end_date: datetime = None, timezone: str = "America/New_York"
    ) -> List[Dict[str, Any]]:
        """Check calendar availability"""
        if not start_date:
            start_date = datetime.now()
        if not end_date:
            end_date = start_date + timedelta(days=7)
            
        params = {
            "startDate": int(start_date.timestamp() * 1000),  # Milliseconds
            "endDate": int(end_date.timestamp() * 1000),
            "timezone": timezone
        }
        
        result = await self.api_call("GET", f"/calendars/{self.calendar_id}/free-slots", params=params)
        
        # Parse GHL's dict format into list of slots
        if result and isinstance(result, dict):
            slots = []
            for date_key, date_data in result.items():
                if date_key == "traceId":
                    continue
                if isinstance(date_data, dict) and "slots" in date_data:
                    for slot_time in date_data["slots"]:
                        start = datetime.fromisoformat(slot_time)
                        end = start + timedelta(hours=1)
                        slots.append({
                            "startTime": start,
                            "endTime": end,
                            "available": True
                        })
            return slots
        return []
    
    async def create_appointment(
        self, contact_id: str, start_time: datetime, end_time: datetime, 
        title: str = "WhatsApp Automation Demo", timezone: str = "America/New_York"
    ) -> Optional[Dict[str, Any]]:
        """Create appointment"""
        data = {
            "calendarId": self.calendar_id,
            "locationId": self.location_id,
            "contactId": contact_id,
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "title": title,
            "appointmentStatus": "confirmed",
            "assignedUserId": self.assigned_user_id,
            "address": "Google Meet",
            "ignoreDateRange": False,
            "toNotify": True,
            "meetingLocationType": "gmeet"
        }
        
        result = await self.api_call("POST", "/calendars/events/appointments", json=data)
        if result:
            logger.info(f"✅ Appointment created for {contact_id}")
        else:
            logger.error(f"❌ Failed to create appointment")
        return result
    
    # Utility Methods
    async def verify_connection(self) -> bool:
        """Verify API connection for health checks"""
        try:
            result = await self.api_call("GET", f"/locations/{self.location_id}")
            return result is not None
        except Exception:
            return False
    
    # Backwards compatibility methods
    async def get_contact_details(self, contact_id: str) -> Optional[Dict]:
        """Alias for get_contact"""
        return await self.get_contact(contact_id)
    
    async def get_contact_custom_fields(self, contact_id: str) -> Optional[Dict]:
        """Get custom fields from contact"""
        contact = await self.get_contact(contact_id)
        return contact.get("customFields", {}) if contact else {}


# Create singleton instance
ghl_client = SimpleGHLClient()