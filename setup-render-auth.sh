#!/bin/bash

echo "Setting up Render authentication..."

# The token you provided might be a one-time code
# Let's try the standard login flow

echo "Please run the following command to authenticate:"
echo ""
echo "render login"
echo ""
echo "This will:"
echo "1. Open your browser"
echo "2. You'll click 'Authorize'"
echo "3. The CLI will be authenticated"
echo ""
echo "If you already have a token from the dashboard, you can also set it like this:"
echo ""
echo "export RENDER_API_KEY='your-actual-api-key'"
echo ""
echo "To get your API key:"
echo "1. Go to https://dashboard.render.com/u/settings"
echo "2. Click on 'API Keys'"
echo "3. Create a new API key"
echo "4. Copy the key (it starts with 'rnd_')"
echo "5. Run: export RENDER_API_KEY='rnd_your_key_here'"