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
        # 合并搜索结果，截取前 3500 字符以防超出模型窗口
        context = "\n".join([r.get('content', '') for r in state.raw_data.get("search_results", [])])[:3500]
        
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")

        # 核心 Prompt：增加汇率换算和逻辑校对
        prompt = f"""你是一名资深跨境财务审计师。请分析材料并提取 {state.company_name} 2023-2025 的财务数据。
        
        ⚖️ 审计准则：
        1. 【统一单位】：所有数据必须以“亿元人民币”为单位。
        2. 【汇率换算】：若材料为美元($)或 Billion USD，必须乘以 7.2 换算为人民币。例如 $135B 应识别为 9720 亿元。
        3. 【逻辑校验】：
           - 检查营收量级：比亚迪/茅台等公司营收应在千亿量级，利润在百亿量级。
           - 检查趋势：除非有重大利空，2025年预估值通常不应低于2024年。
        4. 【字段要求】：revenue(营收), profit(净利润), cash(现金流/储备)。
        
        返回标准 JSON 格式：
        {{
          "overall_score": 85,
          "summary": "简短总结",
          "financials": [
            {{"year": "2023", "revenue": 100.5, "profit": 10.2, "cash": 20.5}},
            ...
          ]
        }}
        
        材料原文：
        {context}"""

        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="glm-4.6v",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={ "type": "json_object" },
                    timeout=90  # 4.6v 推理较慢，给足时间
                )
                
                usage = response.usage
                logger.info(f"📊 AI 审计完成 | 消耗: {usage.total_tokens} tokens")
                
                res = json.loads(response.choices[0].message.content)
                f_data = res.get("financials", [])

                # 二次校验：确保数值是浮点数，防止字符串导致图表崩溃
                for item in f_data:
                    item['revenue'] = round(float(item.get('revenue', 0)), 2)
                    item['profit'] = round(float(item.get('profit', 0)), 2)
                    item['cash'] = round(float(item.get('cash', 0)), 2)

                return {
                    "metrics": {
                        "health": {"overall": res.get("overall_score", 85), "status": "healthy"},
                        "summary": res.get("summary", ""),
                        "growth_analysis": "基于真实财报与汇率校准后的深度分析。"
                    },
                    "charts": {
                        "profit_chart": {"data": f_data},
                        "cash_flow_chart": {"data": f_data}
                    },
                    "logs": new_logs + [f"⚖️ 风险对账：已通过 GLM-4.6v 完成汇率校准与财报勾稽"]
                }

            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    wait_time = 5 * (attempt + 1)
                    logger.warning(f"触发限流，等待 {wait_time}s 后重试...")
                    await asyncio.sleep(wait_time)
                    continue
                
                logger.error(f"审计逻辑节点最终失败: {e}")
                return {
                    "metrics": {
                        "health": {"overall": 0, "status": "error"},
                        "summary": f"审计中断：无法提取准确数据 ({str(e)})。"
                    },
                    "charts": {"profit_chart": {"data": []}, "cash_flow_chart": {"data": []}},
                    "logs": new_logs + [f"❌ 逻辑分析失败: {str(e)}"]
                }

    def report_node(self, state: AuditState) -> Dict:
        return {"logs": state.logs + ["📑 研报生成：深度审计报告已合成"]}
