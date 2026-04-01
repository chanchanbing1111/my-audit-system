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

    async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
        try:
            # 1. 🚀 建立连接 - 立即发送第一条消息确认通道开启
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": "📡 已成功连接至 2026 智能审计云端..."})
            }

            config = {
                "configurable": {
                    "thread_id": str(uuid.uuid4()) 
                },
                "recursion_limit": 20 # 防止多智能体陷入死循环
            }
            
            initial_input = {
                "company_name": company_name, 
                "logs": [], 
                "raw_data": {},
                "retry_count": 0
            }
            
            # 2. ⚡ 异步流式运行多智能体图
            # 使用 astream 的 updates 模式获取每个节点的输出
            async for event in self.engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
                # 兼容性处理：防止 EventSourceResponse 因为长时间无数据而断开
                # 每收到一个节点信号，我们都主动 yield 一个保持连接的消息（虽然 EventSourceResponse 有 ping）
                
                for node_name, node_data in event.items():
                    logger.info(f"🤖 智能体节点完成: {node_name}")
                    
                    # A. 实时发送过程日志
                    # 优化：如果 logs 列表很长，只取最后一条新增的
                    if "logs" in node_data and node_data["logs"]:
                        latest_log = node_data["logs"][-1]
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "log", 
                                "content": latest_log
                            })
                        }
                    
                    # B. 发送最终指标数据
                    if "metrics" in node_data and node_data.get("metrics"):
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "metrics",
                                "metrics": node_data.get("metrics", {}),
                                "charts": node_data.get("charts", {}),
                                "node": node_name
                            })
                        }

            # 3. ✅ 显式发送流程彻底结束的信号
            yield {
                "event": "complete", 
                "data": json.dumps({"success": True, "message": "审计报告生成完毕"})
            }

        except Exception as e:
            error_msg = f"❌ 审计系统异常: {str(e)}"
            logger.error(f"SSE Runtime Error: {error_msg}")
            # 发送错误信息给前端展示
            yield {
                "event": "message", 
                "data": json.dumps({"type": "error", "content": error_msg})
            }

@router.get("/audit")
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="请提供公司名称")
    
    streamer = SSEStreamer()
    
    # 💡 核心修改：增加 headers 解决 Railway/Nginx 缓存导致的 SSE 不实时输出
    return EventSourceResponse(
        streamer.stream_workflow(company_name),
        ping=15, # 每15秒发一个心跳包，防止云端负载均衡器断开长连接
        send_timeout=600,
        headers={
            "X-Accel-Buffering": "no",  # 必须！禁用 Nginx 缓存，确保日志逐条跳出
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )

@router.get("/health")
async def health_check():
    return {"status": "healthy", "mode": "multi-agent", "version": "2026.04"}
