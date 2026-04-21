import React, { useState, useEffect, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  TrendingUp, Mail, Lock, User, UserPlus, AlertCircle, Check, X, Eye, EyeOff,
  Phone, MapPin, FileText, ShieldCheck, Activity, BarChart3, Sparkles, KeyRound,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { validateSignup, scorePassword, validateEmail } from '../utils/validation';

const OAUTH_BASE = '/api/v1';

export default function SignupPage() {
  const { signup, user, loading } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [phone, setPhone] = useState('');
  const [location, setLocation] = useState('Kathmandu, Nepal');
  const [bio, setBio] = useState('');
  const [role, setRole] = useState('user');
  const [adminCode, setAdminCode] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [touched, setTouched] = useState({ email: false, password: false, confirm: false });

  useEffect(() => { if (user) navigate('/me', { replace: true }); }, [user, navigate]);

  const strength = useMemo(() => scorePassword(password), [password]);
  const emailErr = useMemo(() => (touched.email ? validateEmail(email) : null), [touched.email, email]);
  const confirmErr = touched.confirm && confirm && confirm !== password ? 'Passwords do not match.' : null;

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setTouched({ email: true, password: true, confirm: true });
    const err = validateSignup({ email, password, confirm, fullName });
    if (err) return setError(err);
    if (role === 'admin' && !adminCode.trim()) return setError('Admin signup code is required for admin accounts.');
    const r = await signup({
      email,
      password,
      full_name: fullName,
      phone: phone || null,
      location: location || null,
      bio: bio || null,
      role,
      admin_code: role === 'admin' ? adminCode : null,
    });
    if (!r.ok) setError(r.error);
    else navigate('/me', { replace: true });
  };

  const strengthColors = ['bg-red-400', 'bg-orange-400', 'bg-amber-400', 'bg-green-400', 'bg-green-500'];

  return (
    <div className="min-h-screen bg-slate-50 pt-20 px-4 md:px-6 pb-12">
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">

        {/* VISUAL PANEL */}
        <AuthVisual
          eyebrow="JOIN BHAAVSHARE"
          heading="Smarter NEPSE decisions, powered by AI."
          sub="Create your account in under a minute. Track stocks, run forecasts, and get BUY / HOLD / SELL reasoning from our chatbot."
        />

        {/* FORM PANEL */}
        <div className="lg:col-span-6 animate-[fadeSlide_0.5s_ease-out]">
          <div className="text-center mb-6">
            <div className="inline-flex w-12 h-12 rounded-xl bg-blue-600 items-center justify-center shadow-sm mb-4">
              <TrendingUp size={22} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold text-slate-900">Create your account</h1>
            <p className="text-slate-500 text-sm mt-1">Join BhaavShare for AI stock intelligence</p>
          </div>

          <form onSubmit={submit} noValidate className="bg-white border border-slate-200 rounded-xl p-6 md:p-7 space-y-4 shadow-card">
            {error && (
              <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Role selector */}
            <div>
              <label className="text-xs text-slate-600 font-medium mb-1.5 block">I am signing up as</label>
              <div className="grid grid-cols-2 gap-2 p-1 bg-slate-100 rounded-lg">
                <RoleTab active={role === 'user'} onClick={() => setRole('user')} icon={<User size={14} />} label="Investor" desc="Track, analyze, forecast" />
                <RoleTab active={role === 'admin'} onClick={() => setRole('admin')} icon={<ShieldCheck size={14} />} label="Admin" desc="Needs signup code" />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Full Name" icon={<User size={15} />}>
                <input type="text" required autoComplete="name" value={fullName}
                  onChange={e => setFullName(e.target.value)} placeholder="Ram Bahadur" minLength={2} maxLength={100}
                  className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400 w-full" />
              </Field>
              <Field label="Email" icon={<Mail size={15} />} error={emailErr}>
                <input type="email" required autoComplete="email" value={email}
                  onChange={e => setEmail(e.target.value)}
                  onBlur={() => setTouched(t => ({ ...t, email: true }))}
                  placeholder="you@example.com"
                  className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400 w-full" />
              </Field>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Phone (optional)" icon={<Phone size={15} />}>
                <input type="tel" autoComplete="tel" value={phone}
                  onChange={e => setPhone(e.target.value)} placeholder="+977 98..."
                  className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400 w-full" />
              </Field>
              <Field label="Location" icon={<MapPin size={15} />}>
                <input type="text" value={location}
                  onChange={e => setLocation(e.target.value)} placeholder="Kathmandu, Nepal"
                  className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400 w-full" />
              </Field>
            </div>

            <Field label="Bio (optional)" icon={<FileText size={15} />} align="top">
              <textarea rows={2} value={bio} maxLength={500}
                onChange={e => setBio(e.target.value)}
                placeholder="Tell us a bit about your investing style…"
                className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400 resize-none w-full" />
            </Field>

            <Field label="Password" icon={<Lock size={15} />}>
              <input type={showPw ? 'text' : 'password'} required autoComplete="new-password" value={password}
                onChange={e => setPassword(e.target.value)}
                onBlur={() => setTouched(t => ({ ...t, password: true }))}
                placeholder="At least 8 characters"
                className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400 w-full" />
              <button type="button" onClick={() => setShowPw(v => !v)} className="text-slate-400 hover:text-slate-600" tabIndex={-1}>
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </Field>
            {password && (
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex gap-1 flex-1">
                    {[0, 1, 2, 3, 4].map(i => (
                      <div key={i} className={`h-1 flex-1 rounded-full transition ${i < strength.score ? strengthColors[Math.min(i, 4)] : 'bg-slate-200'}`} />
                    ))}
                  </div>
                  <span className={`text-[11px] font-semibold ml-2 ${strength.valid ? 'text-green-600' : 'text-amber-600'}`}>
                    {strength.label}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 text-[11px]">
                  <Rule ok={strength.rules.length} text="8+ characters" />
                  <Rule ok={strength.rules.upper} text="Uppercase A–Z" />
                  <Rule ok={strength.rules.lower} text="Lowercase a–z" />
                  <Rule ok={strength.rules.digit} text="Digit 0–9" />
                </div>
              </div>
            )}

            <Field label="Confirm Password" icon={<Lock size={15} />} error={confirmErr}>
              <input type={showPw ? 'text' : 'password'} required autoComplete="new-password" value={confirm}
                onChange={e => setConfirm(e.target.value)}
                onBlur={() => setTouched(t => ({ ...t, confirm: true }))}
                placeholder="••••••••"
                className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400 w-full" />
            </Field>

            {role === 'admin' && (
              <Field label="Admin Signup Code" icon={<KeyRound size={15} />}>
                <input type="password" value={adminCode}
                  onChange={e => setAdminCode(e.target.value)}
                  placeholder="Ask the platform owner"
                  className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400 w-full" />
              </Field>
            )}

            <button type="submit" disabled={loading || !strength.valid}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 rounded-lg font-semibold transition-colors shadow-sm flex items-center justify-center gap-2 btn-press">
              <UserPlus size={16} /> {loading ? 'Creating…' : `Create ${role === 'admin' ? 'Admin' : 'Investor'} Account`}
            </button>

            {/* OAuth */}
            <div className="flex items-center gap-3 py-2">
              <div className="flex-1 h-px bg-slate-200" />
              <span className="text-xs text-slate-400 font-medium">or continue with</span>
              <div className="flex-1 h-px bg-slate-200" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <a href={`${OAUTH_BASE}/auth/google`}
                className="flex items-center justify-center gap-2 border border-slate-200 rounded-lg py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors btn-press">
                <svg width="16" height="16" viewBox="0 0 48 48"><path fill="#4285F4" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#34A853" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#EA4335" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>
                Google
              </a>
              <a href={`${OAUTH_BASE}/auth/github`}
                className="flex items-center justify-center gap-2 border border-slate-200 rounded-lg py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors btn-press">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
                GitHub
              </a>
            </div>

            <div className="text-center text-sm text-slate-500 pt-2">
              Already have an account? <Link to="/login" className="text-blue-600 hover:text-blue-700 font-medium">Sign in</Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

function Rule({ ok, text }) {
  return (
    <div className={`flex items-center gap-1.5 ${ok ? 'text-green-600' : 'text-slate-400'}`}>
      {ok ? <Check size={10} /> : <X size={10} />}
      <span>{text}</span>
    </div>
  );
}

function Field({ label, icon, error, align = 'center', children }) {
  return (
    <div>
      <label className="text-xs text-slate-600 font-medium mb-1 block">{label}</label>
      <div className={`flex ${align === 'top' ? 'items-start pt-2.5' : 'items-center'} gap-2 bg-slate-50 border rounded-lg px-3.5 py-2.5 transition ${error ? 'border-red-300' : 'border-slate-200 focus-within:border-blue-400'}`}>
        <span className="text-slate-400 shrink-0">{icon}</span>
        {children}
      </div>
      {error && <div className="text-[11px] text-red-600 mt-1 flex items-center gap-1"><AlertCircle size={11} /> {error}</div>}
    </div>
  );
}

function RoleTab({ active, onClick, icon, label, desc }) {
  return (
    <button type="button" onClick={onClick}
      className={`relative flex items-center gap-2.5 px-3 py-2.5 rounded-md text-left transition ${active ? 'bg-white shadow-sm ring-1 ring-blue-500/20' : 'hover:bg-white/60'}`}>
      <span className={`w-7 h-7 rounded-md flex items-center justify-center ${active ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-500'}`}>{icon}</span>
      <span>
        <div className={`text-sm font-semibold ${active ? 'text-slate-900' : 'text-slate-600'}`}>{label}</div>
        <div className="text-[10px] text-slate-500">{desc}</div>
      </span>
    </button>
  );
}

/* ─────────────────────────────────────────────────────────────
 * Shared animated visual panel (used by Login + Signup)
 * ───────────────────────────────────────────────────────────── */
export function AuthVisual({ eyebrow, heading, sub }) {
  return (
    <div className="lg:col-span-6 hidden lg:block">
      <div className="relative h-full min-h-[600px] rounded-2xl overflow-hidden bg-gradient-to-br from-blue-700 via-indigo-800 to-slate-900 text-white p-10 shadow-xl">
        {/* grid bg */}
        <div className="absolute inset-0 opacity-[0.08]" style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,.8) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.8) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }} />
        {/* animated blobs */}
        <div className="absolute -top-24 -right-24 w-80 h-80 rounded-full bg-blue-400/20 blur-3xl animate-pulse" />
        <div className="absolute -bottom-24 -left-24 w-96 h-96 rounded-full bg-indigo-400/15 blur-3xl" />

        {/* Floating candlestick chart svg */}
        <FloatingCandles />

        <div className="relative z-10 flex flex-col h-full">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-white/10 backdrop-blur border border-white/15 rounded-full text-[11px] font-semibold tracking-wider text-white/90 w-max mb-6">
            <Activity size={12} /> {eyebrow}
          </div>
          <h2 className="text-3xl xl:text-4xl font-extrabold leading-tight mb-4 [text-wrap:balance]">
            {heading}
          </h2>
          <p className="text-white/70 max-w-md text-sm xl:text-base leading-relaxed mb-10">{sub}</p>

          <div className="mt-auto grid grid-cols-3 gap-3">
            <VisualStat icon={<BarChart3 size={16} />} value="124+" label="NEPSE stocks" />
            <VisualStat icon={<Sparkles size={16} />} value="27+" label="news sources" />
            <VisualStat icon={<ShieldCheck size={16} />} value="JWT" label="secure auth" />
          </div>
        </div>
      </div>
    </div>
  );
}

