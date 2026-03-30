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
            # 1. 运行审计引擎获取结果
            result = self.engine.run_audit(company_name)
            
            # 2. ✨ 关键：必须把审计结果发给前端！
            # 我们给它打上 type: 'log' 的标签，这样前端 handleSSEMessage 就能认出它是文字内容
            yield {
                "event": "message",  # 使用默认 message 事件，前端 onmessage 就能接到
                "data": json.dumps({
                    "type": "log", 
                    "content": result  # 这里放真正的审计分析文字
                })
            }
            
            # 3. 发送完成信号
            yield {
                "event": "complete", 
                "data": json.dumps({"success": True, "company": company_name})
            }
            
        except Exception as e:
            yield {
                "event": "error", 
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
