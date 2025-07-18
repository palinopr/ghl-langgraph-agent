"""
Webhook processor for GoHighLevel messages
Handles incoming webhooks and formats them for agent processing
"""
from typing import Dict, Any, Optional
from datetime import datetime
import pytz
from ..utils.simple_logger import get_logger

logger = get_logger("webhook_processor")


class WebhookProcessor:
    """Process incoming webhooks from GoHighLevel"""
    
    @staticmethod
    def process_message_webhook(webhook_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process incoming message webhook from GoHighLevel
        
        Args:
            webhook_data: Raw webhook data from GoHighLevel
            
        Returns:
            Formatted MessageData or None if invalid
        """
        try:
            # Extract message details
            message_body = webhook_data.get("body", "")
            contact_id = webhook_data.get("contactId")
            location_id = webhook_data.get("locationId")
            conversation_id = webhook_data.get("conversationId")
            
            if not all([message_body, contact_id, location_id]):
                logger.warning(f"Missing required fields in webhook: {webhook_data}")
                return None
            
            # Extract contact details from webhook
            contact_name = webhook_data.get("contactName", "")
            contact_phone = webhook_data.get("contactPhone", "")
            contact_email = webhook_data.get("contactEmail", "")
            
            # Extract custom fields if present
            custom_fields = {}
            if "customFields" in webhook_data:
                for field in webhook_data["customFields"]:
                    if isinstance(field, dict) and "id" in field:
                        custom_fields[field["id"]] = field.get("value", "")
            
            # Create message data dict
            message_data = {
                "id": webhook_data.get("messageId", ""),
                "contact_id": contact_id,
                "conversation_id": conversation_id,
                "location_id": location_id,
                "message_body": message_body,
                "message_type": webhook_data.get("type", "WhatsApp"),
                "timestamp": datetime.now(pytz.UTC).isoformat(),
                "contact_name": contact_name,
                "contact_phone": contact_phone,
                "contact_email": contact_email,
                "custom_fields": custom_fields,
                "raw_webhook": webhook_data
            }
            
            logger.info(
                f"Processed webhook for contact {contact_id}: {message_body[:50]}..."
            )
            
            return message_data
            
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    def validate_webhook_signature(
        body: bytes, 
        signature: str, 
        secret: str
    ) -> bool:
        """
        Validate webhook signature for security
        
        Args:
            body: Raw webhook body
            signature: Signature from headers
            secret: Webhook secret
            
        Returns:
            True if valid, False otherwise
        """
        import hmac
        import hashlib
        
        try:
            # Calculate expected signature
            expected_sig = hmac.new(
                secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            return hmac.compare_digest(expected_sig, signature)
            
        except Exception as e:
            logger.error(f"Error validating webhook signature: {str(e)}")
            return False


# Create singleton instance
webhook_processor = WebhookProcessor()