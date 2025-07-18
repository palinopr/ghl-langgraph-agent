"""
GoHighLevel API Client for Python
Migrated from ghl-http.js
"""
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pytz
from app.config import get_settings, get_ghl_headers
from app.utils.simple_logger import get_logger

logger = get_logger("ghl_client")


class GHLClient:
    """GoHighLevel API client with all necessary methods"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ghl_api_base_url
        self.headers = get_ghl_headers()
        self.location_id = self.settings.ghl_location_id
        self.calendar_id = self.settings.ghl_calendar_id
        self.assigned_user_id = self.settings.ghl_assigned_user_id
        
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: int = 30
    ) -> Optional[Dict]:
        """
        Make HTTP request to GoHighLevel API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request body data
            params: Query parameters
            timeout: Request timeout in seconds
            
        Returns:
            Response data or None if error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    params=params,
                    timeout=timeout
                )
                
                logger.info(
                    f"GHL API Request: {method} {endpoint} - Status: {response.status_code}"
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"GHL API Error: {response.status_code} - {response.text}"
                    )
                    return None
                    
        except Exception as e:
            logger.error(f"GHL API Request Failed: {str(e)}", exc_info=True)
            return None
    
    async def get_contact_details(self, contact_id: str) -> Optional[Dict]:
        """
        Get contact details from GoHighLevel
        
        Args:
            contact_id: Contact ID
            
        Returns:
            Contact data or None
        """
        endpoint = f"/contacts/{contact_id}"
        result = await self._make_request("GET", endpoint)
        
        if result and "contact" in result:
            return result["contact"]
        return result
    
    async def update_contact(
        self, 
        contact_id: str, 
        updates: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        Update contact in GoHighLevel
        
        Args:
            contact_id: Contact ID
            updates: Fields to update
            
        Returns:
            Updated contact data or None
        """
        endpoint = f"/contacts/{contact_id}"
        return await self._make_request("PUT", endpoint, data=updates)
    
    async def update_custom_fields(
        self, 
        contact_id: str, 
        custom_fields: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        Update contact custom fields
        
        Args:
            contact_id: Contact ID
            custom_fields: Dict of field_id: value
            
        Returns:
            Updated contact data or None
        """
        # Convert to GHL custom fields format
        custom_field_list = []
        for field_id, value in custom_fields.items():
            custom_field_list.append({
                "id": field_id,
                "value": str(value) if value is not None else ""
            })
        
        updates = {"customFields": custom_field_list}
        return await self.update_contact(contact_id, updates)
    
    async def add_tags(self, contact_id: str, tags: List[str]) -> Optional[Dict]:
        """
        Add tags to contact
        
        Args:
            contact_id: Contact ID
            tags: List of tags to add
            
        Returns:
            Updated contact data or None
        """
        updates = {"tags": tags}
        return await self.update_contact(contact_id, updates)
    
    async def send_message(
        self, 
        contact_id: str, 
        message: str,
        message_type: str = "WhatsApp"
    ) -> Optional[Dict]:
        """
        Send message via GoHighLevel
        
        Args:
            contact_id: Contact ID
            message: Message content
            message_type: Type of message (WhatsApp, SMS, etc.)
            
        Returns:
            Message response or None
        """
        endpoint = "/conversations/messages"
        
        # Split long messages
        messages = self._split_message(message)
        results = []
        
        for msg in messages:
            data = {
                "type": message_type,
                "contactId": contact_id,
                "message": msg
            }
            
            result = await self._make_request("POST", endpoint, data=data)
            if result:
                results.append(result)
                logger.info(
                    f"Message sent to {contact_id}: {msg[:50]}..."
                )
            else:
                logger.error(f"Failed to send message to {contact_id}")
                
        return results[0] if results else None
    
    def _split_message(self, message: str, max_length: int = 300) -> List[str]:
        """
        Split message into chunks for WhatsApp
        
        Args:
            message: Full message
            max_length: Maximum length per chunk
            
        Returns:
            List of message chunks
        """
        if len(message) <= max_length:
            return [message]
            
        chunks = []
        current_chunk = ""
        
        for sentence in message.split(". "):
            if len(current_chunk) + len(sentence) + 2 <= max_length:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
    
    async def get_conversation_history(
        self, 
        contact_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a contact
        
        Args:
            contact_id: Contact ID
            
        Returns:
            List of messages
        """
        endpoint = f"/conversations/search"
        params = {
            "contactId": contact_id,
            "limit": 50
        }
        
        result = await self._make_request("GET", endpoint, params=params)
        
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
            
            # Sort by timestamp
            messages.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "")
            return messages
            
        return []
    
    async def check_calendar_availability(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        timezone: str = "America/New_York"
    ) -> List[Dict[str, Any]]:
        """
        Check calendar availability
        
        Args:
            start_date: Start date for checking availability
            end_date: End date for checking availability
            timezone: Timezone for dates
            
        Returns:
            List of available slots
        """
        if not start_date:
            start_date = datetime.now(pytz.timezone(timezone))
        if not end_date:
            end_date = start_date + timedelta(days=7)
            
        endpoint = f"/calendars/{self.calendar_id}/free-slots"
        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "timezone": timezone
        }
        
        result = await self._make_request("GET", endpoint, params=params)
        
        if result and isinstance(result, list):
            return result
            
        logger.warning("No calendar slots returned")
        return []
    
    async def check_existing_appointments(
        self, 
        contact_id: str
    ) -> List[Dict[str, Any]]:
        """
        Check existing appointments for a contact
        
        Args:
            contact_id: Contact ID
            
        Returns:
            List of appointments
        """
        endpoint = f"/calendars/events"
        params = {
            "contactId": contact_id,
            "calendarId": self.calendar_id
        }
        
        result = await self._make_request("GET", endpoint, params=params)
        
        if result and "events" in result:
            return result["events"]
            
        return []
    
    async def create_appointment(
        self,
        contact_id: str,
        start_time: datetime,
        end_time: datetime,
        title: str = "WhatsApp Automation Demo",
        timezone: str = "America/New_York"
    ) -> Optional[Dict[str, Any]]:
        """
        Create appointment in GoHighLevel
        
        Args:
            contact_id: Contact ID
            start_time: Appointment start time
            end_time: Appointment end time
            title: Appointment title
            timezone: Timezone
            
        Returns:
            Created appointment data or None
        """
        endpoint = f"/calendars/{self.calendar_id}/events"
        
        data = {
            "calendarId": self.calendar_id,
            "locationId": self.location_id,
            "contactId": contact_id,
            "startTime": start_time.isoformat(),
            "endTime": end_time.isoformat(),
            "title": title,
            "appointmentStatus": "confirmed",
            "assignedUserId": self.assigned_user_id,
            "timezone": timezone
        }
        
        result = await self._make_request("POST", endpoint, data=data)
        
        if result:
            logger.info(
                f"Appointment created for {contact_id} at {start_time}"
            )
            return result
        else:
            logger.error(f"Failed to create appointment for {contact_id}")
            return None
    
    async def get_notes(self, contact_id: str) -> List[Dict[str, Any]]:
        """
        Get notes for a contact
        
        Args:
            contact_id: Contact ID
            
        Returns:
            List of notes
        """
        endpoint = f"/contacts/{contact_id}/notes"
        result = await self._make_request("GET", endpoint)
        
        if result and "notes" in result:
            return result["notes"]
            
        return []
    
    async def create_note(
        self, 
        contact_id: str, 
        body: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a note for a contact
        
        Args:
            contact_id: Contact ID
            body: Note content
            user_id: User ID (optional)
            
        Returns:
            Created note data or None
        """
        endpoint = f"/contacts/{contact_id}/notes"
        
        data = {
            "body": body,
            "userId": user_id or self.assigned_user_id
        }
        
        result = await self._make_request("POST", endpoint, data=data)
        
        if result:
            logger.info(f"Note created for contact {contact_id}")
            return result
        else:
            logger.error(f"Failed to create note for contact {contact_id}")
            return None


# Create singleton instance
ghl_client = GHLClient()