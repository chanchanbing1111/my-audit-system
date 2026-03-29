from fastapi import APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette import EventSourceResponse
import json
import asyncio
import os
from typing import AsyncGenerator, Dict, Any
from src.audit_engine import AuditEngine, AuditState
from src.sse import router as sse_router  # Import the router for CORS configuration

# Configure CORS
app = APIRouter()

# Add CORS middleware with environment variable support
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(',')
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SSEStreamer:
    """Handles Server-Sent Events streaming for the audit workflow with detailed metrics and charts"""

    def __init__(self):
        self.engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))

    async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
        """Stream audit workflow execution as SSE events with detailed metrics and charts"""

        try:
            # Run the audit workflow
            result = self.engine.run_audit(company_name)

            if result["status"] == "error":
                # Send error event
                yield {
                    "event": "error",
                    "data": json.dumps({
                        'type': 'error',
                        'message': result.get('error', 'Unknown error occurred'),
                        'logs': result.get('logs', [])
                    })
                }
                return

            # Send initial start event
            yield {
                "event": "start",
                "data": json.dumps({
                    'type': 'start',
                    'company': company_name,
                    'timestamp': result.get('execution_time', '')
                })
            }

            # Process logs from the audit state
            if 'logs' in result and result['logs']:
                for log in result['logs']:
                    yield {
                        "event": "log",
                        "data": json.dumps({
                            'type': 'log',
                            'message': log
                        })
                    }

            # Extract metrics and prepare chart data
            metrics = result.get('metrics', {})
            health_data = metrics.get('health', {})

            # Prepare chart data for frontend
            chart_data = self._prepare_chart_data(metrics, company_name)

            # Send metrics event
            yield {
                "event": "metrics",
                "data": json.dumps({
                    'type': 'metrics',
                    'health_score': health_data.get('overall', 0),
                    'status': health_data.get('status', 'unknown'),
                    'anomaly_count': health_data.get('anomaly_count', 0),
                    'charts': chart_data,
                    'metrics_details': {
                        'profitability': metrics.get('profitability', {}),
                        'liquidity': metrics.get('liquidity', {}),
                        'solvency': metrics.get('solvency', {}),
                        'growth': metrics.get('growth', {}),
                        'efficiency': metrics.get('efficiency', {})
                    }
                })
            }

            # Send completion event
            yield {
                "event": "complete",
                "data": json.dumps({
                    'type': 'complete',
                    'success': True,
                    'company': company_name,
                    'health_score': health_data.get('overall', 0),
                    'status': health_data.get('status', 'unknown'),
                    'report_available': 'report' in result
                })
            }

        except Exception as e:
            # Send error event in case of unexpected exceptions
            yield {
                "event": "error",
                "data": json.dumps({
                    'type': 'error',
                    'message': f"Streaming error: {str(e)}",
                    'logs': []
                })
            }

    def _prepare_chart_data(self, metrics: Dict, company_name: str) -> Dict[str, Any]:
        """Prepare chart data for frontend visualization"""
        chart_data = {
            'profit_chart': {
                'type': 'bar',
                'title': f'{company_name} 盈利能力分析',
                'data': [],
                'labels': []
            },
            'liquidity_chart': {
                'type': 'line',
                'title': f'{company_name} 流动性分析',
                'data': [],
                'labels': []
            },
            'solvency_chart': {
                'type': 'bar',
                'title': f'{company_name} 偿债能力分析',
                'data': [],
                'labels': []
            },
            'growth_chart': {
                'type': 'line',
                'title': f'{company_name} 增长趋势分析',
                'data': [],
                'labels': []
            },
            'cash_flow_chart': {
                'type': 'bar',
                'title': f'{company_name} 现金流效率分析',
                'data': [],
                'labels': []
            }
        }

        # Process profitability data
        if 'profitability' in metrics:
            for year, data in metrics['profitability'].items():
                chart_data['profit_chart']['labels'].append(str(year))
                chart_data['profit_chart']['data'].append({
                    'revenue': data.get('revenue', 0),
                    'net_income': data.get('net_income', 0),
                    'profit_margin': data.get('profit_margin', 0)
                })

        # Process liquidity data
        if 'liquidity' in metrics:
            for year, data in metrics['liquidity'].items():
                chart_data['liquidity_chart']['labels'].append(str(year))
                chart_data['liquidity_chart']['data'].append(data.get('current_ratio', 0))

        # Process solvency data
        if 'solvency' in metrics:
            for year, data in metrics['solvency'].items():
                chart_data['solvency_chart']['labels'].append(str(year))
                chart_data['solvency_chart']['data'].append(data.get('debt_to_equity', 0))

        # Process growth data
        if 'growth' in metrics:
            for year, data in metrics['growth'].items():
                chart_data['growth_chart']['labels'].append(str(year))
                chart_data['growth_chart']['data'].append(data.get('revenue_growth', 0))

        # Process efficiency data
        if 'efficiency' in metrics:
            for year, data in metrics['efficiency'].items():
                chart_data['cash_flow_chart']['labels'].append(str(year))
                chart_data['cash_flow_chart']['data'].append(data.get('cash_flow_margin', 0))

        return chart_data

@router.post("/api/audit")
async def stream_audit(request: Request, company_name: str) -> EventSourceResponse:
    """
    Stream financial audit workflow execution with real-time updates and chart data

    Parameters:
    - company_name: The company name to audit (required)
    """
    if not company_name or not company_name.strip():
        raise HTTPException(status_code=400, detail="Company name cannot be empty")

    try:
        streamer = SSEStreamer()
        return EventSourceResponse(streamer.stream_workflow(company_name))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start audit stream: {str(e)}")

@router.post("/api/audit/step")
async def execute_step(company_name: str, step: str):
    """
    Execute a single step of the audit workflow (for testing)

    For testing individual steps without streaming
    """
    try:
        engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))
        # Note: AuditEngine doesn't have run_single_step, this is for compatibility
        # In production, you might want to implement this
        return {"status": "not_implemented", "message": "Single-step execution not implemented in AuditEngine"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step execution failed: {str(e)}")

# Legacy endpoint for compatibility
@router.post("/api/audit/full")
async def run_audit(company_name: str):
    """
    Run complete audit workflow and return final result (non-streaming)
    """
    try:
        engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))
        result = engine.run_audit(company_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")

@router.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "tavily_api_configured": bool(os.getenv('TAVILY_API_KEY')),
        "version": "1.0.0",
        "audit_engine_available": True
    }