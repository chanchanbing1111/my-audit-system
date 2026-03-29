from typing import Dict, List, Optional, Tuple
import statistics
from state import AgentState, AnnualData

class FinancialDataAgent:
    """Agent to analyze and process financial data"""

    def __init__(self):
        self.analysis_metrics = {
            'growth_rates': {},
            'ratios': {},
            'trends': {},
            'anomalies': []
        }

    def calculate_growth_rate(self, current_value: float, previous_value: float) -> float:
        """Calculate year-over-year growth rate"""
        if previous_value == 0:
            return 0.0
        return ((current_value - previous_value) / previous_value) * 100

    def calculate_financial_ratios(self, data: AnnualData) -> Dict[str, float]:
        """Calculate key financial ratios"""
        ratios = {}

        # Liquidity ratios
        ratios['current_ratio'] = data.assets / data.liabilities if data.liabilities > 0 else 0

        # Profitability ratios
        ratios['profit_margin'] = (data.net_profit / data.revenue) * 100 if data.revenue > 0 else 0
        ratios['net_profit_margin'] = ratios['profit_margin']  # Alias for consistency
        ratios['return_on_equity'] = (data.net_profit / data.equity) * 100 if data.equity > 0 else 0

        # Efficiency ratio
        ratios['asset_turnover'] = data.revenue / data.assets if data.assets > 0 else 0

        # Solvency ratio
        ratios['debt_to_equity'] = data.liabilities / data.equity if data.equity > 0 else 0

        return ratios

    def analyze_trends(self, financial_data: List[AnnualData]) -> Dict[str, List[float]]:
        """Analyze trends over time"""
        if len(financial_data) < 2:
            return {}

        trends = {}
        sorted_data = sorted(financial_data, key=lambda x: x.year)

        # Calculate trends for each metric
        metrics = ['assets', 'liabilities', 'equity', 'revenue', 'net_profit', 'cash_flow']
        for metric in metrics:
            values = [getattr(data, metric) for data in sorted_data]
            growth_rates = []

            for i in range(1, len(values)):
                growth = self.calculate_growth_rate(values[i], values[i-1])
                growth_rates.append(growth)

            trends[metric] = {
                'values': values,
                'growth_rates': growth_rates,
                'avg_growth': statistics.mean(growth_rates) if growth_rates else 0,
                'trend_direction': self._determine_trend(growth_rates)
            }

        return trends

    def _determine_trend(self, growth_rates: List[float]) -> str:
        """Determine overall trend direction"""
        if not growth_rates:
            return 'stable'

        positive_count = sum(1 for rate in growth_rates if rate > 0)
        negative_count = sum(1 for rate in growth_rates if rate < 0)

        if positive_count > negative_count:
            return 'increasing'
        elif negative_count > positive_count:
            return 'decreasing'
        else:
            return 'stable'

    def detect_anomalies(self, financial_data: List[AnnualData]) -> List[Dict]:
        """Detect financial anomalies"""
        anomalies = []

        if len(financial_data) < 2:
            return anomalies

        sorted_data = sorted(financial_data, key=lambda x: x.year)

        # Check for unusual growth rates
        for i in range(1, len(sorted_data)):
            current = sorted_data[i]
            previous = sorted_data[i-1]

            # Check for extreme growth (>100% or <-50%)
            metrics = ['revenue', 'assets', 'net_profit']
            for metric in metrics:
                growth_rate = self.calculate_growth_rate(
                    getattr(current, metric),
                    getattr(previous, metric)
                )

                if abs(growth_rate) > 100:  # Extreme growth
                    anomalies.append({
                        'type': 'extreme_growth',
                        'year': current.year,
                        'metric': metric,
                        'growth_rate': growth_rate,
                        'severity': 'high' if abs(growth_rate) > 200 else 'medium'
                    })

            # Check for negative equity
            if current.equity < 0:
                anomalies.append({
                    'type': 'negative_equity',
                    'year': current.year,
                    'value': current.equity,
                    'severity': 'high'
                })

        return anomalies

    def analyze_company_health(self, financial_data: List[AnnualData]) -> Dict[str, str]:
        """Overall company health assessment"""
        if not financial_data:
            return {'overall': 'unknown'}

        latest = financial_data[-1]
        health_indicators = {}

        # Calculate ratios for latest year
        ratios = self.calculate_financial_ratios(latest)

        # Profitability
        profit_margin = ratios.get('profit_margin', 0)
        if profit_margin > 10:
            health_indicators['profitability'] = 'excellent'
        elif profit_margin > 5:
            health_indicators['profitability'] = 'good'
        elif profit_margin > 0:
            health_indicators['profitability'] = 'fair'
        else:
            health_indicators['profitability'] = 'poor'

        # Liquidity
        current_ratio = ratios.get('current_ratio', 0)
        if current_ratio > 2:
            health_indicators['liquidity'] = 'excellent'
        elif current_ratio > 1.5:
            health_indicators['liquidity'] = 'good'
        elif current_ratio > 1:
            health_indicators['liquidity'] = 'fair'
        else:
            health_indicators['liquidity'] = 'poor'

        # Solvency
        debt_to_equity = ratios.get('debt_to_equity', 0)
        if debt_to_equity < 0.5:
            health_indicators['solvency'] = 'excellent'
        elif debt_to_equity < 1:
            health_indicators['solvency'] = 'good'
        elif debt_to_equity < 2:
            health_indicators['solvency'] = 'fair'
        else:
            health_indicators['solvency'] = 'poor'

        # Overall health
        excellent_count = sum(1 for v in health_indicators.values() if v == 'excellent')
        good_count = sum(1 for v in health_indicators.values() if v == 'good')
        poor_count = sum(1 for v in health_indicators.values() if v == 'poor')

        if excellent_count >= 2:
            health_indicators['overall'] = 'excellent'
        elif excellent_count + good_count >= 2:
            health_indicators['overall'] = 'good'
        elif poor_count >= 2:
            health_indicators['overall'] = 'poor'
        else:
            health_indicators['overall'] = 'fair'

        return health_indicators

    def process(self, state: AgentState) -> AgentState:
        """Process financial data analysis"""
        if not state.financial_data:
            state.add_log("WARNING: No financial data to analyze")
            return state

        state.add_log("Starting financial data analysis...")

        # Initialize analysis metrics
        self.analysis_metrics = {
            'growth_rates': {},
            'ratios': {},
            'trends': {},
            'anomalies': []
        }

        # Analyze each year
        for data in state.financial_data:
            ratios = self.calculate_financial_ratios(data)
            state.add_log(f"Year {data.year} - ROE: {ratios.get('return_on_equity', 0):.2f}%, Profit Margin: {ratios.get('profit_margin', 0):.2f}%")

        # Analyze trends
        trends = self.analyze_trends(state.financial_data)
        state.add_log(f"Analysis complete. Found {len(trends)} trend metrics")

        # Detect anomalies
        anomalies = self.detect_anomalies(state.financial_data)
        if anomalies:
            state.add_log(f"WARNING: Detected {len(anomalies)} anomalies")
            for anomaly in anomalies[:3]:  # Log first 3 anomalies
                state.add_log(f"  - {anomaly['type']} in {anomaly['year']}: {anomaly.get('metric', 'N/A')}")

        # Assess overall health
        health = self.analyze_company_health(state.financial_data)
        state.add_log(f"Overall company health: {health.get('overall', 'unknown').upper()}")

        # Store analysis results
        self.analysis_metrics['trends'] = trends
        self.analysis_metrics['anomalies'] = anomalies
        self.analysis_metrics['health'] = health

        state.add_log("Financial analysis completed successfully")
        return state