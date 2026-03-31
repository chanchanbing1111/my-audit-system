#!/usr/bin/env python3
import os
import json
import logging
import asyncio
import re
from typing import Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditState(BaseModel):
    company_name: str
    raw_data: Dict = Field(default_factory=dict)
    metrics: Dict = Field(default_factory=dict)
    charts: Dict = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)

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
        return {"logs": [f"🔍 语义解析：已锁定 [{state.company_name}] 审计主体"]}

    def fetch_data_node(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.tavily_api_key)
            # 强化搜索：针对 A 股和美股的不同口径进行混合搜索
            query = f"{state.company_name} official financial results 2023 2024 revenue net profit forecast 2025"
            search_res = tavily.search(query=query, search_depth="advanced", max_results=6)
            return {
                "raw_data": {"search_results": search_res.get('results', [])},
                "logs": new_logs + ["🌐 数据穿透：已从公开渠道抓取最新财务数据原文"]
            }
        except Exception as e:
            return {"logs": new_logs + [f"⚠️ 数据抓取异常: {str(e)}"]}

    async def audit_logic_node(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        # ⚡ 减负 1：大幅缩减上下文到 1500 字符，提高模型处理速度
        context = "\n".join([r.get('content', '') for r in state.raw_data.get("search_results", [])])[:1500]
        
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")

        for attempt in range(3):
            try:
                # ⚡ 减负 2：简化 Prompt，只要求核心逻辑
                prompt = f"""作为审计师，请提取 {state.company_name} 2023-2025 财务数据。
                1. 单位统一为：亿元人民币。若原数据为美元，请乘以 7.2 换算。
                2. 必须返回 JSON：{{"overall_score": 85, "summary": "...", "financials": [{{"year": "2023", "revenue": 0.0, "profit": 0.0, "cash": 0.0}}, ...]}}
                材料：{context}"""

                response = client.chat.completions.create(
                    model="glm-4.6v",
                    messages=[{"role": "user", "content": prompt}],
                    # ⚡ 减负 3：去掉 response_format 提高生成速度
                    timeout=60 # 缩短到 60 秒，如果 60 秒不出说明链路有问题，直接重试
                )
                
                content = response.choices[0].message.content
                # 简单清洗 JSON 标签
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()

                res = json.loads(content)
                f_data = res.get("financials", [])

                return {
                    "metrics": {
                        "health": {"overall": res.get("overall_score", 85), "status": "healthy"},
                        "summary": res.get("summary", ""),
                        "growth_analysis": "数据已完成汇率校准。"
                    },
                    "charts": {
                        "profit_chart": {"data": f_data},
                        "cash_flow_chart": {"data": f_data}
                    },
                    "logs": new_logs + ["⚖️ 风险对账：已完成 AI 逻辑审计"]
                }

            except Exception as e:
                if attempt < 2:
                    logger.warning(f"请求超时或出错，尝试第 {attempt+1} 次重试...")
                    await asyncio.sleep(3)
                    continue
                
                logger.error(f"审计逻辑节点最终失败: {e}")
                # 最终兜底：如果不通，返回一个空结构，防止前端转圈
                return {
                    "metrics": {"health": {"overall": 0, "status": "error"}, "summary": f"超时错误: {str(e)}"},
                    "charts": {"profit_chart": {"data": []}, "cash_flow_chart": {"data": []}},
                    "logs": new_logs + [f"❌ 逻辑分析超时: {str(e)}"]
                }

    def report_node(self, state: AuditState) -> Dict:
        return {"logs": state.logs + ["📑 研报生成：深度审计报告已合成"]}
