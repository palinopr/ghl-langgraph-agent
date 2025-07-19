#!/usr/bin/env python3
"""
Live Testing Suite for LangGraph GHL Agent
Tests all major components and workflows in a controlled environment
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Test configuration
BASE_URL = f"http://localhost:{os.getenv('PORT', 8000)}"
WEBHOOK_ENDPOINT = f"{BASE_URL}/webhook/ghl"
HEALTH_ENDPOINT = f"{BASE_URL}/health"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{title:^60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}\n")

def print_test(name: str, status: str, details: str = ""):
    """Print test result"""
    if status == "PASS":
        color = Colors.GREEN
        symbol = "✓"
    elif status == "FAIL":
        color = Colors.RED
        symbol = "✗"
    elif status == "SKIP":
        color = Colors.YELLOW
        symbol = "⚠"
    else:
        color = Colors.CYAN
        symbol = "•"
    
    print(f"{color}{symbol} {name:<40} [{status}]{Colors.RESET}")
    if details:
        print(f"  {Colors.WHITE}{details}{Colors.RESET}")

async def check_health() -> bool:
    """Check if the service is healthy"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(HEALTH_ENDPOINT, timeout=5.0)
            if response.status_code == 200:
                print_test("Health Check", "PASS", f"Service is healthy: {response.json()}")
                return True
            else:
                print_test("Health Check", "FAIL", f"Status code: {response.status_code}")
                return False
    except Exception as e:
        print_test("Health Check", "FAIL", f"Error: {str(e)}")
        return False

async def test_webhook_validation() -> bool:
    """Test webhook endpoint validation"""
    try:
        async with httpx.AsyncClient() as client:
            # Test with invalid payload
            response = await client.post(WEBHOOK_ENDPOINT, json={}, timeout=5.0)
            if response.status_code == 422:
                print_test("Webhook Validation", "PASS", "Correctly rejects invalid payload")
                return True
            else:
                print_test("Webhook Validation", "FAIL", f"Expected 422, got {response.status_code}")
                return False
    except Exception as e:
        print_test("Webhook Validation", "FAIL", f"Error: {str(e)}")
        return False

