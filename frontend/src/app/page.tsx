'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, BarChart3, Activity, ArrowLeft, CheckCircle2, Send, User, TrendingUp, Wallet, Plus, AlertCircle } from 'lucide-react';

export default function AuditApp() {
  const [stage, setStage] = useState<'home' | 'chat'>('home');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [activeTabMap, setActiveTabMap] = useState<{ [key: string]: string }>({});
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // 1. 修正：Workflow 步骤定义（用于 UI 渲染循环）
  const getWorkflowSteps = (name: string) => [
    { label: `语义解析`, detail: `识别实体: [${name}]` },
    { label: `数据穿透`, detail: `调取官方财报数据库...` },
    { label: `风险对账`, detail: `校验会计勾稽关系...` },
    { label: `研报生成`, detail: `聚合归因分析完成` }
  ];

  const handleSend = (text?: string) => {
    const query = text || inputValue;
    if (!query.trim()) return;

    const msgId = Date.now();
    const newAssistantMsgId = msgId + 1; 

    // 2. 修正：初始化 AI 消息时，增加 step: 0
    setMessages(prev => [
      ...prev, 
      { id: msgId, role: 'user', content: query },
      { 
        id: newAssistantMsgId, 
        role: 'assistant', 
        content: query, 
        logs: [], 
        step: 0, // 初始步骤
        metrics: null, 
        loading: true 
      } 
    ]);
    
    setInputValue('');
    setStage('chat');
    setIsTyping(true);
    setError(null);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const baseUrl = apiUrl.endsWith('/api/v1') ? apiUrl : `${apiUrl}/api/v1`;
    const url = `${baseUrl}/audit?company_name=${encodeURIComponent(query)}`;
    
    const source = new EventSource(url);

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleSSEMessage(data, newAssistantMsgId);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    source.addEventListener('complete', () => {
      setIsTyping(false);
      source.close();
    });

    source.onerror = () => {
      setError('连接到审计服务器失败');
      setIsTyping(false);
      source.close();
    };

    eventSourceRef.current = source;
  };

  const handleSSEMessage = (data: any, msgId: number) => {
    setMessages(prev => prev.map(msg => {
      if (msg.id === msgId) {
        switch (data.type) {
          case 'log':
            const logContent = data.content || data.message || "处理中...";
            // 3. 修正：每收到一次日志，该消息的 step 自动增加，上限为步骤总数
            return { 
              ...msg, 
              logs: [...(msg.logs || []), logContent],
              step: Math.min((msg.step || 0) + 1, 3) 
            };
          
          case 'metrics':
            setActiveTabMap(prevTab => ({ ...prevTab, [msgId]: 'profit' }));
            return {
              ...msg,
              metrics: data.metrics,
              charts: data.charts,
              step: 4, // 全部完成
              loading: false
            };
          
          case 'error':
            setError(data.content || "审计过程出错");
            return { ...msg, loading: false };
            
          default:
            return msg;
        }
      }
      return msg;
    }));
  };

  useEffect(() => {
    return () => { if (eventSourceRef.current) eventSourceRef.current.close(); };
  }, []);

  useEffect(() => {
    if (stage === 'chat') {
      scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages.length, isTyping, stage]);

  // 动态渲染图表逻辑：显示 2023, 2024, 2025
  const RenderChart = ({ type, chartData }: { type: string; chartData?: any }) => {
    // 1. 营收与利润趋势 (Bar Chart)
    if (type === 'profit') {
      const data = chartData?.profit_chart?.data || [];
      if (data.length === 0) return <div className="text-slate-300 py-20 font-bold">暂无财报营收数据</div>;
      const maxVal = Math.max(...data.map((d: any) => d.revenue || 1));
      
      return (
        <div className="w-full h-full flex flex-col items-center animate-in fade-in duration-500">
          <div className="flex gap-8 mb-6">
            <div className="flex items-center text-[10px] font-black text-slate-400 tracking-widest">
              <div className="w-3 h-3 bg-violet-500 mr-2 rounded-sm" /> 年度总营收 (亿)
            </div>
            <div className="flex items-center text-[10px] font-black text-slate-400 tracking-widest">
              <div className="w-3 h-3 bg-teal-400 mr-2 rounded-sm" /> 年度净利润 (亿)
            </div>
          </div>
          <div className="flex-1 w-full flex items-end justify-around px-10 border-b border-slate-100 pb-2">
            {data.map((d: any, i: number) => (
              <div key={i} className="flex flex-col items-center w-24 group">
                <div className="flex items-end gap-2 h-44 w-full justify-center">
                  <div style={{ height: `${(d.revenue / maxVal) * 90}%` }} className="w-8 bg-violet-500 rounded-t-lg shadow-lg" title={`营收: ${d.revenue}`} />
                  <div style={{ height: `${(d.profit / maxVal) * 90}%` }} className="w-8 bg-teal-400 rounded-t-lg shadow-lg" title={`利润: ${d.profit}`} />
                </div>
                <span className="mt-4 text-[11px] font-bold text-slate-500">{d.year}年</span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    // 2. 年度现金流量 (新增加的动态逻辑)
    if (type === 'cash') {
      const data = chartData?.cash_flow_chart?.data || [];
      if (data.length === 0) return <div className="text-slate-300 py-20 font-bold">未检测到经营现金流数据</div>;
      const maxCash = Math.max(...data.map((d: any) => d.cash || 1));

      return (
        <div className="w-full h-full flex flex-col items-center animate-in fade-in duration-500">
          <div className="flex-1 w-full flex items-center justify-around px-10">
            {data.map((d: any, i: number) => (
              <div key={i} className="flex flex-col items-center group">
                <div className="w-16 bg-slate-50 rounded-2xl border border-slate-100 p-1 flex flex-col-reverse h-48 overflow-hidden">
                  {/* 根据真实 cash 比例填充高度 */}
                  <div 
                    style={{ height: `${(d.cash / maxCash) * 100}%` }} 
                    className="w-full bg-gradient-to-t from-teal-600 to-teal-400 rounded-xl transition-all duration-1000" 
                  />
                </div>
                <span className="mt-4 text-[11px] font-bold text-slate-500">{d.year}年</span>
                <span className="text-[10px] font-black text-teal-600 mt-1">¥{d.cash}亿</span>
              </div>
            ))}
          </div>
        </div>
      );
    }

    // 3. 资产结构 (饼图样式)
    if (type === 'assets') {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center animate-in fade-in duration-500">
          <div className="relative w-48 h-48 mb-6">
            <div className="absolute inset-0 rounded-full border-[16px] border-violet-500 border-r-teal-400 border-b-amber-400 border-l-rose-400 rotate-45" />
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-2xl font-black">2024</span>
              <span className="text-[10px] text-slate-400 font-bold uppercase">资产穿透中</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-10 gap-y-2 text-[11px] font-bold text-slate-500">
             <div className="flex items-center"><div className="w-2 h-2 mr-2 rounded-full bg-violet-500"/>流动资产</div>
             <div className="flex items-center"><div className="w-2 h-2 mr-2 rounded-full bg-teal-400"/>固定资产</div>
          </div>
        </div>
      );
    }

    return <div className="w-full h-full flex items-center justify-center text-slate-300 font-bold">加载中...</div>;
  };
  return (
    <div className="min-h-screen bg-[#FDFDFF] flex flex-col font-sans text-slate-900">
      {/* 顶部滚动条 */}
      <div className="h-9 bg-[#0F172A] flex items-center overflow-hidden shrink-0">
        <div className="flex animate-marquee whitespace-nowrap text-[10px] font-medium tracking-tight">
          {[1, 2].map((_, i) => (
            <div key={i} className="flex items-center space-x-10 px-4">
              <span className="text-white">Tesla <span className="text-rose-500">182.45 -1.2%</span></span>
              <span className="text-white">S&P 500 <span className="text-emerald-400">+0.67%</span></span>
              <span className="text-white">NVIDIA <span className="text-emerald-400">890.23 +2.34%</span></span>
            </div>
          ))}
        </div>
      </div>

      {error && (
        <div className="fixed top-4 right-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg shadow-lg flex items-center space-x-2 z-50">
          <AlertCircle size={18} /> <span className="text-sm font-medium">{error}</span>
        </div>
      )}

      <main className="flex-1 flex flex-col items-center relative overflow-hidden">
        {stage === 'home' ? (
          <div className="w-full max-w-6xl pt-28 px-6 flex flex-col items-center animate-in fade-in duration-700">
            <h1 className="text-[64px] font-black mb-6 tracking-tight text-[#1a1c2e]">智能财务报表分析终端</h1>
            <p className="text-slate-400 text-xl mb-16 font-medium">专业级财报深度解析 · 秒级生成研报级分析</p>
            <div className="w-full max-w-[860px] relative mb-12">
              <div className="absolute inset-y-0 left-7 flex items-center pointer-events-none text-slate-300"><Search size={24} /></div>
              <input
                className="w-full pl-16 pr-32 py-5 bg-white rounded-2xl border border-slate-100 shadow-sm text-[17px] outline-none focus:ring-2 focus:ring-violet-100"
                placeholder="输入公司名称/代码进行分析..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              />
              <button onClick={() => handleSend()} className="absolute right-3 top-2.5 bottom-2.5 px-8 bg-[#9D8BFF] text-white font-bold rounded-xl">分析</button>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-5xl h-full flex flex-col pt-10 pb-32 overflow-y-auto scrollbar-hide px-6 space-y-12">
            <button onClick={() => setStage('home')} className="flex items-center text-slate-400 hover:text-black font-bold text-sm self-start transition-colors">
              <ArrowLeft size={18} className="mr-1" /> 返回首页
            </button>

            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start gap-6 w-full`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${msg.role === 'user' ? 'bg-[#9D8BFF] text-white' : 'bg-white border border-slate-100 text-violet-500'}`}>
                    {msg.role === 'user' ? <User size={20} /> : <Activity size={20} />}
                  </div>

                  {msg.role === 'user' ? (
                    <div className="bg-white border border-slate-100 px-6 py-3 rounded-2xl rounded-tr-none font-bold text-slate-800 shadow-sm">{msg.content}</div>
                  ) : (
                    <div className="bg-white border border-slate-100 rounded-3xl rounded-tl-none shadow-xl w-full overflow-hidden">
                      {/* 4. 修正：Workflow 状态栏，使用消息自带的 msg.step */}
                      <div className="px-10 py-4 bg-slate-50/50 border-b border-slate-50 flex items-center justify-between">
                        {getWorkflowSteps(msg.content).map((s: any, i: number) => (
                          <div key={i} className="flex items-center space-x-2">
                            <CheckCircle2 size={12} className={i <= (msg.step || 0) ? "text-emerald-500" : "text-slate-200"} />
                            <span className={`text-[10px] font-black uppercase tracking-widest ${i <= (msg.step || 0) ? "text-slate-600" : "text-slate-300"}`}>{s.label}</span>
                          </div>
                        ))}
                      </div>

                      <div className="p-10">
                        <div className="mb-8">
                          <div className="text-slate-300 text-[11px] font-bold mb-2 tracking-wide">分析对象：{msg.content} | 统计口径：年度审计数据 (FY2023-2025)</div>
                          <h2 className="text-3xl font-black text-[#1a1c2e]">年度核心指标纵向对比</h2>
                        </div>

                        {msg.metrics && (
                          <div className="grid grid-cols-4 gap-6 mb-12">
                            {[
                              { l: '审计综合评分', v: `${msg.metrics.health?.overall || 0}`, c: '财务稳健' },
                              { l: '最新年营收', v: `¥${msg.charts?.profit_chart?.data?.slice(-1)[0]?.revenue || '--'}亿`, c: '同比实时增长' },
                              { l: '最新净利润', v: `¥${msg.charts?.profit_chart?.data?.slice(-1)[0]?.profit || '--'}亿`, c: '盈利能力分析完成' },
                              { l: '异常项检测', v: `${msg.metrics.health?.anomaly_count || 0}`, c: '项科目待核实' },
                            ].map((item, i) => (
                              <div key={i} className="bg-[#F8FAFF]/50 p-6 rounded-2xl border border-[#F1F5FF]">
                                <div className="text-slate-400 text-[10px] font-black mb-3 uppercase tracking-wider">{item.l}</div>
                                <div className="text-2xl font-black mb-1">{item.v}</div>
                                <div className="text-xs font-bold text-emerald-500">{item.c}</div>
                              </div>
                            ))}
                          </div>
                        )}

                        <div className="flex border-b border-slate-100 mb-8">
                          {[{ id: 'profit', l: '营收利润趋势' }, { id: 'assets', l: '资产构成' }, { id: 'cash', l: '现金流量' }].map(t => (
                            <button
                              key={t.id}
                              onClick={() => setActiveTabMap(prev => ({ ...prev, [msg.id]: t.id }))}
                              className={`px-8 py-4 text-sm font-black relative ${activeTabMap[msg.id] === t.id ? 'text-violet-600' : 'text-slate-400'}`}
                            >
                              {t.l}
                              {activeTabMap[msg.id] === t.id && <div className="absolute bottom-0 left-0 right-0 h-1 bg-violet-600 rounded-t-full" />}
                            </button>
                          ))}
                        </div>

                        <div className="flex flex-col space-y-10">
                          <div className="w-full bg-white border border-slate-100 rounded-3xl p-10 min-h-[400px] flex flex-col items-center">
                            <RenderChart type={activeTabMap[msg.id] || 'profit'} chartData={msg.charts} />
                          </div>
                          
                          <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-8">
                            <div className="border-l-4 border-violet-500 pl-8 py-2">
                              <h4 className="font-black text-xl mb-4">AI 深度审计结论</h4>
                              {/* 5. 修正：替换写死的文字，使用动态 summary */}
                              <p className="text-slate-500 text-base font-medium leading-relaxed">
                                {msg.metrics?.summary || "正在深度解析该企业的资产质量、盈利能力及现金流健康度。通过 Multi-Agent 审计模型，系统将针对该公司的会计勾稽关系进行逻辑校验并生成最终审计意见。"}
                              </p>
                            </div>
                            <div className="bg-slate-50/50 rounded-2xl p-8 space-y-4">
                               <div className="flex items-start gap-4">
                                <TrendingUp size={20} className="text-violet-500 mt-1" />
                                <div><span className="block font-black text-slate-800 text-sm">CAGR:</span><span className="text-slate-500 text-sm font-medium">近三年复合增长率保持行业领先水平。</span></div>
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
            <div ref={scrollRef} className="h-40" />
          </div>
        )}

        {/* 底部输入 */}
        <div className={`fixed bottom-10 w-full flex flex-col items-center transition-all ${stage === 'home' ? 'opacity-0' : 'opacity-100'}`}>
          <div className="w-full max-w-4xl bg-white rounded-3xl shadow-2xl border border-slate-100 p-2 flex items-center">
            <input
              className="flex-1 px-8 py-4 text-[16px] outline-none font-bold bg-transparent text-slate-800"
              placeholder="追问：查看该公司年度负债明细..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
            <button onClick={() => handleSend()} className="bg-[#9D8BFF] p-4 rounded-2xl text-white"><Send size={20} /></button>
          </div>
        </div>
      </main>

      <style jsx global>{`
        @keyframes marquee { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .animate-marquee { animation: marquee 35s linear infinite; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
      `}</style>
    </div>
  );
}
