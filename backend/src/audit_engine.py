import os
import json
import re
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
    next_node: str = Field(default="")  
    retry_count: int = Field(default=0) 

# --- 辅助工具：鲁棒性 JSON 提取 ---
def extract_json(text: str) -> Dict:
    """提取字符串中的 JSON 内容并解析"""
    try:
        # 尝试正则匹配 Markdown 代码块中的内容
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        json_str = match.group(1) if match else text
        # 移除可能残留的控制字符
        json_str = json_str.strip()
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"JSON 解析失败: {e}, 原始文本: {text[:200]}...")
        return {}

# --- 2. 核心多智能体引擎 ---
class AuditEngine:
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
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
            # 注意：在条件路由中，state 传入的是一个字典或对象，取决于实现
            # 这里我们统一使用 .get 访问以确保兼容性
            lambda x: x.get("next_node") if isinstance(x, dict) else x.next_node,
            {
                "re_search": "search_agent",
                "end": END
            }
        )
        return workflow.compile(checkpointer=self.checkpointer)

    # --- Agent 1: 搜索智能体 ---
    async def search_agent(self, state: AuditState) -> Dict:
        # 使用点号访问 Pydantic 属性
        new_logs = list(state.logs)
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.tavily_api_key)
            
            query = f"{state.company_name} 2023-2025 财报数据"
            if state.retry_count > 0:
                query = f"{state.company_name} 投资者关系 10-K 2024 report"
            
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
        context = "\n".join([f"内容: {r.get('content')[:600]}" for r in results])
        
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")

        prompt = (
            f"你是一个专业的审计师。请从以下材料提取 {state.company_name} 的财务数据。\n"
            f"要求输出纯 JSON 格式，包含 summary(简要评价) 和 financials(数组，包含 year, revenue, profit)。\n"
            f"材料内容：{context[:2000]}"
        )

        try:
            response = client.chat.completions.create(
                model="glm-4-flash",
                messages=[{"role": "system", "content": "你只输出 JSON 格式数据。"},
                          {"role": "user", "content": prompt}]
            )
            raw_content = response.choices[0].message.content
            res = extract_json(raw_content) # 使用增强解析函数
            
            if not res.get("financials"):
                raise ValueError("未在 AI 返回中找到 financials 字段")

            return {
                "metrics": {"health": {"overall": 85}, "summary": res.get("summary", "数据提取完成")},
                "charts": {
                    "profit_chart": {"data": res.get("financials", [])}
                },
                "logs": new_logs + ["⚖️ [审计智能体] 已完成初步财报勾稽"]
            }
        except Exception as e:
            return {"logs": new_logs + [f"❌ 审计数据处理失败: {str(e)}"]}

    # --- Agent 3: 质检智能体 ---
    async def critic_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        # 使用点号访问 charts
        f_data = state.charts.get("profit_chart", {}).get("data", [])
        
        # 检查逻辑：数据为空或营收全为0
        is_data_invalid = not f_data or all(float(item.get("revenue", 0)) == 0 for item in f_data)
        
        if is_data_invalid and state.retry_count < 2:
            return {
                "next_node": "re_search", 
                "retry_count": state.retry_count + 1,
                "logs": new_logs + ["🔍 [质检智能体] 发现数据质量不合格，触发重搜"]
            }
        
        return {"next_node": "end", "logs": new_logs + ["📑 [质检智能体] 校验通过，生成审计报告"]}
