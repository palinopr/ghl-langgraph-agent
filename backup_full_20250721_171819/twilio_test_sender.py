#!/usr/bin/env python3
"""
Twilio SMS sender for realistic conversation testing
Sends messages as if they're from real customers to test the GHL webhook
"""
import os
import time
import random
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")  # Your Twilio number

# GHL Configuration
GHL_PHONE_NUMBER = os.getenv("GHL_PHONE_NUMBER")  # The GHL number to send to

# Typing simulation
MIN_TYPING_DELAY = 2.0  # Minimum seconds between messages
MAX_TYPING_DELAY = 8.0  # Maximum seconds between messages
CHARS_PER_SECOND = 35   # Average typing speed


class RealisticSMSSender:
    """Sends SMS messages with realistic timing and patterns"""
    
    def __init__(self):
        """Initialize Twilio client"""
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
            raise ValueError("Missing Twilio credentials. Please set environment variables.")
        
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        self.from_number = TWILIO_PHONE_NUMBER
        self.to_number = GHL_PHONE_NUMBER
        
        if not self.to_number:
            raise ValueError("Missing GHL_PHONE_NUMBER in environment variables")
    
    def calculate_typing_delay(self, message: str) -> float:
        """Calculate realistic typing delay based on message length"""
        # Base delay
        delay = random.uniform(MIN_TYPING_DELAY, MAX_TYPING_DELAY)
        
        # Add time based on message length
        typing_time = len(message) / CHARS_PER_SECOND
        
        # Add thinking time for questions
        if "?" in message:
            delay += random.uniform(1.0, 2.0)
        
        # Total delay
        return delay + typing_time
    
    def send_sms(self, message: str, from_name: Optional[str] = None) -> str:
        """Send a single SMS message"""
        try:
            # Send the message
            sent_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=self.to_number
            )
            
            print(f"📱 Sent: {message}")
            print(f"   SID: {sent_message.sid}")
            print(f"   Status: {sent_message.status}")
            
            return sent_message.sid
            
        except Exception as e:
            print(f"❌ Error sending SMS: {str(e)}")
            return ""
    
    async def send_conversation(self, messages: List[str], persona: Dict[str, str]):
        """Send a conversation with realistic timing"""
        print(f"\n🎭 Starting conversation as: {persona['name']}")
        print(f"📋 Scenario: {persona['scenario']}")
        print("=" * 60)
        
        for i, message in enumerate(messages):
            # Calculate delay (no delay for first message)
            if i > 0:
                delay = self.calculate_typing_delay(message)
                print(f"\n⏳ Waiting {delay:.1f} seconds (typing)...")
                await asyncio.sleep(delay)
            
            # Send the message
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{timestamp}] Sending message {i+1}/{len(messages)}:")
            
            self.send_sms(message, persona['name'])
            
            # Wait a bit after sending
            await asyncio.sleep(1.0)
        
        print(f"\n✅ Conversation complete!")


# Predefined test conversations
CONVERSATIONS = {
    "spanish_restaurant_owner": {
        "persona": {
            "name": "Carlos Mendoza",
            "scenario": "Restaurant owner losing customers, needs help"
        },
        "messages": [
            "Hola, necesito ayuda urgente",
            "Mi nombre es Carlos",
            "Tengo un restaurante",
            "Estoy perdiendo clientes todos los días",
            "Sí, necesito una solución ya",
            "Mi presupuesto es como $500 al mes",
            "Sí, está bien",
            "carlos@mirestaurante.com",
            "Mañana a las 3pm está perfecto"
        ]
    },
    
    "spanish_salon_owner": {
        "persona": {
            "name": "María García", 
            "scenario": "Salon owner wants to automate bookings"
        },
        "messages": [
            "Hola buenas tardes",
            "Me llamo María García",
            "Tengo un salón de belleza",
            "Quiero automatizar las citas de mis clientes",
            "Como unos $300 mensuales puedo pagar",
            "Claro que sí",
            "maria.garcia@salonbelleza.com",
            "El martes a las 10am"
        ]
    },
    
    "spanish_cold_lead": {
        "persona": {
            "name": "Juan Pérez",
            "scenario": "Just exploring options, not ready to buy"
        },
        "messages": [
            "Hola",
            "Juan",
            "Solo estoy viendo opciones",
            "No tengo negocio todavía",
            "Tal vez más adelante",
            "Gracias"
        ]
    },
    
    "returning_customer": {
        "persona": {
            "name": "Sofia Rodríguez",
            "scenario": "Previous customer coming back"
        },
        "messages": [
            "Hola, hablamos la semana pasada",
            "Soy Sofia, del restaurante El Jardín",
            "Ya estoy lista para empezar",
            "Sí, los $400 mensuales que hablamos",
            "Cuando podemos agendar la cita?"
        ]
    },
    
    "english_speaker": {
        "persona": {
            "name": "John Smith",
            "scenario": "English speaker to test language detection"
        },
        "messages": [
            "Hi there",
            "My name is John",
            "I have a small business",
            "I need help with marketing",
            "What's the cost?",
            "Sounds good",
            "john@business.com"
        ]
    }
}


