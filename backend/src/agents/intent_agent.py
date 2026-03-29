from typing import Dict, List, Optional
from state import AgentState, AnnualData

class IntentDetectionAgent:
    """Agent to detect user's intent from query"""

    def __init__(self):
        # Simple keyword-based intent detection without external dependencies
        pass

    def detect_intent(self, query: str) -> str:
        """Detect user's intent from the query"""
        # For now, we'll use simple keyword matching
        # Later, we can integrate with LLM for more sophisticated intent detection

        query_lower = query.lower()

        # Financial analysis keywords
        if any(word in query_lower for word in ['analyze', 'analysis', 'financial', 'audit']):
            return 'financial_analysis'

        # Risk assessment keywords
        if any(word in query_lower for word in ['risk', 'risky', 'danger', 'vulnerable', 'risk assessment']):
            return 'risk_assessment'

        # Trend analysis keywords
        if any(word in query_lower for word in ['trend', 'trending', 'change over time', 'timeline', 'trend analysis']):
            return 'trend_analysis'

        # Compliance keywords
        if any(word in query_lower for word in ['compliance', 'regulation', 'legal', 'sarbanes', 'compliance check']):
            return 'compliance_check'

        # Fraud detection keywords
        if any(word in query_lower for word in ['fraud', 'fraudulent', 'embezzle', 'misrepresent', 'fraud detection']):
            return 'fraud_detection'

        # Default to general inquiry
        return 'general_inquiry'

    def process(self, state: AgentState) -> AgentState:
        """Process intent detection"""
        query = state.intent or "Analyze financial statements"
        detected_intent = self.detect_intent(query)

        state.add_log(f"Intent Detection: Query='{query}' -> Intent='{detected_intent}'")

        return state