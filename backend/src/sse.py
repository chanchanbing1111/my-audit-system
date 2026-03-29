from fastapi import APIRouter, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette import EventSourceResponse
import json
import asyncio
import os
from typing import AsyncGenerator, Dict, Any
from src.audit_engine import AuditEngine, AuditState

# 1. 初始化 Router (不要在这里 import 自己的 router)
router = APIRouter()

class SSEStreamer:
    """Handles Server-Sent Events streaming for the audit workflow with detailed metrics and charts"""

    def __init__(self):
        # 确保从环境变量获取 API Key
        self.engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))

    async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
        """Stream audit workflow execution as SSE events with detailed metrics and charts"""
        try:
            # Run the audit workflow
            result = self.engine.run_audit(company_name)

            if result.get("status") == "error":
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
            'profit_chart': {'type': 'bar', 'title': f'{company_name} 盈利能力分析', 'data': [], 'labels': []},
            'liquidity_chart': {'type': 'line', 'title': f'{company_name} 流动性分析', 'data': [], 'labels': []},
            'solvency_chart': {'type': 'bar', 'title': f'{company_name} 偿债能力分析', 'data': [], 'labels': []},
            'growth_chart': {'type': 'line', 'title': f'{company_name} 增长趋势分析', 'data': [], 'labels': []},
            'cash_flow_chart': {'type': 'bar', 'title': f'{company_name} 现金流效率分析', 'data': [], 'labels': []}
        }

        # 数据提取逻辑保持不变...
        if 'profitability' in metrics:
            for year, data in metrics['profitability'].items():
                chart_data['profit_chart']['labels'].append(str(year))
                chart_data['profit_chart']['data'].append({
                    'revenue': data.get('revenue', 0),
                    'net_income': data.get('net_income', 0),
                    'profit_margin': data.get('profit_margin', 0)
                })
        
        # (其他图表数据处理逻辑省略，保持原样即可)
        if 'liquidity' in metrics:
            for year, data in metrics['liquidity'].items():
                chart_data['liquidity_chart']['labels'].append(str(year))
                chart_data['liquidity_chart']['data'].append(data.get('current_ratio', 0))

        return chart_data

# --- API 路由定义 ---

@router.post("/audit")
async def stream_audit(request: Request, company_name: str):
    if not company_name or not company_name.strip():
        raise HTTPException(status_code=400, detail="Company name cannot be empty")
    try:
        streamer = SSEStreamer()
        return EventSourceResponse(streamer.stream_workflow(company_name))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "tavily_api_configured": bool(os.getenv('TAVILY_API_KEY')),
        "version": "1.0.0"
    }

@router.post("/audit/full")
async def run_audit_full(company_name: str):
    try:
        engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))
        return engine.run_audit(company_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
