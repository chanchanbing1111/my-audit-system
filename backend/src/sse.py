"""
Sentient Audit System - SSE 流式接口 (增强版)
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

        # Step 1: 预热日志
        warmup_logs = [
            f"📡 正在建立 2026 安全审计加密隧道...",
            f"🔎 正在向数据中心申请 {company_name} 2023-2025 深度财报访问权限...",
            f"🧠 正在调度分布式审计智能体节点 (Node: {str(uuid.uuid4())[:8]})...",
            f"📊 正在初始化多年度勾稽关系算法，准备进行三表联动侦测..."
        ]

        for log in warmup_logs:
            yield {"event": "message", "data": json.dumps({"type": "log", "content": log})}
            await asyncio.sleep(0.5)

        # Step 2: 运行 LangGraph 工作流
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        initial_input = {
            "company_name": company_name,
            "logs": [],
            "raw_data": {},
            "retry_count": 0
        }

        try:
            result_queue = asyncio.Queue()

            async def run_workflow():
                """后台运行工作流，捕获每个节点的更新"""
                try:
                    # =====================================================
                    #  改用 .astream() + stream_mode="updates"
                    #  每返回一个 dict: { node_name: node_output_dict }
                    # =====================================================
                    async for event in engine.workflow.astream(
                        initial_input,
                        config=config,
                        stream_mode="updates"
                    ):
                        logger.info(f"[Workflow] Raw event: {type(event)}, value: {event}")
                        # event 格式: { "search_agent": {...}, "auditor_agent": {...}, ... }
                        if isinstance(event, dict):
                            for node_name, node_data in event.items():
                                logger.info(f"[Workflow] Node={node_name}, data_keys={list(node_data.keys()) if isinstance(node_data, dict) else 'not_dict'}")
                                await result_queue.put((node_name, node_data))
                        await asyncio.sleep(0)
                    await result_queue.put(("__done__", None))

                except Exception as e:
                    logger.error(f"[Workflow] Exception: {type(e).__name__}: {str(e)}", exc_info=True)
                    await result_queue.put(("__error__", f"{type(e).__name__}: {str(e)}"))

            workflow_task = asyncio.create_task(run_workflow())

            while True:
                try:
                    node_name, node_data = await asyncio.wait_for(
                        result_queue.get(),
                        timeout=120
                    )
                except asyncio.TimeoutError:
                    yield {"event": "message", "data": json.dumps({"type": "log", "content": "⚠️ 审计节点响应超时（120秒）"})}
                    workflow_task.cancel()
                    try:
                        await workflow_task
                    except asyncio.CancelledError:
                        pass
                    break

                if node_name == "__done__":
                    break
                if node_name == "__error__":
                    yield {"event": "message", "data": json.dumps({"type": "log", "content": f"❌ 审计系统异常: {node_data}"})}
                    break

                # =====================================================
                #  日志推送
                # =====================================================
                if node_data and isinstance(node_data, dict):
                    if "logs" in node_data and node_data["logs"]:
                        last_log = node_data["logs"][-1]
                        yield {
                            "event": "message",
                            "data": json.dumps({"type": "log", "content": f"[{node_name}] {last_log}"})
                        }

                    # =====================================================
                    #  metrics + charts 推送（只在 auditor_agent 节点出现）
                    # =====================================================
                    if node_name == "auditor_agent":
                        metrics = node_data.get("metrics", {})
                        financial_data = node_data.get("financial_data", {})

                        payload = {
                            "type": "metrics",
                            "metrics": {
                                "health": metrics.get("health") or financial_data.get("core_metrics", {}),
                                "score": metrics.get("score") or financial_data.get("audit_score"),
                                "summary": metrics.get("summary") or financial_data.get("insights", {}).get("summary", "")
                            },
                            "charts": node_data.get("charts", {}),
                            "node": node_name
                        }
                        yield {"event": "message", "data": json.dumps(payload)}

                await asyncio.sleep(0)

            workflow_task.cancel()
            try:
                await workflow_task
            except asyncio.CancelledError:
                pass

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[SSE] Generator error: {type(e).__name__}: {str(e)}", exc_info=True)
            yield {"event": "message", "data": json.dumps({"type": "log", "content": f"❌ 连接中断: {str(e)}"})}

        yield {"event": "complete", "data": json.dumps({"success": True})}

    return EventSourceResponse(
        event_generator(),
        ping=20,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )
