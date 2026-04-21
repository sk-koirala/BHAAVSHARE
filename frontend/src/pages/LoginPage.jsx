import React, { useState, useEffect, useMemo } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { TrendingUp, Mail, Lock, LogIn, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { validateEmail, validateLogin } from '../utils/validation';
import { AuthVisual } from './SignupPage';

const OAUTH_BASE = '/api/v1';

export default function LoginPage() {
  const { login, user, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const from = location.state?.from || '/me';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState(() => {
    const oauthErr = params.get('oauth_error');
    const provider = params.get('provider');
    return oauthErr ? `${provider ? provider + ': ' : ''}${oauthErr}` : '';
  });
  const [touched, setTouched] = useState({ email: false });

  useEffect(() => {
    if (user) navigate(from, { replace: true });
  }, [user, from, navigate]);

  const emailErr = useMemo(() => (touched.email ? validateEmail(email) : null), [touched.email, email]);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setTouched({ email: true });
    const err = validateLogin({ email, password });
    if (err) return setError(err);
    const r = await login(email, password);
    if (!r.ok) setError(r.error);
    else navigate(from, { replace: true });
  };

  return (
    <div className="min-h-screen bg-slate-50 pt-20 px-4 md:px-6 pb-12">
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">

        <AuthVisual
          eyebrow="WELCOME BACK"
          heading="Pick up where you left off."
          sub="Open your watchlist, review forecasts, and chat with the AI about today's market moves."
        />

        <div className="lg:col-span-6 flex items-center animate-[fadeSlide_0.5s_ease-out]">
          <div className="w-full max-w-md mx-auto">
            <div className="text-center mb-6">
              <div className="inline-flex w-12 h-12 rounded-xl bg-blue-600 items-center justify-center shadow-sm mb-4">
                <TrendingUp size={22} className="text-white" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900">Welcome back</h1>
              <p className="text-slate-500 text-sm mt-1">Sign in to your BhaavShare account</p>
            </div>

            <form onSubmit={submit} noValidate className="bg-white border border-slate-200 rounded-xl p-7 space-y-4 shadow-card">
              {error && (
                <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  <AlertCircle size={16} className="mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <div>
                <label className="text-xs text-slate-600 font-medium mb-1 block">Email</label>
                <div className={`flex items-center gap-2 bg-slate-50 border rounded-lg px-3.5 py-2.5 transition ${emailErr ? 'border-red-300' : 'border-slate-200 focus-within:border-blue-400'}`}>
                  <Mail size={15} className="text-slate-400" />
                  <input type="email" required autoComplete="email" value={email}
                    onChange={e => setEmail(e.target.value)}
                    onBlur={() => setTouched(t => ({ ...t, email: true }))}
                    placeholder="you@example.com"
                    className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400" />
                </div>
                {emailErr && <div className="text-[11px] text-red-600 mt-1 flex items-center gap-1"><AlertCircle size={11} /> {emailErr}</div>}
              </div>

              <div>
                <label className="text-xs text-slate-600 font-medium mb-1 block">Password</label>
                <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5 focus-within:border-blue-400 transition">
                  <Lock size={15} className="text-slate-400" />
                  <input type={showPw ? 'text' : 'password'} required autoComplete="current-password" value={password}
                    onChange={e => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400" />
                  <button type="button" onClick={() => setShowPw(v => !v)} className="text-slate-400 hover:text-slate-600" tabIndex={-1}>
                    {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              <button type="submit" disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-3 rounded-lg font-semibold transition-colors shadow-sm flex items-center justify-center gap-2 btn-press">
                <LogIn size={16} /> {loading ? 'Signing in…' : 'Sign In'}
              </button>

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
                Don't have an account? <Link to="/signup" className="text-blue-600 hover:text-blue-700 font-medium">Sign up</Link>
              </div>
              <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-400 text-center">
                Default admin: <span className="font-mono text-slate-500">admin@bhaavshare.com</span> / <span className="font-mono text-slate-500">admin123</span>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