def simulate_phone_number() -> str:
    """Generate a realistic phone number for testing"""
    # Format: +1 (555) XXX-XXXX
    area = random.randint(200, 999)
    prefix = random.randint(200, 999)
    line = random.randint(1000, 9999)
    return f"+1{area}{prefix}{line}"


async def main():
    """Main function to run the SMS sender"""
    print("🚀 Twilio SMS Test Sender for GHL")
    print("=" * 60)
    
    # Check configuration
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, GHL_PHONE_NUMBER]):
        print("❌ Missing configuration. Please set these environment variables:")
        print("   - TWILIO_ACCOUNT_SID")
        print("   - TWILIO_AUTH_TOKEN")
        print("   - TWILIO_PHONE_NUMBER (your Twilio number)")
        print("   - GHL_PHONE_NUMBER (the GHL number to send to)")
        return
    
    print(f"📱 From: {TWILIO_PHONE_NUMBER}")
    print(f"📱 To: {GHL_PHONE_NUMBER}")
    print()
    
    # Create sender
    sender = RealisticSMSSender()
    
    # Show conversation options
    print("Available conversations:")
    for i, (key, conv) in enumerate(CONVERSATIONS.items(), 1):
        print(f"{i}. {conv['persona']['name']} - {conv['persona']['scenario']}")
    
    print(f"{len(CONVERSATIONS) + 1}. Send custom message")
    print(f"{len(CONVERSATIONS) + 2}. Run all conversations (with delays)")
    
    # Get user choice
    choice = input(f"\nSelect conversation (1-{len(CONVERSATIONS) + 2}): ")
    
    try:
        choice_num = int(choice)
        
        if choice_num == len(CONVERSATIONS) + 1:
            # Custom message
            message = input("Enter your message: ")
            sender.send_sms(message)
            
        elif choice_num == len(CONVERSATIONS) + 2:
            # Run all conversations
            for key, conv in CONVERSATIONS.items():
                await sender.send_conversation(conv['messages'], conv['persona'])
                
                # Wait between conversations
                if key != list(CONVERSATIONS.keys())[-1]:
                    wait_time = random.randint(30, 60)
                    print(f"\n⏰ Waiting {wait_time} seconds before next conversation...")
                    await asyncio.sleep(wait_time)
        
        elif 1 <= choice_num <= len(CONVERSATIONS):
            # Run selected conversation
            conv_key = list(CONVERSATIONS.keys())[choice_num - 1]
            conv = CONVERSATIONS[conv_key]
            await sender.send_conversation(conv['messages'], conv['persona'])
            
        else:
            print("❌ Invalid choice")
            
    except ValueError:
        print("❌ Please enter a number")
    except KeyboardInterrupt:
        print("\n\n👋 Conversation interrupted")


if __name__ == "__main__":
    # Add Twilio setup instructions
    print("\n📋 SETUP INSTRUCTIONS:")
    print("1. Install Twilio: pip install twilio")
    print("2. Add to .env file:")
    print("   TWILIO_ACCOUNT_SID=your_account_sid")
    print("   TWILIO_AUTH_TOKEN=your_auth_token")
    print("   TWILIO_PHONE_NUMBER=+1234567890  # Your Twilio number")
    print("   GHL_PHONE_NUMBER=+1234567890     # GHL webhook number")
    print("\n3. Make sure GHL webhook is configured to receive SMS at that number")
    print("\nPress Enter to continue or Ctrl+C to exit...")
    input()
    
    # Run the async main function
    asyncio.run(main())