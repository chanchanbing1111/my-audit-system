import json
import asyncio
import os
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException
from sse_starlette import EventSourceResponse
from fastapi.concurrency import run_in_threadpool
from src.audit_engine import AuditEngine

router = APIRouter()

class SSEStreamer:
    def __init__(self):
        # 确保从环境变量读取 Key
        self.engine = AuditEngine(tavily_api_key=os.getenv('TAVILY_API_KEY'))

    async def stream_workflow(self, company_name: str) -> AsyncGenerator[dict, None]:
        try:
            # 1. 🚀 立即发送：撑开水管，告诉 VPN 这不是空连接
            yield {
                "event": "message", 
                "data": json.dumps({"type": "log", "content": "📡 已连接审计服务器，正在启动 AI..."})
            }

            # 2. ⚡ 异步处理：把耗时的 AI 审计丢到后台去跑
            # 这样主程序才能腾出手来不停地发“心跳”
            task = asyncio.create_task(run_in_threadpool(self.engine.run_audit, company_name))

            # 3. ❤️ 心跳循环：只要 AI 没算完，每 4 秒发一个状态，防止断连
            counter = 0
            while not task.done():
                counter += 4
                yield {
                    "event": "message", 
                    "data": json.dumps({"type": "log", "content": f"⏳ AI 正在深度分析中（已耗时 {counter}s）..."})
                }
                await asyncio.sleep(4) # 每 4 秒跳一次

            # 4. 🎁 获取结果：AI 算完了，拿取数据
            result = await task
            
            # 5. 📝 发送过程日志
            if "logs" in result:
                for log in result["logs"]:
                    yield {"event": "message", "data": json.dumps({"type": "log", "content": log})}

            # 6. 📊 发送数据给前端图表
            yield {
                "event": "message",
                "data": json.dumps({
                    "type": "metrics",
                    "metrics": result.get("metrics", {}),
                    "charts": result.get("charts", {}),
                    "metrics_details": result.get("metrics_details", {})
                })
            }
            
            # 7. ✅ 成功结束
            yield {"event": "complete", "data": json.dumps({"success": True})}

        except Exception as e:
            # 发生任何错误都发给前端
            yield {"event": "message", "data": json.dumps({"type": "error", "content": f"审计异常: {str(e)}"})}

@router.get("/audit/")
async def stream_audit(company_name: str):
    if not company_name:
        raise HTTPException(status_code=400, detail="Company name required")
    streamer = SSEStreamer()
    return EventSourceResponse(streamer.stream_workflow(company_name))

@router.get("/health")
async def health_check():
    return {"status": "healthy", "engine": "ready"}
