#!/usr/bin/env python3
"""
Production-grade audit engine using LangGraph for workflow management.
Handles company financial analysis with comprehensive audit logic.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Optional, TypedDict
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pydantic import BaseModel, Field, field_validator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuditState(BaseModel):
    """State for the audit workflow with comprehensive financial analysis data"""
    company_name: str = Field(..., description="Name of the company being audited")
    raw_data: Dict = Field(default_factory=dict, description="Raw financial data from web search")
    metrics: Dict = Field(default_factory=dict, description="Calculated financial metrics and analysis results")
    logs: List[str] = Field(default_factory=list, description="Detailed execution logs for workflow tracking")

    @field_validator('logs')
    @classmethod
    def ensure_logs_initialized(cls, v):
        """Ensure logs is always a list"""
        if v is None:
            return []
        return v

    def add_log(self, message: str):
        """Add a detailed log entry with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        logger.info(log_entry)

        # Keep only last 500 logs to prevent memory issues
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]

class AuditEngine:
    """Production-grade audit engine using LangGraph for workflow management"""

    def __init__(self, tavily_api_key: Optional[str] = None):
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is required for financial data collection")

        self.checkpointer = MemorySaver()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow with 4 nodes"""
        workflow = StateGraph(AuditState)

        # Add nodes
        workflow.add_node("intent_node", self.intent_node)
        workflow.add_node("fetch_data_node", self.fetch_data_node)
        workflow.add_node("audit_logic_node", self.audit_logic_node)
        workflow.add_node("report_node", self.report_node)

        # Define edges
        workflow.set_entry_point("intent_node")
        workflow.add_edge("intent_node", "fetch_data_node")
        workflow.add_edge("fetch_data_node", "audit_logic_node")
        workflow.add_edge("audit_logic_node", "report_node")
        workflow.add_edge("report_node", END)

        return workflow.compile(checkpointer=self.checkpointer)

  def intent_node(self, state: AuditState) -> Dict: # 👈 改为 Dict
        """Parse company name from user intent and initialize audit"""
        # 我们创建一个新的日志列表
        new_logs = list(state.logs) if state.logs else []
        new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 开始审计流程: 解析公司名称 '{state.company_name}'")
        new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 正在验证公司名称格式和有效性...")

        if not state.company_name or len(state.company_name.strip()) < 2:
            new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ 错误: 公司名称无效")
            raise ValueError("Invalid company name")

        new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 公司名称 '{state.company_name}' 验证通过")
        new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 准备开始财务数据收集...")

        # ✅ 关键：返回字典，Key 必须对应 AuditState 里的字段
        return {"logs": new_logs}

   def fetch_data_node(self, state: AuditState) -> Dict:
        """使用 Tavily 搜索真实的财务报告并收集原始数据"""
        # 准备日志
        new_logs = list(state.logs)
        timestamp = datetime.now().strftime('%H:%M:%S')
        new_logs.append(f"[{timestamp}] 🚀 进入真实数据收集阶段")
        new_logs.append(f"[{timestamp}] 🔍 正在为 {state.company_name} 进行深度全网搜索...")

        try:
            # 1. 从环境变量获取真实的 API KEY
            # 这里的 self.tavily_api_key 在 __init__ 中已经通过 os.getenv 读取了
            api_key = self.tavily_api_key
            
            if not api_key or api_key == "your_tavily_api_key_here":
                new_logs.append("⚠️ 未检测到有效的 TAVILY_API_KEY，请在 Railway 环境变量中配置")
                raise ValueError("TAVILY_API_KEY is missing")

            # 2. 调用真实的 Tavily 客户端
            from tavily import TavilyClient
            tavily = TavilyClient(api_key=api_key)
            
            # 构建针对财报的专业搜索指令
            query = f"{state.company_name} 2023 2024 annual report financial highlights revenue net income"
            
            # 执行高级搜索
            search_response = tavily.search(
                query=query, 
                search_depth="advanced", 
                max_results=5,
                include_answer=True # 让 Tavily 直接给出 AI 摘要
            )
            
            # 3. 构造真实的原始数据结构
            real_data = {
                "company": state.company_name,
                "search_context": search_response.get('answer', ''),
                "search_results": search_response.get('results', []),
                "collected_at": datetime.now().isoformat(),
                "source_urls": [r['url'] for r in search_response.get('results', [])]
            }

            new_logs.append(f"✅ 成功获取 {len(real_data['source_urls'])} 个真实数据源")
            new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 数据收集完成，准备进入 AI 审计分析")

            # 4. ✨ 关键：必须返回字典 (Dict) 
            return {
                "raw_data": real_data,
                "logs": new_logs
            }

        except Exception as e:
            error_msg = f"❌ 真实数据搜集失败: {str(e)}"
            logger.error(error_msg)
            new_logs.append(error_msg)
            # 报错时也必须返回字典，防止程序彻底卡死
            return {
                "logs": new_logs,
                "raw_data": {"status": "error", "error_detail": str(e)}
            }

    def audit_logic_node(self, state: AuditState) -> Dict:
        """使用 GLM-4.6v 提取数据并执行审计逻辑"""
        # 1. 准备日志
        new_logs = list(state.logs)
        timestamp = datetime.now().strftime('%H:%M:%S')
        new_logs.append(f"[{timestamp}] 🤖 AI 审计开始：正在调用 GLM-4.6v 分析原始网页数据...")

        try:
            # 2. 获取 API Key (对应你 Railway 里的 OPENAI_API_KEY)
            api_key = os.getenv("OPENAI_API_KEY")
            
            # 3. 构建 Prompt：要求 AI 从文本中精准提取 JSON 数字
            # 注意：我们将 raw_data 传入，这里面存的是上一步 Tavily 搜到的内容
            search_context = str(state.raw_data.get("search_results", "无搜索数据"))
            
            prompt = f"""
            你是一名专业审计师。请阅读以下关于 '{state.company_name}' 的搜索结果，提取 2023 和 2024 年的财务指标。
            
            要求：
            1. 必须返回纯 JSON 格式。
            2. 如果找不到数据，请填入 0。
            3. 格式如下：
            {{
                "years": [2023, 2024],
                "revenue": [2023收入, 2024收入],
                "net_income": [2023净利, 2024净利],
                "assets": [2023资产, 2024资产],
                "liabilities": [2023负债, 2024负债],
                "equity": [2023权益, 2024权益],
                "cash_flow": [2023现金流, 2024现金流]
            }}
            
            搜索结果内容：
            {search_context[:4000]} 
            """

            # 4. 调用 GLM-4.6v (通过 OpenAI 兼容接口)
            from openai import OpenAI
            # 智谱 AI 的官方 API 地址
            client = OpenAI(api_key=api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
            
            response = client.chat.completions.create(
                model="glm-4.6v", # 智谱标准模型名
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" }
            )
            
            # 5. 解析 AI 提取到的数字
            financial_data = json.loads(response.choices[0].message.content)
            years = financial_data.get("years", [2023, 2024])
            new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ AI 成功提取结构化数据")

            # 6. 执行审计计算逻辑 (复用你原来的逻辑)
            metrics = {
                "profitability": {}, "liquidity": {}, "solvency": {},
                "efficiency": {}, "growth": {}, "anomalies": []
            }

            # 示例：盈利能力分析
            for i, year in enumerate(years):
                rev = financial_data["revenue"][i]
                ni = financial_data["net_income"][i]
                if rev > 0:
                    margin = (ni / rev) * 100
                    metrics["profitability"][year] = {"revenue": rev, "net_income": ni, "profit_margin": margin}
                    if margin < 5:
                        metrics["anomalies"].append(f"{year}年: 净利润率 {margin:.2f}% 偏低")

            # 计算健康评分 (复用你原来的逻辑)
            anomaly_count = len(metrics["anomalies"])
            health_score = max(0, 100 - (anomaly_count * 10))
            metrics["health"] = {
                "overall": health_score,
                "anomaly_count": anomaly_count,
                "status": "healthy" if health_score >= 70 else "warning"
            }

            new_logs.append(f"✅ 审计完成，健康评分: {health_score}")

            # 7. ✨ 必须返回字典 (Dict)
            return {
                "metrics": metrics,
                "logs": new_logs
            }

        except Exception as e:
            new_logs.append(f"❌ 审计分析失败: {str(e)}")
            return {"logs": new_logs}

    def report_node(self, state: AuditState) -> Dict: # 👈 关键：返回类型改为 Dict
        """生成最终的综合审计报告"""
        new_logs = list(state.logs)
        timestamp = datetime.now().strftime('%H:%M:%S')
        new_logs.append(f"[{timestamp}] 进入报告生成阶段: 正在汇整审计结论...")

        try:
            # 安全获取指标数据，防止 AI 提取失败导致此处崩溃
            metrics = state.metrics if state.metrics else {}
            health = metrics.get('health', {'overall': 0, 'status': 'N/A', 'anomaly_count': 0})
            
            # 生成 Markdown 格式的报告内容
            report = f"""
