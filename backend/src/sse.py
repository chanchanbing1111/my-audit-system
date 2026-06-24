
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
        self.engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))

    async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
        try:
            # 1. 🚀 建立连接
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": "📡 已连接多智能体审计服务器..."})
            }

            # 2. ⚙️ 配置 LangGraph 线程
            config = {
                "configurable": {
                    "thread_id": str(uuid.uuid4()) 
                }
            }
            
            # 初始化多智能体状态
            initial_input = {
                "company_name": company_name, 
                "logs": [], 
                "raw_data": {},
                "retry_count": 0
            }
            
            # 3. ⚡ 异步流式运行多智能体图
            async for event in self.engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
                for node_name, node_data in event.items():
                    logger.info(f"🤖 智能体节点完成: {node_name}")
                    
                    # A. 实时发送过程日志
                    if "logs" in node_data and node_data["logs"]:
                        latest_log = node_data["logs"][-1]
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "log", 
                                "content": latest_log # 这里包含了类似 [搜索智能体] 的前缀
                            })
                        }
                    
                    # B. 发送财务指标（由审计智能体或质检智能体产出）
                    # 在多智能体架构中，我们监听最终产出数据的节点
                    if "metrics" in node_data and node_data.get("metrics"):
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "metrics",
                                "metrics": node_data.get("metrics", {}),
                                "charts": node_data.get("charts", {}),
                                "metrics_details": f"由 {node_name} 最终核定"
                            })
                        }

            # 4. ✅ 流程彻底结束
            yield {
                "event": "complete", 
                "data": json.dumps({"success": True})
            }

        except Exception as e:
            error_msg = f"❌ 审计流异常: {str(e)}"
            logger.error(f"SSE Error: {error_msg}")
            yield {
                "event": "message", 
                "data": json.dumps({"type": "error", "content": error_msg})
            }

@router.get("/audit")
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    
    streamer = SSEStreamer()
    # 增加 timeout 到 600s，因为多智能体循环（重搜）可能耗时较久
    return EventSourceResponse(
        streamer.stream_workflow(company_name),
        ping=20,
        send_timeout=600 
    )

@router.get("/health")
async def health_check():
    return {"status": "healthy", "mode": "multi-agent"}