function VisualStat({ icon, value, label }) {
  return (
    <div className="bg-white/10 backdrop-blur border border-white/10 rounded-xl p-3">
      <div className="flex items-center gap-1.5 text-white/70 text-[10px] uppercase tracking-wider mb-1">
        {icon} {label}
      </div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}

function FloatingCandles() {
  // Pure-SVG floating candles — no extra deps, looping subtle y-translation.
  return (
    <svg className="absolute right-6 top-1/2 -translate-y-1/2 w-[60%] h-[60%] opacity-40 pointer-events-none" viewBox="0 0 400 300" preserveAspectRatio="none">
      <style>{`
        @keyframes floatA { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
        @keyframes floatB { 0%,100%{transform:translateY(0)} 50%{transform:translateY(8px)} }
        .c-up { fill: #34d399 }
        .c-dn { fill: #f87171 }
        .c-wick { stroke: rgba(255,255,255,.5); stroke-width: 1 }
      `}</style>
      {[
        [20, 160, 60, 'up', 0],  [50, 140, 70, 'dn', 1],  [80, 130, 50, 'up', 0],
        [110, 110, 80, 'up', 1], [140, 120, 40, 'dn', 0], [170, 90, 70, 'up', 1],
        [200, 100, 50, 'dn', 0], [230, 70, 90, 'up', 1],  [260, 80, 40, 'dn', 0],
        [290, 60, 60, 'up', 1],  [320, 50, 50, 'up', 0],  [350, 40, 70, 'up', 1],
      ].map(([x, y, h, dir, anim], i) => (
        <g key={i} style={{ animation: `${anim ? 'floatA' : 'floatB'} ${3 + (i % 4)}s ease-in-out infinite`, transformOrigin: `${x}px ${y}px` }}>
          <line x1={x + 9} y1={y - 12} x2={x + 9} y2={y + h + 12} className="c-wick" />
          <rect x={x} y={y} width={18} height={h} className={dir === 'up' ? 'c-up' : 'c-dn'} rx="2" />
        </g>
      ))}
    </svg>
  );
}
