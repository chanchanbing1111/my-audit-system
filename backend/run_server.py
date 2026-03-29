#!/usr/bin/env python3
"""
Server startup script with proper path handling and SSE support
"""
import os
import sys
import uvicorn

# Add backend to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Set environment variables
os.environ['TAVILY_API_KEY'] = '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'

# Import app
from src.main import app

if __name__ == "__main__":
    print("Starting Sentient Audit System server with SSE support...")
    print("TAVILY_API_KEY configured:", bool(os.getenv('TAVILY_API_KEY')))
    print("CORS enabled for http://localhost:3000")
    print("API endpoints available:")
    print("  - POST /api/v1/api/audit - Stream audit workflow")
    print("  - GET /api/v1/api/health - Health check")
    print("  - GET / - Root endpoint")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )