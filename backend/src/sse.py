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

# 💡 关键：将引擎改为按需延迟加载，防止启动时 Key 缺失导致 500
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        api_key = os.getenv('TAVILY_API_KEY')
        if not api_key:
            raise ValueError("TAVILY_API_KEY is missing in environment variables")
        _engine = AuditEngine(tavily_api_key=api_key)
    return _engine

async def event_generator(company_name: str):
    try:
        engine = get_engine()
        
        # 1. 发送初始日志
        yield {"event": "message", "data": json.dumps({"type": "log", "content": f"🔍 已锁定目标：{company_name}，正在调度多智能体集群..."})}

        # 2. 准备 LangGraph 输入
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        initial_input = {
            "company_name": company_name,
            "logs": [],
            "raw_data": {},
            "retry_count": 0
        }

        # 3. 运行真实的 Graph 逻辑
        # 💡 注意：加上具体的异常捕获，防止某个节点报错导致整个流断开
        async for event in engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
            for node_name, node_data in event.items():
                # 发送节点日志
                if "logs" in node_data and node_data["logs"]:
                    # 再次强调：剔除换行符防止 0xd 错误
                    msg = str(node_data["logs"][-1]).replace("\n", " ").replace("\r", " ")
                    yield {
                        "event": "message", 
                        "data": json.dumps({"type": "log", "content": f"[{node_name}] {msg}"})
                    }
                
                # 发送财务指标数据
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

        # 4. 流程结束
        yield {"event": "complete", "data": json.dumps({"success": True})}

    except Exception as e:
        # 如果中间报错，通过 SSE 发送具体错误堆栈，方便我们最后微调
        import traceback
        logger.error(traceback.format_exc())
        yield {
            "event": "message", 
            "data": json.dumps({"type": "log", "content": f"❌ 审计中断: {str(e)}"})
        }

@router.get("/audit")
async def stream_audit(request: Request, company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    
    # 💡 增加装饰器处理，防止 Railway 的反向代理断连
    return EventSourceResponse(
        event_generator(company_name),
        ping=20,
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        }
    )
