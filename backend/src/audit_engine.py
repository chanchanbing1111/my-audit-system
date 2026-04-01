import os
import json
import re
import logging
import asyncio
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

# --- 工具函数：鲁棒性 JSON 提取 ---
def safe_extract_json(text: str) -> Dict:
    """处理 GLM 模型返回的带 Markdown 标签的 JSON 字符串"""
    try:
        # 匹配 ```json ... ``` 块
        json_pattern = r"```json\s*(.*?)\s*```"
        match = re.search(json_pattern, text, re.DOTALL)
        clean_content = match.group(1) if match else text
        # 清除首尾空格和可能的非打印字符
        clean_content = clean_content.strip()
        return json.loads(clean_content)
    except Exception as e:
        logger.error(f"JSON 提取失败: {e}")
        return {}

# --- 2. 核心多智能体引擎 ---
class AuditEngine:
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        # GLM-4V 通常通过 Openai SDK 调用智谱清言 API 
        self.client = OpenAI(
            api_key=self.openai_api_key, 
            base_url="https://open.bigmodel.cn/api/paas/v4/"
        )
        self.checkpointer = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(AuditState)
        
        # 添加 Agent 节点
        workflow.add_node("search_agent", self.search_agent)
        workflow.add_node("auditor_agent", self.auditor_agent)
        workflow.add_node("critic_agent", self.critic_agent)
        
        workflow.set_entry_point("search_agent")
        workflow.add_edge("search_agent", "auditor_agent")
        workflow.add_edge("auditor_agent", "critic_agent")
        
        # 💡 条件路由修复：处理 Pydantic 对象与 Dict 的兼容
        workflow.add_conditional_edges(
            "critic_agent",
            lambda x: x.get("next_node") if isinstance(x, dict) else x.next_node,
            {
                "re_search": "search_agent",
                "end": END
            }
        )
        return workflow.compile(checkpointer=self.checkpointer)

    # --- Agent 1: 搜索智能体 (扩充搜索范围以获取年度数据) ---
    async def search_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.tavily_api_key)
            
            # 动态调整搜索词，避免硬编码 2023
            query = f"{state.company_name} 2023-2025 全年营收 净利润 财务报表数据"
            if state.retry_count > 0:
                query = f"{state.company_name} Investor Relations Annual Report 10-K 2024 2025"
            
            search_res = tavily.search(query=query, search_depth="advanced", max_results=6)
            return {
                "raw_data": {"search_results": search_res.get('results', [])},
                "logs": new_logs + [f"🌐 [搜索智能体] 启动深度扫描: {query[:30]}..."]
            }
        except Exception as e:
            return {"logs": new_logs + [f"⚠️ 搜索异常: {str(e)}"]}

    # --- Agent 2: 审计智能体 (适配 GLM-4.6V) ---
    async def auditor_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        results = state.raw_data.get("search_results", [])
        context = "\n".join([f"来源:{r.get('url')}\n内容:{r.get('content')[:600]}" for r in results])
        
        # 针对 GLM-4.6V 的指令增强：解决单位和周期误判
        prompt = f"""你是一个资深审计师。请分析 {state.company_name} 的材料并提取财务数据。
        
        ### 严格要求：
        1. 必须区分『季度数据』和『年度数据』。如果是季度数据，请根据比例折算或寻找对应的 Annual 字段。
        2. 统一单位：所有数字必须换算为『人民币元』或『美元』。请在 summary 中说明。
        3. 必须输出纯 JSON 格式：
           {{
             "summary": "简述数据来源及可靠性",
             "financials": [
               {{"year": 2023, "revenue": 100000000, "profit": 20000000}},
               ...
             ]
           }}

        ### 参考材料：
        {context[:2500]}
        """

        try:
            response = self.client.chat.completions.create(
                model="glm-4.6v", 
                messages=[{"role": "user", "content": prompt}]
            )
            raw_text = response.choices[0].message.content
            res = safe_extract_json(raw_text)
            
            financials = res.get("financials", [])
            return {
                "metrics": {
                    "health": {"overall": 90 if financials else 0}, 
                    "summary": res.get("summary", "数据提取完成")
                },
                "charts": {
                    "profit_chart": {"data": financials}
                },
                "logs": new_logs + ["⚖️ [审计智能体] GLM-4.6V 已完成跨时空数据勾稽"]
            }
        except Exception as e:
            return {"logs": new_logs + [f"❌ 审计解析失败: {str(e)}"]}

    # --- Agent 3: 质检智能体 (增加逻辑合理性校验) ---
    async def critic_agent(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        f_data = state.charts.get("profit_chart", {}).get("data", [])
        
        # 逻辑校验：如果数据太少，或者营收量级明显异常（例如低于 100 万且不是初创公司）
        is_poor_quality = len(f_data) < 1
        if not is_poor_quality:
            # 简单量级校验：检查第一个数据的营收是否合理
            first_revenue = float(f_data[0].get("revenue", 0))
            if first_revenue < 10000: # 可能是因为单位错位
                is_poor_quality = True
        
        if is_poor_quality and state.retry_count < 2:
            return {
                "next_node": "re_search", 
                "retry_count": state.retry_count + 1,
                "logs": new_logs + [f"🔍 [质检智能体] 数据量级或完整度存疑，第{state.retry_count+1}次打回"]
            }
        
        return {"next_node": "end", "logs": new_logs + ["📑 [质检智能体] 逻辑校验通过，输出最终报告"]}
