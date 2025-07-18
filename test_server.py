#!/usr/bin/env python
"""Test if the server is running and check optimizations"""
import requests
import json

def test_endpoints():
    """Test various endpoints"""
    base_url = "http://localhost:8000"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Health endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("Health response:", json.dumps(data, indent=2))
    except Exception as e:
        print(f"❌ Health endpoint failed: {e}")
    
    # Test performance endpoint
    try:
        response = requests.get(f"{base_url}/performance", timeout=5)
        print(f"\n✅ Performance endpoint: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            optimizations = data.get("optimizations", {})
            print("\nActive optimizations:")
            for key, value in optimizations.items():
                status = "✅" if value else "❌"
                print(f"  {status} {key}: {value}")
            
            metrics = data.get("metrics", {})
            print("\nPerformance metrics:")
            print(f"  Total requests: {metrics.get('total_requests', 0)}")
            print(f"  JIT optimization rate: {metrics.get('jit_optimization_rate', 'N/A')}")
            print(f"  Parallel executions: {metrics.get('parallel_executions', 0)}")
    except Exception as e:
        print(f"❌ Performance endpoint failed: {e}")
    
    # Test root endpoint
    try:
        response = requests.get(base_url, timeout=5)
        print(f"\n✅ Root endpoint: {response.status_code}")
        if response.status_code == 200:
            print("Response:", response.json())
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")

if __name__ == "__main__":
    print("Testing server endpoints...")
    print("="*50)
    test_endpoints()