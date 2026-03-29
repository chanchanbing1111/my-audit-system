#!/usr/bin/env python3
"""
Comprehensive test script for Tesla TSLA audit with detailed verification
"""
import os
import sys
import json
import time
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['TAVILY_API_KEY'] = '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'

from src.graph import FinancialAuditWorkflow, AgentState
from src.agents.intent_agent import IntentDetectionAgent
from src.agents.tavily_agent import TavilySearchAgent
from src.agents.financial_agent import FinancialDataAgent
from src.agents.report_agent import ReportGenerationAgent

def test_tesla_audit():
    """Test Tesla TSLA audit with detailed verification"""
    print("="*70)
    print("COMPREHENSIVE TESLA (TSLA) AUDIT TEST")
    print("="*70)

    query = "Analyze Tesla (TSLA) financial performance and risks for 2023-2025"
    print(f"Query: {query}")

    # Step 1: Test Intent Detection
    print("\n" + "SECTION 1: Intent Detection")
    print("-"*40)

    workflow = FinancialAuditWorkflow()
    state = AgentState.create_with_audit_years()
    state.intent = query

    intent_agent = IntentDetectionAgent()
    state = intent_agent.process(state)

    print(f"Detected Intent: {state.intent}")
    print(f"Audit Years: {state.get_audit_years()}")
    print(f"Logs: {state.logs[-2:]}")

    # Step 2: Test Tavily Search with Detailed Logging
    print("\n" + "SECTION 2: Tavily Web Search")
    print("-"*40)

    tavily_agent = TavilySearchAgent(api_key=os.getenv('TAVILY_API_KEY'))

    # Print actual search query being sent
    print(f"Search Query: Tesla TSLA financial report 2023 2024 2025")
    print(f"API Endpoint: https://api.tavily.com/search")

    start_time = time.time()

    try:
        state = tavily_agent.process(state, search_depth="advanced")

        search_time = time.time() - start_time
        print(f"Search Time: {search_time:.2f} seconds")
        print(f"Results Found: {len(state.financial_data)} data points")

        # Print search results
        for i, data in enumerate(state.financial_data):
            print(f"\nResult {i+1}:")
            print(f"   Year: {data.year}")
            print(f"   Source: {data.source}")
            print(f"   Title: {data.title[:100]}...")
            print(f"   URL: {data.url}")

            # Extract and show key metrics
            if hasattr(data, 'revenue') and data.revenue:
                print(f"   Revenue: ${data.revenue:,.2f}")
            if hasattr(data, 'net_income') and data.net_income:
                print(f"   Net Income: ${data.net_income:,.2f}")
            if hasattr(data, 'eps') and data.eps:
                print(f"   EPS: ${data.eps:.4f}")

        # Verify years
        years_found = [d.year for d in state.financial_data]
        print(f"\nYears Found: {years_found}")
        required_years = [2023, 2024, 2025]
        print(f"Required Years: {required_years}")
        print(f"Coverage: {set(years_found) & set(required_years)}")

    except Exception as e:
        print(f"Search Error: {str(e)}")
        return False

    # Step 3: Test Financial Data Extraction
    print("\n" + "SECTION 3: Financial Analysis")
    print("-"*40)

    financial_agent = FinancialDataAgent()

    try:
        state = financial_agent.process(state)

        if hasattr(state, 'analysis_metrics'):
            metrics = state.analysis_metrics
            print(f"Health Score: {metrics.get('health', {}).get('overall', 'unknown')}")
            print(f"Anomalies: {len(metrics.get('anomalies', []))}")

            # Show revenue for 2024
            if hasattr(state, 'financial_data'):
                for data in state.financial_data:
                    if data.year == 2024 and hasattr(data, 'revenue'):
                        print(f"\n2024 Revenue: ${data.revenue:,.2f}")
                        break

    except Exception as e:
        print(f"Analysis Error: {str(e)}")
        return False

    # Step 4: Test Report Generation
    print("\n" + "SECTION 4: Report Generation")
    print("-"*40)

    report_agent = ReportGenerationAgent()

    try:
        state = report_agent.process(state)

        if state.report:
            print(f"Report Generated: {len(state.report)} characters")
            print("\nReport Preview:")
            print("-"*40)
            print(state.report[:500] + "...")
            print("-"*40)
        else:
            print("No Report Generated")

    except Exception as e:
        print(f"Report Error: {str(e)}")
        return False

    # Step 5: Verification Summary
    print("\n" + "VERIFICATION SUMMARY")
    print("-"*40)

    # Check for real URLs
    real_urls = []
    for data in state.financial_data:
        if 'tesla.com' in data.url or 'sec.gov' in data.url or 'reuters.com' in data.url:
            real_urls.append(data.url)

    print(f"Real Source URLs Found:")
    for i, url in enumerate(real_urls[:3], 1):
        print(f"   {i}. {url}")

    # Check for financial data
    has_revenue = any(hasattr(d, 'revenue') and d.revenue for d in state.financial_data)
    has_years = set([d.year for d in state.financial_data]) & {2023, 2024, 2025}

    print(f"\nVerification Results:")
    print(f"   - Real source URLs found: {len(real_urls)}")
    print(f"   - Financial data available: {has_revenue}")
    print(f"   - Required years covered: {len(has_years)}/3")

    if len(real_urls) > 0 and has_revenue and len(has_years) > 0:
        print(f"\nSUCCESS: Audit verified with real data!")
        return True
    else:
        print(f"\nISSUE: Audit verification failed")
        return False

if __name__ == "__main__":
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    success = test_tesla_audit()

    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Result: {'PASSED' if success else 'FAILED'}")