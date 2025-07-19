#!/usr/bin/env python3
"""
Simple test to check if appointment booking is working
"""
import os
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables manually from .env file
env_file = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_file):
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Disable tracing to avoid import issues
os.environ['ENABLE_LANGSMITH_TRACING'] = 'false'

async def test_appointment_creation():
    """Test if GHL API is configured and working"""
    
    print("\n🔍 TESTING GHL APPOINTMENT CREATION")
    print("="*60)
    
    # Check environment variables
    print("\n📋 Checking environment variables:")
    calendar_id = os.getenv('GHL_CALENDAR_ID')
    location_id = os.getenv('GHL_LOCATION_ID')
    assigned_user = os.getenv('GHL_ASSIGNED_USER_ID')
    api_token = os.getenv('GHL_API_TOKEN')
    
    print(f"  - GHL_CALENDAR_ID: {'✅ Set' if calendar_id else '❌ Missing'}")
    print(f"  - GHL_LOCATION_ID: {'✅ Set' if location_id else '❌ Missing'}")
    print(f"  - GHL_ASSIGNED_USER_ID: {'✅ Set' if assigned_user else '❌ Missing'}")
    print(f"  - GHL_API_TOKEN: {'✅ Set' if api_token else '❌ Missing'}")
    
    if not all([calendar_id, location_id, assigned_user, api_token]):
        print("\n❌ Missing required environment variables!")
        print("Please set all GHL environment variables in .env file")
        return
    
    # Test direct API call
    print("\n📞 Testing direct GHL API call...")
    
    from app.tools.ghl_client import ghl_client
    from datetime import datetime, timedelta
    import pytz
    
    # Create test appointment for tomorrow
    tz = pytz.timezone("America/New_York")
    tomorrow = datetime.now(tz) + timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
    end_time = start_time + timedelta(hours=1)
    
    print(f"\n📅 Creating test appointment:")
    print(f"  - Contact: z49hFQn0DxOX5sInJg60")
    print(f"  - Start: {start_time}")
    print(f"  - End: {end_time}")
    
    try:
        result = await ghl_client.create_appointment(
            contact_id="z49hFQn0DxOX5sInJg60",
            start_time=start_time,
            end_time=end_time,
            title="TEST - WhatsApp Automation Demo",
            timezone="America/New_York"
        )
        
        print(f"\n📊 Result: {result}")
        
        if result:
            print("\n✅ Appointment created successfully!")
            print(f"Appointment ID: {result.get('id', 'Unknown')}")
        else:
            print("\n❌ Failed to create appointment - check logs above")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 DIRECT GHL APPOINTMENT CREATION TEST")
    print("This tests if we can create appointments directly in GHL")
    
    asyncio.run(test_appointment_creation())