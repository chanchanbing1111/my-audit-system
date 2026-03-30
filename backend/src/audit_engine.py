#!/usr/bin/env python3
import os
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

# 基础库导入
from pydantic import BaseModel, Field, field_validator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditState(BaseModel):
    """状态定义 - 必须包含所有需要在节点间传递的键"""
    company_name: str = Field(..., description="公司名称")
    raw_data: Dict = Field(default_factory=dict, description="原始数据")
    metrics: Dict = Field(default_factory=dict, description="财务指标")
    charts: Dict = Field(default_factory=dict, description="图表数据") # ✅ 新增：存放动态图表
    logs: List[str] = Field(default_factory=list, description="日志")

    @field_validator('logs')
    @classmethod
    def ensure_logs_initialized(cls, v):
        if v is None: return []
        return v

class AuditEngine:
    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY") 
        
        if not self.tavily_api_key:
            logger.warning("TAVILY_API_KEY missing!")
        
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
        new_logs = list(state.logs) if state.logs else []
        new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 启动审计: {state.company_name}")
        return {"logs": new_logs}

    def fetch_data_node(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 正在从互联网获取实时财报数据...")
        
        try:
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=self.tavily_api_key)
            query = f"{state.company_name} 2023 2024 2025 财报 营收 利润 (revenue net income)"
            search_res = tavily.search(query=query, search_depth="advanced", max_results=5)
            
            return {
                "raw_data": {"search_results": search_res.get('results', []), "answer": search_res.get('answer', '')},
                "logs": new_logs + [f"✅ 成功检索到 {len(search_res.get('results', []))} 篇财报来源"]
            }
        except Exception as e:
            return {"logs": new_logs + [f"⚠️ 搜索失败: {str(e)}"]}

    def audit_logic_node(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🤖 AI 正在深度解析财务指标并生成评分...")
        
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
            
            context = str(state.raw_data.get("search_results", ""))
            prompt = f"""你是一名资深审计师。请分析 {state.company_name} 的财务数据。
            1. 提取 2023, 2024, 2025 的营收(revenue)和净利润(net_income)。
            2. 根据数据质量和财务表现给出一个 0-100 的综合健康分(overall_score)。
            
            必须返回如下严格的 JSON 格式：
            {{
              "overall_score": 85,
              "years": {{
                "2023": {{"revenue": 100, "net_income": 10}},
                "2024": {{"revenue": 120, "net_income": 15}},
                "2025": {{"revenue": 150, "net_income": 25}}
              }}
            }}
            内容：{context[:3500]}"""
            
            response = client.chat.completions.create(
                model="glm-4.6v",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            
            res_json = json.loads(response.choices[0].message.content)
            extracted_years = res_json.get("years", {})

            # ✅ 动态生成前端图表需要的格式
            chart_data = []
            for year in sorted(extracted_years.keys()):
                val = extracted_years[year]
                chart_data.append({
                    "year": year,
                    "revenue": val.get("revenue", 0),
                    "profit": val.get("net_income", 0) # 前端 Recharts 对应的是 profit 字段
                })

            # ✅ 构造符合前端要求的 metrics 结构
            metrics = {
                "health": {
                    "overall": res_json.get("overall_score", 80),
                    "status": "healthy" if res_json.get("overall_score", 0) > 70 else "warning",
                    "anomaly_count": 0
                },
                "details": extracted_years
            }

            return {
                "metrics": metrics,
                "charts": {"profit_chart": {"data": chart_data}}, 
                "logs": new_logs + ["✅ 财务指标与动态图表数据生成完毕"]
            }
        except Exception as e:
            logger.error(f"AI Node Error: {e}")
            return {"logs": new_logs + [f"❌ AI 分析出错: {str(e)}"]}

    def report_node(self, state: AuditState) -> Dict:
        """生成文字报告并汇总结果"""
        metrics = state.metrics.get('health', {})
        details = state.metrics.get('details', {})
        
        report_text = f"# {state.company_name} 数字化审计报告\n\n"
        report_text += f"**综合评分：{metrics.get('overall', 'N/A')}分**\n\n"
        report_text += "### 📈 年度财务摘要\n"
        
        if not details:
            report_text += "未提取到有效年度数据。\n"
        else:
            for year, values in details.items():
                report_text += f"- **{year}年**：营业收入 {values.get('revenue', 'N/A')}，净利润 {values.get('net_income', 'N/A')}\n"
        
        report_text += f"\n> 结论：审计流程于 {datetime.now().strftime('%Y-%m-%d %H:%M')} 完成，数据已同步至可视化仪表盘。"

        return {
            "raw_data": {"report_content": report_text}, # 存入 raw_data 供 run_audit 读取
            "logs": state.logs + ["✅ 报告封装完毕"]
        }

    def run_audit(self, company_name: str) -> Dict:
        initial_input = {
            "company_name": company_name,
            "raw_data": {},
            "metrics": {},
            "charts": {},
            "logs": [f"[{datetime.now().strftime('%H:%M:%S')}] 初始化状态"]
        }
        try:
            final_output = self.workflow.invoke(
                initial_input,
                config=RunnableConfig(configurable={"thread_id": f"audit-{datetime.now().timestamp()}"})
            )
            
            # 从 report_node 结果中提取生成的报告文本
            report_content = final_output.get("raw_data", {}).get("report_content", "暂无报告正文")

            return {
                "status": "success",
                "metrics": final_output.get('metrics', {}),
                "charts": final_output.get('charts', {}), 
                "logs": final_output.get('logs', []),
                "metrics_details": report_content # 给前端文本区域显示
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "logs": [str(e)]}

if __name__ == "__main__":
    engine = AuditEngine()
    print(json.dumps(engine.run_audit("Tesla"), indent=2, ensure_ascii=False))
