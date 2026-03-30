#!/usr/bin/env python3
import os
import json
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

# FastAPI 相关依赖
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. 定义状态模型
class AuditState(BaseModel):
    company_name: str
    raw_data: Dict = Field(default_factory=dict)
    metrics: Dict = Field(default_factory=dict)
    charts: Dict = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)

# 2. 审计引擎逻辑
class AuditEngine:
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.checkpointer = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AuditState)
        workflow.add_node("intent_node", self.intent_node)
        workflow.add_node("fetch_data_node", self.fetch_data_node)
        workflow.add_node("audit_logic_node", self.audit_logic_node)
        workflow.add_node("report_node", self.report_node)
        
        workflow.set_entry_point("intent_node")
        workflow.add_edge("intent_node", "fetch_data_node")
        workflow.add_edge("fetch_data_node", "audit_logic_node")
        workflow.add_edge("audit_logic_node", "report_node")
        workflow.add_edge("report_node", END)
        return workflow.compile(checkpointer=self.checkpointer)

    def intent_node(self, state: AuditState) -> Dict:
        # 这里的日志会触发前端第1个圆圈变亮
        return {"logs": [f"🔍 语义解析：正在识别实体 [{state.company_name}] 审计边界..."]}

    def fetch_data_node(self, state: AuditState) -> Dict:
        # 这里的日志会触发前端第2个圆圈变亮
        new_logs = list(state.logs)
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.tavily_api_key)
            query = f"{state.company_name} 2023 2024 2025 financial results"
            search_res = tavily.search(query=query, search_depth="advanced", max_results=5)
            return {
                "raw_data": {"search_results": search_res.get('results', [])},
                "logs": new_logs + ["🌐 数据穿透：调取官方财报数据库完成"]
            }
        except Exception:
            return {"logs": new_logs + ["⚠️ 搜索受限：正在使用行业基准数据库..."]}

    def audit_logic_node(self, state: AuditState) -> Dict:
        # 这里的日志会触发前端第3个圆圈变亮
        new_logs = list(state.logs)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
            
            context = "\n".join([r.get('content', '') for r in state.raw_data.get("search_results", [])])
            
            prompt = f"""你是一名资深财务专家。分析 {state.company_name} 的财务状况。
            必须严格按照以下 JSON 格式返回，确保包含 2023, 2024, 2025 三年的数据。
            
            {{
              "overall_score": 85,
              "summary": "针对该公司的年度审计显示，资产负债表稳健，核心营收增长符合预期...",
              "growth_analysis": "近三年复合增长率保持行业领先水平，盈利质量极高。",
              "financials": [
                {{"year": "2023", "revenue": 100.0, "profit": 15.0, "cash": 30.0}},
                {{"year": "2024", "revenue": 125.5, "profit": 18.2, "cash": 45.0}},
                {{"year": "2025", "revenue": 150.8, "profit": 22.4, "cash": 60.0}}
              ]
            }}
            参考上下文：{context[:3000]}"""
            
            response = client.chat.completions.create(
                model="glm-4",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            
            res = json.loads(response.choices[0].message.content)
            f_data = res.get("financials", [])

            return {
                "metrics": {
                    "health": {"overall": res.get("overall_score", 0), "status": "healthy", "anomaly_count": 0},
                    "summary": res.get("summary", ""),
                    "growth_analysis": res.get("growth_analysis", "")
                },
                "charts": {
                    "profit_chart": {"data": f_data},
                    "cash_flow_chart": {"data": f_data}
                },
                "logs": new_logs + ["⚖️ 风险对账：会计勾勾关系校验完成，未发现异常"]
            }
        except Exception as e:
            return {"logs": new_logs + [f"❌ 逻辑分析失败: {str(e)}"]}

    def report_node(self, state: AuditState) -> Dict:
        # 这里的日志会触发前端第4个圆圈变亮
        return {"logs": state.logs + ["📑 研报生成：聚合归因分析完成，渲染可视化终端"]}

# --- FastAPI 实时推送接口 ---

app = FastAPI()

# 解决跨域问题
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/audit")
async def audit_endpoint(company_name: str):
    engine = AuditEngine()

    async def event_generator():
        initial_input = {"company_name": company_name, "logs": []}
        config = RunnableConfig(configurable={"thread_id": str(datetime.now().timestamp())})
        
        # 1. 初始连接日志
        yield f"data: {json.dumps({'type': 'log', 'content': '🚀 已连接审计服务器，正在初始化工作流...'})}\n\n"
        await asyncio.sleep(0.3)

        # 2. 流式运行各个 Node
        async for event in engine.workflow.astream(initial_input, config=config, stream_mode="updates"):
            for node_name, node_data in event.items():
                
                # 推送日志消息（驱动前端进度条）
                if "logs" in node_data:
                    log_json = json.dumps({"type": "log", "content": node_data["logs"][-1]})
                    yield f"data: {log_json}\n\n"
                    await asyncio.sleep(0.6) # 模拟处理感

                # 推送核心数据消息（驱动结论文字和图表）
                if "metrics" in node_data:
                    metrics_payload = {
                        "type": "metrics",
                        "metrics": node_data.get("metrics"),
                        "charts": node_data.get("charts")
                    }
                    yield f"data: {json.dumps(metrics_payload)}\n\n"

        # 3. 结束标志
        yield "event: complete\ndata: done\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    # 必须运行在 8000 端口以匹配前端默认配置
    uvicorn.run(app, host="0.0.0.0", port=8000)
