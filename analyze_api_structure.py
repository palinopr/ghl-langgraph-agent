#!/usr/bin/env python3
"""
Analyze the API response structure
"""
import asyncio
import json
from app.tools.ghl_client import GHLClient

async def analyze_structure():
    """Analyze the actual API response structure"""
    
    conv_id = "Gxo4ICMMnHSfyUSrD8OP"
    client = GHLClient()
    
    # Get the raw response
    endpoint = f"/conversations/{conv_id}/messages"
    raw = await client._make_request("GET", endpoint)
    
    print("API Response Structure:")
    print("="*60)
    print(json.dumps(raw, indent=2))
    
    print("\n\nAnalysis:")
    print("="*60)
    print(f"Top level type: {type(raw)}")
    print(f"Top level keys: {list(raw.keys())}")
    
    # Check the messages key
    if 'messages' in raw:
        messages_value = raw['messages']
        print(f"\nraw['messages'] type: {type(messages_value)}")
        
        if isinstance(messages_value, dict):
            print(f"raw['messages'] keys: {list(messages_value.keys())}")
            # Check if there's another messages key inside
            if 'messages' in messages_value:
                inner_messages = messages_value['messages']
                print(f"\nraw['messages']['messages'] type: {type(inner_messages)}")
                if isinstance(inner_messages, list):
                    print(f"raw['messages']['messages'] length: {len(inner_messages)}")
                    print(f"First message: {inner_messages[0] if inner_messages else 'Empty'}")
        elif isinstance(messages_value, list):
            print(f"raw['messages'] is a list with {len(messages_value)} items")
            if messages_value:
                print(f"First message keys: {list(messages_value[0].keys())}")

if __name__ == "__main__":
    asyncio.run(analyze_structure())