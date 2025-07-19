"""
GoHighLevel API Client for Python
Migrated from ghl-http.js
UPDATED: Enhanced retry logic for rate limits with exponential backoff
"""
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pytz
import asyncio
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
    wait_fixed,
    wait_random
)
from app.config import get_settings, get_ghl_headers
from app.utils.simple_logger import get_logger

logger = get_logger("ghl_client")


class GHLRateLimitError(Exception):
    """Custom exception for GHL rate limits"""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"GHL rate limit exceeded. Retry after {retry_after} seconds")


class GHLClient:
    """GoHighLevel API client with enhanced rate limit handling"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ghl_api_base_url
        self.headers = get_ghl_headers()
        self.location_id = self.settings.ghl_location_id
        self.calendar_id = self.settings.ghl_calendar_id
        self.assigned_user_id = self.settings.ghl_assigned_user_id
        # Rate limit tracking
        self._rate_limit_reset = None
        self._request_count = 0
        self._request_window_start = datetime.now()
        
    def _check_rate_limit(self, response: httpx.Response) -> bool:
        """Check if we hit rate limit and extract retry-after"""
        if response.status_code == 429:
            # Check for Retry-After header
            retry_after = response.headers.get("Retry-After", "60")
            try:
                retry_seconds = int(retry_after)
            except:
                retry_seconds = 60
            
            self._rate_limit_reset = datetime.now() + timedelta(seconds=retry_seconds)
            logger.warning(f"GHL rate limit hit. Retry after {retry_seconds} seconds")
            raise GHLRateLimitError(retry_seconds)
        return False
    
    @retry(
        stop=stop_after_attempt(5),  # More attempts for rate limits
        wait=wait_exponential(multiplier=2, min=4, max=60) + wait_random(0, 3),  # Add jitter
        retry=(
            retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)) |
            retry_if_exception_type(GHLRateLimitError)
        ),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying GHL API call, attempt {retry_state.attempt_number}"
        )
    )
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
                
                # Track request count
                self._request_count += 1
                
                # Check for rate limits
                self._check_rate_limit(response)
                
                logger.info(
                    f"GHL API Request: {method} {endpoint} - Status: {response.status_code} {'✓' if response.status_code in [200, 201] else '✗'}"
                )
                
                if response.status_code in [200, 201]:  # Both 200 and 201 are success
                    return response.json()
                elif response.status_code == 429:
                    # Rate limit handled by _check_rate_limit
                    pass
                else:
                    logger.error(
                        f"GHL API Error: {response.status_code} - {response.text}"
                    )
                    # Specific error handling
                    if response.status_code == 401:
                        raise httpx.HTTPStatusError(
                            "GHL Authentication failed. Check API token.",
                            request=response.request,
                            response=response
                        )
                    elif response.status_code == 403:
                        raise httpx.HTTPStatusError(
                            "GHL Access forbidden. Check permissions.",
                            request=response.request,
                            response=response
                        )
                    elif response.status_code >= 500:
                        # Server errors - worth retrying
                        raise httpx.HTTPStatusError(
                            f"GHL Server error: {response.status_code}",
                            request=response.request,
                            response=response
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
        # GHL expects timestamps in milliseconds
        params = {
            "startDate": int(start_date.timestamp() * 1000),
            "endDate": int(end_date.timestamp() * 1000),
            "timezone": timezone
        }
        
        result = await self._make_request("GET", endpoint, params=params)
        
        # GHL returns slots as a dict with dates as keys
        if result and isinstance(result, dict):
            slots = []
            for date_key, date_data in result.items():
                if date_key == "traceId":  # Skip traceId field
                    continue
                if isinstance(date_data, dict) and "slots" in date_data:
                    for slot_time in date_data["slots"]:
                        # Parse the slot time and create a 1-hour duration
                        # GHL returns ISO format with timezone
                        start = datetime.fromisoformat(slot_time)
                        end = start + timedelta(hours=1)
                        slots.append({
                            "startTime": start,
                            "endTime": end,
                            "available": True
                        })
            logger.info(f"Found {len(slots)} total slots from GHL")
            return slots
        elif result and isinstance(result, list):
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
        logger.info(f"📞 GHL CREATE_APPOINTMENT API CALLED!")
        logger.info(f"  - contact_id: {contact_id}")
        logger.info(f"  - start_time: {start_time}")
        logger.info(f"  - end_time: {end_time}")
        logger.info(f"  - title: {title}")
        
        # GHL uses calendars/events/appointments endpoint
        endpoint = "/calendars/events/appointments"
        
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
        
        logger.info(f"📜 GHL API Request Data: {data}")
        
        result = await self._make_request("POST", endpoint, data=data)
        
        logger.info(f"📝 GHL API Response: {result}")
        
        if result:
            logger.info(
                f"✅ Appointment created for {contact_id} at {start_time}"
            )
            return result
        else:
            logger.error(f"❌ Failed to create appointment for {contact_id}")
            return None
    
    async def get_calendar_slots(
        self,
        start_date: datetime,
        end_date: datetime,
        timezone: str = "America/New_York"
    ) -> List[Dict[str, Any]]:
        """
        Get available calendar slots
        
        Note: This endpoint might not be available in all GHL accounts.
        If it fails, we'll use generated slots instead.
        """
        endpoint = f"/calendars/{self.calendar_id}/free-slots"
        
        params = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "timezone": timezone
        }
        
        try:
            result = await self._make_request("GET", endpoint, params=params)
            if result and isinstance(result, list):
                logger.info(f"Found {len(result)} available slots")
                return result
            else:
                logger.warning("No slots returned from API, using generated slots")
                return []
        except Exception as e:
            logger.warning(f"Calendar slots API not available: {str(e)}")
            return []
    
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
    
    async def verify_connection(self) -> bool:
        """Verify GHL API connection for health checks"""
        try:
            # Simple API call to verify connection
            result = await self._make_request("GET", f"/locations/{self.location_id}")
            return result is not None
        except Exception:
            return False
    
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        now = datetime.now()
        window_duration = (now - self._request_window_start).total_seconds()
        
        return {
            "requests_made": self._request_count,
            "window_duration_seconds": window_duration,
            "rate_limited": self._rate_limit_reset is not None and self._rate_limit_reset > now,
            "reset_time": self._rate_limit_reset.isoformat() if self._rate_limit_reset else None,
            "requests_per_minute": (self._request_count / window_duration * 60) if window_duration > 0 else 0
        }
    
    async def batch_update_custom_fields(
        self,
        updates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Batch update custom fields for multiple contacts
        Uses Python 3.13 TaskGroup for parallel execution
        
        Args:
            updates: List of dicts with contact_id and custom_fields
            
        Returns:
            List of results
        """
        results = []
        
        try:
            # Use TaskGroup for parallel updates
            async with asyncio.TaskGroup() as tg:
                tasks = []
                for update in updates:
                    task = tg.create_task(
                        self.update_custom_fields(
                            update["contact_id"],
                            update["custom_fields"]
                        )
                    )
                    tasks.append((update["contact_id"], task))
            
            # Collect results
            for contact_id, task in tasks:
                try:
                    result = task.result()
                    results.append({
                        "contact_id": contact_id,
                        "success": result is not None,
                        "result": result
                    })
                except Exception as e:
                    results.append({
                        "contact_id": contact_id,
                        "success": False,
                        "error": str(e)
                    })
                    
        except Exception as e:
            logger.error(f"Batch update failed: {e}")
            
        return results


    async def get_conversations(self, contact_id: str) -> Optional[List[Dict]]:
        """
        Get conversations for a contact
        
        Args:
            contact_id: Contact ID
            
        Returns:
            List of conversations or empty list
        """
        params = {
            "locationId": self.location_id,
            "contactId": contact_id
        }
        
        endpoint = "/conversations/search"
        result = await self._make_request("GET", endpoint, params=params)
        
        if result and "conversations" in result:
            return result["conversations"]
        return []
    
    async def get_conversation_messages(self, conversation_id: str) -> Optional[List[Dict]]:
        """
        Get messages from a specific conversation
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            List of messages or empty list
        """
        endpoint = f"/conversations/{conversation_id}/messages"
        result = await self._make_request("GET", endpoint)
        
        # Handle nested structure: result['messages']['messages']
        if result and "messages" in result:
            messages_data = result["messages"]
            # Check if it's the nested structure
            if isinstance(messages_data, dict) and "messages" in messages_data:
                return messages_data["messages"]
            # Fall back to direct list if structure is different
            elif isinstance(messages_data, list):
                return messages_data
        return []
    
    async def add_tags(self, contact_id: str, tags: List[str]) -> Optional[Dict]:
        """
        Add tags to a contact
        
        Args:
            contact_id: Contact ID
            tags: List of tags to add
            
        Returns:
            Updated contact or None
        """
        endpoint = f"/contacts/{contact_id}"
        data = {
            "tags": tags
        }
        
        return await self._make_request("PUT", endpoint, data=data)


# Create singleton instance
ghl_client = GHLClient()