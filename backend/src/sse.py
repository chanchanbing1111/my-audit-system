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
async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
    try:
        # 1. 立即发送握手信号
        yield {
            "event": "message", 
            "data": json.dumps({"type": "log", "content": "🚀 审计智能体集群已就绪，启动深度侦测..."})
        }

        async for event in self.engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
            for node_name, node_data in event.items():
                # 2. 只有当节点真的产生 logs 时才发送
                if "logs" in node_data and node_data["logs"]:
                    # 取最后一条日志，并强制剔除换行符 \n 和 \r
                    raw_log = str(node_data["logs"][-1])
                    clean_log = raw_log.replace("\n", " ").replace("\r", " ").strip()
                    
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "log", "content": f"[{node_name}] {clean_log}"})
                    }
                
                # 3. 发送指标数据
                if "metrics" in node_data and node_data.get("metrics"):
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "metrics",
                            "metrics": node_data["metrics"],
                            "charts": node_data.get("charts", {})
                        })
                    }
    except Exception as e:
        # 捕获异常并包装成 JSON，防止异常堆栈直接打碎 SSE 流
        yield {
            "event": "message", 
            "data": json.dumps({"type": "log", "content": f"⚠️ 智能体通信波动: {str(e)}"})
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
