from typing import Dict, List, Optional
import sys
import os
import asyncio

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from state import AgentState, AnnualData, create_sample_financial_data
from agents.intent_agent import IntentDetectionAgent
from agents.tavily_agent import TavilySearchAgent
from agents.financial_agent import FinancialDataAgent
from agents.report_agent import ReportGenerationAgent

class FinancialAuditWorkflow:
    """Simple workflow for financial audit without LangGraph dependency"""

    def __init__(self, tavily_api_key: Optional[str] = None):
        self.agents = {
            'intent': IntentDetectionAgent(),
            'tavily': TavilySearchAgent(api_key=tavily_api_key) if tavily_api_key else None,
            'financial': FinancialDataAgent(),
            'report': ReportGenerationAgent()
        }
        self.tavily_enabled = tavily_api_key is not None

    def run_workflow(self, user_query: str):
        """Run the complete audit workflow"""
        # Initialize state
        state = AgentState.create_with_audit_years()
        state.intent = user_query

        # Step 1: Intent Detection
        try:
            state = self.agents['intent'].process(state)
            yield {
                'step': 'intent_detection',
                'status': 'completed',
                'intent': state.intent,
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
        except Exception as e:
            yield {
                'step': 'intent_detection',
                'status': 'error',
                'error': str(e),
                'logs': state.logs
            }
            return

        # Step 2: Tavily Search
        try:
            if not self.tavily_enabled:
                raise RuntimeError("TAVILY_API_KEY environment variable is required but not set")

            state = self.agents['tavily'].process(state, search_depth="advanced")

            yield {
                'step': 'data_collection',
                'status': 'completed',
                'data_points': len(state.financial_data),
                'years': [d.year for d in state.financial_data],
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
        except Exception as e:
            yield {
                'step': 'data_collection',
                'status': 'error',
                'error': str(e),
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
            return

        # Step 3: Financial Analysis
        try:
            state = self.agents['financial'].process(state)
            yield {
                'step': 'financial_analysis',
                'status': 'completed',
                'health_score': state.analysis_metrics.get('health', {}).get('overall', 'unknown') if hasattr(state, 'analysis_metrics') else 'unknown',
                'anomalies_count': len(state.analysis_metrics.get('anomalies', [])) if hasattr(state, 'analysis_metrics') else 0,
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
        except Exception as e:
            yield {
                'step': 'financial_analysis',
                'status': 'error',
                'error': str(e),
                'logs': state.logs
            }
            return

        # Step 4: Report Generation
        try:
            state = self.agents['report'].process(state)
            yield {
                'step': 'report_generation',
                'status': 'completed',
                'report_length': len(state.report) if state.report else 0,
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
        except Exception as e:
            yield {
                'step': 'report_generation',
                'status': 'error',
                'error': str(e),
                'logs': state.logs
            }
            return

        # Final result
        yield {
            'step': 'completed',
            'status': 'success',
            'intent': state.intent,
            'financial_data_count': len(state.financial_data),
            'has_report': state.report is not None,
            'health_score': state.analysis_metrics.get('health', {}).get('overall', 'unknown') if hasattr(state, 'analysis_metrics') else 'unknown',
            'final_logs': state.logs,
            'report': state.report
        }

    async def run_workflow_async(self, user_query: str):
        """Async version of run_workflow"""
        loop = asyncio.get_event_loop()

        # Run the generator in a thread pool executor
        def run_sync():
            return self.run_workflow(user_query)

        # Convert generator to async generator
        executor = loop.run_in_executor(None, run_sync)
        results = await executor

        for result in results:
            yield result
            await asyncio.sleep(0.1)  # Small delay between events
        # Initialize state
        state = AgentState.create_with_audit_years()
        state.intent = user_query

        # Step 1: Intent Detection
        try:
            state = self.agents['intent'].process(state)
            yield {
                'step': 'intent_detection',
                'status': 'completed',
                'intent': state.intent,
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
        except Exception as e:
            yield {
                'step': 'intent_detection',
                'status': 'error',
                'error': str(e),
                'logs': state.logs
            }
            return

        # Step 2: Tavily Search
        try:
            if not self.tavily_enabled:
                raise RuntimeError("TAVILY_API_KEY environment variable is required but not set")

            state = self.agents['tavily'].process(state, search_depth="advanced")

            yield {
                'step': 'data_collection',
                'status': 'completed',
                'data_points': len(state.financial_data),
                'years': [d.year for d in state.financial_data],
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
        except Exception as e:
            yield {
                'step': 'data_collection',
                'status': 'error',
                'error': str(e),
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
            return

        # Step 3: Financial Analysis
        try:
            state = self.agents['financial'].process(state)
            yield {
                'step': 'financial_analysis',
                'status': 'completed',
                'health_score': state.analysis_metrics.get('health', {}).get('overall', 'unknown') if hasattr(state, 'analysis_metrics') else 'unknown',
                'anomalies_count': len(state.analysis_metrics.get('anomalies', [])) if hasattr(state, 'analysis_metrics') else 0,
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
        except Exception as e:
            yield {
                'step': 'financial_analysis',
                'status': 'error',
                'error': str(e),
                'logs': state.logs
            }
            return

        # Step 4: Report Generation
        try:
            state = self.agents['report'].process(state)
            yield {
                'step': 'report_generation',
                'status': 'completed',
                'report_length': len(state.report) if state.report else 0,
                'logs': state.logs[-2:] if len(state.logs) >= 2 else state.logs
            }
        except Exception as e:
            yield {
                'step': 'report_generation',
                'status': 'error',
                'error': str(e),
                'logs': state.logs
            }
            return

        # Final result
        yield {
            'step': 'completed',
            'status': 'success',
            'intent': state.intent,
            'financial_data_count': len(state.financial_data),
            'has_report': state.report is not None,
            'health_score': state.analysis_metrics.get('health', {}).get('overall', 'unknown') if hasattr(state, 'analysis_metrics') else 'unknown',
            'final_logs': state.logs,
            'report': state.report
        }

    def run_single_step(self, user_query: str, step: str) -> Dict:
        """Run a single step of the workflow"""
        # This would be used for step-by-step execution in a real system
        # For now, we'll just return a placeholder
        return {
            'step': step,
            'status': 'not_implemented',
            'message': 'Single-step execution not implemented in this version'
        }

# Example usage and testing
if __name__ == "__main__":
    print("Testing Financial Audit Workflow...")

    # Create workflow instance
    workflow = FinancialAuditWorkflow()

    # Test query
    test_query = "Analyze the financial performance and risks for the company"
    print(f"Query: {test_query}")

    # Run workflow step by step
    print("\nPROCESSING: Running workflow step by step...\n")

    for result in workflow.run_workflow(test_query):
        print(f"Step: {result['step']}")
        print(f"Status: {result['status']}")

        if 'error' in result:
            print(f"ERROR: Error: {result['error']}")

        if 'logs' in result:
            print("Logs:")
            for log in result['logs']:
                print(f"  - {log}")

        if 'intent' in result:
            print(f"Intent: {result['intent']}")

        if 'data_points' in result:
            print(f"Data points collected: {result['data_points']}")
            print(f"Years: {result.get('years', [])}")

        if 'health_score' in result:
            print(f"Health score: {result['health_score']}")

        if 'anomalies_count' in result:
            print(f"Anomalies detected: {result['anomalies_count']}")

        if 'report_length' in result:
            print(f"Report length: {result['report_length']} characters")

        if 'report' in result and result['report']:
            print("\nREPORT: Report preview (first 300 chars):")
            print(result['report'][:300] + "...")

        print("-" * 50)

    print("\nSUCCESS: Workflow test completed!")