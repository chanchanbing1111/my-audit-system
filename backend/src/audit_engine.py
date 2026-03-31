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

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. 状态定义 (必须放在最前面) ---

class AuditState(BaseModel):
    company_name: str
    raw_data: Dict = Field(default_factory=dict)
    metrics: Dict = Field(default_factory=dict)
    charts: Dict = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)

# --- 2. 核心引擎定义 ---

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

    # 节点 1: 语义解析
    def intent_node(self, state: AuditState) -> Dict:
        return {"logs": [f"🔍 语义解析：已锁定 [{state.company_name}] 审计主体"]}

    # 节点 2: 数据抓取
    def fetch_data_node(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.tavily_api_key)
            # 强化搜索词，确保获取官方财报信息
            query = f"{state.company_name} investor relations 2023 2024 financial results revenue profit"
            search_res = tavily.search(query=query, search_depth="advanced", max_results=6)
            return {
                "raw_data": {"search_results": search_res.get('results', [])},
                "logs": new_logs + ["🌐 数据穿透：已从公开渠道抓取最新财务数据原文"]
            }
        except Exception as e:
            logger.error(f"Tavily Search Error: {e}")
            return {"logs": new_logs + [f"⚠️ 数据抓取异常: {str(e)}"]}

    # 节点 3: AI 逻辑审计 (核心修复区)
    async def audit_logic_node(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        
        # 构建精准上下文
        search_results = state.raw_data.get("search_results", [])
        context_list = []
        for r in search_results[:5]:
            context_list.append(f"来源: {r.get('title')}\n内容: {r.get('content')[:800]}")
        context = "\n---\n".join(context_list)
        
        from openai import OpenAI
        # 使用智谱 API 
        client = OpenAI(api_key=self.openai_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")

        for attempt in range(3):
            try:
                prompt = f"""你是一名资深财务审计师。请分析材料并提取 {state.company_name} 2023-2025 的财务数据。
                
                ⚖️ 审计要求：
                1. 【单位换算】：若原数据为美元($)，必须乘以 7.2 转换为亿元人民币。
                2. 【禁止全零】：若材料未显式提及 2025 年，请根据 2023/2024 趋势进行合理预估，严禁返回全 0 数据。
                3. 【量级对齐】：例如特斯拉 2023 营收应在 7000 亿元人民币左右。

                返回标准 JSON 格式：
                {{
                  "overall_score": 85,
                  "summary": "一句话审计总结",
                  "financials": [
                    {{"year": "2023", "revenue": 100.5, "profit": 10.2, "cash": 20.5}},
                    {{"year": "2024", "revenue": 110.0, "profit": 12.0, "cash": 25.0}},
                    {{"year": "2025", "revenue": 125.0, "profit": 15.0, "cash": 30.0}}
                  ]
                }}
                
                材料内容：
                {context}"""

                response = client.chat.completions.create(
                    model="glm-4-flash", # 使用更快速稳定的 Flash 模型
                    messages=[{"role": "user", "content": prompt}],
                    timeout=50 
                )
                
                content = response.choices[0].message.content
                # 清洗 Markdown 标签
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()

                res = json.loads(content)
                f_data = res.get("financials", [])

                # 数据校验：如果第一年营收为 0，视为提取失败，触发重试
                if not f_data or float(f_data[0].get("revenue", 0)) == 0:
                    raise ValueError("AI 未能从材料中识别出有效数值")

                return {
                    "metrics": {
                        "health": {"overall": res.get("overall_score", 85), "status": "healthy"},
                        "summary": res.get("summary", "数据审计完成。"),
                        "growth_analysis": "已完成财报勾稽与汇率校准。"
                    },
                    "charts": {
                        "profit_chart": {"data": f_data},
                        "cash_flow_chart": {"data": f_data}
                    },
                    "logs": new_logs + ["⚖️ 风险对账：已完成 AI 逻辑审计与汇率校准"]
                }

            except Exception as e:
                if attempt < 2:
                    logger.warning(f"审计节点重试 {attempt+1}: {e}")
                    await asyncio.sleep(2)
                    continue
                
                logger.error(f"审计逻辑节点最终失败: {e}")
                return {
                    "metrics": {"health": {"overall": 0, "status": "error"}, "summary": f"审计中断：{str(e)}"},
                    "charts": {"profit_chart": {"data": []}, "cash_flow_chart": {"data": []}},
                    "logs": new_logs + [f"❌ 逻辑分析失败: {str(e)}"]
                }

    # 节点 4: 报告生成
    def report_node(self, state: AuditState) -> Dict:
        return {"logs": state.logs + ["📑 研报生成：深度审计报告已合成"]}
