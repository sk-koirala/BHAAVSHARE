import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp, TrendingDown, BarChart3, Brain, Newspaper, ArrowRight,
  Zap, Shield, Globe, ChevronRight, Activity, Cpu,
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, PieChart, Pie, Cell, Tooltip,
} from 'recharts';
import api from '../utils/api';

const FEATURES = [
  { icon: <Brain size={22} />, title: "LSTM Forecasting", desc: "PyTorch neural network trained on live GitHub OHLCV data for directional predictions." },
  { icon: <BarChart3 size={22} />, title: "124+ NEPSE Stocks", desc: "Complete coverage of every listed company with technicals, fundamentals, and history." },
  { icon: <Newspaper size={22} />, title: "Live News Sentiment", desc: "27+ RSS feeds, Reddit, and HackerNews run through multilingual NLP for market mood." },
  { icon: <Zap size={22} />, title: "Real-Time Data", desc: "Prices fetched from GitHub's auto-updating NEPSE dataset every session." },
  { icon: <Shield size={22} />, title: "AI Chat Advisor", desc: "Context-aware assistant that reads live tensors, sentiment, and prices before responding." },
  { icon: <Globe size={22} />, title: "Bilingual NLP", desc: "Understands both Nepali and English news articles for comprehensive analysis." },
];

