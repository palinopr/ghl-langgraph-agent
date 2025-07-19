#!/usr/bin/env python3
"""
Check the results of the live test - contact status and custom fields
"""
import asyncio
from app.tools.ghl_client import ghl_client
from app.utils.simple_logger import get_logger

logger = get_logger("check_results")

async def check_contact_status(contact_id: str = "XinFGydeogXoZamVtZly"):
    """Check the current status of our test contact"""
    
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 CHECKING CONTACT STATUS: {contact_id}")
    logger.info(f"{'='*60}")
    
    # Get contact details
    contact = await ghl_client.get_contact_details(contact_id)
    
    if not contact:
        logger.error("❌ Contact not found!")
        return
    
    # Basic info
    logger.info("\n📋 Contact Information:")
    logger.info(f"  • Name: {contact.get('name', 'Not set')}")
    logger.info(f"  • Email: {contact.get('email', 'Not set')}")
    logger.info(f"  • Phone: {contact.get('phone', 'Not set')}")
    logger.info(f"  • Tags: {', '.join(contact.get('tags', []))}")
    
    # Custom fields
    logger.info("\n📊 Custom Fields:")
    if "customFields" in contact:
        field_map = {
            "wAPjuqxtfgKLCJqahjo1": "Lead Score",
            "Q1n5kaciimUU6JN5PBD6": "Intent",
            "HtoheVc48qvAfvRUKhfG": "Business Type",
            "4Qe8P25JRLW0IcZc5iOs": "Budget",
            "TjB0I5iNfVwx3zyxZ9sW": "Name",
            "r7jFiJBYHiEllsGn7jZC": "Goal",
            "dXasgCZFgqd62psjw7nd": "Urgency",
            "D1aD9KUDNm5Lp4Kz8yAD": "Preferred Day",
            "M70lUtadchW4f2pJGDJ5": "Preferred Time"
        }
        
        for field in contact["customFields"]:
            field_id = field.get("id", "")
            value = field.get("value")
            if value:  # Only show fields with values
                field_name = field_map.get(field_id, field_id)
                logger.info(f"  • {field_name}: {value}")
    
    # Get recent messages
    logger.info("\n💬 Recent Conversation:")
    conversations = await ghl_client.get_conversations(contact_id)
    
    if conversations and "conversations" in conversations:
        for conv in conversations["conversations"][:1]:  # Just the latest conversation
            conv_id = conv.get("id")
            messages = await ghl_client.get_messages(conv_id, limit=10)
            
            if messages and "messages" in messages:
                for msg in messages["messages"][:5]:  # Last 5 messages
                    direction = "→" if msg.get("direction") == "outbound" else "←"
                    body = msg.get("body", "")[:80] + "..." if len(msg.get("body", "")) > 80 else msg.get("body", "")
                    logger.info(f"  {direction} {body}")
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("📈 SUMMARY:")
    
    # Check score
    score = None
    for field in contact.get("customFields", []):
        if field.get("id") == "wAPjuqxtfgKLCJqahjo1":  # Score field
            score = field.get("value")
            break
    
    if score:
        score_int = int(score) if score.isdigit() else 0
        if score_int >= 8:
            logger.info(f"  ✅ HOT LEAD (Score: {score}) - Ready for appointment!")
        elif score_int >= 5:
            logger.info(f"  🟡 WARM LEAD (Score: {score}) - Needs qualification")
        else:
            logger.info(f"  🔵 COLD LEAD (Score: {score}) - Needs nurturing")
    
    logger.info(f"{'='*60}\n")

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from dotenv import load_dotenv
    load_dotenv()
    
    # Check specific contact or use default test contact
    contact_id = sys.argv[1] if len(sys.argv) > 1 else "XinFGydeogXoZamVtZly"
    
    asyncio.run(check_contact_status(contact_id))