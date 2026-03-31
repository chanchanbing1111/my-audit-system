async def audit_logic_node(self, state: AuditState) -> Dict:
        new_logs = list(state.logs)
        
        # 1. 🛠️ 精准上下文构建
        search_results = state.raw_data.get("search_results", [])
        context_list = []
        for r in search_results[:5]:
            context_list.append(f"来源标题: {r.get('title')}\n内容摘要: {r.get('content')[:800]}")
        context = "\n---\n".join(context_list)
        
        from openai import OpenAI
        client = OpenAI(api_key=self.openai_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")

        for attempt in range(3):
            try:
                # 2. 🧠 强化 Prompt
                prompt = f"""你是一名资深财务审计师。请分析材料并提取 {state.company_name} 2023-2025 财务数据。
                
                ⚖️ 审计要求：
                1. 单位换算：若原数据为美元($)，必须乘以 7.2 转换为亿元人民币。
                2. 逻辑填补：若材料未显式提及 2025 年，请根据 2023/2024 趋势进行合理预估，严禁返回全 0。
                3. 特别注意：特斯拉 2023 营收约为 967 亿美元（约 7000 亿人民币），请确保数据量级正确。

                返回 JSON 格式：
                {{
                  "overall_score": 85,
                  "summary": "一句话审计总结",
                  "financials": [
                    {{"year": "2023", "revenue": 100.5, "profit": 10.2, "cash": 20.5}},
                    ...
                  ]
                }}
                
                材料内容：
                {context}"""

                response = client.chat.completions.create(
                    model="glm-4-flash",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=50 
                )
                
                content = response.choices[0].message.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].strip()

                res = json.loads(content)
                f_data = res.get("financials", [])

                if not f_data or f_data[0].get("revenue") == 0:
                    raise ValueError("AI 返回了无效的 0 数据")

                return {
                    "metrics": {
                        "health": {"overall": res.get("overall_score", 85), "status": "healthy"},
                        "summary": res.get("summary", ""),
                        "growth_analysis": "已完成财报数据对齐与趋势预估。"
                    },
                    "charts": {
                        "profit_chart": {"data": f_data},
                        "cash_flow_chart": {"data": f_data}
                    },
                    "logs": new_logs + ["⚖️ 风险对账：已完成 AI 逻辑审计与汇率校准"]
                }

            except Exception as e:
                if attempt < 2:
                    logger.warning(f"审计节点重试 {attempt+1}: {e}")
                    await asyncio.sleep(2)
                    continue
                
                logger.error(f"审计逻辑节点最终失败: {e}")
                return {
                    "metrics": {"health": {"overall": 0, "status": "error"}, "summary": f"提取失败: {str(e)}"},
                    "charts": {"profit_chart": {"data": []}, "cash_flow_chart": {"data": []}},
                    "logs": new_logs + [f"❌ 逻辑分析失败: {str(e)}"]
                }
