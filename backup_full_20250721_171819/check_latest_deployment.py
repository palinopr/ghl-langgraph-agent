#!/usr/bin/env python3
"""
Quick check of the latest traces to see what's still broken
"""
import os
from langsmith import Client
from datetime import datetime

# Set API key
os.environ["LANGSMITH_API_KEY"] = "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"

def analyze_trace_quick(trace_id):
    """Quick analysis of what's happening"""
    client = Client()
    
    try:
        run = client.read_run(trace_id)
        
        # Get the message
        message = "Unknown"
        if run.inputs and 'messages' in run.inputs:
            msgs = run.inputs['messages']
            if msgs and len(msgs) > 0:
                last_msg = msgs[-1]
                if isinstance(last_msg, dict):
                    message = last_msg.get('content', '')
        
        # Get the response
        response = "No response"
        if run.outputs and isinstance(run.outputs, dict):
            if 'messages' in run.outputs:
                msgs = run.outputs['messages']
                if isinstance(msgs, list) and msgs:
                    last_msg = msgs[-1]
                    if isinstance(last_msg, dict):
                        response = last_msg.get('content', '')
        
        # Get extracted data
        extracted_data = None
        if run.outputs and isinstance(run.outputs, dict):
            extracted_data = run.outputs.get('extracted_data', {})
        
        # Check for errors
        error = run.error if hasattr(run, 'error') else None
        
        return {
            "message": message,
            "response": response,
            "extracted_data": extracted_data,
            "error": error,
            "status": run.status
        }
        
    except Exception as e:
        return {"error": str(e)}

def main():
    print("🔍 CHECKING LATEST TRACES")
    print("=" * 80)
    
    traces = [
        "1f066626-74a1-62f4-a9c3-51db0c3f06bd",
        "1f066627-71b4-6921-a7c2-70571227038a"
    ]
    
    for trace_id in traces:
        print(f"\nTRACE: {trace_id}")
        print("-" * 40)
        
        result = analyze_trace_quick(trace_id)
        
        if "error" in result and not "message" in result:
            print(f"❌ Error: {result['error']}")
            continue
        
        print(f"Message: '{result['message']}'")
        print(f"Response: '{result['response'][:100]}...'")
        
        if result['extracted_data']:
            print(f"Extracted: {result['extracted_data']}")
        
        if result.get('error'):
            print(f"⚠️  Error: {result['error']}")
        
        # Quick diagnosis
        message_lower = result['message'].lower()
        response_lower = result['response'].lower()
        
        # Check for issues
        issues = []
        
        # Issue 1: Still extracting "negocio"?
        if result['extracted_data'] and result['extracted_data'].get('business_type') == 'negocio':
            issues.append("❌ STILL EXTRACTING 'negocio' as business type!")
        
        # Issue 2: Asking for name when already provided?
        if result['extracted_data'] and result['extracted_data'].get('name'):
            if "cuál es tu nombre" in response_lower or "what's your name" in response_lower:
                issues.append(f"❌ Asking for name when already have: {result['extracted_data']['name']}")
        
        # Issue 3: Not acknowledging business?
        if result['extracted_data'] and result['extracted_data'].get('business_type'):
            business = result['extracted_data']['business_type']
            if business not in ['negocio', 'empresa'] and business not in response_lower:
                issues.append(f"❌ Not acknowledging business: {business}")
        
        if issues:
            print("\n🚨 ISSUES FOUND:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("\n✅ No obvious issues")

if __name__ == "__main__":
    main()