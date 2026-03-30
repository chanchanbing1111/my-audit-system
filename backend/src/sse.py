from fastapi import APIRouter, HTTPException, Request
from sse_starlette import EventSourceResponse
import json
import os
from typing import AsyncGenerator
from src.audit_engine import AuditEngine

# 定义为 router，这是最标准的做法
router = APIRouter()

class SSEStreamer:
    def __init__(self):
        self.engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))

    async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
        try:
            # 1. 发送“开始”日志，让前端知道在动了
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": f"🔍 正在启动审计引擎: {company_name}..."})
            }

            # 2. 执行审计（最耗时的一步）
            result = self.engine.run_audit(company_name)
            
            # 3. 发送过程日志（让前端左侧的日志栏跳动）
            if "logs" in result:
                for log in result["logs"]:
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "log", "content": log})
                    }

            # 4. ✨ 核心修改：发送数据给前端的图表和面板
            # 对应前端的 case 'metrics'
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "metrics",
                    "metrics": result.get("metrics", {}),  # 这里包含健康度指标
                    "charts": result.get("charts", {}),    # 如果你有图表数据
                    "metrics_details": result.get("metrics_details", {})
                })
            }
            
            # 5. 发送完成信号
            yield {
                "event": "complete",
                "data": json.dumps({"success": True, "company": company_name})
            }
            
        except Exception as e:
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "message": str(e)})
            }
@router.get("/audit")
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    streamer = SSEStreamer()
    return EventSourceResponse(streamer.stream_workflow(company_name))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "ready"}
