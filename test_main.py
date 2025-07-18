"""
Minimal test server to debug Render deployment
"""
import os
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok", "port": os.environ.get("PORT", "10000")}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting test server on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)