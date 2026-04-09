'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Search, Activity, ArrowLeft, User, Bot, TrendingUp, ShieldCheck, BarChart3, PieChart, Wallet } from 'lucide-react';
export default function AuditApp() {
  const [stage, setStage] = useState<'home' | 'chat'>('home');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'profit' | 'asset' | 'cash'>('profit');
  const [currentAgent, setCurrentAgent] = useState<string>('初始化...');
  // 保存当前正在分析的公司名称
  const currentQueryRef = useRef<string>('');
  // 保存 EventSource 实例，组件卸载时关闭
  const sourceRef = useRef<EventSource | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  // 消息自动滚动
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  // =====================================================
  //  核心修复：使用 useEffect 统一管理 EventSource 生命周期
  // =====================================================
  useEffect(() => {
    // 只有在 chat 阶段且有查询内容时才建立连接
    if (stage !== 'chat' || !currentQueryRef.current) return;
    const query = currentQueryRef.current;
    const url = `https://my-audit-system-production.up.railway.app/api/v1/audit?company_name=${encodeURIComponent(query)}`;
    // 关闭已有连接，防止重复
    if (sourceRef.current) {
      sourceRef.current.close();
    }
    const source = new EventSource(url);
    sourceRef.current = source;
    // 找到当前 assistant 消息的 id（最后一条）
    const assistantMsgId = Date.now() + 1;
    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'log') {
          // 提取节点名称
          const agentName = data.content.match(/\[(.*?)\]/)?.[1] || '';
          if (agentName) setCurrentAgent(agentName);
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                { ...lastMsg, logs: [...(lastMsg.logs || []), data.content] }
              ];
            }
            return prev;
          });
        }
        if (data.type === 'metrics') {
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              return [
                ...prev.slice(0, -1),
                {
                  ...lastMsg,
                  // 防御性赋值，确保不会是 undefined
                  metrics: data.metrics || {},
                  charts: data.charts || {},
                  loading: false
                }
              ];
            }
            return prev;
          });
        }
      } catch (e) {
        console.error('SSE 解析失败', e);
      }
    };
    source.addEventListener('complete', () => {
      source.close();
      sourceRef.current = null;
    });
    source.onerror = () => {
      source.close();
      sourceRef.current = null;
    };
    // =====================================================
    //  清理函数：组件卸载或下次 useEffect 执行前调用
    //  防止内存泄漏和多连接问题
    // =====================================================
    return () => {
      if (sourceRef.current) {
        sourceRef.current.close();
        sourceRef.current = null;
      }
    };
  }, [stage]); // stage 变化时重新执行
  const handleSend = (text?: string) => {
    const query = text || inputValue;
    if (!query.trim()) return;
    // 关闭之前的连接（如果有）
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    // 保存当前查询，供 useEffect 读取
    currentQueryRef.current = query;
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
        metrics: null,
        charts: {},
        loading: true
      }
    ]);
    setInputValue('');
    setStage('chat');
    setCurrentAgent('初始化...');
  };
  // --- 通用柱状图组件（防御性增强） ---
  const MiniBarChart = ({
    data,
    keys,
    colors
  }: {
    data: any[];
    keys: string[];
    colors: string[];
  }) => {
    // 防御：确保 data 是非空数组
    if (!data || !Array.isArray(data) || data.length === 0) {
      return (
        <div className="h-40 flex items-center justify-center text-slate-300 text-xs">
          暂无数据
        </div>
      );
    }
    const maxVal = Math.max(
      ...data.map(d => Math.abs(d[keys[0]]) || 1)
    );
    return (
      <div className="w-full h-40 flex items-end justify-around border-b border-slate-100 pb-2">
        {data.map((d, i) => (
          <div key={i} className="flex flex-col items-center flex-1 group">
            <div className="flex items-end gap-1 h-32 relative">
              {keys.map((key, ki) => (
                <div
                  key={ki}
                  style={{
                    height: `${Math.min((Math.abs(d[key]) / maxVal) * 100, 100)}%`
                  }}
                  className={`w-3 ${colors[ki]} rounded-t-sm transition-all group-hover:opacity-80`}
                />
              ))}
            </div>
            <span className="mt-2 text-[10px] font-bold text-slate-400">
              {d.year}
            </span>
          </div>
        ))}
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
            <h1 className="text-5xl font-black mb-4 tracking-tight text-slate-900 text-center">
              AI 审计专家终端
            </h1>
            <div className="w-full relative max-w-2xl mt-10">
              <input
                className="w-full pl-6 pr-32 py-5 bg-white rounded-2xl border border-slate-100 shadow-2xl outline-none focus:ring-2 ring-violet-500"
                placeholder="输入分析主体，例如：比亚迪..."
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
              />
              <button
                onClick={() => handleSend()}
                className="absolute right-3 top-3 bottom-3 px-6 bg-violet-600 text-white font-bold rounded-xl"
              >
                启动审计
              </button>
            </div>
          </div>
        ) : (
          <div className="w-full max-w-5xl h-full flex flex-col pt-10 pb-20 px-6 overflow-y-auto">
            <div className="flex justify-between items-center mb-8">
              <button
                onClick={() => {
                  // 返回首页时关闭连接
                  if (sourceRef.current) {
                    sourceRef.current.close();
                    sourceRef.current = null;
                  }
                  setStage('home');
                  currentQueryRef.current = '';
                }}
                className="flex items-center text-slate-400 font-bold hover:text-slate-600"
              >
                <ArrowLeft size={18} className="mr-2" /> 返回
              </button>
              <div className="bg-violet-50 px-4 py-2 rounded-full border border-violet-100 flex items-center gap-2">
                <Activity size={14} className="text-violet-500 animate-pulse" />
                <span className="text-[11px] font-black text-violet-600 uppercase">
                  当前节点: {currentAgent}
                </span>
              </div>
            </div>
            <div className="space-y-6">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`p-6 rounded-2xl bg-white border border-slate-100 shadow-xl max-w-[95%] w-full`}
                  >
                    {msg.role === 'assistant' && msg.metrics ? (
                      <div>
                        {/* 1. 核心头部：评分 + 营收 */}
                        <div className="grid grid-cols-3 gap-4 mb-6">
                          <div className="bg-violet-600 p-4 rounded-xl text-white">
                            <div className="text-[10px] font-bold opacity-70 uppercase mb-1">
                              综合审计评分
                            </div>
                            <div className="text-3xl font-black">
                              {msg.metrics.score ?? '—'}
                            </div>
                          </div>
                          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                            <div className="text-[10px] font-black text-slate-400 uppercase mb-1">
                              ROE
                            </div>
                            <div className="text-xl font-black text-slate-900">
                              {msg.metrics.health?.roe ?? '—'}
                            </div>
                          </div>
                          <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
                            <div className="text-[10px] font-black text-slate-400 uppercase mb-1">
                              最新营收
                            </div>
                            <div className="text-xl font-black text-slate-900">
                              {msg.metrics.health?.latest_revenue ?? '—'}
                            </div>
                          </div>
                        </div>
                        {/* 2. 结论分析 */}
                        <div className="text-sm font-bold text-slate-700 bg-teal-50/50 p-4 rounded-xl border border-teal-100/50 mb-6">
                          <TrendingUp size={16} className="inline mr-2 text-teal-500" />
                          {msg.metrics.summary ?? '暂无分析结论'}
                        </div>
                        {/* 3. 多维图表 Tabs */}
                        <div className="bg-slate-50 p-2 rounded-lg flex gap-2 mb-4">
                          {[
                            { id: 'profit', label: '盈利分析', icon: <BarChart3 size={14} /> },
                            { id: 'asset', label: '资产结构', icon: <PieChart size={14} /> },
                            { id: 'cash', label: '现金流', icon: <Wallet size={14} /> }
                          ].map(tab => (
                            <button
                              key={tab.id}
                              onClick={() => setActiveTab(tab.id as any)}
                              className={`flex-1 flex items-center justify-center gap-2 py-2 text-[11px] font-bold rounded-md transition-all ${
                                activeTab === tab.id
                                  ? 'bg-white shadow-sm text-violet-600'
                                  : 'text-slate-400 hover:bg-slate-100'
                              }`}
                            >
                              {tab.icon} {tab.label}
                            </button>
                          ))}
                        </div>
                        <div className="p-4 bg-white rounded-xl border border-slate-100">
                          {activeTab === 'profit' && (
                            <MiniBarChart
                              data={msg.charts?.profit_chart || []}
                              keys={['revenue', 'profit']}
                              colors={['bg-violet-500', 'bg-teal-400']}
                            />
                          )}
                          {activeTab === 'asset' && (
                            <MiniBarChart
                              data={msg.charts?.asset_chart || []}
                              keys={['assets', 'debt']}
                              colors={['bg-blue-500', 'bg-orange-400']}
                            />
                          )}
                          {activeTab === 'cash' && (
                            <MiniBarChart
                              data={msg.charts?.cash_chart || []}
                              keys={['cash_flow']}
                              colors={['bg-emerald-500']}
                            />
                          )}
                          <div className="mt-4 flex gap-4 justify-center">
                            {activeTab === 'profit' && (
                              <>
                                <div className="flex items-center gap-1 text-[10px] text-slate-400">
                                  <div className="w-2 h-2 bg-violet-500 rounded-full" /> 营收
                                </div>
                                <div className="flex items-center gap-1 text-[10px] text-slate-400">
                                  <div className="w-2 h-2 bg-teal-400 rounded-full" /> 利润
                                </div>
                              </>
                            )}
                            {activeTab === 'asset' && (
                              <>
                                <div className="flex items-center gap-1 text-[10px] text-slate-400">
                                  <div className="w-2 h-2 bg-blue-500 rounded-full" /> 总资产
                                </div>
                                <div className="flex items-center gap-1 text-[10px] text-slate-400">
                                  <div className="w-2 h-2 bg-orange-400 rounded-full" /> 总负债
                                </div>
                              </>
                            )}
                            {activeTab === 'cash' && (
                              <div className="flex items-center gap-1 text-[10px] text-slate-400">
                                <div className="w-2 h-2 bg-emerald-500 rounded-full" /> 经营现金流
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {msg.logs?.map((log: string, i: number) => (
                          <div key={i} className="text-[11px] text-slate-400 flex items-center">
                            <span className="w-1 h-1 bg-violet-300 rounded-full mr-2" /> {log}
                          </div>
                        ))}
                        {msg.loading && (
                          <div className="text-xs text-violet-500 font-bold animate-pulse mt-4">
                            正在穿透底层账目...
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={scrollRef} className="h-20" />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
