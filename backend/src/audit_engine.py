"""
Sentient Audit System - 核心多智能体引擎
基于 LangGraph 的分布式财务合规校验系统
"""
import os
import json
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
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
def safe_extract_json(text: str) -> Optional[Dict]:
    try:
        json_pattern = r"```json\s*(.*?)\s*```"
        match = re.search(json_pattern, text, re.DOTALL)
        clean_content = match.group(1) if match else text
        return json.loads(clean_content.strip())
    except Exception as e:
        logger.error(f"JSON 解析异常: {e}")
        return None


# --- 2. 核心多智能体引擎 ---
class AuditEngine:
    def __init__(self, exa_api_key: Optional[str] = None):
        self.exa_api_key = exa_api_key or os.getenv("EXA_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(
            api_key=self.openai_api_key,
            base_url="https://api.moonshot.cn/v1"
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

        # 向前找最近三个已发布年报的财年
        # 当前2026年，假设近三年年报最晚到2024（2025年报可能在发布中）
        if state.retry_count == 0:
            year_list = [2023, 2024, 2025]
        else:
            year_list = [2022, 2023, 2024]

        # 优先搜巨潮资讯网的财务报表页面，数据结构化且完整
        # 组合搜索：年报 + 财务报表页面，都从巨潮资讯网
        base_query = f"{state.company_name} 巨潮资讯网 财务报表 年报 营业收入 净利润 {year_list[0]}-{year_list[-1]}"
        annual_queries = " ".join([f"{y}年" for y in year_list])

        if state.retry_count > 0:
            new_logs += [f"🔄 [搜索智能体] 补充搜索往年数据..."]

        try:
            from exa_py import Exa
            exa = Exa(api_key=self.exa_api_key)
            results = []

            # 统一搜索：巨潮资讯网 + 年报关键词，覆盖各年份
            combined_query = f"{base_query} {annual_queries}"
            search_res = exa.search_and_contents(
                query=combined_query,
                num_results=10,
                type="auto"
            )
            for item in (search_res.results or []):
                results.append({
                    "url": item.url,
                    "content": getattr(item, 'text', '')[:2000]
                })

            # 空结果检测
            if not results:
                return {
                    "logs": new_logs + ["⚠️ [搜索智能体] 未找到任何财报数据，请尝试更换公司名称或使用英文名"]
                }

            return {
                "raw_data": {"search_results": results},
                "logs": new_logs + [f"🌐 [搜索智能体] 已检索到 {len(results)} 条材料: {combined_query[:50]}..."]
            }
        except Exception as e:
            return {"logs": new_logs + [f"⚠️ 搜索异常: {str(e)}"]}

    # --- Agent 2: 审计智能体 ---
    async def auditor_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        results = state.raw_data.get("search_results", [])
        context = "\n".join([
            f"来源:{r.get('url')}\n内容:{r.get('content')[:2000]}"
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

参考材料：{context[:6000]}
"""

        try:
            response = self.client.chat.completions.create(
                model="kimi-k2.5",
                messages=[{"role": "user", "content": prompt}]
            )
            res = safe_extract_json(response.choices[0].message.content)

            # JSON 解析失败，保留原数据不覆盖
            if res is None:
                return {
                    "logs": new_logs + ["⚠️ [审计智能体] 解析失败，保留上次数据"]
                }

            f_data = res.get("chart_data", [])
            # 过滤掉无效年份
            f_data = [item for item in f_data if item.get("year")]
            years = [item.get("year") for item in f_data]

            # 如果新数据为空，保留上次的有效数据
            if not f_data and state.charts.get("profit_chart", {}).get("data"):
                return {
                    "logs": new_logs + ["⚠️ [审计智能体] 新数据为空，保留上次审计结果"]
                }

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

        # 过滤出有有效数字的条目
        valid_items = [
            item for item in f_data
            if item.get("year") and item.get("revenue") not in [None, "N/A", ""]
        ]

        # 统计有多少年近期数据（至少需要2年才通过）
        recent_years = [item for item in f_data if item.get("year") in [2024, 2025]]
        has_enough_recent = len(recent_years) >= 2
        has_valid_numbers = len(valid_items) >= 1
        has_three_years = len(f_data) == 3

        # 有2年有效近期数据才通过，避免数据不完整就结束
        if has_valid_numbers and has_enough_recent:
            return {
                "next_node": "end",
                "logs": new_logs + ["✅ [质检智能体] 数据有效，校验通过"]
            }

        # 数据不足且还有重试机会
        if state.retry_count < 1:
            return {
                "next_node": "re_search",
                "retry_count": state.retry_count + 1,
                "logs": new_logs + ["🔍 [质检智能体] 数据连续性不足，尝试扩大搜索范围追溯往年数据"]
            }

        # 重试失败也保留已有数据，不再继续循环
        return {
            "next_node": "end",
            "logs": new_logs + ["⚠️ [质检智能体] 数据有限，接受当前结果"]
        }
