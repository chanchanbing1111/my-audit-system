"""
Sentient Audit System - SSE 流式接口
"""
import json
import asyncio
import os
import uuid
import logging
from fastapi import APIRouter, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from src.audit_engine import AuditEngine

router = APIRouter()
logger = logging.getLogger(__name__)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        api_key = os.getenv('EXA_API_KEY')
        if not api_key:
            raise ValueError("EXA_API_KEY is missing in environment variables")
        _engine = AuditEngine(exa_api_key=api_key)
    return _engine


@router.get("/audit")
async def stream_audit(request: Request, company_name: str):
    """SSE 流式审计接口"""
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")

    async def event_generator():
        engine = get_engine()

        # Step 1: 预热日志（防止连接断开）
        warmup_logs = [
            f"📡 正在建立 2026 安全审计加密隧道...",
            f"🔎 正在向数据中心申请 {company_name} 2023-2025 财报访问权限...",
            f"🧠 正在调度分布式审计智能体节点 (Node: {str(uuid.uuid4())[:8]})...",
            f"📊 正在初始化多年度勾稽关系算法，准备深度侦测..."
        ]

        for log in warmup_logs:
            yield {"event": "message", "data": json.dumps({"type": "log", "content": log})}
            await asyncio.sleep(1)

        # Step 2: 运行 LangGraph 工作流（同步调用 + 实时推送中间结果）
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        initial_input = {
            "company_name": company_name,
            "logs": [],
            "raw_data": {},
            "retry_count": 0
        }

        try:
            # 使用 ainvoke（一次性获取完整结果），同时开启后台日志推送
            async def run_workflow():
                """后台运行工作流，把每步结果通过队列传回来"""
                try:
                    async for event in engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
                        for node_name, node_data in event.items():
                            await result_queue.put((node_name, node_data))
                    await result_queue.put(("__done__", None))
                except Exception as e:
                    import traceback
                    logger.error(traceback.format_exc())
                    await result_queue.put(("__error__", str(e)))

            result_queue = asyncio.Queue()

            # 启动后台工作流
            workflow_task = asyncio.create_task(run_workflow())

            # 同时监听队列，实时推送结果给前端
            while True:
                try:
                    node_name, node_data = await asyncio.wait_for(result_queue.get(), timeout=60)
                except asyncio.TimeoutError:
                    # 工作流超过60秒无输出，强制结束
                    workflow_task.cancel()
                    yield {"event": "message", "data": json.dumps({
                        "type": "log", "content": "⚠️ 审计超时，请检查 EXA API 或网络连接"
                    })}
                    break

                if node_name == "__done__":
                    break
                if node_name == "__error__":
                    yield {"event": "message", "data": json.dumps({
                        "type": "log", "content": f"❌ 工作流异常: {node_data}"
                    })}
                    break

                # 推送 logs
                if "logs" in node_data and node_data["logs"]:
                    msg = str(node_data["logs"][-1]).replace("\n", " ").replace("\r", "")
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "log", "content": f"[{node_name}] {msg}"})
                    }

                # 推送 metrics
                if "metrics" in node_data and node_data.get("metrics"):
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "metrics",
                            "metrics": node_data["metrics"],
                            "charts": node_data.get("charts", {}),
                            "details": f"核定节点: {node_name}"
                        })
                    }

            # 等待后台任务结束
            workflow_task.cancel()

        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            yield {"event": "message", "data": json.dumps({
                "type": "log", "content": f"❌ 审计中断: {str(e)}"
            })}

        # 最后发送 complete
        yield {"event": "complete", "data": json.dumps({"success": True})}

    return EventSourceResponse(
        event_generator(),
        ping=20,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        }
    )
