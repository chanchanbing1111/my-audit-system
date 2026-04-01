'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, BarChart3, Activity, ArrowLeft, CheckCircle2, Send, User, TrendingUp, AlertCircle, Bot } from 'lucide-react';

export default function AuditApp() {
  const [stage, setStage] = useState<'home' | 'chat'>('home');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [activeTabMap, setActiveTabMap] = useState<{ [key: string]: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [currentAgent, setCurrentAgent] = useState<string>("初始化..."); // 
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const getWorkflowSteps = (name: string) => [
    { label: `语义解析`, detail: `识别主体` },
    { label: `数据穿透`, detail: `Agent 采集中` },
    { label: `风险对账`, detail: `AI 勾稽中` },
    { label: `质检完成`, detail: `多智能体终审` }
  ];

  const handleSend = (text?: string) => {
    const query = text || inputValue;
    if (!query.trim()) return;

    const msgId = Date.now();
    const newAssistantMsgId = msgId + 1;

    setMessages(prev => [
      ...prev, 
      { id: msgId, role: 'user', content: query },
      { 
        id: newAssistantMsgId, 
        role: 'assistant', 
        content: query, 
        logs: [], 
        step: 0, 
        metrics: null, 
        loading: true 
      } 
    ]);

    setInputValue('');
    setStage('chat');
    setIsTyping(true);

    // 1. 获取基础 URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    // 2. 移除末尾可能存在的斜杠，防止拼接出 //
    const cleanedApiUrl = apiUrl.replace(/\/$/, "");

    // 3. 智能拼接：检查环境变量是否已经包含了 /api/v1
    // 如果包含了，就直接用；如果不包含，才手动加上 /api/v1
    const finalBaseUrl = cleanedApiUrl.includes('/api/v1') 
        ? cleanedApiUrl 
        : `${cleanedApiUrl}/api/v1`;

    // 4. 生成最终请求地址
    const handleSend = (text?: string) => {
    const query = text || inputValue;
    if (!query.trim()) return;

    const msgId = Date.now();
    const newAssistantMsgId = msgId + 1;

    setMessages(prev => [
      ...prev, 
      { id: msgId, role: 'user', content: query },
      { 
        id: newAssistantMsgId, 
        role: 'assistant', 
        content: query, 
        logs: [], 
        step: 0, 
        metrics: null, 
        loading: true 
      } 
    ]);

    setInputValue('');
    setStage('chat');
    setIsTyping(true);

    // --- 核心修改部分：跳过 Vercel 代理，直连 Railway ---
    
    // 1. 定义你的 Railway 后端公网地址
    const RAILWAY_BACKEND_URL = "https://my-audit-system-production.up.railway.app";
    
    // 2. 拼接最终请求地址（确保包含 /api/v1 路径）
    const url = `${RAILWAY_BACKEND_URL}/api/v1/audit?company_name=${encodeURIComponent(query)}`;
    
    console.log("🚀 正在直连 Railway 后端（绕过 Vercel 超时限制）:", url);
    
    // 3. 建立 SSE 连接
    const source = new EventSource(url);

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleSSEMessage(data, newAssistantMsgId);
      } catch (e) { 
        console.error("解析数据失败:", e); 
      }
    };

    source.addEventListener('complete', () => {
      console.log("✅ 审计任务圆满完成");
      setIsTyping(false);
      source.close();
    });

    source.onerror = (err) => {
      console.error("SSE 错误详情:", err);
      // 如果你已经充值但仍报错，检查 Railway 日志是否有 429 或 Timeout
      setError('审计服务器响应异常或 AI 额度不足');
      setIsTyping(false);
      source.close();
    };

    eventSourceRef.current = source;
  };

  const handleSSEMessage = (data: any, msgId: number) => {
    setMessages(prev => prev.map(msg => {
      if (msg.id === msgId) {
        if (data.type === 'log') {
          // 如果包含智能体标识，更新当前 Agent 状态 [cite: 18]
          if (data.content.includes('[')) {
            const agentName = data.content.match(/\[(.*?)\]/)?.[1] || "";
            setCurrentAgent(agentName);
          }
          return { 
            ...msg, 
            logs: [...(msg.logs || []), data.content],
            step: Math.min((msg.step || 0) + 1, 3) 
          };
        }
        if (data.type === 'metrics') {
          setActiveTabMap(prevTab => ({ ...prevTab, [msgId]: 'profit' }));
          return { ...msg, metrics: data.metrics, charts: data.charts, step: 4, loading: false };
        }
        return msg;
      }
      return msg;
    }));
  };

  const RenderChart = ({ type, chartData }: { type: string; chartData?: any }) => {
    const data = chartData?.profit_chart?.data || [];
    if (data.length === 0) return <div className="text-slate-300 py-20 font-bold text-center w-full">等待多智能体提取数据...</div>;
    
    if (type === 'profit') {
      const maxVal = Math.max(...data.map((d: any) => d.revenue || 1));
      return (
        <div className="w-full h-full flex flex-col items-center p-6 animate-in fade-in">
          <div className="flex gap-8 mb-6 text-[10px] font-black text-slate-400">
            <div className="flex items-center"><div className="w-3 h-3 bg-violet-500 mr-2 rounded-sm" /> 营收 (亿)</div>
            <div className="flex items-center"><div className="w-3 h-3 bg-teal-400 mr-2 rounded-sm" /> 利润 (亿)</div>
          </div>
          <div className="flex-1 w-full flex items-end justify-around border-b border-slate-100 pb-2">
            {data.map((d: any, i: number) => (
              <div key={i} className="flex flex-col items-center w-20">
                <div className="flex items-end gap-1 h-40">
                  <div style={{ height: `${(d.revenue / maxVal) * 100}%` }} className="w-6 bg-violet-500 rounded-t-sm" />
                  <div style={{ height: `${(d.profit / maxVal) * 100}%` }} className="w-6 bg-teal-400 rounded-t-sm" />
                </div>
                <span className="mt-2 text-[10px] font-bold text-slate-500">{d.year}</span>
              </div>
            ))}
          </div>
        </div>
      );
    }
    return <div className="py-20 text-slate-400">资产负债表穿透中...</div>;
  };

  return (
    <div className="min-h-screen bg-[#FDFDFF] flex flex-col font-sans">
      <main className="flex-1 flex flex-col items-center relative">
        {stage === 'home' ? (
          <div className="w-full max-w-4xl pt-40 px-6 flex flex-col items-center">
            <h1 className="text-5xl font-black mb-4 text-[#1a1c2e]">Multi-Agent 审计终端</h1>
            <p className="text-slate-400 text-lg mb-12">基于 LangGraph 的多智能体财务逻辑校验系统</p>
            <div className="w-full relative">
              <input 
                className="w-full pl-14 pr-32 py-5 bg-white rounded-2xl border border-slate-100 shadow-xl outline-none"
                placeholder="输入分析主体，例如：比亚迪"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              />
              <button onClick={() => handleSend()} className="absolute right-3 top-3 bottom-3 px-8 bg-[#9D8BFF] text-white font-bold rounded-xl">启动审计</button>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-5xl h-full flex flex-col pt-10 pb-40 overflow-y-auto px-6 space-y-12">
             <div className="flex items-center justify-between">
                <button onClick={() => setStage('home')} className="flex items-center text-slate-400 font-bold text-sm"><ArrowLeft size={16} /> 返回</button>
                <div className="flex items-center space-x-2 bg-violet-50 px-4 py-1.5 rounded-full border border-violet-100">
                    <Bot size={14} className="text-violet-500 animate-pulse" />
                    <span className="text-[11px] font-black text-violet-600 uppercase">当前 Agent: {currentAgent}</span>
                </div>
             </div>

            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start gap-4 w-full`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center shadow-sm ${msg.role === 'user' ? 'bg-[#9D8BFF] text-white' : 'bg-white border border-slate-100 text-violet-500'}`}>
                    {msg.role === 'user' ? <User size={20} /> : <Activity size={20} />}
                  </div>

                  {msg.role === 'assistant' && (
                    <div className="bg-white border border-slate-100 rounded-3xl shadow-xl w-full overflow-hidden">
                      <div className="px-10 py-4 bg-slate-50/50 border-b border-slate-50 flex items-center justify-between">
                        {getWorkflowSteps(msg.content).map((s: any, i: number) => (
                          <div key={i} className="flex items-center space-x-2">
                            <CheckCircle2 size={12} className={i <= (msg.step || 0) ? "text-emerald-500" : "text-slate-200"} />
                            <span className={`text-[10px] font-black uppercase ${i <= (msg.step || 0) ? "text-slate-600" : "text-slate-300"}`}>{s.label}</span>
                          </div>
                        ))}
                      </div>
                      <div className="p-10">
                        {msg.metrics ? (
                          <>
                            <div className="grid grid-cols-3 gap-6 mb-10">
                                <div className="bg-[#F8FAFF] p-5 rounded-xl">
                                    <div className="text-[10px] font-black text-slate-400 uppercase mb-2">审计评分</div>
                                    <div className="text-3xl font-black">{msg.metrics.health?.overall || 0}</div>
                                </div>
                                <div className="bg-[#F8FAFF] p-5 rounded-xl col-span-2">
                                    <div className="text-[10px] font-black text-slate-400 uppercase mb-2">AI 审计结论</div>
                                    <div className="text-xs font-bold text-slate-600 leading-relaxed">{msg.metrics.summary}</div>
                                </div>
                            </div>
                            <div className="flex border-b border-slate-100 mb-8">
                                {['profit', 'cash'].map(t => (
                                    <button key={t} onClick={() => setActiveTabMap(p => ({...p, [msg.id]: t}))} className={`px-6 py-3 text-xs font-black ${activeTabMap[msg.id] === t ? 'text-violet-600 border-b-2 border-violet-600' : 'text-slate-400'}`}>
                                        {t === 'profit' ? '营收利润' : '现金流量'}
                                    </button>
                                ))}
                            </div>
                            <div className="h-[300px] flex items-center justify-center">
                                <RenderChart type={activeTabMap[msg.id] || 'profit'} chartData={msg.charts} />
                            </div>
                          </>
                        ) : (
                          <div className="space-y-4 py-10">
                            {msg.logs?.map((log: string, i: number) => (
                              <div key={i} className="text-xs font-medium text-slate-400 flex items-center">
                                <span className="w-1.5 h-1.5 bg-violet-300 rounded-full mr-3" /> {log}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  {msg.role === 'user' && <div className="bg-white border border-slate-100 px-6 py-3 rounded-2xl font-bold shadow-sm">{msg.content}</div>}
                </div>
              </div>
            ))}
            <div ref={scrollRef} className="h-20" />
          </div>
        )}
      </main>
    </div>
  );
}
