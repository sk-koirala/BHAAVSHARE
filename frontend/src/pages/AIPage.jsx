import React, { useState, useEffect, useRef } from 'react';
import { Bot, Send, Plus, Trash2, MessageSquare, Menu, X, Loader2 } from 'lucide-react';
import api from '../utils/api';
import { useAuth } from '../context/AuthContext';

export default function AIPage() {
  const { user } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const chatEnd = useRef(null);

  // Load sessions
  useEffect(() => {
    if (!user) return;
    api.get('/chat/sessions').then(r => {
      setSessions(r.data || []);
      if (r.data?.length > 0 && !activeSession) loadSession(r.data[0].id);
    }).catch(() => {});
  }, [user]);

  const loadSession = async (id) => {
    setActiveSession(id);
    try {
      const r = await api.get(`/chat/sessions/${id}/messages`);
      setMessages(r.data || []);
    } catch { setMessages([]); }
  };

  const createSession = async () => {
    try {
      const r = await api.post('/chat/sessions', { title: 'New Chat' });
      setSessions(s => [r.data, ...s]);
      setActiveSession(r.data.id);
      setMessages([]);
    } catch { /* fallback to local */ }
  };

  const deleteSession = async (id) => {
    try {
      await api.delete(`/chat/sessions/${id}`);
      setSessions(s => s.filter(x => x.id !== id));
      if (activeSession === id) {
        setActiveSession(null);
        setMessages([]);
      }
    } catch { /* silent */ }
  };

  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput('');

    const userMsg = { role: 'user', content: msg, created_at: new Date().toISOString() };
    setMessages(m => [...m, userMsg]);
    setLoading(true);

    try {
      const payload = {
        message: msg,
        session_id: activeSession,
        history: messages.slice(-6).map(m => ({ role: m.role, content: m.content })),
      };
      const r = await api.post('/chatbot', payload);
      const botMsg = { role: 'assistant', content: r.data?.response || r.data?.reply || 'No response.', created_at: new Date().toISOString() };
      setMessages(m => [...m, botMsg]);

      // Update session title from first message
      if (messages.length === 0 && activeSession) {
        const title = msg.length > 40 ? msg.slice(0, 40) + '…' : msg;
        setSessions(s => s.map(x => x.id === activeSession ? { ...x, title } : x));
      }
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: 'Sorry, something went wrong. Please try again.', created_at: new Date().toISOString() }]);
    }
    setLoading(false);
  };

  // Guest mode (no user logged in)
  const sendGuest = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput('');
    setMessages(m => [...m, { role: 'user', content: msg }]);
    setLoading(true);
    try {
      const r = await api.post('/chatbot', { message: msg, history: messages.slice(-6).map(m => ({ role: m.role, content: m.content })) });
      setMessages(m => [...m, { role: 'assistant', content: r.data?.response || r.data?.reply || 'No response.' }]);
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: 'Error connecting to AI. Please try again.' }]);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-50 pt-16 flex">
      {/* Sidebar — only for logged in users */}
      {user && (
        <>
          {/* Mobile toggle */}
          <button onClick={() => setSidebarOpen(v => !v)}
            className="fixed top-20 left-4 z-40 md:hidden bg-white border border-slate-200 rounded-lg p-2 shadow-sm text-slate-600">
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>

          <aside className={`${sidebarOpen ? 'translate-x-0' : '-translate-x-full'} fixed md:sticky top-16 left-0 w-72 h-[calc(100vh-4rem)] bg-white border-r border-slate-200 flex flex-col z-30 transition-transform md:translate-x-0`}>
            <div className="p-4 border-b border-slate-100">
              <button onClick={createSession}
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2.5 rounded-lg text-sm font-medium transition-colors btn-press">
                <Plus size={15} /> New Chat
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-0.5" style={{ scrollbarWidth: 'thin' }}>
              {sessions.length === 0 && (
                <div className="text-center py-8 text-slate-400 text-sm">No conversations yet</div>
              )}
              {sessions.map(s => (
                <div key={s.id}
                  className={`group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                    activeSession === s.id ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-50'}`}
                  onClick={() => loadSession(s.id)}>
                  <MessageSquare size={14} className="shrink-0" />
                  <span className="flex-1 truncate text-sm font-medium">{s.title || 'Untitled'}</span>
                  <button onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
                    className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500 transition">
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
            </div>
          </aside>
        </>
      )}

      {/* Main Chat */}
      <div className="flex-1 flex flex-col h-[calc(100vh-4rem)]">
        {/* Header */}
        <div className="border-b border-slate-200 bg-white px-6 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center">
            <Bot size={18} />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-800">BhaavShare AI</h1>
            <p className="text-xs text-slate-500">NEPSE market intelligence · LSTM + NLP</p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-4" style={{ scrollbarWidth: 'thin' }}>
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-14 h-14 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
                <Bot size={28} />
              </div>
              <h2 className="text-xl font-bold text-slate-800 mb-2">Ask me anything about NEPSE</h2>
              <p className="text-sm text-slate-500 max-w-md mb-6">
                I analyze 124+ stocks using live data, LSTM forecasts, and NLP sentiment from 27+ sources.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg">
                {[
                  'Should I buy NABIL?',
                  'How is EBL doing today?',
                  'Compare NABIL vs HBL',
                  'What\'s the market sentiment?',
                ].map((q, i) => (
                  <button key={i} onClick={() => { setInput(q); }}
                    className="text-left px-4 py-3 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-blue-200 hover:bg-blue-50 transition-colors">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {m.role !== 'user' && (
                <div className="w-7 h-7 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center shrink-0 mt-1">
                  <Bot size={14} />
                </div>
              )}
              <div className={`max-w-[75%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                m.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-sm'
                  : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm shadow-sm'
              }`}>
                <div className="whitespace-pre-wrap break-words"
                  dangerouslySetInnerHTML={{
                    __html: m.role === 'assistant'
                      ? m.content
                          .replace(/^\s*---\s*$/gm, '<hr class="my-3 border-slate-200" />')
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                          .replace(/\n/g, '<br/>')
                          .replace(/\|([^|]+)\|/g, '<span class="font-mono text-xs">$1</span>')
                      : m.content
                  }}
                />
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-7 h-7 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                <Bot size={14} />
              </div>
              <div className="bg-white border border-slate-200 rounded-xl px-4 py-3 shadow-sm">
                <Loader2 size={16} className="animate-spin text-blue-600" />
              </div>
            </div>
          )}
          <div ref={chatEnd} />
        </div>

        {/* Input */}
        <div className="border-t border-slate-200 bg-white px-4 md:px-8 py-4">
          <div className="max-w-3xl mx-auto flex items-center gap-3">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (user ? send() : sendGuest())}
              placeholder="Ask about any NEPSE stock…"
              className="flex-1 border border-slate-200 rounded-lg px-4 py-3 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-400 bg-slate-50 transition"
            />
            <button
              onClick={user ? send : sendGuest}
              disabled={loading || !input.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:opacity-40 text-white px-4 py-3 rounded-lg transition-colors btn-press"
            >
              <Send size={18} />
            </button>
          </div>
          <p className="text-center text-[10px] text-slate-400 mt-2">
            BhaavShare AI may produce inaccuracies. Not financial advice — always do your own research.
          </p>
        </div>
      </div>
    </div>
  );
}
