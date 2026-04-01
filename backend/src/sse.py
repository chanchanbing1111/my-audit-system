import json
import asyncio
import os
import uuid
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from src.audit_engine import AuditEngine

# 初始化日志
logger = logging.getLogger(__name__)
router = APIRouter()

class SSEStreamer:
    def __init__(self):
        # 初始化多智能体审计引擎
        # 建议在初始化时捕获 API Key，防止运行时才报错
        tavily_key = os.getenv('TAVILY_API_KEY')
        if not tavily_key:
            logger.warning("⚠️ TAVILY_API_KEY is not set!")
        self.engine = AuditEngine(tavily_api_key=tavily_key)

    # 修改 stream_workflow 函数内部
# src/sse.py

async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
    try:
        # 先发一个握手信号，确认函数进来了
        yield {"event": "message", "data": json.dumps({"type": "log", "content": "🚀 审计逻辑启动..."})}
        
        # 💡 在这里增加一个极其详细的初始化检查
        if not os.getenv('TAVILY_API_KEY'):
            raise ValueError("环境变量 TAVILY_API_KEY 缺失")

        # 启动 Graph
        async for event in self.engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
            # ... 原有逻辑
            pass

    except Exception as e:
        # 💥 关键修复：不要让程序崩溃，把错误变成消息发给前端
        import traceback
        error_stack = traceback.format_exc()
        print(f"ERROR STACK: {error_stack}") # 这行会强行打入 Railway 日志
        yield {
            "event": "message", 
            "data": json.dumps({"type": "log", "content": f"❌ 内部崩溃: {str(e)}"})
        }
@router.get("/audit")
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="请提供公司名称")
    
    streamer = SSEStreamer()
    
    # 💡 核心修改：增加 headers 解决 Railway/Nginx 缓存导致的 SSE 不实时输出
   # 在 sse.py 中修改返回部分
    return EventSourceResponse(
        streamer.stream_workflow(company_name),
        ping=15, 
        send_timeout=600,
        headers={
            # 1. 核心修复：禁止代理服务器对数据进行任何压缩或转换
            "Cache-Control": "no-cache, no-transform", 
            # 2. 确保不被 Nginx 缓存
            "X-Accel-Buffering": "no",  
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            # 3. 显式指定编码，防止中文乱码干扰协议
            "Content-Encoding": "none", 
        }
    )

@router.get("/health")
async def health_check():
    return {"status": "healthy", "mode": "multi-agent", "version": "2026.04"}
