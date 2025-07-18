"""Debug deployment to test Railway"""
import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "message": "Debug deployment working",
        "python_version": os.sys.version,
        "port": os.environ.get("PORT", "unknown")
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting debug server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)