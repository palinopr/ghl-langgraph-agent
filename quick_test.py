#!/usr/bin/env python3
"""
Quick test any message
Usage: python quick_test.py "your message here"
"""
import asyncio
import sys
sys.path.append('.')

from test_locally import test_specific_issue

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quick_test.py \"your message here\"")
        print("Example: python quick_test.py \"tengo un negocio\"")
        sys.exit(1)
    
    message = " ".join(sys.argv[1:])
    asyncio.run(test_specific_issue(message))