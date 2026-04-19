import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Search, TrendingUp, TrendingDown, Minus, Cpu, Activity, Star, CheckCircle2, XCircle, Clock } from 'lucide-react';
import {
  ResponsiveContainer, ComposedChart, Area, Line, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine, Legend,
} from 'recharts';
import api, { ALL_STOCKS } from '../utils/api';
import { useAuth } from '../context/AuthContext';

const RANGES = [
  { label: '1M', days: 22 }, { label: '3M', days: 66 }, { label: '6M', days: 132 },
  { label: '1Y', days: 252 }, { label: 'All', days: 800 },
];

export default function StocksPage() {
  const { symbol: urlSymbol } = useParams();
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();

  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState(urlSymbol?.toUpperCase() || 'NABIL');
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [predHistory, setPredHistory] = useState(null);
  const [range, setRange] = useState(RANGES[1]);
  const [training, setTraining] = useState(false);
  const [trainMsg, setTrainMsg] = useState(null);
  const [watchlist, setWatchlist] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sectorFilter, setSectorFilter] = useState('All');

  const filtered = useMemo(() =>
    ALL_STOCKS.filter(s => s.includes(search.toUpperCase())),
  [search]);

  useEffect(() => {
    if (!user) return;
    api.get('/watchlist').then(r => setWatchlist(r.data.map(w => w.symbol))).catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    setTrainMsg(null);
    Promise.allSettled([
      api.get(`/stocks/${selected}`),
      api.get(`/stocks/${selected}/history?days=${range.days}`),
      api.get(`/predict/${selected}`),
      api.get(`/predict/${selected}/history?limit=10`),
    ]).then(([s, h, p, ph]) => {
      setSummary(s.status === 'fulfilled' ? s.value.data : null);
      setHistory(h.status === 'fulfilled' ? h.value.data : null);
      setPrediction(p.status === 'fulfilled' ? p.value.data : null);
      setPredHistory(ph.status === 'fulfilled' ? ph.value.data : null);
      setLoading(false);
    });
  }, [selected, range]);

  useEffect(() => {
    if (urlSymbol && urlSymbol.toUpperCase() !== selected) setSelected(urlSymbol.toUpperCase());
    // eslint-disable-next-line
  }, [urlSymbol]);

  const trainModel = async () => {
    setTraining(true);
    setTrainMsg(`Training LSTM on ${selected}…`);
    try {
      const r = await api.post(`/predict/train/${selected}?epochs=20`);
      setTrainMsg(`✓ Done — ${r.data.epochs} epochs · Loss ${r.data.loss.toFixed(4)}`);
      const p = await api.get(`/predict/${selected}`);
      setPrediction(p.data);
    } catch { setTrainMsg('✗ Training failed.'); }
    finally { setTraining(false); }
  };

  const toggleWatch = async () => {
    if (!user) { navigate('/login'); return; }
    if (watchlist.includes(selected)) {
      await api.delete(`/watchlist/${selected}`).catch(() => {});
      setWatchlist(w => w.filter(s => s !== selected));
    } else {
      await api.post('/watchlist', { symbol: selected }).catch(() => {});
      setWatchlist(w => [...w, selected]);
    }
  };

  const DirIcon = prediction?.predicted_direction === 'UP' ? TrendingUp
    : prediction?.predicted_direction === 'DOWN' ? TrendingDown : Minus;
  const dirColor = prediction?.predicted_direction === 'UP' ? 'green'
    : prediction?.predicted_direction === 'DOWN' ? 'red' : 'slate';

  const points = history?.points || [];
  const isWatched = watchlist.includes(selected);

  const tradeSignal = useMemo(() => {
    if (!summary) return null;
    const score = scoreSignals(summary);
    let label = 'HOLD', color = 'slate';
    if (score >= 2) { label = 'BUY'; color = 'green'; }
    else if (score >= 1) { label = 'WEAK BUY'; color = 'green'; }
    else if (score <= -2) { label = 'SELL'; color = 'red'; }
    else if (score <= -1) { label = 'WEAK SELL'; color = 'red'; }
    return { label, color, score };
  }, [summary]);

  return (
    <div className="min-h-screen bg-slate-50 pt-20 px-4 md:px-6 pb-12">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Stock Analysis</h1>
            <p className="text-slate-500 text-sm mt-1">124 NEPSE stocks · LSTM forecasts · Technicals · Live data</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={toggleWatch}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium border transition-colors btn-press
                ${isWatched ? 'bg-amber-50 border-amber-200 text-amber-700'
                  : 'bg-white border-slate-200 text-slate-600 hover:border-amber-200'}`}>
              <Star size={15} className={isWatched ? 'fill-amber-500 text-amber-500' : ''} />
              {isWatched ? 'Watching' : 'Watch'}
            </button>
            {isAdmin && (
              <button onClick={trainModel} disabled={training}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-5 py-2 rounded-lg font-medium shadow-sm transition-colors btn-press text-sm">
                <Cpu size={15} className={training ? 'animate-spin' : ''} />
                {training ? 'Training…' : 'Train LSTM'}
              </button>
            )}
          </div>
        </div>

        {trainMsg && (
          <div className="mb-5 p-3 bg-blue-50 border border-blue-100 rounded-lg text-blue-700 text-sm flex items-center gap-2">
            <Activity size={15} /> {trainMsg}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Stock Sidebar */}
          <div className="lg:col-span-3 bg-white border border-slate-200 rounded-xl p-4 h-[calc(100vh-12rem)] flex flex-col sticky top-20 shadow-card">
            <div className="flex items-center gap-2 bg-slate-50 rounded-lg px-3 py-2 border border-slate-200 mb-3">
              <Search size={15} className="text-slate-400" />
              <input type="text" placeholder="Search stocks…" value={search} onChange={e => setSearch(e.target.value)}
                className="bg-transparent w-full text-sm text-slate-800 focus:outline-none placeholder-slate-400" />
            </div>
            <div className="flex gap-1.5 mb-3 flex-wrap">
              {['All', 'Banking', 'Hydropower', 'Insurance', 'Finance'].map(s => (
                <button key={s} onClick={() => setSectorFilter(s)}
                  className={`text-[10px] px-2 py-1 rounded-md font-semibold uppercase tracking-wider transition-colors
                    ${sectorFilter === s ? 'bg-blue-50 text-blue-600' : 'bg-slate-50 text-slate-500 hover:bg-slate-100'}`}>
                  {s}
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-y-auto space-y-0.5 pr-1" style={{ scrollbarWidth: 'thin' }}>
              {filtered.map(s => (
                <button key={s} onClick={() => { setSelected(s); navigate(`/stocks/${s}`); }}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center justify-between
                    ${s === selected ? 'bg-blue-50 text-blue-600 border border-blue-100' : 'text-slate-700 hover:bg-slate-50 border border-transparent'}`}>
                  <span>{s}</span>
                  {watchlist.includes(s) && <Star size={11} className="text-amber-500 fill-amber-500" />}
                </button>
              ))}
            </div>
          </div>

          {/* Main panel */}
          <div className="lg:col-span-9 space-y-5">
            {/* Price header */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h2 className="text-3xl font-bold text-slate-900">{selected}</h2>
                    <span className="text-xs text-slate-500 uppercase tracking-wider bg-slate-100 px-2 py-1 rounded font-medium">{summary?.sector || '—'}</span>
                  </div>
                  <div className="flex items-baseline gap-3 mt-2">
                    <div className="text-2xl font-mono font-bold text-slate-900">
                      NPR {summary?.latest_close ? summary.latest_close.toFixed(2) : '--'}
                    </div>
                    <div className={`text-sm font-mono font-semibold ${
                      (summary?.change || 0) >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {(summary?.change || 0) >= 0 ? '▲' : '▼'} {Math.abs(summary?.change || 0).toFixed(2)} ({Math.abs(summary?.change_pct || 0).toFixed(2)}%)
                    </div>
                  </div>
                </div>
                {tradeSignal && (
                  <div className={`px-4 py-2.5 rounded-lg ${
                    tradeSignal.color === 'green' ? 'bg-green-50 border border-green-200' :
                    tradeSignal.color === 'red' ? 'bg-red-50 border border-red-200' :
                    'bg-slate-50 border border-slate-200'
                  }`}>
                    <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-500">Signal</div>
                    <div className={`text-xl font-bold ${
                      tradeSignal.color === 'green' ? 'text-green-700' :
                      tradeSignal.color === 'red' ? 'text-red-700' : 'text-slate-700'
                    }`}>{tradeSignal.label}</div>
                  </div>
                )}
              </div>
              <div className="mt-4 grid grid-cols-2 md:grid-cols-6 gap-3">
                <Stat label="52W High" val={summary?.high_52w} />
                <Stat label="52W Low" val={summary?.low_52w} />
                <Stat label="SMA 30" val={summary?.sma_30} />
                <Stat label="SMA 200" val={summary?.sma_200} />
                <Stat label="RSI (14)" val={summary?.rsi_14} fmt={v => v?.toFixed(1)} />
                <Stat label="MACD" val={summary?.macd} fmt={v => v?.toFixed(3)} />
              </div>
            </div>

            {/* Chart */}
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <h3 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                  <Activity size={14} className="text-blue-600" /> Price Chart
                </h3>
                <div className="flex items-center gap-1 bg-slate-50 p-1 rounded-lg border border-slate-200">
                  {RANGES.map(r => (
                    <button key={r.label} onClick={() => setRange(r)}
                      className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors
                        ${range.label === r.label ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-700'}`}>
                      {r.label}
                    </button>
                  ))}
                </div>
              </div>
              {loading || !points.length ? (
                <div className="h-72 flex items-center justify-center text-slate-400 text-sm">
                  {loading ? 'Loading chart…' : 'No data available'}
                </div>
              ) : (
                <div className="h-72">
                  <ResponsiveContainer>
                    <ComposedChart data={points}>
                      <defs>
                        <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#2563eb" stopOpacity={0.12}/>
                          <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} minTickGap={40} />
                      <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} domain={['auto', 'auto']} />
                      <Tooltip contentStyle={{backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px'}} labelStyle={{color: '#64748b'}} />
                      <Legend wrapperStyle={{fontSize: 11}} />
                      <Area type="monotone" dataKey="close" name="Close" stroke="#2563eb" strokeWidth={2} fill="url(#colorClose)" />
                      <Line type="monotone" dataKey="sma20" name="SMA 20" stroke="#06b6d4" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                      <Line type="monotone" dataKey="sma50" name="SMA 50" stroke="#d97706" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* RSI + MACD */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">RSI (14)</h3>
                <div className="h-40">
                  <ResponsiveContainer>
                    <ComposedChart data={points}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis dataKey="date" hide />
                      <YAxis stroke="#94a3b8" fontSize={10} domain={[0, 100]} ticks={[0, 30, 50, 70, 100]} />
                      <Tooltip contentStyle={{backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px'}} />
                      <ReferenceLine y={70} stroke="#dc2626" strokeDasharray="3 3" />
                      <ReferenceLine y={30} stroke="#16a34a" strokeDasharray="3 3" />
                      <Line type="monotone" dataKey="rsi" stroke="#7c3aed" strokeWidth={2} dot={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">&gt;70 overbought · &lt;30 oversold</p>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">MACD</h3>
                <div className="h-40">
                  <ResponsiveContainer>
                    <ComposedChart data={points}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis dataKey="date" hide />
                      <YAxis stroke="#94a3b8" fontSize={10} />
                      <Tooltip contentStyle={{backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px'}} />
                      <ReferenceLine y={0} stroke="#94a3b8" />
                      <Bar dataKey="macd_hist" name="Hist" fill="#cbd5e1" />
                      <Line type="monotone" dataKey="macd" name="MACD" stroke="#2563eb" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="macd_signal" name="Signal" stroke="#d97706" strokeWidth={2} dot={false} />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">MACD above Signal → bullish · below → bearish</p>
              </div>
            </div>

            {/* LSTM + Snapshot */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="bg-white border border-slate-200 rounded-xl p-6 flex flex-col items-center justify-center shadow-card">
                <div className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold flex items-center gap-1.5">
                  <Cpu size={12} /> LSTM Prediction
                </div>
                {prediction ? (
                  <>
                    <DirIcon className={`mt-3 ${dirColor === 'green' ? 'text-green-600' : dirColor === 'red' ? 'text-red-600' : 'text-slate-400'}`} size={36} />
                    <div className={`text-3xl font-bold mt-1 ${dirColor === 'green' ? 'text-green-600' : dirColor === 'red' ? 'text-red-600' : 'text-slate-500'}`}>
                      {prediction.predicted_direction}
                    </div>
                    <div className="text-xs font-mono text-slate-500 mt-1">
                      {(prediction.confidence * 100).toFixed(1)}% confidence
                    </div>
                  </>
                ) : <div className="text-slate-400 text-sm mt-4">Loading…</div>}
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-6 md:col-span-2 shadow-card">
                <h3 className="text-sm font-semibold text-slate-700 mb-4">Snapshot</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                  <Row k="Symbol" v={selected} />
                  <Row k="Sector" v={summary?.sector || '—'} />
                  <Row k="Records" v={summary?.records || '—'} />
                  <Row k="52W Range" v={summary ? `${(summary.low_52w || 0).toFixed(0)} – ${(summary.high_52w || 0).toFixed(0)}` : '—'} />
                  <Row k="Avg Vol 30d" v={summary?.volume_avg_30 ? Math.round(summary.volume_avg_30).toLocaleString() : '—'} />
                  <Row k="Daily Change" v={summary ? `${summary.change >= 0 ? '+' : ''}${(summary.change || 0).toFixed(2)}` : '—'}
                    highlight={summary?.change >= 0 ? 'green' : 'red'} />
                </div>
              </div>
            </div>

            <PredictionValidation data={predHistory} />
          </div>
        </div>
      </div>
    </div>
  );
}

function PredictionValidation({ data }) {
  const items = data?.items || [];
  const s = data?.summary || {};
  const acc = s.accuracy == null ? null : Math.round(s.accuracy * 1000) / 10;

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
            <Activity size={14} className="text-blue-600" /> Prediction vs Actual
          </h3>
          <p className="text-[11px] text-slate-500 mt-0.5">Historical LSTM calls for this symbol, validated against realised price action.</p>
        </div>
        <div className="flex items-center gap-2">
          <AccPill label="Accuracy" value={acc == null ? '—' : `${acc.toFixed(1)}%`} tone={acc == null ? 'slate' : acc >= 60 ? 'green' : acc >= 45 ? 'amber' : 'red'} />
          <AccPill label="Correct" value={s.correct ?? 0} tone="green" />
          <AccPill label="Wrong" value={s.incorrect ?? 0} tone="red" />
          <AccPill label="Pending" value={s.pending ?? 0} tone="slate" />
        </div>
      </div>

      {items.length === 0 ? (
        <div className="text-sm text-slate-400 py-6 text-center">No predictions logged yet for this symbol.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] uppercase tracking-wider text-slate-500 border-b border-slate-100">
                <th className="text-left py-2 font-semibold">Date</th>
                <th className="text-left py-2 font-semibold">Predicted</th>
                <th className="text-left py-2 font-semibold">Conf.</th>
                <th className="text-left py-2 font-semibold">Actual Move</th>
                <th className="text-left py-2 font-semibold">Close</th>
                <th className="text-left py-2 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {items.map(it => (
                <tr key={it.id}
                  className={`border-b border-slate-50 ${it.validation_status === 'incorrect' ? 'bg-red-50/40' : ''}`}>
                  <td className="py-2.5 text-slate-600 text-xs font-mono">{it.predicted_date?.slice(0, 10) || '—'}</td>
                  <td className="py-2.5">
                    <DirTag dir={it.predicted_direction} />
                  </td>
                  <td className="py-2.5 text-slate-600 font-mono text-xs">{((it.confidence || 0) * 100).toFixed(0)}%</td>
                  <td className={`py-2.5 font-mono text-xs ${
                    it.error_margin_pct == null ? 'text-slate-400'
                      : it.error_margin_pct >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    {it.error_margin_pct == null ? '—' : `${it.error_margin_pct >= 0 ? '+' : ''}${it.error_margin_pct.toFixed(2)}%`}
                  </td>
                  <td className="py-2.5 text-slate-700 font-mono text-xs">
                    {it.actual_close == null ? '—' : `NPR ${it.actual_close.toFixed(2)}`}
                  </td>
                  <td className="py-2.5">
                    <StatusPill status={it.validation_status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AccPill({ label, value, tone }) {
  const cls = {
    green: 'bg-green-50 border-green-200 text-green-700',
    red: 'bg-red-50 border-red-200 text-red-700',
    amber: 'bg-amber-50 border-amber-200 text-amber-700',
    slate: 'bg-slate-50 border-slate-200 text-slate-600',
  }[tone] || 'bg-slate-50 border-slate-200 text-slate-600';
  return (
    <div className={`border rounded-lg px-3 py-1.5 ${cls}`}>
      <div className="text-[9px] uppercase tracking-wider font-semibold opacity-75">{label}</div>
      <div className="text-sm font-mono font-bold leading-tight">{value}</div>
    </div>
  );
}

function DirTag({ dir }) {
  const cfg = dir === 'UP' ? { cls: 'bg-green-50 text-green-700 border-green-200', Icon: TrendingUp }
    : dir === 'DOWN' ? { cls: 'bg-red-50 text-red-700 border-red-200', Icon: TrendingDown }
    : { cls: 'bg-slate-50 text-slate-600 border-slate-200', Icon: Minus };
  const { Icon, cls } = cfg;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[11px] font-semibold ${cls}`}>
      <Icon size={11} /> {dir || '—'}
    </span>
  );
}

function StatusPill({ status }) {
  if (status === 'correct') {
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-green-50 text-green-700 border border-green-200 text-[11px] font-semibold"><CheckCircle2 size={11} /> Correct</span>;
  }
  if (status === 'incorrect') {
    return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-red-50 text-red-700 border border-red-200 text-[11px] font-semibold"><XCircle size={11} /> Incorrect</span>;
  }
  return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-50 text-slate-500 border border-slate-200 text-[11px] font-semibold"><Clock size={11} /> Pending</span>;
}

function Stat({ label, val, fmt }) {
  const formatted = val == null ? '—' : (fmt ? fmt(val) : (typeof val === 'number' ? val.toFixed(2) : val));
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-2.5">
      <div className="text-[10px] uppercase text-slate-500 font-medium">{label}</div>
      <div className="text-sm font-mono font-semibold mt-0.5 text-slate-800">{formatted}</div>
    </div>
  );
}

function Row({ k, v, highlight }) {
  return (
    <div className="flex items-center justify-between bg-slate-50 border border-slate-100 rounded-lg px-3 py-2">
      <span className="text-[11px] uppercase text-slate-500">{k}</span>
      <span className={`font-mono font-semibold text-sm ${highlight === 'green' ? 'text-green-600' : highlight === 'red' ? 'text-red-600' : 'text-slate-800'}`}>{v}</span>
    </div>
  );
}

function scoreSignals(s) {
  if (!s) return 0;
  let score = 0;
  if (s.latest_close != null && s.sma_30 != null) score += s.latest_close > s.sma_30 ? 1 : -1;
  if (s.latest_close != null && s.sma_200 != null) score += s.latest_close > s.sma_200 ? 1 : -1;
  if (s.rsi_14 != null) { if (s.rsi_14 < 30) score += 1; else if (s.rsi_14 > 70) score -= 1; }
  if (s.macd != null && s.macd_signal != null) score += s.macd > s.macd_signal ? 1 : -1;
  return score;
}
