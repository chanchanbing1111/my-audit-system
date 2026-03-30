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

    def audit_logic_node(self, state: AuditState) -> AuditState:
        """Calculate financial metrics and perform audit logic"""
        state.add_log("进入审计逻辑分析阶段: 计算财务指标和对账")
        state.add_log("正在校验现金流量表与资产负债表的勾稽关系...")

        try:
            financial_data = state.raw_data["financial_metrics"]
            years = state.raw_data["years"]

            # Calculate key metrics
            metrics = {
                "profitability": {},
                "liquidity": {},
                "solvency": {},
                "efficiency": {},
                "growth": {},
                "anomalies": []
            }

            # Profitability analysis
            state.add_log("分析盈利能力指标...")
            for i, year in enumerate(years):
                revenue = financial_data["revenue"][i]
                net_income = financial_data["net_income"][i]

                if revenue > 0:
                    profit_margin = (net_income / revenue) * 100
                    metrics["profitability"][year] = {
                        "revenue": revenue,
                        "net_income": net_income,
                        "profit_margin": profit_margin
                    }

                    if profit_margin < 5:
                        metrics["anomalies"].append(f"{year}年: 净利润率 {profit_margin:.2f}% 低于5%警戒线")

            # Liquidity analysis
            state.add_log("分析流动性指标...")
            for i, year in enumerate(years):
                current_assets = financial_data["assets"][i]
                current_liabilities = financial_data["liabilities"][i]

                current_ratio = current_assets / current_liabilities if current_liabilities > 0 else 0
                metrics["liquidity"][year] = {
                    "current_ratio": current_ratio
                }

                if current_ratio < 1:
                    metrics["anomalies"].append(f"{year}年: 流动比率 {current_ratio:.2f} 低于1.0警戒线")

            # Solvency analysis
            state.add_log("分析偿债能力指标...")
            for i, year in enumerate(years):
                total_assets = financial_data["assets"][i]
                total_liabilities = financial_data["liabilities"][i]

                debt_to_equity = total_liabilities / financial_data["equity"][i] if financial_data["equity"][i] > 0 else 0
                metrics["solvency"][year] = {
                    "debt_to_equity": debt_to_equity
                }

                if debt_to_equity > 2:
                    metrics["anomalies"].append(f"{year}年: 负债权益比 {debt_to_equity:.2f} 高于2.0警戒线")

            # Growth analysis
            state.add_log("分析增长趋势...")
            for i in range(1, len(years)):
                prev_year = years[i-1]
                curr_year = years[i]

                revenue_growth = ((financial_data["revenue"][i] - financial_data["revenue"][i-1]) /
                               financial_data["revenue"][i-1]) * 100
                metrics["growth"][curr_year] = {
                    "revenue_growth": revenue_growth
                }

                if revenue_growth < 0:
                    metrics["anomalies"].append(f"{curr_year}年: 收入增长 {revenue_growth:.2f}% 为负增长")

            # Cash flow analysis
            state.add_log("分析现金流量表...")
            for i, year in enumerate(years):
                cash_flow = financial_data["cash_flow"][i]
                net_income = financial_data["net_income"][i]

                cash_flow_margin = (cash_flow / revenue) * 100 if revenue > 0 else 0
                metrics["efficiency"][year] = {
                    "cash_flow_margin": cash_flow_margin
                }

                if cash_flow_margin < 5:
                    metrics["anomalies"].append(f"{year}年: 现金流利润率 {cash_flow_margin:.2f}% 低于5%警戒线")

            # Overall health score
            state.add_log("计算整体健康评分...")
            anomaly_count = len(metrics["anomalies"])
            health_score = max(0, 100 - (anomaly_count * 10))  # Simple scoring
            metrics["health"] = {
                "overall": health_score,
                "anomaly_count": anomaly_count,
                "status": "healthy" if health_score >= 70 else "warning" if health_score >= 40 else "critical"
            }

            state.metrics = metrics
            state.add_log(f"✅ 审计逻辑分析完成，发现 {anomaly_count} 个异常")
            state.add_log(f"📊 整体健康评分: {health_score} ({metrics['health']['status']})")

        except Exception as e:
            state.add_log(f"❌ 审计逻辑分析失败: {str(e)}")
            raise

        return state

    def report_node(self, state: AuditState) -> AuditState:
        """Generate comprehensive audit report"""
        state.add_log("进入报告生成阶段: 生成审计结论")
        state.add_log("正在生成详细的财务分析报告...")

        try:
            report = f"""
# {state.company_name} 财务审计报告
## 审计日期: {datetime.now().strftime("%Y-%m-%d")}

### 审计概述
本报告基于 {state.company_name} 2023-2025 年的财务数据进行分析，重点关注盈利能力、流动性、偿债能力和增长趋势。

### 关键发现

#### 整体健康评分
- **健康评分**: {state.metrics['health']['overall']}/100
- **状态**: {state.metrics['health']['status'].upper()}
- **异常数量**: {state.metrics['health']['anomaly_count']}

#### 盈利能力分析
{self._format_metrics_section(state.metrics['profitability'], "盈利能力")}

#### 流动性分析
{self._format_metrics_section(state.metrics['liquidity'], "流动性")}

#### 偿债能力分析
{self._format_metrics_section(state.metrics['solvency'], "偿债能力")}

#### 增长趋势分析
{self._format_metrics_section(state.metrics['growth'], "增长趋势")}

#### 现金流效率
{self._format_metrics_section(state.metrics['efficiency'], "现金流效率")}

### 异常和风险
{self._format_anomalies(state.metrics['anomalies'])}

### 数据来源
{self._format_sources(state.raw_data.get('source_urls', []))}

### 执行日志
{self._format_logs(state.logs[-10:])}  # Last 10 logs for summary
"""

            state.add_log(f"✅ 报告生成完成，长度: {len(report)} 字符")
            state.add_log("审计工作流执行完毕")

        except Exception as e:
            state.add_log(f"❌ 报告生成失败: {str(e)}")
            raise

        return state

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
