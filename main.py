"""
Entry point for Railway deployment
Imports and runs the FastAPI app from src.main
"""
from src.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
