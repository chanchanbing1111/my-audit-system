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

# 假设你的工程结构中包含此路径
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
                    # 使用 astream 监听每个节点的更新
                    async for event in engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
                        for node_name, node_data in event.items():
                            await result_queue.put((node_name, node_data))
                    await result_queue.put(("__done__", None))
                except Exception as e:
                    logger.error(f"Workflow Error: {str(e)}")
                    await result_queue.put(("__error__", str(e)))

            # 启动后台任务
            workflow_task = asyncio.create_task(run_workflow())

            while True:
                try:
                    node_name, node_data = await asyncio.wait_for(result_queue.get(), timeout=90)
                except asyncio.TimeoutError:
                    workflow_task.cancel()
                    yield {"event": "message", "data": json.dumps({"type": "log", "content": "⚠️ 审计节点响应超时"})}
                    break

                if node_name == "__done__": break
                if node_name == "__error__":
                    yield {"event": "message", "data": json.dumps({"type": "log", "content": f"❌ 审计系统异常: {node_data}"})}
                    break

                # --- 核心修改点：多维度数据透传 ---
                
                # 1. 日志推送：提取当前节点的最新一条日志
                if "logs" in node_data and node_data["logs"]:
                    last_log = node_data["logs"][-1]
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "log", "content": f"[{node_name}] {last_log}"})
                    }

                # 2. 指标与评分推送：当 auditor_agent 完成核定时推送
                # 注意：这里需要兼容你新定义的 financial_data 或 metrics 结构
                if node_name == "auditor_agent" or "metrics" in node_data:
                    # 优先获取封装好的财务指标和评分
                    payload = {
                        "type": "metrics",
                        "metrics": {
                            "health": node_data.get("metrics", {}).get("health"),
                            "score": node_data.get("metrics", {}).get("score") or node_data.get("financial_data", {}).get("audit_score"),
                            "summary": node_data.get("metrics", {}).get("summary") or node_data.get("financial_data", {}).get("insights", {}).get("summary")
                        },
                        "charts": node_data.get("charts", {}), # 包含 profit_chart, asset_chart, cash_chart
                        "node": node_name
                    }
                    yield {
                        "event": "message",
                        "data": json.dumps(payload)
                    }

            workflow_task.cancel()

        except Exception as e:
            yield {"event": "message", "data": json.dumps({"type": "log", "content": f"❌ 连接中断: {str(e)}"})}

        yield {"event": "complete", "data": json.dumps({"success": True})}

    return EventSourceResponse(
        event_generator(),
        ping=20,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*", # 解决跨域
        }
    )
