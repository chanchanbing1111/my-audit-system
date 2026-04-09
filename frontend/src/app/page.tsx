'use client';
import React, { useState, useEffect, useRef } from 'react';
import { Search, Activity, ArrowLeft, TrendingUp, ShieldCheck, BarChart3, PieChart, Wallet } from 'lucide-react';

// --- 模拟顶部行情数据 ---
const TICKER_DATA = [
  { name: '创业板指', val: '2,456.78', change: '-0.45%', up: false },
  { name: '标普500', val: '4,789.32', change: '+0.67%', up: true },
  { name: '纳斯达克', val: '15,234.56', change: '+1.12%', up: true },
  { name: '道琼斯', val: '38,567.23', change: '+0.34%', up: true },
  { name: '上证指数', val: '3,245.67', change: '+1.24%', up: true },
  { name: '恒生指数', val: '16,723.12', change: '-0.12%', up: false },
];

export default function AuditApp() {
  const [stage, setStage] = useState<'home' | 'chat'>('home');
  const [inputValue, setInputValue] = useState('');
  const [messages, setMessages] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'profit' | 'asset' | 'cash'>('profit');
  const [currentAgent, setCurrentAgent] = useState<string>('初始化...');
  
  const currentQueryRef = useRef<string>('');
  const sourceRef = useRef<EventSource | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 自动滚动 [cite: 6]
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // SSE 核心逻辑 [cite: 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
  useEffect(() => {
    if (stage !== 'chat' || !currentQueryRef.current) return;
    const query = currentQueryRef.current;
    const url = `https://my-audit-system-production.up.railway.app/api/v1/audit?company_name=${encodeURIComponent(query)}`;
    
    if (sourceRef.current) sourceRef.current.close();
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'log') {
          const agentName = data.content.match(/\[(.*?)\]/)?.[1] || '';
          if (agentName) setCurrentAgent(agentName);
          setMessages(prev => {
            const lastMsg = prev[prev.length - 1];
            if (lastMsg && lastMsg.role === 'assistant') {
              return [...prev.slice(0, -1), { ...lastMsg, logs: [...(lastMsg.logs || []), data.content] }];
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
                { ...lastMsg, metrics: data.metrics || {}, charts: data.charts || {}, loading: false }
              ];
            }
            return prev;
          });
        }
      } catch (e) { console.error('SSE 解析失败', e); }
    };

    source.addEventListener('complete', () => { source.close(); sourceRef.current = null; });
    source.onerror = () => { source.close(); sourceRef.current = null; };

    return () => { if (sourceRef.current) { sourceRef.current.close(); sourceRef.current = null; } };
  }, [stage]);

  const handleSend = (text?: string) => {
    const query = text || inputValue;
    if (!query.trim()) return;
    if (sourceRef.current) { sourceRef.current.close(); sourceRef.current = null; }
    currentQueryRef.current = query;
    const msgId = Date.now();
    setMessages(prev => [
      ...prev,
      { id: msgId, role: 'user', content: query },
      { id: msgId + 1, role: 'assistant', content: query, logs: [], metrics: null, charts: {}, loading: true }
    ]);
    setInputValue('');
    setStage('chat');
    setCurrentAgent('初始化...');
  };

  // --- 通用柱状图组件 [cite: 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35] ---
  const MiniBarChart = ({ data, keys, colors, formatValue, unit = '' }: any) => {
    if (!data || data.length === 0) return <div className="h-40 flex items-center justify-center text-slate-300 text-xs">暂无数据</div>;
    const maxVal = Math.max(...data.map((d: any) => Math.abs(d[keys[0]]) || 1));
    const defaultFormat = (v: number) => v >= 1000 ? `${(v / 10000).toFixed(1)}万` : v.toFixed(1);

    return (
      <div className="w-full">
        <div className="w-full h-40 flex items-end justify-around border-b border-slate-100 pb-2">
          {data.map((d: any, i: number) => (
            <div key={i} className="flex flex-col items-center flex-1 group">
              <div className="flex flex-col items-center gap-0.5 mb-1">
                {keys.map((key: string, ki: number) => (
                  <div key={ki} className="text-[9px] font-black text-slate-600 leading-tight">
                    {formatValue ? formatValue(d[key]) : defaultFormat(d[key])}
                  </div>
                ))}
              </div>
              <div className="flex items-end gap-1 h-32 relative">
                {keys.map((key: string, ki: number) => (
                  <div key={ki} style={{ height: `${Math.min((Math.abs(d[key]) / maxVal) * 100, 100)}%` }}
                    className={`w-4 ${colors[ki]} rounded-t-sm transition-all group-hover:opacity-80 relative`}
                  />
                ))}
              </div>
              <span className="mt-2 text-[10px] font-bold text-slate-400">{d.year}年</span>
            </div>
          ))}
        </div>
        {unit && <div className="text-center text-[9px] text-slate-400 mt-1">{unit}</div>}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#FDFDFF] flex flex-col font-sans">
      <main className="flex-1 flex flex-col relative overflow-hidden">
        {stage === 'home' ? (
          <div className="w-full flex flex-col items-center">
            {/* 1. 顶部实时行情条 */}
            <div className="w-full bg-[#0F172A] text-white py-2.5 overflow-hidden border-b border-slate-800">
              <div className="flex gap-10 whitespace-nowrap animate-pulse px-6">
                {TICKER_DATA.concat(TICKER_DATA).map((item, i) => (
                  <div key={i} className="flex gap-2 text-[12px] font-medium">
                    <span className="opacity-50">{item.name}</span>
                    <span className="font-bold">{item.val}</span>
                    <span className={item.up ? 'text-emerald-400' : 'text-red-400'}>{item.change}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="w-full max-w-5xl pt-24 px-6 flex flex-col items-center">
              {/* 2. 徽章 */}
              <div className="mb-6 px-4 py-1.5 bg-violet-50 rounded-full border border-violet-100 flex items-center gap-2">
                <Activity size={14} className="text-violet-500" />
                <span className="text-[11px] font-bold text-violet-600 uppercase tracking-wider">
                  Multi-Agent 驱动 · 数据 100% 真实 · 全球市场覆盖
                </span>
              </div>

              {/* 3. 标题区 */}
              <h1 className="text-6xl font-black mb-4 tracking-tight text-slate-900 text-center">
                智能财务报表分析终端
              </h1>
              <p className="text-slate-400 font-medium mb-12 text-lg">
                专业级财报深度解析 · 秒级生成研报级分析
              </p>

              {/* 4. 搜索框 */}
              <div className="w-full relative max-w-3xl mb-20 group">
                <div className="absolute left-6 top-1/2 -translate-y-1/2 text-slate-300 group-focus-within:text-violet-500 transition-colors">
                  <Search size={22} />
                </div>
                <input
                  className="w-full pl-16 pr-36 py-5.5 bg-white rounded-2xl border border-slate-100 shadow-[0_20px_50px_rgba(0,0,0,0.04)] outline-none focus:ring-2 ring-violet-500/20 focus:border-violet-200 text-lg transition-all"
                  placeholder="输入公司名称/代码，或直接提问：对比比亚迪与特斯拉的盈利能力"
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleSend()}
                />
                <button
                  onClick={() => handleSend()}
                  className="absolute right-2.5 top-2.5 bottom-2.5 px-8 bg-[#A594FD] hover:bg-violet-500 text-white font-bold rounded-xl transition-all shadow-lg shadow-violet-200"
                >
                  分析
                </button>
              </div>

              {/* 5. 功能卡片网格 */}
              <div className="grid grid-cols-3 gap-8 w-full mb-16">
                {[
                  { icon: <Search className="text-blue-500" />, title: '智能数据检索', desc: '自动抓取最新官方财报数据，覆盖多维度财务指标' },
                  { icon: <BarChart3 className="text-purple-500" />, title: '可视化图表', desc: '交互式图表展示财务趋势，直观呈现关键指标变化' },
                  { icon: <Activity className="text-teal-500" />, title: '深度统计分析', desc: '基于统计模型生成专业研报，涵盖盈利、资产、现金流分析' },
                ].map((feat, i) => (
                  <div key={i} className="p-8 bg-white border border-slate-50 rounded-2xl shadow-sm hover:shadow-md transition-all">
                    <div className="w-12 h-12 bg-slate-50 rounded-xl flex items-center justify-center mb-6">{feat.icon}</div>
                    <h3 className="text-lg font-bold text-slate-800 mb-2">{feat.title}</h3>
                    <p className="text-sm text-slate-500 leading-relaxed">{feat.desc}</p>
                  </div>
                ))}
              </div>

              {/* 6. 快速入口 */}
              <div className="flex flex-col items-center gap-4">
                <span className="text-[11px] font-bold text-slate-300 uppercase tracking-[0.2em]">快速入口</span>
                <div className="flex gap-3">
                  {['2025 科技行业展望', '高 ROE 企业排名', '新能源汽车财务对比', '芯片行业盈利分析'].map(tag => (
                    <button key={tag} onClick={() => handleSend(tag)} className="px-5 py-2.5 bg-white border border-slate-100 rounded-xl text-sm font-bold text-slate-500 hover:border-violet-200 hover:text-violet-600 transition-all shadow-sm">
                      {tag}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* 聊天界面逻辑 [cite: 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86] */
          <div className="w-full max-w-5xl h-full flex flex-col pt-10 pb-20 px-6 overflow-y-auto mx-auto">
            <div className="flex justify-between items-center mb-8">
              <button
                onClick={() => { if (sourceRef.current) sourceRef.current.close(); setStage('home'); }}
                className="flex items-center text-slate-400 font-bold hover:text-slate-600 transition-colors"
              >
                <ArrowLeft size={18} className="mr-2" /> 返回首页
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
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className="p-8 rounded-3xl bg-white border border-slate-100 shadow-2xl shadow-slate-200/50 max-w-[95%] w-full">
                    {msg.role === 'assistant' && msg.metrics ? (
                      <div>
                        <div className="grid grid-cols-3 gap-4 mb-6">
                          <div className="bg-violet-600 p-5 rounded-2xl text-white shadow-lg shadow-violet-200">
                            <div className="text-[10px] font-bold opacity-70 uppercase mb-1">综合审计评分</div>
                            <div className="text-4xl font-black">{msg.metrics.score ?? '—'}</div>
                          </div>
                          <div className="bg-slate-50 p-5 rounded-2xl border border-slate-100">
                            <div className="text-[10px] font-black text-slate-400 uppercase mb-1">ROE</div>
                            <div className="text-xl font-black text-slate-900">{msg.metrics.health?.roe ?? '—'}</div>
                          </div>
                          <div className="bg-slate-50 p-5 rounded-2xl border border-slate-100">
                            <div className="text-[10px] font-black text-slate-400 uppercase mb-1">最新营收</div>
                            <div className="text-xl font-black text-slate-900">{msg.metrics.health?.latest_revenue ?? '—'}</div>
                          </div>
                        </div>

                        <div className="text-sm font-bold text-slate-700 bg-teal-50/50 p-5 rounded-2xl border border-teal-100/50 mb-6 leading-relaxed">
                          <TrendingUp size={18} className="inline mr-2 text-teal-500" />
                          {msg.metrics.summary ?? '暂无分析结论'}
                        </div>

                        <div className="bg-slate-50 p-2 rounded-xl flex gap-2 mb-4">
                          {[
                            { id: 'profit', label: '盈利分析', icon: <BarChart3 size={14} /> },
                            { id: 'asset', label: '资产结构', icon: <PieChart size={14} /> },
                            { id: 'cash', label: '现金流', icon: <Wallet size={14} /> }
                          ].map(tab => (
                            <button key={tab.id} onClick={() => setActiveTab(tab.id as any)}
                              className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-[11px] font-bold rounded-lg transition-all ${
                                activeTab === tab.id ? 'bg-white shadow-sm text-violet-600' : 'text-slate-400 hover:bg-slate-100'
                              }`}
                            >
                              {tab.icon} {tab.label}
                            </button>
                          ))}
                        </div>

                        <div className="p-6 bg-white rounded-2xl border border-slate-100">
                          {activeTab === 'profit' && <MiniBarChart data={msg.charts?.profit_chart || []} keys={['revenue', 'profit']} colors={['bg-violet-500', 'bg-teal-400']} formatValue={(v: any) => `${v}亿`} unit="单位：亿元" />}
                          {activeTab === 'asset' && <MiniBarChart data={msg.charts?.asset_chart || []} keys={['assets', 'debt']} colors={['bg-blue-500', 'bg-orange-400']} formatValue={(v: any) => `${v}亿`} unit="单位：亿元" />}
                          {activeTab === 'cash' && <MiniBarChart data={msg.charts?.cash_chart || []} keys={['cash_flow']} colors={['bg-emerald-500']} formatValue={(v: any) => `${v}亿`} unit="单位：亿元" />}
                          
                          <div className="mt-6 flex gap-6 justify-center border-t border-slate-50 pt-4">
                            {activeTab === 'profit' && (
                              <>
                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400"><div className="w-2.5 h-2.5 bg-violet-500 rounded-full" /> 营业收入</div>
                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400"><div className="w-2.5 h-2.5 bg-teal-400 rounded-full" /> 净利润</div>
                              </>
                            )}
                            {activeTab === 'asset' && (
                              <>
                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400"><div className="w-2.5 h-2.5 bg-blue-500 rounded-full" /> 总资产</div>
                                <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400"><div className="w-2.5 h-2.5 bg-orange-400 rounded-full" /> 总负债</div>
                              </>
                            )}
                            {activeTab === 'cash' && (
                              <div className="flex items-center gap-2 text-[10px] font-bold text-slate-400"><div className="w-2.5 h-2.5 bg-emerald-500 rounded-full" /> 经营现金流</div>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {msg.logs?.map((log: string, i: number) => (
                          <div key={i} className="text-[12px] text-slate-400 flex items-center font-medium">
                            <span className="w-1.5 h-1.5 bg-violet-300 rounded-full mr-3" /> {log}
                          </div>
                        ))}
                        {msg.loading && (
                          <div className="text-sm text-violet-500 font-black animate-pulse mt-6 flex items-center gap-2">
                            <Activity size={16} /> 正在穿透底层账目，调取实时数据...
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
