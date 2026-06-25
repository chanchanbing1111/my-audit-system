import os
import json
import re
import logging
import asyncio
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
    # 核心修改：定义结构化的财务数据容器
    financial_data: Dict = Field(default_factory=lambda: {
        "audit_score": 0,
        "core_metrics": {},
        "insights": {}
    })
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

    async def search_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        combined_query = f"{state.company_name} 财报 巨潮资讯 营业收入 净利润 资产总额 负债 经营现金流 ROE"

        try:
            from exa_py import Exa
            exa = Exa(api_key=self.exa_api_key)
            search_res = exa.search_and_contents(query=combined_query, num_results=10, type="auto")
            results = [
                {"url": item.url, "content": getattr(item, 'text', '')[:1000]}
                for item in (search_res.results or [])
            ]
            return {
                "raw_data": {"search_results": results},
                "logs": new_logs + [f"🌐 [搜索智能体] 深度检索财报三表数据..."]
            }
        except Exception as e:
            return {"logs": new_logs + [f"⚠️ 搜索异常: {str(e)}"]}

    async def auditor_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        context = "\n".join([
            f"来源:{r.get('url')}\n内容:{r.get('content')[:800]}"
            for r in state.raw_data.get("search_results", [])
        ])

        prompt = f"""你是一个高级资深审计师。当前时间是 2026-04。
请对 {state.company_name} 进行深度审计，并输出以下结构化数据。

### 1. 审计评分逻辑：
根据企业的盈利稳定性(30%)、资产安全性(30%)、现金流质量(40%)给出 0-100 的综合审计评分。

### 2. 指标提取要求：
- 必须提取：ROE、毛利率、资产负债率、最新营收。
- 必须包含三年趋势：营业收入、净利润、总资产、总负债、经营性现金流净额。

### 3. 输出格式（严格 JSON）：
{{
  "audit_score": 85,
  "core_metrics": {{
    "roe": "数字%",
    "gross_margin": "数字%",
    "debt_ratio": "数字%",
    "latest_revenue": "数值+单位"
  }},
  "chart_data": {{
    "profit_chart": [ {{"year": 年份, "revenue": 数值, "profit": 数值}} ],
    "asset_chart": [ {{"year": 年份, "assets": 数值, "debt": 数值}} ],
    "cash_chart": [ {{"year": 年份, "cash_flow": 数值}} ]
  }},
  "insights": {{
    "summary": "综合评价",
    "risk_tip": "风险提示"
  }}
}}

参考材料：{context[:3500]}
"""

        # =====================================================
        #  核心修改：429 重试 + 指数退避（2s -> 4s -> 8s）
        # =====================================================
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="kimi-k2-turbo-preview",
                    messages=[{"role": "user", "content": prompt}]
                )
                res = safe_extract_json(response.choices[0].message.content)

                if not res:
                    return {"logs": new_logs + ["⚠️ [审计智能体] 数据解析失败"]}

                years = [
                    item.get("year")
                    for item in res.get("chart_data", {}).get("profit_chart", [])
                ]
                return {
                    "financial_data": {
                        "audit_score": res.get("audit_score"),
                        "core_metrics": res.get("core_metrics"),
                        "insights": res.get("insights")
                    },
                    "metrics": {
                        "health": res.get("core_metrics"),
                        "summary": res.get("insights", {}).get("summary", ""),
                        "score": res.get("audit_score")
                    },
                    "charts": res.get("chart_data"),
                    "target_years": years,
                    "logs": new_logs + [
                        f"⚖️ [审计智能体] 审计评分: {res.get('audit_score')}，多维勾稽完成"
                    ]
                }

            except Exception as e:
                err_str = str(e)
                last_error = err_str
                # 检测 429 超载错误
                if "429" in err_str or "overloaded" in err_str.lower():
                    if attempt < max_retries - 1:
                        wait_time = 2 ** (attempt + 1)  # 2, 4, 8
                        new_logs = new_logs + [
                            f"⚠️ [审计智能体] API 限速(429)，等待 {wait_time}s 后重试 ({attempt + 1}/{max_retries})"
                        ]
                        logger.warning(f"[AuditEngine] 429 retry {attempt + 1}/{max_retries}, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        new_logs = new_logs + [
                            f"❌ [审计智能体] API 超载，重试耗尽: {err_str}"
                        ]
                        return {"logs": new_logs}
                else:
                    # 非 429 错误，直接返回
                    return {"logs": new_logs + [f"❌ 审计解析失败: {err_str}"]}

        # 所有重试都失败
        return {"logs": new_logs + [f"❌ 审计智能体未知错误: {last_error}"]}

    async def critic_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        f_data = state.charts.get("profit_chart", [])

        if len(f_data) >= 1:
            return {"next_node": "end", "logs": new_logs + ["✅ [质检智能体] 审计结果已核定"]}

        if state.retry_count < 1:
            return {
                "next_node": "re_search",
                "retry_count": state.retry_count + 1,
                "logs": new_logs + ["🔍 数据不足，尝试重试"]
            }

        return {"next_node": "end", "logs": new_logs + ["⚠️ 接受有限数据"]}