export default function HomePage() {
  const [overview, setOverview] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.allSettled([
      api.get('/market/overview'),
      api.get('/sentiment/live'),
      api.get('/news?limit=6'),
    ]).then(([ov, se, nw]) => {
      if (!active) return;
      if (ov.status === 'fulfilled') setOverview(ov.value.data);
      if (se.status === 'fulfilled') setSentiment(se.value.data);
      if (nw.status === 'fulfilled') setNews(nw.value.data || []);
      setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const index = overview?.index;
  const gainers = overview?.gainers || [];
  const losers = overview?.losers || [];
  const tickerRow = [...gainers, ...losers];

  const pieData = sentiment ? [
    { name: 'Positive', value: sentiment.positive },
    { name: 'Negative', value: sentiment.negative },
    { name: 'Neutral', value: sentiment.neutral },
  ] : [];
  const PIE = ['#16a34a', '#dc2626', '#94a3b8'];

  const indexSeries = React.useMemo(() => {
    const base = index?.value || 1000;
    const pct = (index?.change_pct || 0) / 100;
    return Array.from({ length: 24 }).map((_, i) => ({
      t: i,
      v: +(base * (1 - pct + (pct * i / 23))).toFixed(2) + Math.sin(i / 2) * (base * 0.003),
    }));
  }, [index]);

  return (
    <div className="min-h-screen bg-slate-50">
      {/* HERO */}
      <section className="relative pt-28 pb-16 px-4 sm:px-6 bg-white border-b border-slate-100">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-100 rounded-full text-blue-600 text-xs font-semibold mb-6">
            <Activity size={12} /> AI-Powered NEPSE Intelligence
          </div>
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold leading-tight mb-5 text-slate-900">
            Smart Analysis for{' '}
            <span className="text-blue-600">NEPSE Stocks</span>
          </h1>
          <p className="text-lg text-slate-500 max-w-2xl mx-auto mb-8 leading-relaxed">
            Deep learning predictions, real-time sentiment analysis, and intelligent market insights — all in one platform built for Nepal's stock market.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link to="/stocks" className="group flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-7 py-3.5 rounded-lg font-semibold transition-colors shadow-sm btn-press">
              Explore Stocks <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
            </Link>
            <Link to="/ai" className="flex items-center gap-2 border border-slate-200 hover:border-slate-300 text-slate-700 hover:text-slate-900 px-7 py-3.5 rounded-lg font-semibold transition-colors bg-white btn-press">
              Try AI Assistant
            </Link>
          </div>
        </div>
      </section>

      {/* LIVE TICKER */}
      <section className="border-b border-slate-200 bg-white overflow-hidden">
        <div className="flex items-center gap-4 py-3 px-6">
          <div className="flex items-center gap-2 text-green-600 text-xs font-bold tracking-wider shrink-0">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
            LIVE
          </div>
          <div className="flex-1 overflow-hidden relative">
            <div className="flex gap-8 whitespace-nowrap" style={{ animation: 'scroll 60s linear infinite' }}>
              {(tickerRow.length ? [...tickerRow, ...tickerRow] : Array(8).fill({ symbol: '---', latest_close: 0, change_pct: 0 })).map((s, i) => (
                <Link to={`/stocks/${s.symbol}`} key={i} className="flex items-center gap-2 text-sm shrink-0 hover:opacity-80">
                  <span className="font-semibold text-slate-800">{s.symbol}</span>
                  <span className="font-mono text-slate-500">NPR {(s.latest_close || 0).toFixed(2)}</span>
                  <span className={`font-mono font-semibold ${(s.change_pct || 0) > 0 ? 'text-green-600' : (s.change_pct || 0) < 0 ? 'text-red-600' : 'text-slate-400'}`}>
                    {(s.change_pct || 0) > 0 ? '▲' : (s.change_pct || 0) < 0 ? '▼' : '–'} {Math.abs(s.change_pct || 0).toFixed(2)}%
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* MARKET SNAPSHOT */}
      <section className="py-12 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-end justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-slate-900 mb-1">Market Snapshot</h2>
              <p className="text-slate-500 text-sm">Live composite across {overview?.total_covered || 24} popular NEPSE tickers</p>
            </div>
            <Link to="/stocks" className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1 font-medium">All stocks <ChevronRight size={16} /></Link>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Index card */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card card-hover">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">BhaavShare Composite</div>
                  <div className="text-4xl font-bold mt-1 text-slate-900">
                    {index?.value ? index.value.toFixed(2) : '--'}
                  </div>
                </div>
                <div className={`px-3 py-1.5 rounded-lg text-sm font-semibold ${
                  (index?.change_pct || 0) >= 0
                    ? 'text-green-700 bg-green-50'
                    : 'text-red-700 bg-red-50'
                }`}>
                  {(index?.change_pct || 0) >= 0 ? '▲' : '▼'} {Math.abs(index?.change_pct || 0).toFixed(2)}%
                </div>
              </div>
              <div className="h-36 -mx-2">
                <ResponsiveContainer>
                  <AreaChart data={indexSeries}>
                    <defs>
                      <linearGradient id="idxFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2563eb" stopOpacity={0.15}/>
                        <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <Area type="monotone" dataKey="v" stroke="#2563eb" strokeWidth={2} fill="url(#idxFill)" />
                    <Tooltip contentStyle={{backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px'}} labelStyle={{display: 'none'}} itemStyle={{color: '#2563eb'}} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-4">
                <MiniStat label="Components" value={index?.components || '--'} />
                <MiniStat label="Gainers" value={gainers.filter(g => (g.change_pct || 0) > 0).length} color="green" />
                <MiniStat label="Losers" value={losers.filter(l => (l.change_pct || 0) < 0).length} color="red" />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <MoverCard title="Top Gainers" icon={<TrendingUp size={14} />} color="green" rows={gainers} loading={loading} />
              <MoverCard title="Top Losers" icon={<TrendingDown size={14} />} color="red" rows={losers} loading={loading} />
            </div>
          </div>
        </div>
      </section>

      {/* SENTIMENT + NEWS */}
      <section className="py-12 px-6 bg-white border-y border-slate-100">
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sentiment */}
          <div className="lg:col-span-5 bg-slate-50 border border-slate-200 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center">
                <Activity size={18} />
              </div>
              <div>
                <h3 className="text-base font-semibold text-slate-900">Market Sentiment</h3>
                <p className="text-xs text-slate-500">From {sentiment?.total_analyzed || 0} articles</p>
              </div>
            </div>
            {sentiment ? (
              <div className="h-48">
                <ResponsiveContainer>
                  <PieChart>
                    <Pie data={pieData} innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value" stroke="none">
                      {pieData.map((_, idx) => <Cell key={idx} fill={PIE[idx]} />)}
                    </Pie>
                    <Tooltip contentStyle={{backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px'}} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : <div className="h-48 flex items-center justify-center text-slate-400 text-sm">Loading...</div>}
            <div className="grid grid-cols-3 gap-3 mt-2">
              {[
                { label: 'Positive', val: sentiment?.positive, color: 'text-green-600' },
                { label: 'Neutral', val: sentiment?.neutral, color: 'text-slate-600' },
                { label: 'Negative', val: sentiment?.negative, color: 'text-red-600' },
              ].map(s => (
                <div key={s.label} className="bg-white border border-slate-200 rounded-lg p-3 text-center">
                  <div className={`text-xl font-bold ${s.color}`}>{s.val ?? '–'}</div>
                  <div className="text-[10px] text-slate-500 uppercase mt-0.5 font-medium">{s.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* News */}
          <div className="lg:col-span-7 bg-slate-50 border border-slate-200 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center">
                  <Newspaper size={18} />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-slate-900">Latest Market News</h3>
                  <p className="text-xs text-slate-500">From 27+ sources</p>
                </div>
              </div>
              <Link to="/news" className="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 font-medium">See all <ChevronRight size={14} /></Link>
            </div>
            <div className="space-y-2 max-h-[340px] overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
              {news.length === 0 && <div className="text-slate-400 text-sm text-center py-10">Fetching latest headlines…</div>}
              {news.map((n, i) => (
                <a key={i} href={n.url?.startsWith('http') ? n.url : '#'} target="_blank" rel="noreferrer"
                  className="block p-3 bg-white border border-slate-200 rounded-lg hover:border-blue-200 hover:shadow-sm transition">
                  <div className="text-sm font-medium text-slate-800 line-clamp-2 mb-1.5">{n.title}</div>
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold
                      ${n.sentiment_label === 'positive' ? 'bg-green-50 text-green-700'
                        : n.sentiment_label === 'negative' ? 'bg-red-50 text-red-700'
                        : 'bg-slate-100 text-slate-600'}`}>
                      {n.sentiment_label || 'neutral'}
                    </span>
                    <span className="text-[10px] text-slate-400">{n.source}</span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* FEATURES */}
      <section className="py-16 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-2xl md:text-3xl font-bold text-slate-900 mb-2">Everything You Need</h2>
            <p className="text-slate-500 max-w-xl mx-auto">Built from scratch with PyTorch, FastAPI, and React — no shortcuts.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f, i) => (
              <div key={i} className="group p-6 bg-white border border-slate-200 rounded-xl card-hover">
                <div className="w-11 h-11 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-4 group-hover:bg-blue-100 transition-colors">
                  {f.icon}
                </div>
                <h3 className="text-slate-900 font-semibold text-base mb-2">{f.title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 px-4 sm:px-6">
        <div className="max-w-3xl mx-auto text-center bg-white border border-slate-200 rounded-xl p-8 sm:p-12 shadow-card">
          <Cpu className="mx-auto text-blue-600 mb-4" size={32} />
          <h2 className="text-2xl md:text-3xl font-bold text-slate-900 mb-3">
            Ready to make smarter investments?
          </h2>
          <p className="text-slate-500 mb-6">Join BhaavShare and get AI-powered insights for your NEPSE portfolio.</p>
          <Link to="/signup" className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-7 py-3.5 rounded-lg font-semibold transition-colors shadow-sm btn-press">
            Start Free <ChevronRight size={18} />
          </Link>
        </div>
      </section>
    </div>
  );
}

function MiniStat({ label, value, color }) {
  const textColor = color === 'green' ? 'text-green-600' : color === 'red' ? 'text-red-600' : 'text-slate-800';
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-center">
      <div className="text-[10px] text-slate-500 uppercase font-medium">{label}</div>
      <div className={`font-bold mt-0.5 ${textColor}`}>{value}</div>
    </div>
  );
}

function MoverCard({ title, icon, color, rows, loading }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card card-hover">
      <div className={`flex items-center gap-2 mb-3 ${color === 'green' ? 'text-green-600' : 'text-red-600'} text-xs uppercase font-semibold tracking-wider`}>
        {icon} {title}
      </div>
      {loading ? (
        <div className="space-y-2">{Array.from({length: 5}).map((_, i) => <div key={i} className="h-10 bg-slate-100 rounded-lg animate-pulse"/>)}</div>
      ) : (
        <div className="space-y-1.5">
          {rows.slice(0, 6).map((s, i) => (
            <Link to={`/stocks/${s.symbol}`} key={i}
              className="flex items-center justify-between gap-2 p-2.5 bg-slate-50 border border-slate-100 rounded-lg hover:border-slate-200 transition min-w-0">
              <div className="min-w-0">
                <div className="font-semibold text-sm text-slate-800">{s.symbol}</div>
                <div className="text-[10px] text-slate-400 truncate">{s.sector}</div>
              </div>
              <div className="text-right shrink-0">
                <div className="font-mono text-sm text-slate-700 whitespace-nowrap">NPR {(s.latest_close || 0).toFixed(2)}</div>
                <div className={`text-[11px] font-mono font-semibold whitespace-nowrap ${(s.change_pct || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {(s.change_pct || 0) >= 0 ? '+' : ''}{(s.change_pct || 0).toFixed(2)}%
                </div>
              </div>
            </Link>
          ))}
          {!rows.length && <div className="text-center text-slate-400 text-xs py-6">No data</div>}
        </div>
      )}
    </div>
  );
}