# {state.company_name} 财务审计报告
## 审计日期: {datetime.now().strftime("%Y-%m-%d")}

### 审计概述
本报告基于智谱 GLM-4-9B 对 {state.company_name} 实时搜索数据的分析，重点关注盈利能力、流动性、偿债能力和增长趋势。

### 关键发现

#### 整体健康评分
- **健康评分**: {health.get('overall', 0)}/100
- **状态**: {str(health.get('status', 'unknown')).upper()}
- **异常数量**: {health.get('anomaly_count', 0)}

#### 盈利能力分析
{self._format_metrics_section(metrics.get('profitability', {}), "盈利能力")}

#### 流动性分析
{self._format_metrics_section(metrics.get('liquidity', {}), "流动性")}

#### 偿债能力分析
{self._format_metrics_section(metrics.get('solvency', {}), "偿债能力")}

#### 增长趋势分析
{self._format_metrics_section(metrics.get('growth', {}), "增长趋势")}

#### 现金流效率
{self._format_metrics_section(metrics.get('efficiency', {}), "现金流效率")}

### 异常和风险
{self._format_anomalies(metrics.get('anomalies', []))}

### 数据来源
{self._format_sources(state.raw_data.get('source_urls', []))}

### 审计结论
根据 AI 分析，{state.company_name} 目前的财务状况评级为 **{health.get('status', '未知')}**。请结合具体异常项进行风险评估。
"""

            new_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ 审计报告生成完成")
            new_logs.append("审计工作流执行完毕，正在向前端推送最终结果...")

            # ✅ 最终返回：更新日志，并保持其他状态不变
            # 在 LangGraph 中，END 节点前的最后一个 return 会决定最终 invoke 的输出
            return {
                "logs": new_logs
            }

        except Exception as e:
            error_msg = f"❌ 报告生成失败: {str(e)}"
            new_logs.append(error_msg)
            # 即使失败也返回字典，确保流转能结束
            return {"logs": new_logs}
    def _format_metrics_section(self, metrics: Dict, title: str) -> str:
        """Format a metrics section for the report"""
        if not metrics:
            return f"**{title}**: 无可用数据\n"

        result = f"**{title}**:\n"
        for year, data in metrics.items():
            result += f"- {year}年: "
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    result += f"{key}: {value:.2f}, "
                else:
                    result += f"{key}: {value}, "
            result = result.rstrip(", ") + "\n"
        return result

    def _format_anomalies(self, anomalies: List[str]) -> str:
        """Format anomalies section"""
        if not anomalies:
            return "**异常和风险**: 无重大异常\n"

        result = "**异常和风险**:\n"
        for anomaly in anomalies:
            result += f"- {anomaly}\n"
        return result

    def _format_sources(self, sources: List[str]) -> str:
        """Format data sources section"""
        if not sources:
            return "**数据来源**: 未提供\n"

        result = "**数据来源**:\n"
        for source in sources:
            result += f"- {source}\n"
        return result

    def _format_logs(self, logs: List[str]) -> str:
        """Format execution logs for report"""
        if not logs:
            return "无执行日志\n"

        result = "**执行日志**:\n"
        for log in logs:
            result += f"- {log}\n"
        return result

    def run_audit(self, company_name: str) -> Dict:
        """Run the complete audit workflow"""
        # 关键修改：直接构造一个符合 AuditState 结构的字典，而不是实例化对象
        initial_input = {
            "company_name": company_name,
            "raw_data": {},
            "metrics": {},
            "logs": [f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 初始化审计状态"]
        }

        try:
            # 调用 workflow 时传入字典
            final_output = self.workflow.invoke(
                initial_input,
                config=RunnableConfig(
                    configurable={"thread_id": f"audit-{datetime.now().timestamp()}"}
                )
            )

            # final_output 现在是一个字典或对象，取决于 LangGraph 版本，我们统一处理
            return {
                "status": "success",
                "company_name": company_name,
                "metrics": getattr(final_output, 'metrics', final_output.get('metrics', {})),
                "report": "success",
                "logs": getattr(final_output, 'logs', final_output.get('logs', [])),
                "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return {
                "status": "error",
                "company_name": company_name,
                "error": str(e),
                "logs": [f"Error: {str(e)}"],
                "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

# Example usage and testing
if __name__ == "__main__":
    print("="*80)
    print("PRODUCTION AUDIT ENGINE TEST")
    print("="*80)

    try:
        # Initialize engine
        engine = AuditEngine()

        # Test with Tesla
        test_company = "Tesla Inc."
        print(f"\nRunning audit for: {test_company}")

        result = engine.run_audit(test_company)

        if result["status"] == "success":
            print("\nAUDIT SUCCESSFUL!")
            print(f"Company: {result['company_name']}")
            print(f"Health Score: {result['metrics']['health']['overall']}/100")
            print(f"Status: {result['metrics']['health']['status'].upper()}")
            print(f"Anomalies: {result['metrics']['health']['anomaly_count']}")
            print(f"\nLast execution log: {result['logs'][-1] if result['logs'] else 'No logs'}")
        else:
            print(f"\nAUDIT FAILED: {result['error']}")
            print(f"Last logs: {result['logs'][-5:] if result['logs'] else 'No logs'}")

    except Exception as e:
        print(f"TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
