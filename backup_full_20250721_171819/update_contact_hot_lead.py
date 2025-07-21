#!/usr/bin/env python3
"""
Update existing contact to be a hot lead ready for appointment
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv
from app.utils.simple_logger import get_logger

# Load environment
load_dotenv()

logger = get_logger("update_contact")

# Configuration
GHL_API_TOKEN = os.getenv("GHL_API_TOKEN")
GHL_LOCATION_ID = os.getenv("GHL_LOCATION_ID")
BASE_URL = "https://services.leadconnectorhq.com"

# Headers for GHL API
HEADERS = {
    "Authorization": f"Bearer {GHL_API_TOKEN}",
    "Version": "2021-07-28",
    "Content-Type": "application/json"
}

# Contact to update
CONTACT_ID = "Emp7UWc546yDMiWVEzKF"


async def update_to_hot_lead():
    """Update contact to be a hot lead"""
    logger.info("\n" + "="*60)
    logger.info("UPDATING CONTACT TO HOT LEAD")
    logger.info("="*60)
    
    # Update data
    update_data = {
        "customFields": [
            {"id": "wAPjuqxtfgKLCJqahjo1", "value": "10"},  # Score
            {"id": "TjB0I5iNfVwx3zyxZ9sW", "value": "Diego Fernandez"},  # Name
            {"id": "HtoheVc48qvAfvRUKhfG", "value": "restaurante"},  # Business
            {"id": "r7jFiJBYHiEllsGn7jZC", "value": "automatizar reservas"},  # Goal
            {"id": "4Qe8P25JRLW0IcZc5iOs", "value": "500"},  # Budget
            {"id": "Q1n5kaciimUU6JN5PBD6", "value": "LISTO_COMPRAR"},  # Intent
            {"id": "dXasgCZFgqd62psjw7nd", "value": "ALTA"}  # Urgency
        ],
        "tags": ["hot-lead", "qualified", "restaurant", "appointment-ready"],
        "name": "Diego Fernandez",
        "firstName": "Diego", 
        "lastName": "Fernandez",
        "email": "diego@restaurant.com"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                f"{BASE_URL}/contacts/{CONTACT_ID}",
                headers=HEADERS,
                json=update_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                logger.info(f"\n✅ Contact updated successfully!")
                logger.info(f"   ID: {CONTACT_ID}")
                logger.info(f"   Name: Diego Fernandez")
                logger.info(f"   Score: 10 (HOT)")
                logger.info(f"   Business: restaurante")
                logger.info(f"   Budget: $500")
                logger.info(f"   Intent: LISTO_COMPRAR")
                logger.info(f"   Tags: hot-lead, qualified")
                
                return True
            else:
                logger.error(f"Failed to update: {response.status_code}")
                logger.error(response.text)
                return False
                
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return False


async def main():
    """Update contact"""
    logger.info("\n" + "🔧"*20)
    logger.info("UPDATE CONTACT TO HOT LEAD")
    logger.info("🔧"*20)
    
    success = await update_to_hot_lead()
    
    if success:
        logger.info("\n✅ Contact is now a HOT LEAD!")
        logger.info(f"Ready for appointment booking test")
        logger.info(f"GHL: https://app.gohighlevel.com/location/{GHL_LOCATION_ID}/contacts/{CONTACT_ID}")


if __name__ == "__main__":
    asyncio.run(main())