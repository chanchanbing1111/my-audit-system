import json
import asyncio
import os
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from src.audit_engine import AuditEngine

router = APIRouter()

class SSEStreamer:
    def __init__(self):
        # 确保从环境变量读取 Key
        self.engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))

    async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
        try:
            # 1. 🚀 建立连接
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": "📡 已连接审计服务器，正在启动 AI 审计流..."})
            }

            # 2. ⚡ 核心修复：LangGraph 必须要求提供 configurable 包含 thread_id
            # 这里的 config 结构必须严格遵守 LangGraph 要求
            config = {
                "configurable": {
                    "thread_id": str(uuid.uuid4()) # 为每次审计生成唯一的线程ID
                }
            }
            
            initial_input = {"company_name": company_name, "logs": []}
            
            # 使用 astream 模式运行
            async for event in self.engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
                for node_name, node_data in event.items():
                    
                    # A. 发送过程日志 (用于点亮前端 4 个步骤)
                    if "logs" in node_data:
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "log", 
                                "content": node_data["logs"][-1]
                            })
                        }
                        # 给前端动画留出时间
                        await asyncio.sleep(0.5)

                    # B. 发送财务指标和图表数据
                    if "metrics" in node_data:
                        # 确保发送给前端的数据包含 summary 字段
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "metrics",
                                "metrics": node_data.get("metrics", {}),
                                "charts": node_data.get("charts", {}),
                                "metrics_details": node_data.get("metrics_details", "")
                            })
                        }

            # 3. ✅ 成功结束
            yield {
                "event": "complete", 
                "data": json.dumps({"success": True})
            }

        except Exception as e:
            # 捕获并向前端发送错误
            error_msg = f"审计异常: {str(e)}"
            print(f"Error detail: {error_msg}") # 服务端打印调试
            yield {
                "event": "message", 
                "data": json.dumps({"type": "error", "content": error_msg})
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
