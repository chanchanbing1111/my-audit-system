'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Search, Activity, ArrowLeft, User, Bot, TrendingUp, ShieldCheck } from 'lucide-react';

export default function AuditApp() {
  const [stage, setStage] = useState<'home' | 'chat'>('home');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentAgent, setCurrentAgent] = useState<string>("初始化...");
  const scrollRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // 消息自动滚动
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const handleSend = (text?: string) => {
    const query = text || inputValue;
    if (!query.trim()) return;

    const msgId = Date.now();
    const newAssistantMsgId = msgId + 1;

    setMessages(prev => [
      ...prev,
      { id: msgId, role: 'user', content: query },
      { id: newAssistantMsgId, role: 'assistant', content: query, logs: [], step: 0, metrics: null, charts: null, loading: true }
    ]);

    setInputValue('');
    setStage('chat');
    setIsTyping(true);
    setError(null);

    // ✅ 直连 Railway 后端
    const RAILWAY_BACKEND_URL = "https://my-audit-system-production.up.railway.app";
    const url = `${RAILWAY_BACKEND_URL}/api/v1/audit?company_name=${encodeURIComponent(query)}`;

    const source = new EventSource(url);
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleSSEMessage(data, newAssistantMsgId);
      } catch (e) {
        console.error("数据解析失败", e);
      }
    };

    source.addEventListener('complete', () => {
      setIsTyping(false);
      source.close();
    });

    source.onerror = () => {
      setError('审计连接中断，请检查 API 余额或网络');
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
          return { ...msg, metrics: data.metrics, charts: data.charts, step: 4, loading: false };
        }
      }
      return msg;
    }));
  };

  const RenderChart = ({ chartData }: { chartData?: any }) => {
    const data = chartData?.profit_chart?.data || [];
    if (!data || data.length === 0) return null;

    const maxVal = Math.max(...data.map((d: any) => d.revenue || 1));
    return (
      <div className="w-full flex flex-col items-center mt-6 p-4 bg-slate-50 rounded-xl">
        <div className="text-[10px] font-black text-slate-400 mb-4 self-start">营收与利润趋势</div>
        <div className="w-full h-40 flex items-end justify-around border-b border-slate-200 pb-2">
          {data.map((d: any, i: number) => (
            <div key={i} className="flex flex-col items-center w-full">
              <div className="flex items-end gap-1 h-32">
                <div style={{ height: `${(d.revenue / maxVal) * 100}%` }} className="w-4 bg-violet-500 rounded-t-sm" />
                <div style={{ height: `${(d.profit / maxVal) * 100}%` }} className="w-4 bg-teal-400 rounded-t-sm" />
              </div>
              <span className="mt-2 text-[10px] font-bold text-slate-500">{d.year}</span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#FDFDFF] flex flex-col font-sans">
      <main className="flex-1 flex flex-col items-center relative overflow-hidden">
        {stage === 'home' ? (
          <div className="w-full max-w-4xl pt-40 px-6 flex flex-col items-center">
            <div className="w-16 h-16 bg-violet-600 rounded-3xl flex items-center justify-center mb-8 shadow-2xl shadow-violet-200">
              <ShieldCheck className="text-white" size={32} />
            </div>
            <h1 className="text-5xl font-black mb-4 tracking-tight text-slate-900">Multi-Agent 审计终端</h1>
            <p className="text-slate-400 mb-12 text-lg">基于 LangGraph 的分布式财务合规校验系统</p>
            <div className="w-full relative max-w-2xl">
              <input
                className="w-full pl-6 pr-32 py-5 bg-white rounded-2xl border border-slate-100 shadow-2xl outline-none focus:ring-2 ring-violet-500 transition-all"
                placeholder="输入分析主体，例如：比亚迪..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              />
              <button
                onClick={() => handleSend()}
                className="absolute right-3 top-3 bottom-3 px-6 bg-violet-600 text-white font-bold rounded-xl hover:bg-violet-700 transition-colors"
              >
                启动审计
              </button>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-5xl h-full flex flex-col pt-10 pb-20 px-6 overflow-y-auto">
            <div className="flex justify-between items-center mb-12">
              <button
                onClick={() => setStage('home')}
                className="flex items-center text-slate-400 font-bold hover:text-slate-600 transition-colors"
              >
                <ArrowLeft size={18} className="mr-2" /> 返回
              </button>
              <div className="bg-violet-50 px-4 py-2 rounded-full border border-violet-100 flex items-center gap-2">
                <Activity size={14} className="text-violet-500 animate-pulse" />
                <span className="text-[11px] font-black text-violet-600 uppercase">当前节点: {currentAgent}</span>
              </div>
            </div>

            <div className="space-y-8">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`flex ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start gap-4 max-w-[90%]`}>
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${msg.role === 'user' ? 'bg-violet-600 text-white' : 'bg-white border border-slate-100 text-violet-500'}`}>
                      {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                    </div>
                    <div className={`p-6 rounded-2xl ${msg.role === 'user' ? 'bg-white border border-slate-100 font-bold shadow-sm' : 'bg-white border border-slate-100 shadow-xl w-full'}`}>
                      {msg.role === 'assistant' ? (
                        <div className="space-y-4">
                          {msg.metrics ? (
                            <div>
                              <div className="grid grid-cols-2 gap-4 mb-6">
                                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                                  <div className="text-[10px] font-black text-slate-400 uppercase mb-1">审计评分</div>
                                  <div className="text-2xl font-black text-violet-600">
                                    {msg.metrics.health?.roe || "—"}
                                  </div>
                                </div>
                                <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                                  <div className="text-[10px] font-black text-slate-400 uppercase mb-1">最新营收</div>
                                  <div className="text-2xl font-black text-slate-900">
                                    {msg.metrics.health?.latest_revenue || "已核定"}
                                  </div>
                                </div>
                              </div>
                              <div className="text-sm font-bold text-slate-700 leading-relaxed mb-4">
                                <TrendingUp size={16} className="inline mr-2 text-teal-500" />
                                {msg.metrics.summary || "数据分析完成"}
                              </div>
                              <RenderChart chartData={msg.charts} />
                            </div>
                          ) : (
                            <div className="space-y-3">
                              {msg.logs.map((log: string, i: number) => (
                                <div key={i} className="text-xs text-slate-400 flex items-center">
                                  <span className="w-1 h-1 bg-violet-300 rounded-full mr-2" /> {log}
                                </div>
                              ))}
                              {msg.loading && (
                                <div className="text-xs text-violet-500 font-bold animate-pulse">
                                  Agent 正在勾稽底层账目...
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="text-slate-800">{msg.content}</div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {error && (
                <div className="p-4 bg-red-50 text-red-500 rounded-xl text-xs font-bold border border-red-100 text-center">
                  {error}
                </div>
              )}
              <div ref={scrollRef} className="h-4" />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
