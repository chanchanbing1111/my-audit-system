import json
import asyncio
import os
import logging
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from src.audit_engine import AuditEngine

router = APIRouter()
logger = logging.getLogger(__name__)

# 💡 关键：将引擎改为按需延迟加载，防止启动时 Key 缺失导致 500
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            raise ValueError("TAVILY_API_KEY is missing in environment variables")
        _engine = AuditEngine(tavily_api_key=api_key)
    return _engine

async def event_generator(company_name: str):
    try:
        # 1. 立即尝试获取引擎
        engine = get_engine()
        
        # 2. 发送初始心跳
        yield {"event": "message", "data": json.dumps({"type": "log", "content": "🚀 引擎已就绪..."})}
        
        # ... 你的 initial_input 和 astream 逻辑 ...
        # 注意：在这里先写一个最简单的测试循环，确认 SSE 能跑通
        for i in range(3):
            yield {"event": "message", "data": json.dumps({"type": "log", "content": f"正在准备数据 ({i+1})..."}) }
            await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"STREAM ERROR: {str(e)}")
        yield {"event": "message", "data": json.dumps({"type": "error", "content": str(e)})}

@router.get("/audit")
async def stream_audit(request: Request, company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    
    # 💡 增加装饰器处理，防止 Railway 的反向代理断连
    return EventSourceResponse(
        event_generator(company_name),
        ping=20,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        }
    )
