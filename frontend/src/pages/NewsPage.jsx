import React, { useState, useEffect, useMemo } from 'react';
import {
  Newspaper, ExternalLink, RefreshCw, Search, Languages, Filter,
  Radio, MessageCircle, Tag, Globe2,
} from 'lucide-react';
import api from '../utils/api';
import { useAuth } from '../context/AuthContext';

const SENTIMENTS = [
  { key: 'all', label: 'All' },
  { key: 'positive', label: 'Positive' },
  { key: 'neutral', label: 'Neutral' },
  { key: 'negative', label: 'Negative' },
];

const CATEGORIES = ['all', 'Market', 'Banking', 'IPO', 'Dividend', 'Hydropower', 'Insurance', 'Economy', 'General'];
const SOURCE_TYPES = [
  { key: 'all', label: 'All Media', icon: <Globe2 size={12} /> },
  { key: 'rss', label: 'News', icon: <Newspaper size={12} /> },
  { key: 'reddit', label: 'Social', icon: <MessageCircle size={12} /> },
];

function sentimentBadge(label) {
  if (label === 'positive') return 'bg-green-50 text-green-700 border-green-200';
  if (label === 'negative') return 'bg-red-50 text-red-700 border-red-200';
  return 'bg-slate-100 text-slate-600 border-slate-200';
}

