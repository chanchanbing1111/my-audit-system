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

        result_queue = asyncio.Queue()

        async def run_workflow():
            """后台运行工作流，捕获每个节点的更新"""
            try:
                logger.info(f"[Workflow] Starting workflow for {company_name}, thread={thread_id}")
                # =====================================================
                #  修复：使用 astream_events 或确保节点是异步兼容的
                #  如果你的节点是 async def，必须用 astream_events
                #  或者改用 .stream() 配合异步节点
                # =====================================================
                async for event in engine.workflow.astream_events(
                    initial_input,
                    config=config,
                    stream_mode="updates"
                ):
                    logger.info(f"[Workflow] Event: {type(event)}")
                    # astream_events 返回的是包含 'event' 和 'data' 的结构
                    # event 类型: "on_chain_start", "on_chain_end", "on_node_start", "on_node_end"
                    if isinstance(event, dict):
                        event_name = event.get("event", "")
                        if event_name in ("on_node_end", "on_chain_end"):
                            data = event.get("data", {})
                            if isinstance(data, dict):
                                # 提取节点输出
                                node_output = data.get("output", {}) or data.get("node_output", {})
                                if node_output:
                                    node_name = event.get("name", "unknown")
                                    await result_queue.put((node_name, node_output))
                            elif isinstance(data, list):
                                # stream_mode="updates" 返回 [node_name, node_data]
                                for item in data:
                                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                                        await result_queue.put((item[0], item[1]))
                                    elif isinstance(item, dict):
                                        for k, v in item.items():
                                            await result_queue.put((k, v))
                    await asyncio.sleep(0)  # 让出控制权

                logger.info("[Workflow] Workflow completed normally")
                await result_queue.put(("__done__", None))

            except Exception as e:
                logger.error(f"[Workflow] Exception: {type(e).__name__}: {str(e)}", exc_info=True)
                await result_queue.put(("__error__", f"{type(e).__name__}: {str(e)}"))

        # 启动后台任务
        workflow_task = asyncio.create_task(run_workflow())

        try:
            while True:
                try:
                    # 加一个合理的超时，如果队列超过 120 秒没数据就报错
                    node_name, node_data = await asyncio.wait_for(
                        result_queue.get(),
                        timeout=120
                    )
                except asyncio.TimeoutError:
                    logger.error("[Workflow] Queue timeout - no events for 120 seconds")
                    yield {"event": "message", "data": json.dumps({"type": "log", "content": "⚠️ 审计节点响应超时（120秒），请检查 Exa API 或网络连接"})}
                    workflow_task.cancel()
                    try:
                        await workflow_task
                    except asyncio.CancelledError:
                        pass
                    break

                logger.info(f"[SSE] Received from queue: {node_name}")

                if node_name == "__done__":
                    logger.info("[SSE] Workflow done")
                    break

                if node_name == "__error__":
                    yield {"event": "message", "data": json.dumps({"type": "log", "content": f"❌ 审计系统异常: {node_data}"})}
                    break

                # 1. 日志推送
                if "logs" in node_data and node_data["logs"]:
                    last_log = node_data["logs"][-1]
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "log", "content": f"[{node_name}] {last_log}"})
                    }

                # 2. 指标与评分推送
                if node_name == "auditor_agent" or "metrics" in node_data or "financial_data" in node_data:
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

                # 每处理一个事件，让出控制权，防止阻塞
                await asyncio.sleep(0)

        except asyncio.CancelledError:
            logger.warning("[SSE] Event generator cancelled")
            workflow_task.cancel()
            try:
                await workflow_task
            except asyncio.CancelledError:
                pass
        except Exception as e:
            logger.error(f"[SSE] Generator error: {type(e).__name__}: {str(e)}", exc_info=True)
            yield {"event": "message", "data": json.dumps({"type": "log", "content": f"❌ 连接中断: {type(e).__name__}: {str(e)}"})}

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
