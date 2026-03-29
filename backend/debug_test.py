import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.state import AgentState, AnnualData, create_sample_financial_data
from src.agents.financial_agent import FinancialDataAgent

# Create test data
state = AgentState.create_with_audit_years()
state.financial_data = create_sample_financial_data()

print("Financial data created:")
for data in state.financial_data:
    print(f"  {data.year}: assets={data.assets}, liabilities={data.liabilities}, equity={data.equity}")

# Run financial analysis
agent = FinancialDataAgent()
state = agent.process(state)

print(f"\nAnalysis metrics: {agent.analysis_metrics}")
print(f"Health: {agent.analysis_metrics.get('health', {})}")