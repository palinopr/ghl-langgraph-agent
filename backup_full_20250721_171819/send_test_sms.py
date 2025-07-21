#!/usr/bin/env python3
"""
Quick SMS sender for testing GHL webhook with Twilio
Simple script to send individual messages
"""
import os
import sys
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
GHL_PHONE_NUMBER = os.getenv("GHL_PHONE_NUMBER")


def send_sms(message: str):
    """Send a single SMS message to GHL"""
    
    # Check credentials
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, GHL_PHONE_NUMBER]):
        print("❌ Missing Twilio configuration!")
        print("\nAdd to your .env file:")
        print("TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxx")
        print("TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxx")
        print("TWILIO_PHONE_NUMBER=+1234567890")
        print("GHL_PHONE_NUMBER=+1234567890")
        return False
    
    try:
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send message
        sent = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=GHL_PHONE_NUMBER
        )
        
        print(f"✅ Message sent!")
        print(f"📱 From: {TWILIO_PHONE_NUMBER}")
        print(f"📱 To: {GHL_PHONE_NUMBER}")
        print(f"💬 Message: {message}")
        print(f"🆔 SID: {sent.sid}")
        print(f"📊 Status: {sent.status}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    """Main function"""
    
    # Quick test messages
    test_messages = {
        "1": "Hola, necesito información",
        "2": "Mi nombre es Carlos",
        "3": "Tengo un restaurante", 
        "4": "Estoy perdiendo clientes",
        "5": "Mi presupuesto es $500 al mes",
        "6": "Sí, está bien",
        "7": "carlos@restaurante.com",
        "8": "Mañana a las 3pm está perfecto",
        "9": "Custom message"
    }
    
    print("🚀 Quick SMS Test Sender")
    print("=" * 40)
    print("\nTest Messages:")
    for key, msg in test_messages.items():
        print(f"{key}. {msg}")
    
    # Get choice
    choice = input("\nSelect message (1-9) or type your own: ")
    
    # Determine message
    if choice in test_messages:
        if choice == "9":
            message = input("Enter your custom message: ")
        else:
            message = test_messages[choice]
    else:
        # Treat as custom message
        message = choice
    
    # Send the message
    print(f"\n📤 Sending: {message}")
    send_sms(message)


if __name__ == "__main__":
    # Check if message passed as argument
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        print(f"📤 Sending: {message}")
        send_sms(message)
    else:
        main()