"""
Webhook deduplication to prevent double message processing
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib
import json
from app.utils.simple_logger import get_logger

logger = get_logger("webhook_dedup")


class WebhookDeduplicator:
    """
    Simple in-memory deduplication for webhooks
    Prevents processing the same message multiple times
    """
    
    def __init__(self, ttl_seconds: int = 60):
        """
        Initialize deduplicator
        
        Args:
            ttl_seconds: How long to remember processed messages
        """
        self.processed_messages: Dict[str, datetime] = {}
        self.ttl_seconds = ttl_seconds
        
    def _cleanup_old_entries(self):
        """Remove entries older than TTL"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.ttl_seconds)
        
        # Remove old entries
        to_remove = [
            key for key, timestamp in self.processed_messages.items()
            if timestamp < cutoff
        ]
        
        for key in to_remove:
            del self.processed_messages[key]
            
    def _generate_message_key(self, webhook_data: Dict) -> str:
        """
        Generate unique key for webhook message
        
        Args:
            webhook_data: Webhook payload
            
        Returns:
            Unique message key
        """
        # Use contact ID + message + timestamp (rounded to second)
        key_parts = [
            webhook_data.get("contactId", ""),
            webhook_data.get("id", ""),  # GHL contact ID
            webhook_data.get("message", ""),
            # Round timestamp to nearest second to handle minor variations
            str(int(webhook_data.get("timestamp", datetime.now().timestamp())))
        ]
        
        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
        
    def is_duplicate(self, webhook_data: Dict) -> bool:
        """
        Check if this webhook has been processed recently
        
        Args:
            webhook_data: Webhook payload
            
        Returns:
            True if duplicate, False if new
        """
        # Cleanup old entries
        self._cleanup_old_entries()
        
        # Generate key
        message_key = self._generate_message_key(webhook_data)
        
        # Check if already processed
        if message_key in self.processed_messages:
            logger.warning(
                f"Duplicate webhook detected for contact {webhook_data.get('contactId')}. "
                f"Message: {webhook_data.get('message', '')[:50]}..."
            )
            return True
            
        # Mark as processed
        self.processed_messages[message_key] = datetime.now()
        logger.info(
            f"New webhook processed for contact {webhook_data.get('contactId')}. "
            f"Cache size: {len(self.processed_messages)}"
        )
        
        return False


# Global deduplicator instance
webhook_deduplicator = WebhookDeduplicator(ttl_seconds=60)


def is_duplicate_webhook(webhook_data: Dict) -> bool:
    """
    Check if webhook is a duplicate
    
    Args:
        webhook_data: Webhook payload
        
    Returns:
        True if duplicate, False if new
    """
    return webhook_deduplicator.is_duplicate(webhook_data)