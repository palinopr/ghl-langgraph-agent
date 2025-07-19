#!/bin/bash
# Test like a real customer - send messages one by one

echo "🎭 REAL CUSTOMER SIMULATION"
echo "=========================================="
echo "This simulates a NEW customer texting for the first time"
echo ""

# Generate unique phone number
TIMESTAMP=$(date +%s)
PHONE="+1555${TIMESTAMP: -7}"
LOCATION_ID="sHFG9Rw6BdGh6d6bfMqG"

echo "📱 Phone Number: $PHONE"
echo "📍 Location ID: $LOCATION_ID"
echo ""
echo "Make sure your webhook is running at http://localhost:8000"
echo "Press Enter to start..."
read

# Function to send message
send_message() {
    local message="$1"
    local description="$2"
    local msg_id="msg_${TIMESTAMP}_${RANDOM}"
    
    echo ""
    echo "------------------------------------------------------------"
    echo "💬 $description"
    echo "📤 Sending: '$message'"
    echo ""
    
    # Send to webhook
    curl -X POST http://localhost:8000/webhook/message \
        -H "Content-Type: application/json" \
        -d '{
            "id": "'$msg_id'",
            "contactId": "'$PHONE'",
            "message": "'$message'",
            "body": "'$message'",
            "type": "SMS",
            "locationId": "'$LOCATION_ID'",
            "direction": "inbound",
            "dateAdded": "'$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")'",
            "contactName": "",
            "contactEmail": "",
            "contactPhone": "'$PHONE'"
        }' 2>/dev/null | jq '.' 2>/dev/null || echo "Response received"
    
    echo ""
}

# Send messages one by one
echo "============================================================"
echo "Starting conversation..."
echo "============================================================"

# Message 1
send_message "Hola" "MESSAGE 1/8: Customer says hello"
echo "⏳ Waiting 3 seconds..."
sleep 3

# Message 2  
send_message "Mi nombre es Carlos" "MESSAGE 2/8: Customer gives name"
echo "⏳ Waiting 3 seconds..."
sleep 3

# Message 3
send_message "Tengo un restaurante" "MESSAGE 3/8: Customer mentions business"
echo "⏳ Waiting 3 seconds..."
sleep 3

# Message 4
send_message "Necesito automatizar las reservas" "MESSAGE 4/8: Customer explains need"
echo "⏳ Waiting 3 seconds..."
sleep 3

# Message 5
send_message "Cuánto cuesta?" "MESSAGE 5/8: Customer asks about price"
echo "⏳ Waiting 3 seconds..."
sleep 3

# Message 6
send_message "Sí, está bien" "MESSAGE 6/8: Customer agrees to budget"
echo "⏳ Waiting 3 seconds..."
sleep 3

# Message 7
send_message "carlos@mirestaurante.com" "MESSAGE 7/8: Customer provides email"
echo "⏳ Waiting 3 seconds..."
sleep 3

# Message 8
send_message "El martes a las 2pm" "MESSAGE 8/8: Customer selects appointment time"

echo ""
echo "============================================================"
echo "✅ CONVERSATION COMPLETE!"
echo "============================================================"
echo "Phone: $PHONE"
echo ""
echo "🔍 Check the following:"
echo "1. Your webhook logs to see processing"
echo "2. LangSmith traces for agent behavior"
echo "3. GHL to see if contact was created"
echo ""
echo "This is EXACTLY how a real customer interaction works!"
echo "============================================================"