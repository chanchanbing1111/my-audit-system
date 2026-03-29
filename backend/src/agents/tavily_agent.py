import os
from typing import Dict, List, Optional
import httpx
from ..state import AgentState, AnnualData

class TavilySearchAgent:
    """Agent to search for financial data using Tavily API"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('TAVILY_API_KEY')
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")

        self.base_url = "https://api.tavily.com"
        self.client = httpx.Client(timeout=30.0)

    def build_search_query(self, query: str, years: List[int]) -> str:
        """Build optimized search query for financial data"""
        year_str = ", ".join(map(str, years))
        return f"""
        {query} financial statements annual report
        for years {year_str}
        balance sheet income statement cash flow
        assets liabilities equity revenue profit
        """

    def search_financial_data(self, query: str, years: List[int], search_depth: str = "advanced") -> Dict:
        """Search for financial data using Tavily"""
        search_query = self.build_search_query(query, years)

        state_data = {
            "query": query,
            "years": years,
            "search_depth": search_depth,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }

        try:
            state.add_log(f"Starting Tavily search for: {search_query}")

            # Tavily API request
            response = self.client.post(
                f"{self.base_url}/search",
                json={
                    "query": search_query,
                    "api_key": self.api_key,
                    "search_depth": search_depth,
                    "max_results": 10,
                    "include_answer": True
                }
            )

            if response.status_code == 200:
                results = response.json()
                state.add_log(f"Tavily search successful. Found {len(results.get('results', []))} results.")
                return {"success": True, "data": results, "state": state_data}
            else:
                error_msg = f"Tavily API error: {response.status_code}"
                state.add_log(f"ERROR: {error_msg}")
                return {"success": False, "error": error_msg, "state": state_data}

        except httpx.RequestError as e:
            error_msg = f"HTTP request failed: {str(e)}"
            state.add_log(f"ERROR: {error_msg}")
            return {"success": False, "error": error_msg, "state": state_data}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            state.add_log(f"ERROR: {error_msg}")
            return {"success": False, "error": error_msg, "state": state_data}

    def extract_financial_info(self, search_results: Dict) -> List[AnnualData]:
        """Extract financial information from search results"""
        financial_data = []

        try:
            # In production, this would use NLP to extract structured data
            # from actual search results. For now, we'll raise an error
            # to ensure we don't use mock data.

            error_msg = "Tavily search data extraction not yet implemented. " \
                       "Please implement actual NLP extraction based on search results."
            search_results['state'].add_log(f"ERROR: {error_msg}")
            raise NotImplementedError(error_msg)

            # Placeholder for actual implementation:
            # Get the years from the original state
            # if 'state' in search_results:
            #     years = search_results['state'].get('years', [])
            # else:
            #     years = [2022, 2023, 2024]
            #
            # for year in years:
            #     # Extract actual financial data from search results
            #     # This would involve parsing HTML, PDFs, or structured data
            #     pass

            return financial_data

        except Exception as e:
            error_msg = f"Failed to extract financial data: {str(e)}"
            search_results['state'].add_log(f"ERROR: {error_msg}")
            return []

    def process(self, state: AgentState, search_depth: str = "advanced") -> AgentState:
        """Process Tavily search"""
        if not state.intent:
            state.add_log("ERROR: No intent detected. Skipping Tavily search.")
            return state

        # Get audit years
        audit_years = state.get_audit_years()
        state.add_log(f"Preparing to search for data from years: {audit_years}")

        # Perform search
        search_result = self.search_financial_data(
            query=state.intent,
            years=audit_years,
            search_depth=search_depth
        )

        if search_result["success"]:
            # Extract financial data
            financial_data = self.extract_financial_info(search_result)
            state.financial_data = financial_data
            state.add_log(f"Successfully extracted {len(financial_data)} annual records")
        else:
            state.add_log(f"Search failed: {search_result['error']}")
            raise RuntimeError(f"Tavily search failed: {search_result['error']}")

        return state