"""
Message Batcher - Aggregates rapid-fire messages to appear more human
Prevents bot-like behavior of responding to each message individually
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import redis.asyncio as redis
from app.config import get_settings
from app.utils.simple_logger import get_logger

logger = get_logger("message_batcher")


class MessageBatcher:
    """
    Batches incoming messages from the same contact to prevent rapid responses
    Uses Redis for distributed locking and state management
    """
    
    def __init__(
        self,
        batch_window_seconds: int = 15,  # Wait 15 seconds for more messages
        max_batch_size: int = 10,        # Process after 10 messages regardless
        redis_url: Optional[str] = None
    ):
        self.batch_window = timedelta(seconds=batch_window_seconds)
        self.max_batch_size = max_batch_size
        self.redis_url = redis_url or get_settings().redis_url
        self._redis_client = None
        self._local_batches = defaultdict(list)  # Fallback if Redis unavailable
        
    async def get_redis(self) -> Optional[redis.Redis]:
        """Get or create Redis connection"""
        if self._redis_client is None and self.redis_url:
            try:
                self._redis_client = redis.from_url(
                    self.redis_url,
                    decode_responses=True
                )
                await self._redis_client.ping()
                logger.info("Connected to Redis for message batching")
            except Exception as e:
                logger.warning(f"Redis not available for batching: {e}")
                self._redis_client = None
                
        return self._redis_client
    
    async def add_message(
        self,
        contact_id: str,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add a message to the batch for a contact
        
        Returns:
            {
                "should_process": bool,  # Whether to process now
                "messages": List[Dict],  # All batched messages if should_process
                "wait_time": int,       # Seconds to wait if not processing
                "batch_id": str        # Unique batch identifier
            }
        """
        timestamp = datetime.now()
        message["batched_at"] = timestamp.isoformat()
        
        # Try Redis first
        redis_client = await self.get_redis()
        if redis_client:
            return await self._add_message_redis(
                redis_client, contact_id, message, timestamp
            )
        else:
            return await self._add_message_local(
                contact_id, message, timestamp
            )
    
    async def _add_message_redis(
        self,
        redis_client: redis.Redis,
        contact_id: str,
        message: Dict[str, Any],
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Add message using Redis for distributed batching"""
        batch_key = f"msg_batch:{contact_id}"
        lock_key = f"msg_lock:{contact_id}"
        timer_key = f"msg_timer:{contact_id}"
        
        # Acquire lock to prevent race conditions
        async with redis_client.lock(lock_key, timeout=5):
            # Get current batch
            batch_data = await redis_client.get(batch_key)
            if batch_data:
                import json
                messages = json.loads(batch_data)
            else:
                messages = []
            
            # Add new message
            messages.append(message)
            
            # Check if we should process now
            should_process = False
            wait_time = self.batch_window.seconds
            
            # Get first message time
            first_msg_time = await redis_client.get(timer_key)
            if not first_msg_time:
                # First message in batch
                await redis_client.setex(
                    timer_key,
                    self.batch_window.seconds,
                    timestamp.isoformat()
                )
                first_msg_time = timestamp
            else:
                first_msg_time = datetime.fromisoformat(first_msg_time)
            
            # Check conditions
            time_elapsed = timestamp - first_msg_time
            
            if len(messages) >= self.max_batch_size:
                # Max messages reached
                should_process = True
                logger.info(f"Batch full for {contact_id}: {len(messages)} messages")
            elif time_elapsed >= self.batch_window:
                # Time window expired
                should_process = True
                logger.info(f"Batch timer expired for {contact_id}: {time_elapsed.seconds}s")
            else:
                # Still waiting
                wait_time = int((self.batch_window - time_elapsed).total_seconds())
                
            if should_process:
                # Clear batch and return messages
                await redis_client.delete(batch_key, timer_key)
                batch_id = f"{contact_id}:{timestamp.timestamp()}"
                
                return {
                    "should_process": True,
                    "messages": messages,
                    "wait_time": 0,
                    "batch_id": batch_id
                }
            else:
                # Save updated batch
                import json
                await redis_client.setex(
                    batch_key,
                    self.batch_window.seconds,
                    json.dumps(messages)
                )
                
                return {
                    "should_process": False,
                    "messages": [],
                    "wait_time": wait_time,
                    "batch_id": None
                }
    
    async def _add_message_local(
        self,
        contact_id: str,
        message: Dict[str, Any],
        timestamp: datetime
    ) -> Dict[str, Any]:
        """Fallback local batching if Redis unavailable"""
        batch = self._local_batches[contact_id]
        
        # Add message with metadata
        if not batch:
            message["first_in_batch"] = True
            message["batch_started"] = timestamp.isoformat()
        batch.append(message)
        
        # Check if should process
        first_msg_time = datetime.fromisoformat(batch[0]["batched_at"])
        time_elapsed = timestamp - first_msg_time
        
        if len(batch) >= self.max_batch_size or time_elapsed >= self.batch_window:
            # Process batch
            messages = batch.copy()
            self._local_batches[contact_id] = []
            
            return {
                "should_process": True,
                "messages": messages,
                "wait_time": 0,
                "batch_id": f"{contact_id}:{timestamp.timestamp()}"
            }
        else:
            # Keep batching
            wait_time = int((self.batch_window - time_elapsed).total_seconds())
            return {
                "should_process": False,
                "messages": [],
                "wait_time": wait_time,
                "batch_id": None
            }
    
    async def force_process(self, contact_id: str) -> List[Dict[str, Any]]:
        """Force process any pending messages for a contact"""
        redis_client = await self.get_redis()
        
        if redis_client:
            batch_key = f"msg_batch:{contact_id}"
            batch_data = await redis_client.get(batch_key)
            if batch_data:
                import json
                messages = json.loads(batch_data)
                await redis_client.delete(
                    batch_key,
                    f"msg_timer:{contact_id}"
                )
                return messages
        else:
            messages = self._local_batches.get(contact_id, [])
            self._local_batches[contact_id] = []
            return messages
        
        return []
    
    def merge_messages(self, messages: List[Dict[str, Any]]) -> str:
        """
        Merge multiple messages into a single coherent message
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Combined message text
        """
        if not messages:
            return ""
        
        if len(messages) == 1:
            return messages[0].get("message", "")
        
        # Extract text from each message
        texts = []
        for msg in messages:
            text = msg.get("message", "").strip()
            if text:
                texts.append(text)
        
        # Smart merging based on patterns
        merged = self._smart_merge(texts)
        
        logger.info(
            f"Merged {len(messages)} messages: "
            f"{[m.get('message')[:20] + '...' for m in messages]} → "
            f"{merged[:50]}..."
        )
        
        return merged
    
    def _smart_merge(self, texts: List[str]) -> str:
        """
        Intelligently merge message texts
        
        Handles cases like:
        - "Hi" + "My name is John" → "Hi, my name is John"
        - "I have a restaurant" + "Italian food" → "I have a restaurant, Italian food"
        - "300" + "per month" → "300 per month"
        """
        if not texts:
            return ""
        
        if len(texts) == 1:
            return texts[0]
        
        merged_parts = []
        
        for i, text in enumerate(texts):
            # Clean the text
            text = text.strip()
            
            if i == 0:
                # First message
                merged_parts.append(text)
            else:
                prev_text = merged_parts[-1] if merged_parts else ""
                
                # Check if this completes previous message
                if self._is_continuation(prev_text, text):
                    # Direct continuation
                    if prev_text and not prev_text[-1] in '.!?':
                        merged_parts[-1] = f"{prev_text} {text}"
                    else:
                        merged_parts.append(text)
                else:
                    # New sentence/thought
                    if prev_text and not prev_text[-1] in '.!?,':
                        merged_parts[-1] = f"{prev_text}. {text}"
                    else:
                        merged_parts.append(text)
        
        # Join all parts
        result = " ".join(merged_parts)
        
        # Clean up spacing
        result = " ".join(result.split())
        
        return result
    
    def _is_continuation(self, prev: str, curr: str) -> bool:
        """Check if current text continues previous text"""
        # Lowercase for comparison
        prev_lower = prev.lower()
        curr_lower = curr.lower()
        
        # Clear continuations
        continuations = [
            # Name patterns
            ("mi nombre es", curr_lower),
            ("me llamo", curr_lower),
            ("soy", curr_lower.split()[0] if curr_lower else ""),
            
            # Budget patterns
            (prev_lower.endswith("$"), True),
            (prev_lower[-3:].isdigit(), curr_lower.startswith(("al mes", "mensuales", "por mes"))),
            
            # Business patterns
            ("tengo un", curr_lower),
            ("tengo una", curr_lower),
            
            # Time patterns
            (prev_lower.endswith(("a las", "el")), curr_lower[:2].isdigit()),
        ]
        
        for pattern, condition in continuations:
            if isinstance(condition, str):
                if prev_lower.endswith(pattern):
                    return True
            elif condition:
                if pattern in prev_lower:
                    return True
        
        # Check if current starts with lowercase (likely continuation)
        if curr and curr[0].islower() and not curr_lower.startswith(("hola", "si", "no", "ok")):
            return True
        
        return False


# Singleton instance
message_batcher = MessageBatcher()


async def process_with_batching(
    contact_id: str,
    message: Dict[str, Any],
    process_callback: Any
) -> Dict[str, Any]:
    """
    Helper function to process messages with batching
    
    Args:
        contact_id: Contact identifier
        message: Incoming message data
        process_callback: Async function to call when batch is ready
        
    Returns:
        Batch status information
    """
    # Add message to batch
    batch_result = await message_batcher.add_message(contact_id, message)
    
    if batch_result["should_process"]:
        # Merge messages
        merged_message = message_batcher.merge_messages(batch_result["messages"])
        
        # Update message with merged content
        message["message"] = merged_message
        message["is_batch"] = True
        message["batch_size"] = len(batch_result["messages"])
        message["batch_id"] = batch_result["batch_id"]
        
        # Process the batch
        await process_callback(message)
        
        return {
            "status": "processed",
            "batch_id": batch_result["batch_id"],
            "message_count": len(batch_result["messages"])
        }
    else:
        # Still batching
        logger.info(
            f"Batching message for {contact_id}, "
            f"waiting {batch_result['wait_time']}s more"
        )
        
        # Schedule future processing
        asyncio.create_task(_delayed_processing(
            contact_id,
            batch_result["wait_time"],
            process_callback
        ))
        
        return {
            "status": "batching",
            "wait_time": batch_result["wait_time"]
        }


async def _delayed_processing(
    contact_id: str,
    wait_seconds: int,
    process_callback: Any
):
    """Handle delayed batch processing"""
    await asyncio.sleep(wait_seconds)
    
    # Force process any remaining messages
    messages = await message_batcher.force_process(contact_id)
    if messages:
        merged_message = message_batcher.merge_messages(messages)
        
        # Create batch message
        batch_message = {
            "contact_id": contact_id,
            "message": merged_message,
            "is_batch": True,
            "batch_size": len(messages),
            "batch_id": f"{contact_id}:{datetime.now().timestamp()}"
        }
        
        await process_callback(batch_message)


__all__ = [
    "MessageBatcher",
    "message_batcher",
    "process_with_batching"
]