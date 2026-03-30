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
            # 🚀 第一步：立刻发送 3 条消息，防止 Railway 认为连接断开
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": "📡 已建立安全审计连接..."})
            }
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": f"🔍 正在锁定目标企业：{company_name}"})
            }
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": "🤖 AI 审计引擎正在进行多维度分析，这可能需要约 60 秒，请勿刷新页面..."})
            }

            # 🛠 第二步：在这里执行真正的 AI 审计（让 AI 慢慢算）
            result = self.engine.run_audit(company_name)
            
            # (剩下的代码保持不变，继续发送 logs 和 metrics)
            if "logs" in result:
                for log in result["logs"]:
                    yield {"event": "message", "data": json.dumps({"type": "log", "content": log})}

            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "metrics",
                    "metrics": result.get("metrics", {}),
                    "charts": result.get("charts", {}),
                    "metrics_details": result.get("metrics_details", {})
                })
            }
            yield {"event": "complete", "data": json.dumps({"success": True})}
            
        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}
@router.get("/audit/")
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    streamer = SSEStreamer()
    return EventSourceResponse(streamer.stream_workflow(company_name))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "ready"}
