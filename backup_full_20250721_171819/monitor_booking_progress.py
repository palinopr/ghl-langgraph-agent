#!/usr/bin/env python3
"""
Monitor appointment booking progress in real-time
"""
import asyncio
import sys
sys.path.append('.')

from app.tools.ghl_client import GHLClient
from app.config import get_settings
from datetime import datetime
import json

class BookingProgressMonitor:
    """Monitor the progress of appointment booking"""
    
    def __init__(self, contact_id: str):
        self.contact_id = contact_id
        self.ghl_client = GHLClient()
        self.settings = get_settings()
        self.previous_score = 0
        self.previous_agent = None
        
    async def check_progress(self):
        """Check current progress"""
        try:
            # Get contact details
            contact = await self.ghl_client.get_contact(self.contact_id)
            if not contact:
                print("❌ Contact not found")
                return None
                
            # Get custom fields
            custom_fields = contact.get('customFields', {})
            
            # Extract key data
            current_data = {
                'name': contact.get('contactName', 'Unknown'),
                'phone': contact.get('phone', 'N/A'),
                'score': custom_fields.get('score', 0),
                'business_type': custom_fields.get('business_type'),
                'budget': custom_fields.get('budget'),
                'goal': custom_fields.get('goal'),
                'current_agent': custom_fields.get('current_agent', 'unknown'),
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            
            # Get recent messages
            conversations = await self.ghl_client.get_conversations(self.contact_id)
            if conversations:
                conv_id = conversations[0].get('id')
                messages = await self.ghl_client.get_conversation_messages(
                    self.contact_id, 
                    conv_id, 
                    limit=5
                )
                
                if messages:
                    recent_messages = []
                    for msg in messages[:3]:  # Last 3 messages
                        direction = "👤" if msg.get('direction') == 'inbound' else "🤖"
                        content = msg.get('body', '')[:80] + "..."
                        recent_messages.append(f"{direction} {content}")
                    current_data['recent_messages'] = recent_messages
            
            return current_data
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return None
    
    async def monitor_live(self, interval: int = 2):
        """Monitor progress in real-time"""
        print("\n" + "="*80)
        print("🔍 LIVE APPOINTMENT BOOKING MONITOR")
        print("="*80)
        print(f"Contact ID: {self.contact_id}")
        print("Press Ctrl+C to stop monitoring")
        print("="*80)
        
        while True:
            try:
                data = await self.check_progress()
                if data:
                    # Clear screen for better display
                    print("\033[H\033[J", end='')  # Clear screen
                    
                    print("="*80)
                    print(f"⏰ {data['timestamp']} - BOOKING PROGRESS MONITOR")
                    print("="*80)
                    
                    # Contact info
                    print(f"\n📱 Contact: {data['name']} ({data['phone']})")
                    
                    # Score progress bar
                    score = int(data.get('score', 0))
                    progress = "█" * score + "░" * (10 - score)
                    print(f"\n📊 Score Progress: [{progress}] {score}/10")
                    
                    # Score change detection
                    if score > self.previous_score:
                        print(f"   ⬆️  Score increased from {self.previous_score} → {score}")
                    self.previous_score = score
                    
                    # Current stage
                    agent = data.get('current_agent', 'unknown')
                    stage = self.get_stage(score, agent)
                    print(f"\n🎯 Current Stage: {stage}")
                    
                    # Agent change detection
                    if agent != self.previous_agent and self.previous_agent:
                        print(f"   🔄 Agent changed: {self.previous_agent} → {agent}")
                    self.previous_agent = agent
                    
                    # Collected data
                    print(f"\n📋 Collected Data:")
                    print(f"   • Name: {data.get('name', 'Not collected')}")
                    print(f"   • Business: {data.get('business_type', 'Not collected')}")
                    print(f"   • Budget: {data.get('budget', 'Not collected')}")
                    print(f"   • Goal: {data.get('goal', 'Not collected')}")
                    
                    # Recent messages
                    if 'recent_messages' in data:
                        print(f"\n💬 Recent Messages:")
                        for msg in data['recent_messages']:
                            print(f"   {msg}")
                    
                    # Appointment status
                    if score >= 8:
                        print(f"\n🎉 READY FOR APPOINTMENT BOOKING!")
                        if score == 10:
                            print("   ✅ APPOINTMENT BOOKED!")
                    
                    print("\n" + "="*80)
                
                await asyncio.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n\n👋 Monitoring stopped")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
                await asyncio.sleep(interval)
    
    def get_stage(self, score: int, agent: str) -> str:
        """Determine current stage based on score and agent"""
        if score >= 10:
            return "✅ APPOINTMENT CONFIRMED"
        elif score >= 9:
            return "📅 Selecting appointment time (Sofia)"
        elif score >= 8:
            return "🔥 Hot lead - Ready for appointment (Sofia)"
        elif score >= 5:
            return "🌡️ Warm lead - Qualifying (Carlos)"
        elif score >= 3:
            return "❄️ Cold lead - Gathering info (Maria)"
        else:
            return "👋 Initial contact (Maria)"

async def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        contact_id = sys.argv[1]
    else:
        contact_id = "ZPEl0zWM38GqLjOxxRCW"  # Default from traces
    
    monitor = BookingProgressMonitor(contact_id)
    await monitor.monitor_live()

if __name__ == "__main__":
    asyncio.run(main())