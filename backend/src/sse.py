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

# 引擎按需加载
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        api_key = os.getenv('EXA_API_KEY')
        if not api_key:
            raise ValueError("EXA_API_KEY is missing in environment variables")
        _engine = AuditEngine(exa_api_key=api_key)
    return _engine


async def event_generator(company_name: str):
    try:
        engine = get_engine()

        # 预热日志（防止连接断开）
        warmup_logs = [
            f"📡 正在建立 2026 安全审计加密隧道...",
            f"🔎 正在向数据中心申请 {company_name} 2023-2025 财报访问权限...",
            f"🧠 正在调度分布式审计智能体节点 (Node: {str(uuid.uuid4())[:8]})...",
            f"📊 正在初始化多年度勾稽关系算法，准备深度侦测..."
        ]

        for log in warmup_logs:
            yield {"event": "message", "data": json.dumps({"type": "log", "content": log})}
            await asyncio.sleep(1)

        # 运行 LangGraph
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        initial_input = {
            "company_name": company_name,
            "logs": [],
            "raw_data": {},
            "retry_count": 0
        }

        async for event in engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
            for node_name, node_data in event.items():
                if "logs" in node_data and node_data["logs"]:
                    msg = str(node_data["logs"][-1]).replace("\n", " ").replace("\r", "")
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "log", "content": f"[{node_name}] {msg}"})
                    }

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

        yield {"event": "complete", "data": json.dumps({"success": True})}

    except Exception as e:
        import traceback
        logger.error(traceback.format_exc())
        yield {
            "event": "message",
            "data": json.dumps({"type": "log", "content": f"❌ 审计中断: {str(e)}"})
        }


@router.get("/audit")
async def stream_audit(request: Request, company_name: str):
    """SSE 流式审计接口 - 路由已统一为 /audit（无尾部斜杠）"""
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")

    return EventSourceResponse(
        event_generator(company_name),
        ping=20,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        }
    )
