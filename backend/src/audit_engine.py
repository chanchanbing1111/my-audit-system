#!/usr/bin/env python3
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

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
        return {"logs": [f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 开始审计: {state.company_name}"]}

    def fetch_data_node(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.tavily_api_key)
            # 强化搜索词，确保搜到具体数字
            query = f"{state.company_name} latest financial results revenue net income 2023 2024"
            search_res = tavily.search(query=query, search_depth="advanced", max_results=5)
            
            results = search_res.get('results', [])
            return {
                "raw_data": {"search_results": results},
                "logs": new_logs + [f"✅ 找到 {len(results)} 条实时财报资讯"]
            }
        except Exception as e:
            return {"logs": new_logs + [f"⚠️ 搜索失败: {str(e)}"]}

    def audit_logic_node(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
            
            # 提取搜索到的文本内容
            context = "\n".join([f"Source: {r.get('content')}" for r in state.raw_data.get("search_results", [])])
            
            prompt = f"""你是一名专业的财务审计师。请从以下搜索内容中提取 {state.company_name} 真实财务数据。
            
            注意：
            1. 严禁使用虚假数据或提示词中的示例数据。
            2. 如果搜索内容中没有具体数字，请根据已知信息进行估算，并在 reason 中说明。
            3. 返回 2022, 2023, 2024 的数据。
            
            必须严格返回此 JSON 格式：
            {{
              "overall_score": 75,
              "reason": "基于最新财报分析...",
              "financials": [
                {{"year": "2022", "revenue": 123.4, "profit": 12.3}},
                {{"year": "2023", "revenue": 150.5, "profit": 15.6}},
                {{"year": "2024", "revenue": 180.2, "profit": 20.1}}
              ]
            }}
            
            搜索到的参考内容：
            {context[:4000]}"""
            
            response = client.chat.completions.create(
                model="glm-4.6v",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            
            res_json = json.loads(response.choices[0].message.content)
            logger.info(f"AI Raw Response: {res_json}") # 在终端查看 AI 到底给没给真数据

            # 格式化给前端
            chart_data = res_json.get("financials", [])
            
            metrics = {
                "health": {
                    "overall": res_json.get("overall_score", 0),
                    "status": "healthy" if res_json.get("overall_score", 0) > 70 else "warning",
                    "anomaly_count": 0
                },
                "reason": res_json.get("reason", "")
            }

            return {
                "metrics": metrics,
                "charts": {"profit_chart": {"data": chart_data}},
                "logs": new_logs + ["✅ 实时财务指标提取完成"]
            }
        except Exception as e:
            return {"logs": new_logs + [f"❌ AI 分析出错: {str(e)}"]}

    def report_node(self, state: AuditState) -> Dict:
        metrics = state.metrics
        charts = state.charts.get("profit_chart", {}).get("data", [])
        
        report = f"# {state.company_name} 审计简报\n\n"
        report += f"**审计结论**：{metrics.get('reason', '完成深度扫描')}\n\n"
        report += "### 📊 提取到的关键数据\n"
        for item in charts:
            report += f"- **{item['year']}年**：营收 {item['revenue']}亿，利润 {item['profit']}亿\n"
            
        return {
            "metrics_details": report, # 统一传给这个字段
            "logs": state.logs + ["✅ 审计报告已生成"]
        }

    def run_audit(self, company_name: str) -> Dict:
        initial_input = {"company_name": company_name, "logs": []}
        try:
            final_output = self.workflow.invoke(
                initial_input,
                config=RunnableConfig(configurable={"thread_id": "temp"})
            )
            return {
                "status": "success",
                "metrics": final_output.get('metrics', {}),
                "charts": final_output.get('charts', {}),
                "logs": final_output.get('logs', []),
                "metrics_details": final_output.get('metrics_details', "")
            }
        except Exception as e:
            return {"status": "error", "logs": [str(e)]}
