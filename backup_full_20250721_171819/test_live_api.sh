#!/bin/bash
# Live test of appointment booking flow via API

CONTACT_ID="XinFGydeogXoZamVtZly"
API_URL="http://localhost:8000/webhook/message"

echo "🚀 LIVE APPOINTMENT BOOKING TEST"
echo "Contact ID: $CONTACT_ID"
echo ""

# Function to send message and show response
send_message() {
    local message="$1"
    local step="$2"
    local expected="$3"
    
    echo "========================================"
    echo "STEP $step: Sending '$message'"
    echo "Expected: $expected"
    echo "========================================"
    
    # Send the message
    response=$(curl -s -X POST "$API_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"id\": \"$CONTACT_ID\",
            \"contactId\": \"$CONTACT_ID\",
            \"message\": \"$message\",
            \"body\": \"$message\",
            \"type\": \"SMS\",
            \"locationId\": \"sHFG9Rw6BdGh6d6bfMqG\",
            \"direction\": \"inbound\",
            \"dateAdded\": \"$(date -u +%Y-%m-%dT%H:%M:%S.000Z)\"
        }")
    
    echo "Response: $response"
    echo ""
    
    # Wait before next message
    sleep 3
}

# Step 1: Name
send_message "Jaime" "1" "tipo de negocio"

# Step 2: Business type
send_message "Restaurante" "2" "desafío"

# Step 3: Challenge
send_message "No puedo responder rápido a los clientes" "3" "\$300"

# Step 4: Budget confirmation
send_message "Sí, está bien" "4" "correo"

# Step 5: Email
send_message "jaime@restaurant.com" "5" "horarios disponibles"

# Step 6: Time selection
echo "🎯 CRITICAL STEP: Selecting appointment time"
send_message "10:00 AM" "6" "confirmado"

echo ""
echo "✅ Test completed! Check GHL for appointment creation."