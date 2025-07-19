#!/usr/bin/env python3
"""
Verify the GHL client bug
"""
import asyncio
import json
from app.tools.ghl_client import GHLClient

async def verify_bug():
    """Verify the get_conversation_messages bug"""
    
    ghl_client = GHLClient()
    
    # Test conversation ID from previous debug
    conv_id = "Gxo4ICMMnHSfyUSrD8OP"
    
    print("Testing get_conversation_messages method")
    print("="*60)
    
    # Make the raw request
    endpoint = f"/conversations/{conv_id}/messages"
    raw_result = await ghl_client._make_request("GET", endpoint)
    
    print("Raw API result:")
    print(f"Type: {type(raw_result)}")
    print(f"Keys: {list(raw_result.keys()) if isinstance(raw_result, dict) else 'Not a dict'}")
    
    if isinstance(raw_result, dict) and "messages" in raw_result:
        print(f"\nMessages key exists: True")
        print(f"Type of messages: {type(raw_result['messages'])}")
        print(f"Is list: {isinstance(raw_result['messages'], list)}")
        print(f"Length: {len(raw_result['messages'])}")
        
        # Now test the method
        print("\n" + "="*60)
        print("Testing get_conversation_messages method:")
        
        # Import and check the exact method
        from app.tools.ghl_client import GHLClient as GHLClientImport
        import inspect
        
        # Show the method source
        print("\nMethod source code:")
        print(inspect.getsource(GHLClientImport.get_conversation_messages))
        
        # Call the method
        method_result = await ghl_client.get_conversation_messages(conv_id)
        print(f"\nMethod result type: {type(method_result)}")
        print(f"Method result: {method_result}")

if __name__ == "__main__":
    asyncio.run(verify_bug())