export default function NewsPage() {
  const { isAdmin } = useAuth();
  const [news, setNews] = useState([]);
  const [sources, setSources] = useState({ rss: [], reddit: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [sentiment, setSentiment] = useState('all');
  const [language, setLanguage] = useState('all');
  const [category, setCategory] = useState('all');
  const [sourceType, setSourceType] = useState('all');
  const [search, setSearch] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [toast, setToast] = useState(null);

  const fetchNews = async () => {
    setLoading(true);
    try {
      const r = await api.get('/news?limit=200');
      setNews(r.data || []);
    } finally { setLoading(false); }
  };

  const fetchSources = async () => {
    try {
      const r = await api.get('/news/sources');
      setSources(r.data || {});
    } catch { /* ignore */ }
  };

  const triggerScrape = async () => {
    setRefreshing(true);
    setToast(null);
    try {
      await api.post('/scrape/run');
      setToast({ type: 'ok', text: 'Scraping started — new articles will arrive in ~30s.' });
      setTimeout(fetchNews, 3500);
    } catch (e) {
      const code = e?.response?.status;
      if (code === 401 || code === 403) setToast({ type: 'err', text: 'Only administrators can trigger a scrape.' });
      else setToast({ type: 'err', text: 'Scrape failed. Try again.' });
    } finally {
      setTimeout(() => setRefreshing(false), 3600);
      setTimeout(() => setToast(null), 5000);
    }
  };

  useEffect(() => { fetchNews(); fetchSources(); }, []);

  const filtered = useMemo(() => {
    return news.filter(n => {
      if (sentiment !== 'all' && n.sentiment_label !== sentiment) return false;
      if (language !== 'all' && n.language !== language) return false;
      if (category !== 'all' && (n.category || 'General') !== category) return false;
      if (sourceType !== 'all' && n.source_type !== sourceType) return false;
      if (search) {
        const q = search.toLowerCase();
        if (!(n.title || '').toLowerCase().includes(q) && !(n.summary || '').toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [news, sentiment, language, category, sourceType, search]);

  const counts = useMemo(() => {
    const c = { positive: 0, neutral: 0, negative: 0, rss: 0, reddit: 0 };
    news.forEach(n => {
      if (n.sentiment_label === 'positive') c.positive++;
      else if (n.sentiment_label === 'negative') c.negative++;
      else c.neutral++;
      if (n.source_type === 'reddit') c.reddit++;
      else c.rss++;
    });
    return c;
  }, [news]);

  return (
    <div className="min-h-screen bg-slate-50 pt-20 px-4 md:px-6 pb-12">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
              <Newspaper className="text-blue-600" size={24} /> Live Market News
            </h1>
            <p className="text-slate-500 text-sm mt-1">
              Aggregated from <span className="text-blue-600 font-medium">{sources.total || 17}+ sources</span> — NLP sentiment analysis
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={fetchNews} disabled={loading}
              className="flex items-center gap-2 bg-white hover:bg-slate-50 border border-slate-200 text-slate-600 px-4 py-2 rounded-lg text-sm font-medium transition-colors">
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Reload
            </button>
            {isAdmin && (
              <button onClick={triggerScrape} disabled={refreshing}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm">
                <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} /> Re-scrape
              </button>
            )}
          </div>
        </div>

        {toast && (
          <div className={`mb-4 rounded-lg border p-3 text-sm flex items-center gap-2
            ${toast.type === 'ok' ? 'bg-green-50 border-green-200 text-green-700' : 'bg-red-50 border-red-200 text-red-700'}`}>
            {toast.text}
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
          <StatCard label="Total" val={news.length} color="blue" icon={<Newspaper size={14} />} />
          <StatCard label="Positive" val={counts.positive} color="green" icon={<Filter size={14} />} />
          <StatCard label="Neutral" val={counts.neutral} color="slate" icon={<Filter size={14} />} />
          <StatCard label="Negative" val={counts.negative} color="red" icon={<Filter size={14} />} />
          <StatCard label="Social" val={counts.reddit} color="blue" icon={<MessageCircle size={14} />} />
        </div>

        {/* Filters */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 mb-5 space-y-3 shadow-card">
          <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center flex-wrap">
            <div className="flex items-center gap-2 bg-slate-50 rounded-lg px-3 py-2 border border-slate-200 flex-1 min-w-[220px]">
              <Search size={14} className="text-slate-400" />
              <input type="text" placeholder="Search headlines…" value={search} onChange={e => setSearch(e.target.value)}
                className="bg-transparent w-full text-sm text-slate-800 focus:outline-none placeholder-slate-400" />
            </div>
            <div className="flex items-center gap-1 bg-slate-50 p-1 rounded-lg border border-slate-200">
              {SENTIMENTS.map(s => (
                <button key={s.key} onClick={() => setSentiment(s.key)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors
                    ${sentiment === s.key ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-700'}`}>
                  {s.label}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-1 bg-slate-50 p-1 rounded-lg border border-slate-200">
              <Languages size={12} className="text-slate-400 ml-2" />
              {['all', 'en', 'ne'].map(l => (
                <button key={l} onClick={() => setLanguage(l)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors uppercase
                    ${language === l ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-700'}`}>
                  {l === 'all' ? 'All' : l.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-semibold uppercase tracking-wider mr-1"><Radio size={11} /> Media:</div>
            {SOURCE_TYPES.map(st => (
              <button key={st.key} onClick={() => setSourceType(st.key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-semibold rounded-full transition-colors border
                  ${sourceType === st.key ? 'bg-blue-50 text-blue-600 border-blue-200' : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'}`}>
                {st.icon} {st.label}
              </button>
            ))}
            <div className="flex items-center gap-1.5 text-[11px] text-slate-500 font-semibold uppercase tracking-wider ml-3 mr-1"><Tag size={11} /> Category:</div>
            {CATEGORIES.map(c => (
              <button key={c} onClick={() => setCategory(c)}
                className={`px-3 py-1.5 text-[11px] font-semibold rounded-full transition-colors border
                  ${category === c ? 'bg-blue-50 text-blue-600 border-blue-200' : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'}`}>
                {c === 'all' ? 'All' : c}
              </button>
            ))}
          </div>
        </div>

        {/* News grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="bg-white border border-slate-200 rounded-xl p-6 animate-pulse">
                <div className="h-4 bg-slate-100 rounded w-3/4 mb-3"></div>
                <div className="h-3 bg-slate-100 rounded w-full mb-2"></div>
                <div className="h-3 bg-slate-100 rounded w-1/2"></div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filtered.map((item, idx) => (
              <article key={idx} className="group bg-white border border-slate-200 rounded-xl p-5 hover:border-blue-200 transition-all card-hover">
                <div className="flex items-start justify-between gap-3 mb-2">
                  <h3 className="text-sm font-medium leading-snug text-slate-800 group-hover:text-slate-900 line-clamp-2 flex-1">
                    {item.title}
                  </h3>
                  {item.url && item.url.startsWith('http') && (
                    <a href={item.url} target="_blank" rel="noreferrer" className="text-slate-400 hover:text-blue-600 transition shrink-0 mt-0.5">
                      <ExternalLink size={14} />
                    </a>
                  )}
                </div>
                {item.category && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-600 border border-blue-100 text-[9px] rounded-full font-semibold uppercase tracking-wider mb-2">
                    <Tag size={8} /> {item.category}
                  </span>
                )}
                {item.summary && (
                  <p className="text-slate-500 text-xs leading-relaxed mb-3 line-clamp-3">{item.summary}</p>
                )}
                <div className="flex items-center justify-between">
                  <span className={`px-2 py-0.5 text-[10px] rounded-full font-semibold border ${sentimentBadge(item.sentiment_label)}`}>
                    {item.sentiment_label || 'processing'}
                  </span>
                  <div className="flex items-center gap-2">
                    {item.source_type === 'reddit' ? (
                      <span className="flex items-center gap-1 text-[10px] text-orange-600 font-mono"><MessageCircle size={10} /> {item.source}</span>
                    ) : (
                      <span className="text-[10px] text-slate-400 font-mono">{item.source}</span>
                    )}
                    <span className="text-[10px] text-slate-400">{item.language === 'ne' ? 'NE' : 'EN'}</span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
        {!loading && filtered.length === 0 && (
          <div className="text-center py-16 text-slate-400">No articles match your filters.</div>
        )}

        {/* Sources footer */}
        {sources.total > 0 && (
          <div className="mt-8 bg-white border border-slate-200 rounded-xl p-5 shadow-card">
            <h3 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
              <Globe2 size={14} className="text-blue-600" /> Data Sources ({sources.total})
            </h3>
            <div className="flex flex-wrap gap-2">
              {(sources.rss || []).map(s => (
                <span key={s.name} className="text-[10px] px-2 py-1 bg-slate-50 border border-slate-200 rounded-full text-slate-500">
                  {s.name} <span className="text-slate-300">·{s.language === 'ne' ? 'NE' : 'EN'}</span>
                </span>
              ))}
              {(sources.reddit || []).map(s => (
                <span key={s.name} className="text-[10px] px-2 py-1 bg-orange-50 border border-orange-200 rounded-full text-orange-600 flex items-center gap-1">
                  <MessageCircle size={9} /> {s.name}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, val, color, icon }) {
  const colors = {
    blue: 'border-blue-200 text-blue-600',
    green: 'border-green-200 text-green-600',
    red: 'border-red-200 text-red-600',
    slate: 'border-slate-200 text-slate-600',
  };
  return (
    <div className={`bg-white border ${colors[color]} rounded-xl p-4 text-center shadow-card`}>
      <div className="flex items-center justify-center gap-1 text-[10px] uppercase text-slate-500 tracking-wider font-medium mb-1">
        {icon} {label}
      </div>
      <div className={`text-2xl font-bold ${colors[color]}`}>{val}</div>
    </div>
  );
}
