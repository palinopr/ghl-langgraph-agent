"""Railway deployment entry point with Python 3.13 optimizations"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable Python 3.13 optimizations before importing anything else
if os.environ.get("ENABLE_FREE_THREADING", "true").lower() == "true":
    os.environ["PYTHON_GIL"] = "0"
if os.environ.get("ENABLE_JIT_COMPILATION", "true").lower() == "true":
    os.environ["PYTHON_JIT"] = "1"

# Import and run the main application
if __name__ == "__main__":
    try:
        from main import app
        import uvicorn
        
        port = int(os.environ.get("PORT", 8000))
        print(f"Starting server on port {port}...")
        
        uvicorn.run(app, host="0.0.0.0", port=port)
    except ImportError as e:
        print(f"Import error: {e}")
        print("Trying alternative import...")
        
        # Import configuration to check settings
        from app.config import get_settings
        settings = get_settings()
        
        # Try importing concurrent webhook if enabled
        if settings.enable_concurrent_webhooks:
            try:
                from app.api.webhook_concurrent import app
                print("Using concurrent webhook with Python 3.13 TaskGroup support")
            except ImportError:
                from app.api.webhook_enhanced import app
                print("Using enhanced webhook with streaming support")
        else:
            # Try importing enhanced webhook first
            try:
                from app.api.webhook_enhanced import app
                print("Using enhanced webhook with streaming support")
            except ImportError:
                from app.api.webhook import app
                print("Using standard webhook")
        
        import uvicorn
        
        port = int(os.environ.get("PORT", 8000))
        print(f"Starting server on port {port}...")
        print(f"Python 3.13 optimizations: GIL={os.environ.get('PYTHON_GIL', '1')}, JIT={os.environ.get('PYTHON_JIT', '0')}")
        
        # Use uvloop for better async performance
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=port,
            loop="uvloop",  # Python 3.13 optimized event loop
            log_level="info"
        )