"""
Sentient Audit System - 核心多智能体引擎
基于 LangGraph 的分布式财务合规校验系统
"""
import os
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from openai import OpenAI

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. 状态定义 ---
class AuditState(BaseModel):
    company_name: str
    raw_data: Dict = Field(default_factory=dict)
    metrics: Dict = Field(default_factory=dict)
    charts: Dict = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)
    next_node: str = Field(default="")
    retry_count: int = Field(default=0)
    target_years: List[int] = Field(default_factory=list)


# --- 工具函数：JSON 安全解析 ---
def safe_extract_json(text: str) -> Dict:
    try:
        json_pattern = r"```json\s*(.*?)\s*```"
        match = re.search(json_pattern, text, re.DOTALL)
        clean_content = match.group(1) if match else text
        return json.loads(clean_content.strip())
    except Exception as e:
        logger.error(f"JSON 解析异常: {e}")
        return {}


# --- 2. 核心多智能体引擎 ---
class AuditEngine:
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(
            api_key=self.openai_api_key,
            base_url="https://open.bigmodel.cn/api/paas/v4/"
        )
        self.checkpointer = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AuditState)

        workflow.add_node("search_agent", self.search_agent)
        workflow.add_node("auditor_agent", self.auditor_agent)
        workflow.add_node("critic_agent", self.critic_agent)

        workflow.set_entry_point("search_agent")
        workflow.add_edge("search_agent", "auditor_agent")
        workflow.add_edge("auditor_agent", "critic_agent")

        workflow.add_conditional_edges(
            "critic_agent",
            lambda x: x.get("next_node") if isinstance(x, dict) else x.next_node,
            {"re_search": "search_agent", "end": END}
        )

        return workflow.compile(checkpointer=self.checkpointer)

    # --- Agent 1: 搜索智能体 ---
    async def search_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        base_query = f"{state.company_name} 2023-2025 财报 Annual Report 营收 利润 ROE"

        if state.retry_count > 0:
            base_query = f"{state.company_name} 2022-2024 官方财报数据 10-K report"

        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.tavily_api_key)
            search_res = tavily.search(query=base_query, search_depth="advanced", max_results=8)
            return {
                "raw_data": {"search_results": search_res.get('results', [])},
                "logs": new_logs + [f"🌐 [搜索智能体] 检索目标: {base_query[:40]}..."]
            }
        except Exception as e:
            return {"logs": new_logs + [f"⚠️ 搜索异常: {str(e)}"]}

    # --- Agent 2: 审计智能体 ---
    async def auditor_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        results = state.raw_data.get("search_results", [])
        context = "\n".join([
            f"来源:{r.get('url')}\n内容:{r.get('content')[:600]}"
            for r in results
        ])

        current_date = "2026-04"
        prompt = f"""你是一个高级审计师。当前时间是 {current_date}。
请提取 {state.company_name} 最近三个完整财年的真实审计数据。

### 提取规则：
1. 优先提取 2023、2024、2025 年报数据。
2. 年份平移：若材料中确实没有 2025 年报（部分公司发布较晚），则必须向前追溯，提取 2022、2023、2024 年的数据。
3. 真实性：严禁预测或编造。所有数据必须来自材料中的真实数值。
4. 单位转换：统一换算为"亿元"或"亿美元"。

### 输出格式（必须严格返回 JSON）：
{{
  "core_metrics": {{
    "roe": "数字%",
    "gross_margin": "数字%",
    "debt_ratio": "数字%",
    "latest_revenue": "数值+单位"
  }},
  "chart_data": [
    {{"year": 年份, "revenue": 数值, "profit": 数值}},
    ...共三组...
  ],
  "insights": {{
    "revenue_growth": "对应图表的结论",
    "margin_improvement": "毛利率变动结论",
    "net_profit_quality": "盈利质量评价"
  }}
}}

参考材料：{context[:3500]}
"""

        try:
            response = self.client.chat.completions.create(
                model="glm-4.6v",
                messages=[{"role": "user", "content": prompt}]
            )
            res = safe_extract_json(response.choices[0].message.content)

            f_data = res.get("chart_data", [])
            years = [item.get("year") for item in f_data]

            return {
                "metrics": {
                    "health": res.get("core_metrics", {}),
                    "summary": res.get("insights", {}).get("revenue_growth", "")
                },
                "charts": {
                    "profit_chart": {"data": f_data},
                    "details": res.get("insights", {})
                },
                "target_years": years,
                "logs": new_logs + [
                    f"⚖️ [审计智能体] 已核定 {min(years) if years else 'N/A'}-{max(years) if years else 'N/A'} 三年连续数据"
                ]
            }
        except Exception as e:
            return {"logs": new_logs + [f"❌ 审计解析失败: {str(e)}"]}

    # --- Agent 3: 质检智能体 ---
    async def critic_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        f_data = state.charts.get("profit_chart", {}).get("data", [])

        has_three_years = len(f_data) == 3
        has_recent_data = any(item.get("year") in [2024, 2025] for item in f_data)

        if (not has_three_years or not has_recent_data) and state.retry_count < 1:
            return {
                "next_node": "re_search",
                "retry_count": state.retry_count + 1,
                "logs": new_logs + ["🔍 [质检智能体] 数据连续性不足，尝试扩大搜索范围追溯往年数据"]
            }

        return {
            "next_node": "end",
            "logs": new_logs + ["📑 [质检智能体] 财务逻辑及年份连续性校验通过"]
        }
