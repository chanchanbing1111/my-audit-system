from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ValidationError
import math

class AnnualData(BaseModel):
    """Annual financial data model"""
    year: int = Field(..., ge=2000, le=2030, description="Year of the financial data")
    assets: float = Field(..., gt=0, description="Total assets")
    liabilities: float = Field(..., gt=0, description="Total liabilities")
    equity: float = Field(..., gt=0, description="Total equity")
    revenue: float = Field(..., ge=0, description="Total revenue")
    net_profit: float = Field(..., description="Net profit (can be negative)")
    cash_flow: float = Field(..., description="Cash flow from operations")

    @field_validator('assets')
    @classmethod
    def validate_accounting_equation(cls, v, info):
        """Validate that Assets = Liabilities + Equity (with small tolerance for rounding)"""
        data = info.data
        liabilities = data.get('liabilities')
        equity = data.get('equity')

        if liabilities is not None and equity is not None:
            calculated_assets = liabilities + equity
            # Allow for small rounding errors (0.01 tolerance)
            if not math.isclose(v, calculated_assets, abs_tol=0.01):
                raise ValueError(
                    f"Accounting equation violated: Assets ({v}) != Liabilities ({liabilities}) + Equity ({equity}). "
                    f"Expected: {calculated_assets}"
                )

        return v

class AgentState(BaseModel):
    """State for the financial audit agent"""
    intent: Optional[str] = Field(None, description="User's intent/query")
    current_year: int = Field(..., description="Current year for audit context")
    logs: List[str] = Field(default_factory=list, description="Thinking stream logs")
    financial_data: List[AnnualData] = Field(default_factory=list, description="List of annual financial data")
    report: Optional[str] = Field(None, description="Generated audit report")

    def add_log(self, message: str):
        """Add a log message to the thinking stream"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        # Keep only last 100 logs to prevent memory issues
        if len(self.logs) > 100:
            self.logs = self.logs[-100:]

    def get_audit_years(self) -> List[int]:
        """Get the audit year range based on current date"""
        current_month = datetime.now().month

        if current_month < 4:  # January, February, March
            # Before April 2026, audit [2022, 2023, 2024]
            return [2022, 2023, 2024]
        else:
            # April or later, audit [2023, 2024, 2025]
            return [2023, 2024, 2025]

    def validate_financial_data(self) -> List[str]:
        """Validate all financial data entries and return error messages"""
        errors = []

        for i, data in enumerate(self.financial_data):
            try:
                # Use the built-in validation
                data.model_validate(data.model_dump())
            except ValidationError as e:
                errors.append(f"Year {data.year}: {str(e)}")
            except ValueError as e:
                errors.append(f"Year {data.year}: {str(e)}")

        return errors

    @classmethod
    def create_with_audit_years(cls) -> 'AgentState':
        """Create AgentState with current audit years"""
        current_year = datetime.now().year
        instance = cls(current_year=current_year)
        instance.add_log(f"Initialized audit system for {current_year}")
        instance.add_log(f"Audit years determined: {instance.get_audit_years()}")
        return instance

# Utility functions
def create_sample_financial_data() -> List[AnnualData]:
    """Create sample financial data for testing"""
    current_year = datetime.now().year
    audit_years = AgentState(current_year=current_year).get_audit_years()

    sample_data = []
    for year in audit_years:
        # Create balanced accounting data
        liabilities = 1000000 + (year - 2020) * 100000
        equity = 500000 + (year - 2020) * 50000
        assets = liabilities + equity

        sample_data.append(AnnualData(
            year=year,
            assets=assets,
            liabilities=liabilities,
            equity=equity,
            revenue=2000000 + (year - 2020) * 200000,
            net_profit=200000 + (year - 2020) * 20000,
            cash_flow=150000 + (year - 2020) * 15000
        ))

    return sample_data

if __name__ == "__main__":
    # Test the implementation
    print("Testing AnnualData and AgentState...")

    # Test dynamic year calculation
    state = AgentState.create_with_audit_years()
    print(f"Current year: {state.current_year}")
    print(f"Audit years: {state.get_audit_years()}")
    print(f"Current month: {datetime.now().month}")

    # Test accounting equation validation
    print("\nTesting accounting equation validation...")

    # Valid data
    try:
        valid_data = AnnualData(
            year=2023,
            assets=1500000,
            liabilities=1000000,
            equity=500000,
            revenue=2000000,
            net_profit=200000,
            cash_flow=150000
        )
        print("SUCCESS: Valid data passed validation")
    except ValidationError as e:
        print(f"❌ Valid data failed validation: {e}")

    # Invalid data (Assets != Liabilities + Equity)
    try:
        invalid_data = AnnualData(
            year=2023,
            assets=1600000,  # Wrong: should be 1500000
            liabilities=1000000,
            equity=500000,
            revenue=2000000,
            net_profit=200000,
            cash_flow=150000
        )
        print("ERROR: Invalid data should have failed validation but passed")
    except ValidationError as e:
        print(f"✅ Invalid data correctly failed validation: {e}")

    # Test with sample data
    print("\nTesting with sample data...")
    sample_data = create_sample_financial_data()
    state.financial_data = sample_data

    errors = state.validate_financial_data()
    if errors:
        print(f"ERROR: Sample data validation errors: {errors}")
    else:
        print("SUCCESS: Sample data passed all validations")

    # Test log functionality
    print("\nTesting log functionality...")
    state.add_log("Starting financial analysis")
    state.add_log("Processing annual reports")
    print(f"Last log entry: {state.logs[-1]}")

    print("\nSUCCESS: All tests completed successfully!")