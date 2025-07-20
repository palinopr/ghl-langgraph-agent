"""Deployment entry point"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable Python 3.13 optimizations if available
if os.environ.get("ENABLE_FREE_THREADING", "true").lower() == "true":
    os.environ["PYTHON_GIL"] = "0"
if os.environ.get("ENABLE_JIT_COMPILATION", "true").lower() == "true":
    os.environ["PYTHON_JIT"] = "1"

# Import and run the main application
if __name__ == "__main__":
    # Import the simple webhook app (no Supabase dependency)
    from app.api.webhook_simple import app
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on port {port}...")
    print(f"Debug endpoints available at http://localhost:{port}/debug")
    
    # Run the server
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        reload=True,
        log_level="info"
    )