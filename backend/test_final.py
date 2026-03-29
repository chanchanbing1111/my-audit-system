#!/usr/bin/env python3
"""
Final test for the complete system
"""
import os
import sys
import asyncio

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['TAVILY_API_KEY'] = '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'

async def test_workflow():
    """Test the complete workflow"""
    print("Testing Sentient Audit System...")

    try:
        # Import and test workflow
        from src.graph import FinancialAuditWorkflow

        workflow = FinancialAuditWorkflow()

        # Test with a query
        query = "Analyze financial performance for 2022-2024"
        print(f"\nTesting with query: {query}")
        print("-" * 50)

        # Run workflow and collect results
        results = []
        async for result in workflow.run_workflow_async(query):
            results.append(result)
            print(f"Step: {result['step']}")
            print(f"Status: {result['status']}")

            if 'error' in result:
                print(f"ERROR: {result['error']}")
                break

            if 'logs' in result:
                for log in result['logs']:
                    print(f"  LOG: {log}")

            if result.get('step') == 'completed':
                print("\nFINAL RESULT:")
                print(f"Health Score: {result.get('health_score', 'unknown')}")
                print(f"Financial Data Points: {result.get('financial_data_count', 0)}")
                print(f"Report Available: {result.get('has_report', False)}")
                break

        print(f"\nTotal steps completed: {len(results)}")
        return True

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_workflow())
    print(f"\nSystem test {'PASSED' if success else 'FAILED'}")