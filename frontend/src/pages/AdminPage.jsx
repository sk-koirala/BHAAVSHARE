import React, { useEffect, useState } from 'react';
import {
  Shield, Users, Newspaper, MessageSquare, Cpu, RefreshCw, Trash2, Star,
  CheckCircle, XCircle, Activity, TrendingUp, AlertTriangle, BarChart3,
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, LineChart, Line,
} from 'recharts';
import api, { ALL_STOCKS } from '../utils/api';
import { useAuth } from '../context/AuthContext';

const TABS = [
  { key: 'overview', label: 'Overview', icon: <Activity size={14} /> },
  { key: 'analytics', label: 'Analytics', icon: <BarChart3 size={14} /> },
  { key: 'users', label: 'Users', icon: <Users size={14} /> },
  { key: 'news', label: 'News', icon: <Newspaper size={14} /> },
  { key: 'contacts', label: 'Contacts', icon: <MessageSquare size={14} /> },
  { key: 'ops', label: 'Operations', icon: <Cpu size={14} /> },
];

const PIE_COLORS = ['#16a34a', '#94a3b8', '#dc2626'];

export default function AdminPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [news, setNews] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [trainSym, setTrainSym] = useState('NABIL');
  const [trainLog, setTrainLog] = useState(null);
  const [training, setTraining] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState(null);

  const refresh = async () => {
    setLoading(true);
    try {
      const [s, u, n, c] = await Promise.allSettled([
        api.get('/admin/stats'),
        api.get('/admin/users'),
        api.get('/news?limit=100'),
        api.get('/admin/contacts'),
      ]);
      if (s.status === 'fulfilled') setStats(s.value.data);
      if (u.status === 'fulfilled') setUsers(u.value.data || []);
      if (n.status === 'fulfilled') setNews(n.value.data || []);
      if (c.status === 'fulfilled') setContacts(c.value.data || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []);

  const toggleActive = async (id) => { await api.post(`/admin/users/${id}/toggle-active`).catch(() => {}); refresh(); };
  const toggleAdmin = async (id) => { await api.post(`/admin/users/${id}/toggle-admin`).catch(() => {}); refresh(); };
  const deleteUser = async (id) => { if (!confirm('Delete user?')) return; await api.delete(`/admin/users/${id}`).catch(() => {}); refresh(); };
  const deleteNews = async (id) => { await api.delete(`/admin/news/${id}`).catch(() => {}); refresh(); };
  const markContactRead = async (id) => { await api.post(`/admin/contacts/${id}/read`).catch(() => {}); refresh(); };

  const runScrape = async () => {
    setScrapeMsg('Starting…');
    try { await api.post('/scrape/run'); setScrapeMsg('✓ Scraper pipeline started.'); setTimeout(refresh, 5000); }
    catch { setScrapeMsg('✗ Scrape failed.'); }
  };

  const runTrain = async () => {
    setTraining(true);
    setTrainLog(`Training ${trainSym}…`);
    try {
      const r = await api.post(`/predict/train/${trainSym}?epochs=20`);
      setTrainLog(`✓ ${trainSym}: ${r.data.epochs} epochs · Loss ${r.data.loss?.toFixed(4) ?? r.data.final_loss?.toFixed(4)}`);
    } catch { setTrainLog(`✗ Training failed.`); }
    finally { setTraining(false); }
  };

  // Analytics data
  const sentimentPie = stats ? [
    { name: 'Positive', value: stats.news_positive || 0 },
    { name: 'Neutral', value: (stats.news_total || 0) - (stats.news_positive || 0) - (stats.news_negative || 0) },
    { name: 'Negative', value: stats.news_negative || 0 },
  ] : [];

  const userGrowth = users.slice().sort((a, b) => new Date(a.created_at) - new Date(b.created_at)).reduce((acc, u, i) => {
    const date = new Date(u.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    acc.push({ date, total: i + 1 });
    return acc;
  }, []).slice(-14);

  return (
    <div className="min-h-screen bg-slate-50 pt-20 px-4 md:px-6 pb-12">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-2 text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-full text-[10px] font-semibold uppercase tracking-wider mb-2">
              <Shield size={11} /> Admin Console
            </div>
            <h1 className="text-2xl font-bold text-slate-900">Welcome, {user?.full_name || user?.email}</h1>
            <p className="text-slate-500 text-sm mt-0.5">Manage users, content, and ML pipelines.</p>
          </div>
          <button onClick={refresh} disabled={loading}
            className="flex items-center gap-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 bg-white border border-slate-200 p-1 rounded-lg mb-5 overflow-x-auto shadow-card">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors whitespace-nowrap
                ${tab === t.key ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'}`}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Overview */}
        {tab === 'overview' && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Users" value={stats?.users_total ?? '—'} icon={<Users size={18} />} color="blue" />
              <StatCard label="AI Accuracy" value={stats?.predictions ? `${(stats.predictions.accuracy * 100).toFixed(1)}%` : '—'} 
                icon={<Activity size={18} />} color="blue" badge={stats?.predictions?.validated > 0 ? `${stats.predictions.validated} checked` : null} />
              <StatCard label="Live News" value={stats?.news_total ?? '—'} icon={<Newspaper size={18} />} color="green" />
              <StatCard label="Contacts" value={stats?.contact_messages ?? '—'} icon={<MessageSquare size={18} />} color="amber" badge={stats?.contact_unread ? `${stats.contact_unread} new` : null} />
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card">
              <h3 className="font-semibold text-slate-900 mb-3">System Health</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                <SysRow k="API" v="Online" ok />
                <SysRow k="Stocks Tracked" v={`${stats?.stocks_tracked ?? 0} / 124`} ok />
                <SysRow k="News Pipeline" v="RSS + NLP multilingual" ok />
                <SysRow k="LSTM Models" v="PyTorch on-demand" ok />
              </div>
            </div>
          </div>
        )}

        {/* Analytics */}
        {tab === 'analytics' && (
          <div className="space-y-5">
            {/* Model Accuracy + Prediction outcomes */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card flex flex-col items-center justify-center text-center">
                <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-4">
                  <Cpu size={24} />
                </div>
                <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Model Accuracy</h4>
                <div className="text-4xl font-black text-slate-900">{stats?.predictions ? `${(stats.predictions.accuracy * 100).toFixed(1)}%` : '—'}</div>
                <p className="text-[11px] text-slate-400 mt-2">Across {stats?.predictions?.validated || 0} validated predictions</p>
                <button onClick={async () => { await api.post('/admin/predictions/validate-now'); refresh(); }}
                  className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-[10px] font-bold rounded-lg transition-colors">
                  Force Verification
                </button>
              </div>
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card md:col-span-2">
                <h3 className="text-sm font-semibold text-slate-800 mb-4">Prediction Success vs Failure</h3>
                <div className="h-48">
                  <ResponsiveContainer>
                    <BarChart data={[
                      { name: 'Correct', count: stats?.predictions?.correct || 0, fill: '#16a34a' },
                      { name: 'Incorrect', count: (stats?.predictions?.validated || 0) - (stats?.predictions?.correct || 0), fill: '#dc2626' },
                      { name: 'Pending', count: (stats?.predictions?.total || 0) - (stats?.predictions?.validated || 0), fill: '#94a3b8' },
                    ]}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                      <XAxis dataKey="name" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis fontSize={11} tickLine={false} axisLine={false} />
                      <Tooltip cursor={{fill: '#f8fafc'}} />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={40} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {/* Sentiment Distribution */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card">
                <h3 className="text-sm font-semibold text-slate-800 mb-4">News Sentiment Distribution</h3>
                <div className="h-56">
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie data={sentimentPie} innerRadius={60} outerRadius={85} paddingAngle={3} dataKey="value" stroke="none">
                        {sentimentPie.map((_, idx) => <Cell key={idx} fill={PIE_COLORS[idx]} />)}
                      </Pie>
                      <Tooltip contentStyle={{backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px'}} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="grid grid-cols-3 gap-3 mt-2">
                  {[{ label: 'Positive', val: stats?.news_positive, cls: 'text-green-600' }, { label: 'Neutral', val: (stats?.news_total || 0) - (stats?.news_positive || 0) - (stats?.news_negative || 0), cls: 'text-slate-600' }, { label: 'Negative', val: stats?.news_negative, cls: 'text-red-600' }].map(s => (
                    <div key={s.label} className="bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-center">
                      <div className={`text-lg font-bold ${s.cls}`}>{s.val ?? 0}</div>
                      <div className="text-[10px] text-slate-500 uppercase font-medium">{s.label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* User Growth */}
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card">
                <h3 className="text-sm font-semibold text-slate-800 mb-4">User Growth</h3>
                <div className="h-56">
                  <ResponsiveContainer>
                    <LineChart data={userGrowth}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                      <XAxis dataKey="date" stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
                      <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{backgroundColor: '#fff', borderColor: '#e2e8f0', borderRadius: '8px', fontSize: '12px'}} />
                      <Line type="monotone" dataKey="total" stroke="#2563eb" strokeWidth={2} dot={{ fill: '#2563eb', r: 3 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">Cumulative user registrations over last 14 data points</p>
              </div>
            </div>

            {/* User Role Distribution */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-card">
              <h3 className="text-sm font-semibold text-slate-800 mb-4">Platform Overview</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MiniAnalytic label="Standard Users" value={users.filter(u => !u.is_admin).length} total={users.length} color="blue" />
                <MiniAnalytic label="Admin Users" value={users.filter(u => u.is_admin).length} total={users.length} color="amber" />
                <MiniAnalytic label="Active Users" value={users.filter(u => u.is_active).length} total={users.length} color="green" />
                <MiniAnalytic label="Disabled" value={users.filter(u => !u.is_active).length} total={users.length} color="red" />
              </div>
            </div>
          </div>
        )}
        
        {/* Users */}
        {tab === 'users' && (
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-card">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr className="text-xs uppercase tracking-wider text-slate-500">
                  <th className="text-left px-4 py-3 font-semibold">User</th>
                  <th className="text-left px-4 py-3 font-semibold">Email</th>
                  <th className="text-left px-4 py-3 font-semibold">Created</th>
                  <th className="text-left px-4 py-3 font-semibold">Status</th>
                  <th className="text-right px-4 py-3 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-800">{u.full_name || '—'}</td>
                    <td className="px-4 py-3 text-slate-500">{u.email}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs">{new Date(u.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        {u.is_active
                          ? <span className="px-2 py-0.5 text-[10px] rounded-full bg-green-50 text-green-700 border border-green-200 font-semibold">Active</span>
                          : <span className="px-2 py-0.5 text-[10px] rounded-full bg-red-50 text-red-700 border border-red-200 font-semibold">Disabled</span>}
                        {u.is_admin && <span className="px-2 py-0.5 text-[10px] rounded-full bg-amber-50 text-amber-700 border border-amber-200 font-semibold">Admin</span>}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex gap-1">
                        <button onClick={() => toggleActive(u.id)} title="Toggle active"
                          className="p-1.5 rounded-md bg-slate-50 hover:bg-slate-100 text-slate-500 border border-slate-200 transition-colors">
                          {u.is_active ? <XCircle size={13} /> : <CheckCircle size={13} />}
                        </button>
                        <button onClick={() => toggleAdmin(u.id)} title="Toggle admin"
                          className="p-1.5 rounded-md bg-amber-50 hover:bg-amber-100 text-amber-600 border border-amber-200 transition-colors">
                          <Shield size={13} />
                        </button>
                        <button onClick={() => deleteUser(u.id)} title="Delete"
                          className="p-1.5 rounded-md bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 transition-colors">
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && <tr><td colSpan={5} className="px-4 py-10 text-center text-slate-400">No users yet.</td></tr>}
              </tbody>
            </table>
          </div>
        )}

        {/* News */}
        {tab === 'news' && (
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-card">
            <div className="space-y-1.5 max-h-[70vh] overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
              {news.map((n, i) => (
                <div key={n.id || i} className="flex items-start gap-3 p-3 bg-slate-50 border border-slate-100 rounded-lg hover:border-slate-200 transition">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full font-semibold border
                        ${n.sentiment_label === 'positive' ? 'bg-green-50 text-green-700 border-green-200'
                          : n.sentiment_label === 'negative' ? 'bg-red-50 text-red-700 border-red-200'
                          : 'bg-slate-100 text-slate-600 border-slate-200'}`}>
                        {n.sentiment_label || 'neutral'}
                      </span>
                      <span className="text-[10px] text-slate-400 font-mono">{n.source}</span>
                      <span className="text-[10px] text-slate-400">{n.language === 'ne' ? 'NE' : 'EN'}</span>
                    </div>
                    <div className="text-sm font-medium text-slate-800 line-clamp-1">{n.title}</div>
                    {n.summary && <div className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">{n.summary}</div>}
                  </div>
                  {n.id && (
                    <button onClick={() => deleteNews(n.id)} className="p-1.5 text-slate-400 hover:text-red-500 transition shrink-0">
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              ))}
              {news.length === 0 && <div className="text-center text-slate-400 py-10 text-sm">No articles.</div>}
            </div>
          </div>
        )}

        {/* Contacts */}
        {tab === 'contacts' && (
          <div className="space-y-3">
            {contacts.length === 0 && <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-slate-400 shadow-card">No messages yet.</div>}
            {contacts.map(c => (
              <div key={c.id} className={`bg-white border rounded-xl p-5 shadow-card transition
                ${c.is_read ? 'border-slate-200' : 'border-blue-200 bg-blue-50/30'}`}>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-800">{c.name}</span>
                      <span className="text-xs text-slate-500">&lt;{c.email}&gt;</span>
                      {!c.is_read && <span className="text-[10px] bg-blue-100 text-blue-600 px-2 py-0.5 rounded-full font-semibold">NEW</span>}
                    </div>
                    <div className="text-xs text-slate-400 mt-0.5">{new Date(c.created_at).toLocaleString()}</div>
                  </div>
                  {!c.is_read && (
                    <button onClick={() => markContactRead(c.id)}
                      className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 px-3 py-1.5 rounded-lg font-medium transition-colors">
                      Mark Read
                    </button>
                  )}
                </div>
                {c.subject && <div className="text-sm font-medium text-slate-700 mb-1">Re: {c.subject}</div>}
                <div className="text-sm text-slate-600 whitespace-pre-wrap">{c.message}</div>
              </div>
            ))}
          </div>
        )}

        {/* Operations */}
        {tab === 'ops' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
              <h3 className="font-semibold text-slate-900 mb-1 flex items-center gap-2"><Newspaper size={16} className="text-blue-600" /> News Pipeline</h3>
              <p className="text-xs text-slate-500 mb-4">Re-run the RSS scraper + NLP sentiment pipeline.</p>
              <button onClick={runScrape}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-lg font-semibold transition-colors shadow-sm btn-press">
                <RefreshCw size={15} /> Trigger Scrape
              </button>
              {scrapeMsg && <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-600">{scrapeMsg}</div>}
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
              <h3 className="font-semibold text-slate-900 mb-1 flex items-center gap-2"><Cpu size={16} className="text-blue-600" /> LSTM Training</h3>
              <p className="text-xs text-slate-500 mb-4">Train PyTorch model on any stock's latest data.</p>
              <div className="flex gap-2 mb-3">
                <select value={trainSym} onChange={e => setTrainSym(e.target.value)}
                  className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-sm text-slate-800 focus:outline-none focus:border-blue-400">
                  {ALL_STOCKS.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
                <button onClick={runTrain} disabled={training}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2.5 rounded-lg font-semibold transition-colors shadow-sm btn-press">
                  <Cpu size={14} className={training ? 'animate-spin' : ''} /> {training ? 'Training…' : 'Train'}
                </button>
              </div>
              {trainLog && <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-600">{trainLog}</div>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, color, badge }) {
  const cm = { blue: 'bg-blue-50 text-blue-600 border-blue-200', green: 'bg-green-50 text-green-600 border-green-200', amber: 'bg-amber-50 text-amber-600 border-amber-200', red: 'bg-red-50 text-red-600 border-red-200' };
  const ic = { blue: 'bg-blue-100 text-blue-600', green: 'bg-green-100 text-green-600', amber: 'bg-amber-100 text-amber-600', red: 'bg-red-100 text-red-600' };
  return (
    <div className={`bg-white border border-slate-200 rounded-xl p-4 shadow-card relative`}>
      <div className={`w-9 h-9 rounded-lg ${ic[color]} flex items-center justify-center mb-2`}>{icon}</div>
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500 font-medium mt-0.5">{label}</div>
      {badge && <div className="absolute top-3 right-3 text-[9px] bg-blue-50 text-blue-600 border border-blue-200 px-1.5 py-0.5 rounded-full font-semibold">{badge}</div>}
    </div>
  );
}

function SysRow({ k, v, ok }) {
  return (
    <div className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5">
      <span className="text-xs text-slate-500 uppercase">{k}</span>
      <span className={`text-sm font-semibold ${ok ? 'text-green-600' : 'text-slate-500'}`}>{v}</span>
    </div>
  );
}

function MiniAnalytic({ label, value, total, color }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  const cm = { blue: 'bg-blue-600', green: 'bg-green-600', amber: 'bg-amber-500', red: 'bg-red-500' };
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
      <div className="text-xs text-slate-500 font-medium uppercase mb-2">{label}</div>
      <div className="text-2xl font-bold text-slate-800">{value}</div>
      <div className="h-1.5 bg-slate-200 rounded-full mt-2 overflow-hidden">
        <div className={`h-full ${cm[color]} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <div className="text-[10px] text-slate-400 mt-1">{pct}% of {total}</div>
    </div>
  );
}
