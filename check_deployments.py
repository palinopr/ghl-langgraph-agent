#!/usr/bin/env python3
"""
Check LangSmith deployments
"""
import requests

LANGSMITH_API_KEY = "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"
url = "https://smith.langchain.com/api/v1/deployments"

headers = {
    "X-API-Key": LANGSMITH_API_KEY,
}

print("🔍 Checking LangSmith deployments...")
response = requests.get(url, headers=headers)

print(f"Status: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"Content Type: {response.headers.get('content-type')}")
print(f"Content length: {len(response.text)}")
print(f"Content preview: {response.text[:500]}...")

# Check if it's HTML (redirect page)
if 'text/html' in response.headers.get('content-type', ''):
    print("\n⚠️  Got HTML response - this might be a UI page, not an API endpoint")
    print("You may need to use the LangSmith UI to manage deployments")