#!/usr/bin/env python3
"""
Simple test for Tavily search
"""
import os
import sys
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['TAVILY_API_KEY'] = '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'

def test_tavily_search():
    """Test Tavily search directly"""
    print("="*50)
    print("TAVILY SEARCH TEST FOR TESLA")
    print("="*50)

    try:
        # Import the agent
        from src.agents.tavily_agent import TavilySearchAgent

        # Create agent
        agent = TavilySearchAgent()

        # Build search query
        years = [2023, 2024, 2025]
        query = "Tesla TSLA financial report"

        print(f"\nSearch Query: {query}")
        print(f"Years: {years}")
        print(f"\nSending request to Tavily API...")

        # Perform search
        result = agent.search_financial_data(query, years, search_depth="advanced")

        print(f"\nSearch Results:")
        print(f"Total Results: {len(result.get('results', []))}")

        # Show top 3 results
        for i, item in enumerate(result.get('results', [])[:3], 1):
            print(f"\n{i}. {item.get('title', 'No title')}")
            print(f"   URL: {item.get('url', 'No URL')}")
            print(f"   Content: {item.get('content', '')[:200]}...")

        # Extract and show financial data if available
        if 'financial_data' in result and result['financial_data']:
            print(f"\n📊 Financial Data Extracted:")
            for data in result['financial_data']:
                print(f"\nYear {data.get('year', 'Unknown')}:")
                print(f"   Revenue: ${data.get('revenue', 0):,.2f}")
                print(f"   Source: {data.get('source', 'Unknown')}")
                print(f"   URL: {data.get('url', 'Unknown')}")

        return True

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Test started...")

    success = test_tavily_search()

    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")