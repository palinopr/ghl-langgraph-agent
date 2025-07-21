#!/bin/bash
# Setup ngrok for local GHL webhook testing

echo "🚀 Setting up ngrok for GHL webhook testing"
echo "=========================================="

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok not found. Installing..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install ngrok/ngrok/ngrok
    else
        # Linux
        curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
        echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
        sudo apt update && sudo apt install ngrok
    fi
fi

# Start the local server
echo ""
echo "📦 Starting local GHL testing server..."
python3 setup_local_ghl_testing.py &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to start
sleep 3

# Start ngrok
echo ""
echo "🌐 Starting ngrok tunnel..."
ngrok http 8001 &
NGROK_PID=$!

# Wait for ngrok to start
sleep 3

# Get ngrok URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; print(json.load(sys.stdin)['tunnels'][0]['public_url'])")

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Go to GHL and update your webhook URL to:"
echo "   $NGROK_URL/webhook/ghl"
echo ""
echo "2. Send a test message through GHL/WhatsApp"
echo ""
echo "3. Watch the terminal for real-time processing"
echo ""
echo "4. To stop: Press Ctrl+C"
echo ""
echo "=========================================="
echo "Server running at: http://localhost:8001"
echo "Ngrok URL: $NGROK_URL"
echo "=========================================="

# Wait for Ctrl+C
trap "kill $SERVER_PID $NGROK_PID; exit" INT
wait