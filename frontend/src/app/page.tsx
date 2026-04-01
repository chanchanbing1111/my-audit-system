'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, BarChart3, Activity, ArrowLeft, CheckCircle2, User, Bot } from 'lucide-react';

export default function AuditApp() {
  const [stage, setStage] = useState<'home' | 'chat'>('home');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [activeTabMap, setActiveTabMap] = useState<{ [key: string]: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [currentAgent, setCurrentAgent] = useState<string>("初始化...");
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
      { id: newAssistantMsgId, role: 'assistant', content: query, logs: [], step: 0, metrics: null, loading: true } 
    ]);

    setInputValue('');
    setStage('chat');
    setIsTyping(true);

    // ✅ 核心修复：直连 Railway 后端，绕过 Vercel 10秒超时限制
    const RAILWAY_BACKEND_URL = "https://my-audit-system-production.up.railway.app";
    const url = `${RAILWAY_BACKEND_URL}/api/v1/audit?company_name=${encodeURIComponent(query)}`;
    
    console.log("🚀 正在请求后端地址:", url);
    
    const source = new EventSource(url);
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleSSEMessage(data, newAssistantMsgId);
      } catch (e) { console.error(e); }
    };

    source.addEventListener('complete', () => {
      setIsTyping(false);
      source.close();
    });

    source.onerror = () => {
      setError('审计服务器连接超时');
      setIsTyping(false);
      source.close();
    };

    eventSourceRef.current = source;
  };

  const handleSSEMessage = (data: any, msgId: number) => {
    setMessages(prev => prev.map(msg => {
      if (msg.id === msgId) {
        if (data.type === 'log') {
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
    
    const maxVal = Math.max(...data.map((d: any) => d.revenue || 1));
    return (
      <div className="w-full h-full flex flex-col items-center p-6 animate-in fade-in">
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
  };

  return (
    <div className="min-h-screen bg-[#FDFDFF] flex flex-col">
      <main className="flex-1 flex flex-col items-center relative">
        {stage === 'home' ? (
          <div className="w-full max-w-4xl pt-40 px-6 flex flex-col items-center">
            <h1 className="text-5xl font-black mb-4">Multi-Agent 审计终端</h1>
            <input 
              className="w-full p-5 bg-white rounded-2xl border border-slate-100 shadow-xl"
              placeholder="输入分析主体..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            />
          </div>
        ) : (
          <div className="w-full max-w-5xl p-10">
             <div className="flex justify-between mb-8">
                <button onClick={() => setStage('home')} className="text-slate-400 font-bold">← 返回</button>
                <div className="bg-violet-50 px-4 py-1.5 rounded-full border border-violet-100">
                    <span className="text-[11px] font-black text-violet-600 uppercase">Agent: {currentAgent}</span>
                </div>
             </div>

            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} mb-6`}>
                <div className={`flex ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start gap-4 w-full`}>
                  <div className="w-10 h-10 rounded-xl bg-white border border-slate-100 flex items-center justify-center">
                    {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                  </div>
                  <div className="bg-white border border-slate-100 p-6 rounded-2xl shadow-sm max-w-3xl">
                    {msg.role === 'assistant' && msg.metrics ? (
                        <RenderChart type={activeTabMap[msg.id] || 'profit'} chartData={msg.charts} />
                    ) : (
                        <div className="text-sm text-slate-600">{msg.content}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
} // ✅ 确保这里是文件末尾，且 AuditApp 组件已闭合
