#!/usr/bin/env python3
"""
Test script for SSE endpoints
"""
import os
import sys
import json
import asyncio
from fastapi.testclient import TestClient
from src.main import app
import uuid

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['TAVILY_API_KEY'] = os.getenv('TAVILY_API_KEY', 'test_key')

def test_sse_endpoint():
    """Test the SSE endpoint"""
    client = TestClient(app)

    # Test query
    test_query = "Analyze financial performance for the company"

    print("="*50)
    print("Testing SSE Endpoint")
    print("="*50)
    print(f"Query: {test_query}")

    # Test the streaming endpoint
    try:
        with client.stream("POST", "/api/v1/audit/stream", json={"user_query": test_query}) as response:
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                event_count = 0
                for line in response.iter_lines():
                    if line:
                        # Parse SSE line
                        line = line.decode('utf-8')
                        if line.startswith("data: "):
                            # Remove "data: " prefix
                            json_str = line[6:]
                            try:
                                data = json.loads(json_str)
                                print(f"\nEvent {event_count + 1}: {data.get('event', 'unknown')}")

                                if 'data' in data:
                                    payload = data['data']
                                    print(f"  Step: {payload.get('step')}")
                                    print(f"  Status: {payload.get('status')}")

                                    if 'error' in payload:
                                        print(f"  ERROR: {payload['error']}")

                                    if 'logs' in payload:
                                        for log in payload['logs'][-2:]:  # Show last 2 logs
                                            print(f"    LOG: {log}")

                                    if 'intent' in payload:
                                        print(f"  Intent: {payload['intent']}")

                                    if 'data_points' in payload:
                                        print(f"  Data points: {payload['data_points']}")

                                    if 'health_score' in payload:
                                        print(f"  Health score: {payload['health_score']}")

                                    if 'report' in payload and payload['report']:
                                        print(f"  Report: {payload['report'][:200]}...")

                                event_count += 1
                                if payload.get('step') == 'completed':
                                    break

                            except json.JSONDecodeError:
                                print(f"Failed to parse JSON: {json_str}")

                print(f"\nTotal events received: {event_count}")

            else:
                print(f"Error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Exception during SSE test: {str(e)}")

def test_health_endpoint():
    """Test the health endpoint"""
    client = TestClient(app)

    print("\n" + "="*50)
    print("Testing Health Endpoint")
    print("="*50)

    response = client.get("/api/v1/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

if __name__ == "__main__":
    print("Starting SSE tests...")

    # Test health endpoint first
    test_health_endpoint()

    # Test SSE endpoint
    test_sse_endpoint()

    print("\nSSE tests completed.")