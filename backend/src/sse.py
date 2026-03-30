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
            # 🚀 第一步：立即发报，防止浏览器超时报错
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": f"🚀 正在连接审计服务器..."})
            }
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": f"📊 目标确认：{company_name}，正在检索财报..."})
            }

            # 🛠 第二步：执行耗时任务（AI 搜索和分析）
            result = self.engine.run_audit(company_name)
            
            # 📝 第三步：发送 AI 运行过程中的所有日志
            if "logs" in result:
                for log in result["logs"]:
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "log", "content": log})
                    }

            # 📈 第四步：发送核心指标（对应前端的 case 'metrics'）
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "metrics",
                    "metrics": result.get("metrics", {}),
                    "charts": result.get("charts", {}),
                    "metrics_details": result.get("metrics_details", {})
                })
            }
            
            # ✅ 第五步：发送完成信号
            yield {
                "event": "complete",
                "data": json.dumps({"success": True, "company": company_name})
            }
            
        except Exception as e:
            # 如果中间断了，也要告诉前端原因
            yield {
                "event": "message",
                "data": json.dumps({"type": "error", "content": f"审计中断: {str(e)}"})
            }
@router.get("/audit/")
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    streamer = SSEStreamer()
    return EventSourceResponse(streamer.stream_workflow(company_name))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "ready"}
