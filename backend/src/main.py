from fastapi import FastAPI
import os
from dotenv import load_dotenv
from .sse import app as sse_app  # Import the configured router with CORS

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Sentient Audit System API",
    description="AI Financial Audit System Backend with Real-time Streaming",
    version="1.0.0"
)

# Check for required API key
if not os.getenv("TAVILY_API_KEY"):
    print("WARNING: TAVILY_API_KEY not found in environment variables")
    print("Please create a .env file in the backend directory with your TAVILY_API_KEY")

# Include SSE routes with CORS configuration
app.include_router(sse_app, prefix="/api/v1", tags=["audit"])

@app.get("/")
async def root():
    return {"message": "Sentient Audit System API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}