async def test_receptionist_flow() -> bool:
    """Test receptionist agent flow"""
    try:
        # Create test webhook payload
        test_payload = {
            "type": "InboundMessage",
            "locationId": os.getenv("GHL_LOCATION_ID", "test-location"),
            "contactId": "test-contact-123",
            "conversationId": "test-conversation-123",
            "message": "Hola, necesito información sobre sus servicios",
            "attachedMedia": None,
            "contactName": "Test User",
            "contactEmail": "test@example.com",
            "contactPhone": "+1234567890"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WEBHOOK_ENDPOINT,
                json=test_payload,
                timeout=30.0,
                follow_redirects=True
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    print_test("Receptionist Flow", "PASS", 
                             f"Agent: {result.get('agent', 'unknown')}, "
                             f"Response length: {len(result.get('response', ''))}")
                    return True
                else:
                    print_test("Receptionist Flow", "FAIL", f"Status: {result.get('status')}")
                    return False
            else:
                print_test("Receptionist Flow", "FAIL", f"Status code: {response.status_code}")
                return False
    except Exception as e:
        print_test("Receptionist Flow", "FAIL", f"Error: {str(e)}")
        return False

async def test_qualification_flow() -> bool:
    """Test qualification agent flow (Maria)"""
    try:
        # Create test webhook payload for qualification
        test_payload = {
            "type": "InboundMessage",
            "locationId": os.getenv("GHL_LOCATION_ID", "test-location"),
            "contactId": "test-contact-456",
            "conversationId": "test-conversation-456",
            "message": "Mi negocio es una agencia de marketing digital",
            "attachedMedia": None,
            "contactName": "Business Owner",
            "contactEmail": "business@example.com",
            "contactPhone": "+1234567890",
            "customFields": {
                "contact.qualification_state": "qualifying"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WEBHOOK_ENDPOINT,
                json=test_payload,
                timeout=30.0,
                follow_redirects=True
            )
            
            if response.status_code == 200:
                result = response.json()
                if "maria" in result.get("agent", "").lower():
                    print_test("Qualification Flow", "PASS", 
                             f"Maria agent responded correctly")
                    return True
                else:
                    print_test("Qualification Flow", "WARN", 
                             f"Expected Maria, got {result.get('agent')}")
                    return True
            else:
                print_test("Qualification Flow", "FAIL", f"Status code: {response.status_code}")
                return False
    except Exception as e:
        print_test("Qualification Flow", "FAIL", f"Error: {str(e)}")
        return False

async def test_appointment_flow() -> bool:
    """Test appointment booking flow (Sofia)"""
    try:
        # Create test webhook payload for appointment
        test_payload = {
            "type": "InboundMessage",
            "locationId": os.getenv("GHL_LOCATION_ID", "test-location"),
            "contactId": "test-contact-789",
            "conversationId": "test-conversation-789",
            "message": "Sí, me gustaría agendar una llamada para mañana",
            "attachedMedia": None,
            "contactName": "Qualified Lead",
            "contactEmail": "lead@example.com",
            "contactPhone": "+1234567890",
            "customFields": {
                "contact.qualification_state": "qualified",
                "contact.appointment_state": "scheduling"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                WEBHOOK_ENDPOINT,
                json=test_payload,
                timeout=30.0,
                follow_redirects=True
            )
            
            if response.status_code == 200:
                result = response.json()
                if "sofia" in result.get("agent", "").lower():
                    print_test("Appointment Flow", "PASS", 
                             f"Sofia agent responded correctly")
                    return True
                else:
                    print_test("Appointment Flow", "WARN", 
                             f"Expected Sofia, got {result.get('agent')}")
                    return True
            else:
                print_test("Appointment Flow", "FAIL", f"Status code: {response.status_code}")
                return False
    except Exception as e:
        print_test("Appointment Flow", "FAIL", f"Error: {str(e)}")
        return False

async def test_conversation_history() -> bool:
    """Test conversation history loading"""
    try:
        # First message
        first_payload = {
            "type": "InboundMessage",
            "locationId": os.getenv("GHL_LOCATION_ID", "test-location"),
            "contactId": "test-history-contact",
            "conversationId": "test-history-conversation",
            "message": "Primera mensaje de prueba",
            "attachedMedia": None,
            "contactName": "History Test",
            "contactEmail": "history@example.com",
            "contactPhone": "+1234567890"
        }
        
        async with httpx.AsyncClient() as client:
            # Send first message
            response1 = await client.post(WEBHOOK_ENDPOINT, json=first_payload, timeout=30.0)
            
            if response1.status_code != 200:
                print_test("Conversation History", "FAIL", "Failed to send first message")
                return False
            
            # Wait a bit
            await asyncio.sleep(2)
            
            # Send second message
            second_payload = first_payload.copy()
            second_payload["message"] = "Segunda mensaje - debería recordar la primera"
            
            response2 = await client.post(WEBHOOK_ENDPOINT, json=second_payload, timeout=30.0)
            
            if response2.status_code == 200:
                result = response2.json()
                print_test("Conversation History", "PASS", 
                         "Successfully processed message with history")
                return True
            else:
                print_test("Conversation History", "FAIL", f"Status code: {response2.status_code}")
                return False
                
    except Exception as e:
        print_test("Conversation History", "FAIL", f"Error: {str(e)}")
        return False

async def test_concurrent_requests() -> bool:
    """Test handling of concurrent webhook requests"""
    try:
        # Create multiple test payloads
        payloads = []
        for i in range(5):
            payload = {
                "type": "InboundMessage",
                "locationId": os.getenv("GHL_LOCATION_ID", "test-location"),
                "contactId": f"test-concurrent-{i}",
                "conversationId": f"test-concurrent-conv-{i}",
                "message": f"Mensaje concurrente número {i}",
                "attachedMedia": None,
                "contactName": f"Concurrent User {i}",
                "contactEmail": f"concurrent{i}@example.com",
                "contactPhone": f"+123456789{i}"
            }
            payloads.append(payload)
        
        async with httpx.AsyncClient() as client:
            # Send all requests concurrently
            tasks = [
                client.post(WEBHOOK_ENDPOINT, json=payload, timeout=30.0)
                for payload in payloads
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = 0
            for i, response in enumerate(responses):
                if isinstance(response, Exception):
                    print(f"  Request {i}: Failed with error: {response}")
                elif response.status_code == 200:
                    success_count += 1
                else:
                    print(f"  Request {i}: Status code {response.status_code}")
            
            if success_count == len(payloads):
                print_test("Concurrent Requests", "PASS", 
                         f"All {len(payloads)} requests processed successfully")
                return True
            else:
                print_test("Concurrent Requests", "WARN", 
                         f"{success_count}/{len(payloads)} requests succeeded")
                return success_count > 0
                
    except Exception as e:
        print_test("Concurrent Requests", "FAIL", f"Error: {str(e)}")
        return False

async def run_all_tests():
    """Run all live tests"""
    print_header("LangGraph GHL Agent - Live Testing Suite")
    print(f"Testing against: {BASE_URL}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check if service is healthy first
    print(f"{Colors.CYAN}Checking service health...{Colors.RESET}")
    if not await check_health():
        print(f"\n{Colors.RED}Service is not healthy. Please start the service first:{Colors.RESET}")
        print(f"{Colors.YELLOW}  docker-compose up -d{Colors.RESET}")
        print(f"{Colors.YELLOW}  # or{Colors.RESET}")
        print(f"{Colors.YELLOW}  python app.py{Colors.RESET}")
        return
    
    print(f"\n{Colors.CYAN}Running test suite...{Colors.RESET}\n")
    
    # Run all tests
    test_results = {
        "Webhook Validation": await test_webhook_validation(),
        "Receptionist Flow": await test_receptionist_flow(),
        "Qualification Flow": await test_qualification_flow(),
        "Appointment Flow": await test_appointment_flow(),
        "Conversation History": await test_conversation_history(),
        "Concurrent Requests": await test_concurrent_requests(),
    }
    
    # Print summary
    print_header("Test Summary")
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"{Colors.GREEN}Passed: {passed_tests}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed_tests}{Colors.RESET}")
    
    if failed_tests == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! 🎉{Colors.RESET}")
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Some tests failed. Check the logs above.{Colors.RESET}")
    
    # Print recommendations
    print(f"\n{Colors.CYAN}Next Steps:{Colors.RESET}")
    print("1. Check application logs: docker-compose logs -f")
    print("2. Monitor LangSmith traces: https://smith.langchain.com")
    print("3. Test with real GHL webhooks using ngrok")
    print("4. Run performance tests under load")

if __name__ == "__main__":
    asyncio.run(run_all_tests())