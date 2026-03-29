from fastapi import APIRouter, HTTPException, Request
from sse_starlette import EventSourceResponse
import json
import asyncio
import os
from typing import AsyncGenerator, Dict, Any
from src.audit_engine import AuditEngine

# 1. 这里定义为 app，解决你的 ImportError
app = APIRouter()

class SSEStreamer:
    """处理审计流程的 SSE 流"""

    def __init__(self):
        # 自动获取环境变量中的 API Key
        self.engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))

    async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
        """将审计步骤作为 SSE 事件发送"""
        try:
            # 执行审计引擎
            result = self.engine.run_audit(company_name)

            if result.get("status") == "error":
                yield {
                    "event": "error",
                    "data": json.dumps({
                        'type': 'error',
                        'message': result.get('error', '未知错误'),
                        'logs': result.get('logs', [])
                    })
                }
                return

            # 发送开始事件
            yield {
                "event": "start",
                "data": json.dumps({
                    'type': 'start',
                    'company': company_name,
                    'timestamp': result.get('execution_time', '')
                })
            }

            # 发送日志
            if 'logs' in result and result['logs']:
                for log in result['logs']:
                    yield {
                        "event": "log",
                        "data": json.dumps({'type': 'log', 'message': log})
                    }

            # 发送核心指标和图表数据
            metrics = result.get('metrics', {})
            health_data = metrics.get('health', {})
            
            yield {
                "event": "metrics",
                "data": json.dumps({
                    'type': 'metrics',
                    'health_score': health_data.get('overall', 0),
                    'status': health_data.get('status', 'unknown'),
                    'anomaly_count': health_data.get('anomaly_count', 0),
                    'metrics_details': metrics
                })
            }

            # 发送完成事件
            yield {
                "event": "complete",
                "data": json.dumps({
                    'type': 'complete',
                    'success': True,
                    'company': company_name
                })
            }

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({'type': 'error', 'message': str(e)})
            }

# --- 路由定义使用 app ---

@app.post("/audit")
async def stream_audit(request: Request, company_name: str):
    if not company_name or not company_name.strip():
        raise HTTPException(status_code=400, detail="公司名称不能为空")
    try:
        streamer = SSEStreamer()
        return EventSourceResponse(streamer.stream_workflow(company_name))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "tavily_api_configured": bool(os.getenv('TAVILY_API_KEY')),
        "version": "1.0.0"
    }

@app.post("/audit/full")
async def run_audit_full(company_name: str):
    try:
        engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))
        return engine.run_audit(company_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
