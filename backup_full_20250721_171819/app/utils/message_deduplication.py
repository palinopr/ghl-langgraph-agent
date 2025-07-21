"""
Message Deduplication System
Prevents sending duplicate messages to GHL
"""
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
import hashlib
from app.utils.simple_logger import get_logger

logger = get_logger("message_deduplication")


class MessageDeduplicator:
    """
    Tracks sent messages to prevent duplicates.
    Uses in-memory cache with TTL for sent message hashes.
    """
    
    def __init__(self, ttl_minutes: int = 30):
        self.sent_messages: Dict[str, datetime] = {}  # hash -> timestamp
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _generate_hash(self, contact_id: str, message: str) -> str:
        """Generate unique hash for contact + message combination"""
        content = f"{contact_id}:{message}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()[:16]
    
    def _cleanup_old_entries(self):
        """Remove entries older than TTL"""
        now = datetime.now()
        expired = [
            hash_key for hash_key, timestamp in self.sent_messages.items()
            if now - timestamp > self.ttl
        ]
        for hash_key in expired:
            del self.sent_messages[hash_key]
    
    def is_duplicate(self, contact_id: str, message: str) -> bool:
        """
        Check if this message was already sent recently.
        
        Args:
            contact_id: The contact ID
            message: The message content
            
        Returns:
            True if duplicate (already sent), False if new
        """
        # Cleanup old entries periodically
        self._cleanup_old_entries()
        
        # Generate hash
        msg_hash = self._generate_hash(contact_id, message)
        
        # Check if exists
        if msg_hash in self.sent_messages:
            logger.warning(f"Duplicate message detected for contact {contact_id}: {message[:50]}...")
            return True
        
        return False
    
    def mark_sent(self, contact_id: str, message: str):
        """
        Mark a message as sent to prevent future duplicates.
        
        Args:
            contact_id: The contact ID
            message: The message content
        """
        msg_hash = self._generate_hash(contact_id, message)
        self.sent_messages[msg_hash] = datetime.now()
        logger.info(f"Marked message as sent for contact {contact_id}")
    
    def clear_contact(self, contact_id: str):
        """Clear all sent messages for a specific contact"""
        # This would need to iterate through all hashes
        # For now, just log
        logger.info(f"Would clear messages for contact {contact_id}")
    
    def get_stats(self) -> Dict[str, int]:
        """Get deduplication statistics"""
        self._cleanup_old_entries()
        return {
            "tracked_messages": len(self.sent_messages),
            "ttl_minutes": self.ttl.total_seconds() / 60
        }


# Global instance
_deduplicator = MessageDeduplicator()


def is_duplicate_message(contact_id: str, message: str) -> bool:
    """Check if message is a duplicate"""
    return _deduplicator.is_duplicate(contact_id, message)


def mark_message_sent(contact_id: str, message: str):
    """Mark message as sent"""
    _deduplicator.mark_sent(contact_id, message)


def get_dedup_stats() -> Dict[str, int]:
    """Get deduplication statistics"""
    return _deduplicator.get_stats()