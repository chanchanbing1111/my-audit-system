#!/usr/bin/env python3
"""
Simple test script to check modules can be imported
"""
import os
import sys
import json

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['TAVILY_API_KEY'] = os.getenv('TAVILY_API_KEY', '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')

def test_modules():
    """Test if all modules can be imported"""
    print("Testing module imports...")

    try:
        # Test graph module
        from src.graph import FinancialAuditWorkflow
        print("SUCCESS: FinancialAuditWorkflow imported successfully")

        # Test workflow
        workflow = FinancialAuditWorkflow()
        print("SUCCESS: FinancialAuditWorkflow instance created")

        # Test workflow with a simple query
        print("\nTesting workflow...")
        results = list(workflow.run_workflow("Analyze financial performance"))
        print(f"SUCCESS: Workflow completed with {len(results)} results")

        # Print first result
        if results:
            print(f"\nFirst result:")
            print(f"Step: {results[0].get('step')}")
            print(f"Status: {results[0].get('status')}")

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_modules()