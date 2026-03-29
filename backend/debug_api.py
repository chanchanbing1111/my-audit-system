#!/usr/bin/env python3
"""
Debug API endpoint
"""
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['TAVILY_API_KEY'] = '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'

try:
    from src.main import app
    print("SUCCESS: API app imported successfully")

    # Test health endpoint directly
    @app.get("/debug/test")
    def debug_test():
        return {"message": "Debug endpoint working", "tavily_key": bool(os.getenv('TAVILY_API_KEY'))}

    # Test SSE endpoint
    from src.sse import SSEStreamer
    streamer = SSEStreamer()

    print("SUCCESS: All modules imported successfully")
    print("Server ready to start on port 8000")

except Exception as e:
    print(f"ERROR: {str(e)}")
    import traceback
    traceback.print_exc()