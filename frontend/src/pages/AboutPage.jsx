import React from 'react';
import { Brain, Database, Globe, BarChart3, Code2, Shield, Cpu, Newspaper, Activity, Zap } from 'lucide-react';

const PIPELINE = [
  { icon: <Brain size={20} />, name: "PyTorch LSTM", role: "Forecasting Engine", desc: "30-day lookback, 3-feature window (close/volume/sentiment) → 3-class direction." },
  { icon: <Database size={20} />, name: "GitHub Dataset", role: "Data Pipeline", desc: "Auto-updated Aabishkar2/nepse-data OHLCV for 124+ companies." },
  { icon: <Globe size={20} />, name: "Multilingual NLP", role: "Sentiment", desc: "mBERT + VADER for both Nepali and English financial news." },
  { icon: <Code2 size={20} />, name: "FastAPI", role: "API Layer", desc: "High-performance async Python with JWT auth and admin controls." },
  { icon: <BarChart3 size={20} />, name: "Technical Indicators", role: "Analytics", desc: "SMA, EMA, RSI, MACD, Bollinger Bands computed server-side." },
  { icon: <Newspaper size={20} />, name: "RSS Scraper", role: "News Feed", desc: "10+ live sources ingested, cleaned, and classified in real time." },
];

const TECH = [
  { name: "PyTorch", desc: "LSTM Neural Network" },
  { name: "FastAPI", desc: "Backend Framework" },
  { name: "React 19", desc: "Frontend UI" },
  { name: "PostgreSQL", desc: "Database" },
  { name: "TailwindCSS", desc: "Styling" },
  { name: "Docker", desc: "Containerization" },
  { name: "Recharts", desc: "Visualizations" },
  { name: "HuggingFace", desc: "NLP Models" },
];

const STATS = [
  { value: "124+", label: "NEPSE Stocks", icon: <BarChart3 size={16} /> },
  { value: "27+", label: "News Sources", icon: <Newspaper size={16} /> },
  { value: "5", label: "Technical Indicators", icon: <Activity size={16} /> },
  { value: "24/7", label: "AI Available", icon: <Zap size={16} /> },
];

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-slate-50 pt-20 px-4 md:px-6 pb-12">
      <div className="max-w-5xl mx-auto">
        {/* Hero */}
        <div className="text-center mb-12 pt-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-3 text-slate-900">About BhaavShare</h1>
          <p className="text-slate-500 text-base max-w-2xl mx-auto leading-relaxed">
            Nepal's most advanced AI-powered stock market analysis platform, built with deep learning,
            multilingual NLP, and real-time data pipelines.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
          {STATS.map((s, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 text-center shadow-card">
              <div className="w-10 h-10 mx-auto rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3">{s.icon}</div>
              <div className="text-2xl font-bold text-blue-600">{s.value}</div>
              <div className="text-slate-500 text-xs mt-1 font-medium">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Mission */}
        <div className="bg-white border border-slate-200 rounded-xl p-8 md:p-10 mb-10 shadow-card">
          <h2 className="text-xl font-bold mb-3 text-slate-900">Our Mission</h2>
          <p className="text-slate-600 leading-relaxed text-sm">
            BhaavShare was built to democratize stock market intelligence for every Nepali investor.
            We believe that advanced AI tools — deep learning predictions, real-time sentiment analysis,
            and intelligent market advisors — shouldn't be locked behind expensive subscriptions. Our
            platform makes world-class financial analytics accessible and free.
          </p>
        </div>

        {/* Architecture */}
        <h2 className="text-xl font-bold mb-5 text-slate-900">System Architecture</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10">
          {PIPELINE.map((t, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-xl p-5 flex items-start gap-4 hover:border-blue-200 transition card-hover">
              <div className="w-11 h-11 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">{t.icon}</div>
              <div>
                <h3 className="text-slate-900 font-semibold">{t.name}</h3>
                <p className="text-blue-600 text-[10px] font-semibold uppercase tracking-wider mb-1">{t.role}</p>
                <p className="text-slate-500 text-sm">{t.desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Tech Stack */}
        <h2 className="text-xl font-bold mb-5 text-slate-900">Tech Stack</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
          {TECH.map((t, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-lg p-4 text-center hover:border-blue-200 transition group card-hover">
              <div className="text-slate-800 font-semibold text-sm group-hover:text-blue-600 transition-colors">{t.name}</div>
              <div className="text-slate-400 text-xs mt-1">{t.desc}</div>
            </div>
          ))}
        </div>

        {/* Data Sources */}
        <div className="bg-white border border-slate-200 rounded-xl p-8 md:p-10 mb-8 shadow-card">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-3 text-slate-900"><Database className="text-blue-600" size={22} /> Data Sources</h2>
          <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
            <p><span className="text-slate-900 font-medium">Historical Prices:</span> Sourced from <a href="https://github.com/Aabishkar2/nepse-data" target="_blank" rel="noreferrer" className="text-blue-600 underline">Aabishkar2/nepse-data</a> — 124 companies with auto-updated OHLCV data.</p>
            <p><span className="text-slate-900 font-medium">News Feeds:</span> 27+ live RSS sources including ArthaSarokar, KhabarHub, ShareSansar, and Kathmandu Post.</p>
            <p><span className="text-slate-900 font-medium">Sentiment:</span> Multilingual NLP pipeline using mBERT + VADER for Nepali and English classification.</p>
            <p><span className="text-slate-900 font-medium">Predictions:</span> PyTorch LSTM with 30-day lookback windows, class-balanced loss, chronological split.</p>
          </div>
        </div>

        {/* Disclaimer */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-5 flex gap-3">
          <Shield className="text-amber-600 shrink-0 mt-0.5" size={18} />
          <div className="text-xs text-slate-600 leading-relaxed">
            <span className="text-amber-700 font-semibold">Disclaimer:</span> BhaavShare provides AI-generated analysis for educational purposes only. Nothing constitutes financial advice. All trading decisions are your sole responsibility.
          </div>
        </div>
      </div>
    </div>
  );
}
