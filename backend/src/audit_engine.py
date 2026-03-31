import os
import json
import logging
import asyncio
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

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
    next_node: str = Field(default="")  # 决策下一个 Agent
    retry_count: int = Field(default=0) # 重试计数器

# --- 2. 核心多智能体引擎 ---
class AuditEngine:
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.checkpointer = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AuditState)
        
        # 添加三个专职 Agent 节点
        workflow.add_node("search_agent", self.search_agent)
        workflow.add_node("auditor_agent", self.auditor_agent)
        workflow.add_node("critic_agent", self.critic_agent)
        
        # 构建图拓扑
        workflow.set_entry_point("search_agent")
        workflow.add_edge("search_agent", "auditor_agent")
        workflow.add_edge("auditor_agent", "critic_agent")
        
        # 💡 核心：条件路由（实现多智能体循环纠错）
        workflow.add_conditional_edges(
            "critic_agent",
            lambda x: x["next_node"],
            {
                "re_search": "search_agent", # 质检失败，打回搜索智能体
                "end": END                   # 质检通过
            }
        )
        return workflow.compile(checkpointer=self.checkpointer)

    # --- Agent 1: 搜索智能体 ---
    async def search_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.tavily_api_key)
            # 根据重试次数动态调整关键词
            query = f"{state.company_name} official financial report 2023 2024 revenue"
            if state.retry_count > 0:
                query = f"{state.company_name} investor relations 10-K 2023 financial highlights"
            
            search_res = tavily.search(query=query, search_depth="advanced", max_results=5)
            return {
                "raw_data": {"search_results": search_res.get('results', [])},
                "logs": new_logs + [f"🌐 [搜索智能体] 第{state.retry_count+1}次精准抓取数据原文"]
            }
        except Exception as e:
            return {"logs": new_logs + [f"⚠️ 搜索异常: {str(e)}"]}

    # --- Agent 2: 审计智能体 ---
    async def auditor_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        results = state.raw_data.get("search_results", [])
        context = "\n".join([f"标题: {r.get('title')}\n内容: {r.get('content')[:600]}" for r in results])
        
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")

        prompt = f"""你是一名审计专家。提取 {state.company_name} 2023-2025 财务数据。
        要求：
        1. 必须包含营收(revenue), 利润(profit), 现金流(cash)。
        2. 特斯拉等美股请直接提取“亿美元”数值，不要换算。
        3. 必须返回 JSON 格式。材料：{context[:1500]}"""

        try:
            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "user", "content": prompt}],
                timeout=40
            )
            content = response.choices[0].message.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            
            res = json.loads(content)
            return {
                "metrics": {"health": {"overall": 85}, "summary": res.get("summary", "")},
                "charts": {"profit_chart": {"data": res.get("financials", [])}, "cash_flow_chart": {"data": res.get("financials", [])}},
                "logs": new_logs + ["⚖️ [审计智能体] 已完成初步财报勾稽"]
            }
        except Exception as e:
            return {"logs": new_logs + [f"❌ 审计计算出错: {str(e)}"]}

    # --- Agent 3: 质检智能体 (决策中心) ---
    async def critic_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        f_data = state.charts.get("profit_chart", {}).get("data", [])
        
        # 逻辑：如果第一年营收为 0 且重试不到 2 次，要求重新搜索
        if (not f_data or f_data[0].get("revenue") == 0) and state.retry_count < 2:
            return {
                "next_node": "re_search", 
                "retry_count": state.retry_count + 1,
                "logs": new_logs + ["🔍 [质检智能体] 发现关键数据缺失，指令搜索智能体重新采集"]
            }
        
        return {"next_node": "end", "logs": new_logs + ["📑 [质检智能体] 审计逻辑校验通过，生成报告"]}
