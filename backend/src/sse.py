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
            result = self.engine.run_audit(company_name)
            # ... (保持你之前的 yield 逻辑不变) ...
            yield {"event": "complete", "data": json.dumps({"success": True, "company": company_name})}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"type": "error", "message": str(e)})}

@router.post("/audit")
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    streamer = SSEStreamer()
    return EventSourceResponse(streamer.stream_workflow(company_name))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "ready"}
