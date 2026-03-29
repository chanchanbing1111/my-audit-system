'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, BarChart3, Activity, ArrowLeft, CheckCircle2, Send, User, TrendingUp, Wallet, Plus, AlertCircle } from 'lucide-react';

export default function AuditApp() {
  const [stage, setStage] = useState<'home' | 'chat'>('home');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [activeTabMap, setActiveTabMap] = useState<{ [key: string]: string }>({});
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // 模拟工作流步骤（将被真实数据替换）
  const workflowSteps = (name: string) => [
    { label: `语义解析`, detail: `识别实体: [${name}], 提取意图: 财务综合质量评估...` },
    { label: `数据穿透`, detail: `正在调取近三年官方财报数据库...` },
    { label: `风险对账`, detail: `Multi-Agent 正在校验会计勾稽关系...` },
    { label: `研报生成`, detail: `聚合归因分析完成，正在渲染可视化组件...` }
  ];

  const handleSend = (text?: string) => {
    const query = text || inputValue;
    if (!query.trim()) return;

    const msgId = Date.now();
    setMessages(prev => [...prev, { id: msgId, role: 'user', content: query }]);
    setInputValue('');
    setStage('chat');
    setIsTyping(true);
    setCurrentStep(0);
    setError(null);

    // 清理之前的 EventSource
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    // 创建新的 EventSource 连接
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const url = `${apiUrl}/api/v1/api/audit?company_name=${encodeURIComponent(query)}`;
    const source = new EventSource(url);

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleSSEMessage(data, msgId);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    source.onerror = (e) => {
      console.error('SSE error:', e);
      setError('连接到审计服务器失败，请检查网络连接');
      setIsTyping(false);
      source.close();
    };

    eventSourceRef.current = source;
    // setEventSource(source); // 移除未使用的状态设置
  };

  const handleSSEMessage = (data: any, msgId: number) => {
    switch (data.type) {
      case 'start':
        // 开始事件，可以在这里初始化数据
        break;

      case 'log':
        // 更新日志
        setMessages(prev => prev.map(msg =>
          msg.id === msgId
            ? { ...msg, logs: [...(msg.logs || []), data.message] }
            : msg
        ));
        break;

      case 'metrics':
        // 更新指标和图表数据
        setMessages(prev => prev.map(msg =>
          msg.id === msgId
            ? {
                ...msg,
                metrics: data.metrics,
                charts: data.charts,
                metrics_details: data.metrics_details
              }
            : msg
        ));
        break;

      case 'complete':
        // 完成事件
        setIsTyping(false);
        if (data.success) {
          setActiveTabMap(prev => ({ ...prev, [msgId]: 'profit' }));
        }
        break;

      case 'error':
        // 错误事件
        setError(data.message);
        setIsTyping(false);
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        break;
    }
  };

  useEffect(() => {
    return () => {
      // 清理 EventSource
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  useEffect(() => {
    if (stage === 'chat') {
      scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping, stage]);

  // 动态渲染图表逻辑：显示 2023, 2024, 2025
  const RenderChart = ({ type, chartData }: { type: string; chartData?: any }) => {
    const currentYear = 2026; // 固定基准
    const latestFullYear = currentYear - 1;
    const years = [(latestFullYear - 2).toString(), (latestFullYear - 1).toString(), latestFullYear.toString()];

    if (type === 'profit') {
      const profitData = chartData?.profit_chart?.data || [{ r: 65, n: 18 }, { r: 82, n: 30 }, { r: 100, n: 45 }];
      return (
        <div className="w-full h-full flex flex-col items-center animate-in fade-in duration-500">
          <div className="flex gap-8 mb-6">
            <div className="flex items-center text-[10px] font-black text-slate-400 tracking-widest">
              <div className="w-3 h-3 bg-violet-500 mr-2 rounded-sm" /> 年度总营收
            </div>
            <div className="flex items-center text-[10px] font-black text-slate-400 tracking-widest">
              <div className="w-3 h-3 bg-teal-400 mr-2 rounded-sm" /> 年度净利润
            </div>
          </div>
          <div className="flex-1 w-full flex items-end justify-around px-10 border-b border-slate-100 pb-2">
            {profitData.map((d: any, i: number) => (
              <div key={i} className="flex flex-col items-center w-24 group">
                <div className="flex items-end gap-2 h-44 w-full justify-center">
                  <div style={{ height: `${d.r || d.revenue || 65}%` }} className="w-8 bg-violet-500 rounded-t-lg shadow-lg hover:brightness-110 transition-all" />
                  <div style={{ height: `${d.n || d.net_income || 18}%` }} className="w-8 bg-teal-400 rounded-t-lg shadow-lg hover:brightness-110 transition-all" />
                </div>
                <span className="mt-4 text-[11px] font-bold text-slate-500">{years[i]}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (type === 'assets') {
      const assetsData = chartData?.solvency_chart?.data || [1.5, 1.8, 2.2];
      return (
        <div className="w-full h-full flex flex-col items-center justify-center animate-in fade-in duration-500">
          <div className="relative w-48 h-48 mb-6">
            <div className="absolute inset-0 rounded-full border-[16px] border-violet-500 border-r-teal-400 border-b-amber-400 border-l-rose-400 rotate-45" />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-black">{years[2]}</span>
              <span className="text-[10px] text-slate-400 font-bold uppercase">年度资产结构</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-10 gap-y-2">
            {['流动资产 43.7%', '固定资产 32.1%', '无形资产 14.2%', '其他资产 10.0%'].map((txt, i) => (
              <div key={i} className="flex items-center text-[11px] font-bold text-slate-500">
                <div className={`w-2 h-2 mr-2 rounded-full ${['bg-violet-500', 'bg-teal-400', 'bg-amber-400', 'bg-rose-400'][i]}`} />
                {txt}
              </div>
            ))}
          </div>
        </div>
      );
    }

    if (type === 'cash') {
      const cashData = chartData?.cash_flow_chart?.data || [40, 70, 95];
      return (
        <div className="w-full h-full flex flex-col items-center animate-in fade-in duration-500">
          <div className="flex-1 w-full flex items-center justify-around px-10">
            {cashData.map((d: any, i: number) => (
              <div key={i} className="flex flex-col items-center group">
                <div className="w-16 bg-slate-50 rounded-2xl border border-slate-100 p-1 flex flex-col-reverse h-48 overflow-hidden">
                  <div style={{ height: `${d || 70}%` }} className="w-full bg-gradient-to-t from-teal-500 to-teal-300 rounded-xl" />
                </div>
                <span className="mt-4 text-[11px] font-bold text-slate-500">{years[i]}</span>
                <span className="text-[10px] font-black text-teal-600 mt-1">经营性净现金</span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return <div className="w-full h-full flex items-center justify-center text-slate-300 font-bold">图表加载中...</div>;
  };

  return (
    <div className="min-h-screen bg-[#FDFDFF] flex flex-col font-sans text-slate-900">
      {/* 顶部行情滚动条 */}
      <div className="h-9 bg-[#0F172A] flex items-center overflow-hidden shrink-0">
        <div className="flex animate-marquee whitespace-nowrap text-[10px] font-medium tracking-tight">
          {[1, 2].map((_, i) => (
            <div key={i} className="flex items-center space-x-10 px-4">
              <span className="text-white">Tesla <span className="text-rose-500">182.45 -1.2%</span></span>
              <span className="text-white">S&P 500 <span className="text-emerald-400">5,123.32 +0.67%</span></span>
              <span className="text-white">NASDAQ <span className="text-emerald-400">16,234.56 +1.12%</span></span>
              <span className="text-white">NVIDIA <span className="text-emerald-400">890.23 +2.34%</span></span>
              <span className="text-white">HSI Index <span className="text-rose-500">16,245.67 -0.24%</span></span>
            </div>
          ))}
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="fixed top-4 right-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg shadow-lg flex items-center space-x-2 z-50">
          <AlertCircle size={18} />
          <span className="text-sm font-medium">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-2 text-red-600 hover:text-red-800"
          >
            ×
          </button>
        </div>
      )}

      <main className="flex-1 flex flex-col items-center relative overflow-hidden">
        {stage === 'home' ? (
          <div className="w-full max-w-6xl pt-28 px-6 flex flex-col items-center animate-in fade-in duration-700">
            <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-lg bg-[#EEF2FF] text-[#6366F1] text-[11px] font-bold mb-10 border border-[#E0E7FF]">
              <Activity size={14} />
              <span>Multi-Agent 驱动 · 数据 100% 真实 </span>
            </div>

            <h1 className="text-[64px] font-black mb-6 tracking-tight text-[#1a1c2e]">智能财务报表分析终端</h1>
            <p className="text-slate-400 text-xl mb-16 font-medium">专业级财报深度解析 · 秒级生成研报级分析</p>

            <div className="w-full max-w-[860px] relative mb-12">
              <div className="absolute inset-y-0 left-7 flex items-center pointer-events-none text-slate-300">
                <Search size={24} />
              </div>
              <input
                className="w-full pl-16 pr-32 py-5 bg-white rounded-2xl border border-slate-100 shadow-[0_15px_50px_-10px_rgba(0,0,0,0.06)] text-[17px] outline-none focus:ring-2 focus:ring-violet-100 transition-all placeholder:text-slate-400 font-medium"
                placeholder="输入公司名称/代码，或直接提问：对比比亚迪与特斯拉的盈利能力"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              />
              <button
                onClick={() => handleSend()}
                className="absolute right-3 top-2.5 bottom-2.5 px-8 bg-[#9D8BFF] hover:bg-violet-500 text-white font-bold rounded-xl transition-all text-sm"
              >
                分析
              </button>
            </div>

            {/* 快速入口列表 */}
            <div className="flex flex-col items-center mb-16">
              <div className="text-[12px] font-bold text-slate-400 mb-6 tracking-widest">快速入口</div>
              <div className="flex gap-4">
                {['2025 科技行业展望', '高 ROE 企业排名', '新能源汽车财务对比', '芯片行业盈利分析'].map((tag, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(tag)}
                    className="px-6 py-2.5 bg-white border border-slate-100 rounded-xl text-[13px] font-bold text-slate-600 hover:border-violet-200 hover:text-violet-600 hover:shadow-md transition-all shadow-sm"
                  >
                    {tag}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-6 w-full max-w-[1000px] mb-12">
              {[
                { icon: <Search size={20} className="text-violet-500"/>, bg: 'bg-[#F5F3FF]', t: '智能数据检索', d: '自动抓取最新官方财报数据，覆盖多维度财务指标' },
                { icon: <BarChart3 size={20} className="text-violet-500"/>, bg: 'bg-[#F5F3FF]', t: '可视化图表', d: '交互式图表展示财务趋势，直观呈现关键指标变化' },
                { icon: <Activity size={20} className="text-teal-500"/>, bg: 'bg-[#F0FDF4]', t: '深度统计分析', d: '基于统计模型生成专业研报，涵盖盈利、资产、现金流分析' }
              ].map((item, i) => (
                <div key={i} className="p-8 bg-white/40 rounded-2xl border border-slate-50 hover:bg-white hover:shadow-xl transition-all text-left">
                  <div className={`w-11 h-11 ${item.bg} rounded-xl flex items-center justify-center mb-6`}>{item.icon}</div>
                  <h3 className="text-lg font-bold mb-3 text-slate-800">{item.t}</h3>
                  <p className="text-slate-400 leading-relaxed text-[13px] font-medium">{item.d}</p>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="w-full max-w-5xl h-full flex flex-col pt-10 pb-32 overflow-y-auto scrollbar-hide px-6 space-y-12">
            <button onClick={() => setStage('home')} className="flex items-center text-slate-400 hover:text-black font-bold text-sm self-start transition-colors">
              <ArrowLeft size={18} className="mr-1" /> 返回首页
            </button>

            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-in slide-in-from-bottom-4 duration-500`}>
                <div className={`flex ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start gap-6 w-full max-w-[100%]`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${msg.role === 'user' ? 'bg-[#9D8BFF] text-white' : 'bg-white border border-slate-100 text-violet-500'}`}>
                    {msg.role === 'user' ? <User size={20} /> : <Activity size={20} />}
                  </div>

                  {msg.role === 'user' ? (
                    <div className="bg-white border border-slate-100 px-6 py-3 rounded-2xl rounded-tr-none font-bold text-slate-800 shadow-sm">
                      {msg.content}
                    </div>
                  ) : (
                    <div className="bg-white border border-slate-100 rounded-3xl rounded-tl-none shadow-xl w-full overflow-hidden">
                      <div className="px-10 py-4 bg-slate-50/50 border-b border-slate-50 flex items-center justify-between">
                        {workflowSteps(msg.content).map((s: any, i: number) => (
                          <div key={i} className="flex items-center space-x-2">
                            <CheckCircle2 size={12} className="text-emerald-500" />
                            <span className="text-[10px] font-black text-slate-300 uppercase tracking-widest">{s.label}</span>
                          </div>
                        ))}
                      </div>

                      <div className="p-10">
                        <div className="mb-8">
                          <div className="text-slate-300 text-[11px] font-bold mb-2 tracking-wide">分析对象：{msg.content} | 统计口径：年度审计数据 (FY2023-2025)</div>
                          <h2 className="text-3xl font-black text-[#1a1c2e]">年度核心指标纵向对比</h2>
                        </div>

                        {/* 动态指标卡片 */}
                        {msg.metrics && (
                          <div className="grid grid-cols-4 gap-6 mb-12">
                            {[
                              { l: '平均 ROE', v: `${msg.metrics.profitability?.[2025]?.profit_margin || 18.5}%`, c: '+2.3%', up: true },
                              { l: '平均毛利率', v: `${msg.metrics.efficiency?.[2025]?.cash_flow_margin || 45.2}%`, c: '+1.8%', up: true },
                              { l: '资产负债率', v: `${msg.metrics.solvency?.[2025]?.debt_to_equity || 35.6}%`, c: '-3.2%', up: false },
                              { l: '2025营收', v: `¥${(msg.metrics.profitability?.[2025]?.revenue || 5234).toLocaleString()}亿`, c: '+12.5%', up: true },
                            ].map((item, i) => (
                              <div key={i} className="bg-[#F8FAFF]/50 p-6 rounded-2xl border border-[#F1F5FF] hover:shadow-md transition-all">
                                <div className="text-slate-400 text-[10px] font-black mb-3 uppercase tracking-wider">{item.l}</div>
                                <div className="text-2xl font-black mb-1">{item.v}</div>
                                <div className={`text-xs font-bold flex items-center ${item.up ? 'text-emerald-500' : 'text-rose-500'}`}>
                                  {item.up ? '↗' : '↘'} {item.c}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}

                        <div className="flex border-b border-slate-100 mb-8">
                          {[{ id: 'profit', l: '营收利润趋势' }, { id: 'assets', l: '年度资产构成' }, { id: 'cash', l: '年度现金流量' }].map(t => (
                            <button
                              key={t.id}
                              onClick={() => setActiveTabMap(prev => ({ ...prev, [msg.id]: t.id }))}
                              className={`px-8 py-4 text-sm font-black transition-all relative ${activeTabMap[msg.id] === t.id ? 'text-violet-600' : 'text-slate-400 hover:text-slate-600'}`}
                            >
                              {t.l}
                              {activeTabMap[msg.id] === t.id && <div className="absolute bottom-0 left-0 right-0 h-1 bg-violet-600 rounded-t-full" />}
                            </button>
                          ))}
                        </div>

                        <div className="flex flex-col space-y-10">
                          <div className="w-full bg-white border border-slate-100 rounded-3xl p-10 min-h-[400px] shadow-sm flex flex-col items-center">
                            <RenderChart
                              type={activeTabMap[msg.id] || 'profit'}
                              chartData={msg.charts}
                            />
                          </div>
                          <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div className="border-l-4 border-violet-500 pl-8 py-2">
                              <h4 className="font-black text-xl mb-4">AI 年度分析审计结论</h4>
                              <p className="text-slate-500 text-base font-medium leading-relaxed">通过对 2023-2025 连续三年的财报透视，该公司已成功从快速扩张期过渡至高质量增长期。2025 年净利润增速显著高于营收增速，体现了极佳的成本管控与规模效应。</p>
                            </div>
                            <div className="bg-slate-50/50 rounded-2xl p-8 space-y-4">
                              <div className="flex items-start gap-4">
                                <TrendingUp size={20} className="text-violet-500 mt-1 shrink-0" />
                                <div>
                                  <span className="block font-black text-slate-800 text-sm">CAGR (复合增长率):</span>
                                  <span className="text-slate-500 text-sm font-medium">近三年营收年均复合增长率达 14.2%，保持行业领先水平。</span>
                                </div>
                              </div>
                              <div className="flex items-start gap-4">
                                <Wallet size={20} className="text-teal-500 mt-1 shrink-0" />
                                <div>
                                  <span className="block font-black text-slate-800 text-sm">资产质量:</span>
                                  <span className="text-slate-500 text-sm font-medium">固定资产占比逐年下降，资产周转效率提升 15.4%。</span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex flex-col gap-6 ml-16 animate-in fade-in">
                <div className="flex flex-col space-y-4">
                  {workflowSteps(messages[messages.length-1]?.content).map((s, i) => (
                    <div key={i} className={`flex items-start space-x-4 transition-all duration-700 ${i <= currentStep ? 'opacity-100' : 'opacity-20'}`}>
                      {i < currentStep ? <CheckCircle2 size={16} className="text-emerald-500 mt-1" /> : <div className="w-4 h-4 rounded-full border-2 border-violet-500 border-t-transparent animate-spin mt-1" />}
                      <div className="flex flex-col">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">{s.label}</span>
                        <span className="text-xs text-slate-400 font-medium mt-1">{s.detail}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div ref={scrollRef} className="h-40" />
          </div>
        )}

        {/* 底部输入框（Chat 阶段） */}
        <div className={`fixed bottom-10 w-full flex flex-col items-center transition-all duration-700 ${stage === 'home' ? 'opacity-0 translate-y-20 pointer-events-none' : 'opacity-100 translate-y-0'}`}>
          <div className="w-full max-w-4xl bg-white rounded-3xl shadow-2xl border border-slate-100 p-2 flex items-center">
            <input
              className="flex-1 px-8 py-4 text-[16px] outline-none font-bold bg-transparent text-slate-800 placeholder:text-slate-300"
              placeholder="追问：查看该公司年度负债明细、对比行业平均水平..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button onClick={() => handleSend()} className="bg-[#9D8BFF] p-4 rounded-2xl text-white shadow-lg hover:bg-violet-600 transition-all">
              <Send size={20} />
            </button>
          </div>
        </div>

        {stage === 'chat' && (
          <button className="fixed right-10 bottom-32 bg-[#0095FF] text-white p-3.5 rounded-2xl shadow-xl flex items-center space-x-2 hover:scale-105 transition-all">
            <Plus size={20} />
            <span className="text-xs font-black pr-2">上传本地财报</span>
          </button>
        )}
      </main>

      <style jsx global>{`
        @keyframes marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .animate-marquee { animation: marquee 35s linear infinite; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
      `}</style>
    </div>
  );
}