"""Railway deployment entry point"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
        
        # Try importing from app.api.webhook
        from app.api.webhook import app
        import uvicorn
        
        port = int(os.environ.get("PORT", 8000))
        print(f"Starting server on port {port}...")
        
        uvicorn.run(app, host="0.0.0.0", port=port)