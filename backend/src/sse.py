import json
import asyncio
import os
import uuid
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from src.audit_engine import AuditEngine

# 初始化日志，方便在 Railway 查看
logger = logging.getLogger(__name__)
router = APIRouter()

class SSEStreamer:
    def __init__(self):
        # 确保从环境变量读取 Key
        self.engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))

    async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
        try:
            # 1. 🚀 建立连接阶段
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": "📡 已连接审计服务器，正在启动 AI 审计流..."})
            }

            # 2. ⚙️ 配置线程
            config = {
                "configurable": {
                    "thread_id": str(uuid.uuid4()) 
                }
            }
            
            # 初始化输入
            initial_input = {"company_name": company_name, "logs": [], "raw_data": {}}
            
            # 3. ⚡ 异步运行 LangGraph
            # 使用 astream 模式，这是处理长耗时 AI 任务的最佳方式
            async for event in self.engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
                for node_name, node_data in event.items():
                    
                    # A. 健壮的日志发送逻辑
                    if "logs" in node_data and node_data["logs"]:
                        # 始终发送最后一条最新日志
                        latest_log = node_data["logs"][-1]
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "log", 
                                "content": latest_log
                            })
                        }
                    
                    # B. 核心财务数据发送
                    # 当 audit_logic_node 完成时，node_data 会包含 metrics 和 charts
                    if "metrics" in node_data or node_name == "audit_logic_node":
                        logger.info(f"📊 节点 {node_name} 已完成，正在推送财务指标包")
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "metrics",
                                "metrics": node_data.get("metrics", {}),
                                "charts": node_data.get("charts", {}),
                                "metrics_details": node_data.get("metrics_details", "")
                            })
                        }

            # 4. ✅ 成功结束
            yield {
                "event": "complete", 
                "data": json.dumps({"success": True})
            }

        except Exception as e:
            error_msg = f"❌ 审计流异常: {str(e)}"
            logger.error(f"SSE Streaming Error: {error_msg}")
            yield {
                "event": "message", 
                "data": json.dumps({"type": "error", "content": error_msg})
            }

@router.get("/audit")
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    
    streamer = SSEStreamer()
    # 💡 关键：ping=20 维持心跳，避免网关超时；send_timeout 设置为足够长
    return EventSourceResponse(
        streamer.stream_workflow(company_name),
        ping=20,
        send_timeout=300 # 允许最长 5 分钟的审计过程
    )

@router.get("/health")
async def health_check():
    return {"status": "healthy"}
