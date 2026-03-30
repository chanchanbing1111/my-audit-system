import json
import asyncio
import os
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
            # 1. 🚀 建立连接：立即告知前端已连接
            yield {
                "event": "message",
                "data": json.dumps({"type": "log", "content": "📡 已连接审计服务器，正在启动 AI 审计流..."})
            }

            # 2. ⚡ 核心逻辑：直接遍历 LangGraph 的异步流 (astream)
            # 这会实时捕获每个节点的 logs，从而驱动前端进度条点亮
            initial_input = {"company_name": company_name, "logs": []}
            
            # 使用 astream 模式运行
            async for event in self.engine.workflow.astream(initial_input, stream_mode="updates"):
                for node_name, node_data in event.items():
                    
                    # A. 发送过程日志 (用于驱动前端 getWorkflowSteps 进度条)
                    if "logs" in node_data:
                        # 每次产生新日志，立即推送到前端
                        # 前端收到一条 log，进度条就会自动 +1
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "log", 
                                "content": node_data["logs"][-1]
                            })
                        }
                        # 稍微停顿，让前端动画有节奏感
                        await asyncio.sleep(0.4)

                    # B. 发送财务指标和图表数据 (通常在 audit_logic_node 产生)
                    if "metrics" in node_data:
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "metrics",
                                "metrics": node_data.get("metrics", {}),
                                "charts": node_data.get("charts", {}),
                                # 兼容字段
                                "metrics_details": node_data.get("metrics_details", "")
                            })
                        }

            # 3. ✅ 成功结束：发送 complete 事件告知前端关闭 EventSource
            yield {
                "event": "complete", 
                "data": json.dumps({"success": True})
            }

        except Exception as e:
            # 发生任何错误都发给前端显示
            yield {
                "event": "message", 
                "data": json.dumps({"type": "error", "content": f"审计异常: {str(e)}"})
            }

@router.get("/audit")  # 注意：前端计算的路径是 /api/v1/audit，确保 prefix 正确
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    streamer = SSEStreamer()
    # 返回 EventSourceResponse 供前端 EventSource 订阅
    return EventSourceResponse(streamer.stream_workflow(company_name))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "ready"}
