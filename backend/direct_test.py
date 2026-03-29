#!/usr/bin/env python3
"""
Direct test of Tavily API
"""
import os
import httpx
import json

def test_direct_tavily():
    """Test Tavily API directly"""
    print("="*50)
    print("DIRECT TAVILY API TEST")
    print("="*50)

    # Set up API call
    api_key = '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'
    base_url = "https://api.tavily.com"

    # Search query for Tesla financial data
    query = "Tesla TSLA financial report 2023 2024 2025 annual balance sheet revenue"

    print("\nSearch Query: " + query)
    print("API Endpoint: " + base_url + "/search")

    try:
        # Make the API request
        response = httpx.post(
            f"{base_url}/search",
            json={
                "query": query,
                "api_key": api_key,
                "max_results": 10,
                "include_answer": True,
                "search_depth": "advanced"
            },
            timeout=30.0
        )

        print("\nResponse Status: " + str(response.status_code))

        if response.status_code == 200:
            data = response.json()

            print("\nSearch Successful!")
            print("Total Results: " + str(len(data.get('results', []))))

            # Show top 3 results
            print("\nTop 3 Results:")
            for i, result in enumerate(data.get('results', [])[:3], 1):
                print("\n" + str(i) + ". " + result.get('title', 'No title'))
                print("   URL: " + result.get('url', 'No URL'))

                # Show source
                if 'source' in result:
                    print("   Source: " + result['source'])

                # Show answer if available
                if 'answer' in result:
                    print("   Answer: " + result['answer'][:200] + "...")

                # Show snippet
                if 'content' in result:
                    print("   Content: " + result['content'][:300] + "...")

            # Check for specific sources
            print("\nSource Analysis:")
            sources_found = []
            for result in data.get('results', []):
                url = result.get('url', '')
                if 'tesla.com' in url or 'sec.gov' in url or 'reuters.com' in url:
                    sources_found.append(url)
                    print("   Official Source: " + url)

            if sources_found:
                print("\nFound " + str(len(sources_found)) + " official sources!")
            else:
                print("\nNo official sources found in results")

            # Try to find financial numbers in content
            print("\nLooking for Financial Data:")
            for result in data.get('results', [])[:3]:
                content = result.get('content', '')
                if content:
                    # Simple extraction for revenue numbers
                    lines = content.split('\n')
                    for line in lines:
                        if 'revenue' in line.lower() and any(year in line for year in ['2023', '2024', '2025']):
                            print("   Found in " + result.get('title', 'Unknown') + ": " + line.strip())

            return True

        else:
            print("API Error: " + str(response.status_code))
            print("Response: " + response.text)
            return False

    except Exception as e:
        print("Error: " + str(e))
        return False

if __name__ == "__main__":
    print("Starting direct Tavily test...")

    success = test_direct_tavily()

    print("\nTest result: " + ("SUCCESS" if success else "FAILED"))