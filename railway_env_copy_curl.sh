#!/bin/bash

# Railway API Configuration
API_URL="https://backboard.railway.com/graphql/v2"
AUTH_TOKEN="07037cf7-0b95-4c13-9175-72d34b479e41"
PROJECT_ID="c08abbf5-1609-48d3-ab0d-7d3ac509f2f2"
ENVIRONMENT_ID="c0fea238-049d-42b6-a66f-78271501b50f"
DEST_SERVICE_ID="4f9c41d5-5ec1-40ca-a9ba-664ee886de9c"

# Function to set a variable
set_variable() {
    local name=$1
    local value=$2
    
    echo "Setting $name..."
    
    curl -X POST "$API_URL" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        -H "Content-Type: application/json" \
        -d @- <<EOF
{
    "query": "mutation UpsertVariable(\$projectId: String!, \$environmentId: String!, \$serviceId: String!, \$name: String!, \$value: String!) { variableUpsert(input: { projectId: \$projectId, environmentId: \$environmentId, serviceId: \$serviceId, name: \$name, value: \$value }) }",
    "variables": {
        "projectId": "$PROJECT_ID",
        "environmentId": "$ENVIRONMENT_ID",
        "serviceId": "$DEST_SERVICE_ID",
        "name": "$name",
        "value": "$value"
    }
}
EOF
    echo ""
}

# Instructions
echo "Railway Environment Variable Copy Script"
echo "======================================="
echo ""
echo "This script will help you copy environment variables to service: $DEST_SERVICE_ID"
echo ""
echo "To use this script, you need to provide the values for each variable."
echo "You can find these values in your Railway dashboard for the source service."
echo ""
echo "Example usage:"
echo "  set_variable \"OPENAI_API_KEY\" \"sk-your-actual-key-here\""
echo "  set_variable \"GHL_API_TOKEN\" \"your-ghl-token\""
echo ""
echo "Add your set_variable commands below:"
echo ""

# Add your set_variable commands here:
# set_variable "OPENAI_API_KEY" "your-value-here"
# set_variable "GHL_API_TOKEN" "your-value-here"
# set_variable "GHL_LOCATION_ID" "your-value-here"
# set_variable "GHL_CALENDAR_ID" "your-value-here"
# set_variable "GHL_ASSIGNED_USER_ID" "your-value-here"
# set_variable "SUPABASE_URL" "your-value-here"
# set_variable "SUPABASE_KEY" "your-value-here"
# set_variable "LANGCHAIN_TRACING_V2" "your-value-here"
# set_variable "LANGCHAIN_API_KEY" "your-value-here"
# set_variable "LANGCHAIN_PROJECT" "your-value-here"
# set_variable "APP_ENV" "your-value-here"
# set_variable "LOG_LEVEL" "your-value-here"