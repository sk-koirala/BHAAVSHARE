import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Mail, Star, Trash2, Plus, ArrowRight, Shield, LogOut, Search,
  TrendingUp, TrendingDown, User as UserIcon, Settings, Camera,
  Lock, Save, Phone, MapPin, FileText, CheckCircle2, AlertCircle,
  Award, Activity, Upload,
} from 'lucide-react';
import api, { ALL_STOCKS } from '../utils/api';
import { useAuth } from '../context/AuthContext';
import { scorePassword } from '../utils/validation';

function cn(...args) { return args.filter(Boolean).join(' '); }

export default function UserPage() {
  const { user, isAdmin, logout, updateProfile, changePassword, uploadAvatar } = useAuth();
  const navigate = useNavigate();

  const [tab, setTab] = useState('overview');
  const [watchlist, setWatchlist] = useState([]);
  const [quotes, setQuotes] = useState({});
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [pickerSearch, setPickerSearch] = useState('');

  const [profile, setProfile] = useState({
    full_name: user?.full_name || '', avatar_url: user?.avatar_url || '',
    bio: user?.bio || '', phone: user?.phone || '', location: user?.location || '',
  });
  const [profileMsg, setProfileMsg] = useState(null);
  const [pwForm, setPwForm] = useState({ current: '', next: '', confirm: '' });
  const [pwMsg, setPwMsg] = useState(null);
  const fileInputRef = useRef(null);
  const [avatarUploading, setAvatarUploading] = useState(false);

  const handleAvatarFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!/^image\/(png|jpe?g|webp|gif)$/i.test(file.type)) {
      setProfileMsg({ type: 'err', text: 'Only PNG, JPEG, WebP or GIF.' }); return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setProfileMsg({ type: 'err', text: 'Image must be under 5MB.' }); return;
    }
    setAvatarUploading(true);
    try {
      const reader = new FileReader();
      reader.onload = async () => {
        const img = new Image();
        img.onload = async () => {
          const maxDim = 384;
          let { width, height } = img;
          if (width > height && width > maxDim) { height = Math.round(height * (maxDim / width)); width = maxDim; }
          else if (height > maxDim) { width = Math.round(width * (maxDim / height)); height = maxDim; }
          const canvas = document.createElement('canvas');
          canvas.width = width; canvas.height = height;
          canvas.getContext('2d').drawImage(img, 0, 0, width, height);
          const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
          const r = await uploadAvatar(dataUrl);
          if (r.ok) { setProfile(p => ({ ...p, avatar_url: dataUrl })); setProfileMsg({ type: 'ok', text: 'Picture updated.' }); }
          else setProfileMsg({ type: 'err', text: r.error });
          setAvatarUploading(false);
          setTimeout(() => setProfileMsg(null), 4000);
        };
        img.onerror = () => { setProfileMsg({ type: 'err', text: 'Could not read image.' }); setAvatarUploading(false); };
        img.src = reader.result;
      };
      reader.readAsDataURL(file);
    } catch (err) { setProfileMsg({ type: 'err', text: 'Upload error.' }); setAvatarUploading(false); }
    finally { if (fileInputRef.current) fileInputRef.current.value = ''; }
  };

  useEffect(() => { refresh(); }, []);
  useEffect(() => {
    if (user) setProfile({
      full_name: user.full_name || '', avatar_url: user.avatar_url || '',
      bio: user.bio || '', phone: user.phone || '', location: user.location || '',
    });
  }, [user]);

  const refresh = async () => {
    setLoading(true);
    try {
      const r = await api.get('/watchlist');
      setWatchlist(r.data || []);
      const results = await Promise.allSettled((r.data || []).map(w => api.get(`/stocks/${w.symbol}`)));
      const q = {};
      results.forEach((res, idx) => {
        if (res.status === 'fulfilled') q[r.data[idx].symbol] = res.value.data;
      });
      setQuotes(q);
    } finally { setLoading(false); }
  };

  const addSymbol = async (sym) => { await api.post('/watchlist', { symbol: sym }).catch(() => {}); setAdding(false); setPickerSearch(''); refresh(); };
  const removeSymbol = async (sym) => { await api.delete(`/watchlist/${sym}`).catch(() => {}); refresh(); };
  const doLogout = () => { logout(); navigate('/'); };

  const saveProfile = async (e) => {
    e.preventDefault(); setProfileMsg(null);
    const r = await updateProfile(profile);
    setProfileMsg(r.ok ? { type: 'ok', text: 'Profile updated.' } : { type: 'err', text: r.error });
    setTimeout(() => setProfileMsg(null), 4000);
  };

  const submitPassword = async (e) => {
    e.preventDefault(); setPwMsg(null);
    const pw = scorePassword(pwForm.next);
    if (!pw.valid) return setPwMsg({ type: 'err', text: `Requirements: ${pw.issues.join(', ')}.` });
    if (pwForm.next !== pwForm.confirm) return setPwMsg({ type: 'err', text: 'Passwords do not match.' });
    const r = await changePassword(pwForm.current, pwForm.next);
    if (r.ok) { setPwMsg({ type: 'ok', text: 'Password changed.' }); setPwForm({ current: '', next: '', confirm: '' }); }
    else setPwMsg({ type: 'err', text: r.error });
    setTimeout(() => setPwMsg(null), 4000);
  };

  const filteredPickerStocks = ALL_STOCKS.filter(s => s.includes(pickerSearch.toUpperCase())).filter(s => !watchlist.some(w => w.symbol === s)).slice(0, 50);
  const avatarInitial = (user?.full_name || user?.email || 'U')[0].toUpperCase();
  const upCount = Object.values(quotes).filter(q => (q?.change || 0) > 0).length;
  const downCount = Object.values(quotes).filter(q => (q?.change || 0) < 0).length;

  return (
    <div className="min-h-screen bg-slate-50 pt-20 px-4 md:px-6 pb-12">
      <div className="max-w-6xl mx-auto">
        {/* Profile Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 mb-5 shadow-card">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
            <div className="flex items-center gap-4">
              <div className="relative group/avatar">
                {user?.avatar_url ? (
                  <img src={user.avatar_url} alt="" className="w-20 h-20 rounded-xl object-cover ring-2 ring-slate-200" onError={(e) => { e.target.style.display = 'none'; }} />
                ) : (
                  <div className="w-20 h-20 rounded-xl bg-blue-600 flex items-center justify-center text-3xl font-bold text-white">{avatarInitial}</div>
                )}
                <button type="button" onClick={() => fileInputRef.current?.click()}
                  className="absolute inset-0 rounded-xl bg-black/50 text-white flex flex-col items-center justify-center gap-0.5 opacity-0 group-hover/avatar:opacity-100 transition cursor-pointer">
                  {avatarUploading ? <span className="text-[10px] animate-pulse">Uploading…</span> : <><Camera size={16} /><span className="text-[9px] font-medium">Change</span></>}
                </button>
                {isAdmin && (
                  <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-amber-500 flex items-center justify-center ring-2 ring-white">
                    <Shield size={11} className="text-white" />
                  </div>
                )}
              </div>
              <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif" className="hidden" onChange={handleAvatarFile} />
              <div>
                <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
                  {user?.full_name || 'Member'}
                  {isAdmin && <span className="text-[10px] bg-amber-50 text-amber-600 border border-amber-200 px-2 py-0.5 rounded-full font-semibold"><Award size={10} className="inline mr-0.5" />ADMIN</span>}
                </h1>
                <div className="flex items-center gap-1.5 text-slate-500 text-sm mt-0.5"><Mail size={13} /> {user?.email}</div>
                {user?.bio && <p className="text-slate-500 text-sm max-w-md mt-1 italic">"{user.bio}"</p>}
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 mt-1">
                  {user?.location && <span className="flex items-center gap-1"><MapPin size={10} /> {user.location}</span>}
                  {user?.phone && <span className="flex items-center gap-1"><Phone size={10} /> {user.phone}</span>}
                  <span>Since {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '—'}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isAdmin && <Link to="/admin" className="flex items-center gap-1.5 bg-amber-50 hover:bg-amber-100 border border-amber-200 text-amber-700 px-3 py-2 rounded-lg text-sm font-medium transition-colors"><Shield size={13} /> Admin</Link>}
              <button onClick={doLogout} className="flex items-center gap-1.5 bg-white hover:bg-red-50 border border-slate-200 text-slate-600 hover:text-red-600 px-3 py-2 rounded-lg text-sm font-medium transition-colors"><LogOut size={13} /> Sign Out</button>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3 mt-5">
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-center">
              <div className="text-[10px] text-slate-500 uppercase font-medium">Watching</div>
              <div className="text-xl font-bold text-slate-800 mt-0.5">{watchlist.length}</div>
            </div>
            <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
              <div className="text-[10px] text-green-600 uppercase font-medium">In Profit</div>
              <div className="text-xl font-bold text-green-700 mt-0.5">{upCount}</div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-center">
              <div className="text-[10px] text-red-600 uppercase font-medium">Down Today</div>
              <div className="text-xl font-bold text-red-700 mt-0.5">{downCount}</div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-1 mb-5 bg-white border border-slate-200 rounded-lg p-1 overflow-x-auto shadow-card">
          {[
            { key: 'overview', label: 'Overview', icon: <UserIcon size={14} /> },
            { key: 'watchlist', label: 'Watchlist', icon: <Star size={14} /> },
            { key: 'settings', label: 'Settings', icon: <Settings size={14} /> },
          ].map(t => (
            <button key={t.key} onClick={() => setTab(t.key)}
              className={cn('flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap',
                tab === t.key ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50')}>
              {t.icon} {t.label}
            </button>
          ))}
        </div>

        {/* Overview */}
        {tab === 'overview' && (
          <div className="space-y-5">
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center"><Activity size={17} /></div>
                <div><h2 className="font-semibold text-slate-900">Quick Insights</h2><p className="text-xs text-slate-500">Your snapshot at a glance</p></div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-5">
                  <div className="text-xs text-slate-500 font-medium uppercase">Top Holding Today</div>
                  {watchlist.length > 0 ? (() => {
                    const best = Object.entries(quotes).sort(([, a], [, b]) => (b?.change_pct || -999) - (a?.change_pct || -999))[0];
                    if (!best) return <div className="text-slate-400 text-sm mt-2">No data yet.</div>;
                    const [sym, q] = best; const up = (q?.change_pct || 0) >= 0;
                    return (<div className="mt-2"><div className="text-xl font-bold text-slate-800">{sym}</div>
                      <div className={cn('text-sm font-mono font-semibold mt-1 flex items-center gap-1', up ? 'text-green-600' : 'text-red-600')}>
                        {up ? <TrendingUp size={14} /> : <TrendingDown size={14} />} {q?.change_pct?.toFixed(2)}%</div></div>);
                  })() : <div className="text-slate-400 text-sm mt-2">Add stocks to your watchlist.</div>}
                </div>
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-5">
                  <div className="text-xs text-slate-500 font-medium uppercase">Profile Completeness</div>
                  {(() => {
                    const fields = ['full_name', 'avatar_url', 'bio', 'phone', 'location'];
                    const filled = fields.filter(f => user?.[f] && String(user[f]).trim()).length;
                    const pct = Math.round((filled / fields.length) * 100);
                    return (<div className="mt-2">
                      <div className="flex items-center justify-between text-sm mb-2"><span className="text-slate-500">{filled}/{fields.length} fields</span><span className="font-bold text-blue-600">{pct}%</span></div>
                      <div className="h-2 bg-slate-200 rounded-full overflow-hidden"><div className="h-full bg-blue-600 rounded-full transition-all" style={{ width: `${pct}%` }} /></div>
                      {pct < 100 && <button onClick={() => setTab('settings')} className="text-xs text-blue-600 hover:text-blue-700 mt-2 font-medium">Complete →</button>}
                    </div>);
                  })()}
                </div>
              </div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-slate-900">Permissions</h2>
                <span className={cn('text-xs font-semibold px-2.5 py-1 rounded-full', isAdmin ? 'bg-amber-50 text-amber-600 border border-amber-200' : 'bg-blue-50 text-blue-600 border border-blue-200')}>
                  {isAdmin ? 'ADMIN' : 'USER'}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                <PermRow allow label="View stocks, news, and predictions" />
                <PermRow allow label="Manage personal watchlist" />
                <PermRow allow label="Use AI chatbot" />
                <PermRow allow label="Update profile" />
                <PermRow allow={isAdmin} label="Trigger scraping" />
                <PermRow allow={isAdmin} label="Train LSTM models" />
                <PermRow allow={isAdmin} label="Manage users" />
                <PermRow allow={isAdmin} label="Moderate content" />
              </div>
            </div>
          </div>
        )}

        {/* Watchlist */}
        {tab === 'watchlist' && (
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
            <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center"><Star size={17} /></div>
                <div><h2 className="text-lg font-bold text-slate-900">Watchlist</h2><p className="text-xs text-slate-500">{watchlist.length} stocks tracked</p></div>
              </div>
              <button onClick={() => setAdding(v => !v)} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-sm btn-press">
                <Plus size={14} /> Add Stock
              </button>
            </div>
            {adding && (
              <div className="mb-5 bg-slate-50 border border-slate-200 rounded-lg p-4">
                <div className="flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-2 mb-3">
                  <Search size={14} className="text-slate-400" />
                  <input type="text" placeholder="Search symbol…" value={pickerSearch} onChange={e => setPickerSearch(e.target.value)} autoFocus
                    className="bg-transparent flex-1 text-sm text-slate-800 focus:outline-none placeholder-slate-400" />
                </div>
                <div className="grid grid-cols-4 md:grid-cols-8 gap-2 max-h-48 overflow-y-auto">
                  {filteredPickerStocks.map(s => (
                    <button key={s} onClick={() => addSymbol(s)}
                      className="px-2 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:text-blue-600 hover:border-blue-200 transition-colors">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {loading ? <div className="text-center py-10 text-slate-400 text-sm">Loading…</div>
            : watchlist.length === 0 ? (
              <div className="text-center py-14"><Star size={40} className="text-slate-200 mx-auto mb-3" /><p className="text-slate-400 text-sm">Your watchlist is empty.</p></div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {watchlist.map(w => {
                  const q = quotes[w.symbol]; const up = (q?.change || 0) >= 0;
                  return (
                    <div key={w.id} className="bg-slate-50 border border-slate-200 rounded-xl p-4 hover:border-blue-200 transition group relative card-hover">
                      <div className="flex items-start justify-between mb-2">
                        <div><div className="font-bold text-lg text-slate-800">{w.symbol}</div><div className="text-[10px] text-slate-500 uppercase">{q?.sector || '—'}</div></div>
                        <button onClick={() => removeSymbol(w.symbol)} className="text-slate-300 hover:text-red-500 transition opacity-0 group-hover:opacity-100"><Trash2 size={14} /></button>
                      </div>
                      <div className="text-xl font-mono font-bold text-slate-800">NPR {q?.latest_close ? q.latest_close.toFixed(2) : '--'}</div>
                      <div className={cn('flex items-center gap-1 text-sm font-mono font-semibold mt-1', up ? 'text-green-600' : 'text-red-600')}>
                        {up ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                        {q ? `${up ? '+' : ''}${q.change?.toFixed(2)} (${q.change_pct?.toFixed(2)}%)` : '—'}
                      </div>
                      <div className="grid grid-cols-2 gap-2 mt-3 text-[10px] text-slate-500">
                        <div>RSI: <span className="text-slate-700 font-mono">{q?.rsi_14?.toFixed(1) ?? '—'}</span></div>
                        <div>SMA30: <span className="text-slate-700 font-mono">{q?.sma_30?.toFixed(2) ?? '—'}</span></div>
                      </div>
                      <Link to={`/stocks/${w.symbol}`} className="mt-3 flex items-center justify-center gap-2 bg-white hover:bg-blue-50 border border-slate-200 hover:border-blue-200 text-blue-600 py-2 rounded-lg text-xs font-medium transition-colors">
                        View Analysis <ArrowRight size={12} />
                      </Link>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Settings */}
        {tab === 'settings' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <form onSubmit={saveProfile} className="bg-white border border-slate-200 rounded-xl p-6 shadow-card">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center"><UserIcon size={17} /></div>
                <div><h2 className="text-lg font-bold text-slate-900">Profile</h2><p className="text-xs text-slate-500">Keep your info updated</p></div>
              </div>
              {profileMsg && (
                <div className={cn('flex items-center gap-2 p-3 rounded-lg text-sm mb-4', profileMsg.type === 'ok' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700')}>
                  {profileMsg.type === 'ok' ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />} {profileMsg.text}
                </div>
              )}
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-600 font-medium mb-1 block">Profile Picture</label>
                  <div className="flex items-center gap-4 bg-slate-50 border border-slate-200 rounded-lg px-4 py-3">
                    {profile.avatar_url ? <img src={profile.avatar_url} alt="" className="w-14 h-14 rounded-lg object-cover ring-2 ring-slate-200" />
                      : <div className="w-14 h-14 rounded-lg bg-blue-600 flex items-center justify-center text-lg font-bold text-white">{avatarInitial}</div>}
                    <div className="flex-1">
                      <button type="button" onClick={() => fileInputRef.current?.click()} disabled={avatarUploading}
                        className="flex items-center gap-2 bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-600 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50">
                        <Upload size={11} /> {avatarUploading ? 'Uploading…' : 'Upload'}
                      </button>
                      <div className="text-[11px] text-slate-400 mt-1">PNG, JPEG, WebP, GIF · Max 5MB</div>
                    </div>
                  </div>
                </div>
                <Field label="Full Name" icon={<UserIcon size={14} />} value={profile.full_name} onChange={v => setProfile({ ...profile, full_name: v })} placeholder="Ram Bahadur" />
                <Field label="Phone" icon={<Phone size={14} />} value={profile.phone} onChange={v => setProfile({ ...profile, phone: v })} placeholder="+977 98XXXXXXXX" />
                <Field label="Location" icon={<MapPin size={14} />} value={profile.location} onChange={v => setProfile({ ...profile, location: v })} placeholder="Kathmandu, Nepal" />
                <div>
                  <label className="text-xs text-slate-600 font-medium mb-1 block">Bio</label>
                  <div className="flex items-start gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5 focus-within:border-blue-400 transition">
                    <FileText size={14} className="text-slate-400 mt-0.5" />
                    <textarea rows={3} value={profile.bio} onChange={e => setProfile({ ...profile, bio: e.target.value })}
                      placeholder="About your investing style…"
                      className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400 resize-none" />
                  </div>
                </div>
              </div>
              <button type="submit" className="w-full mt-5 bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm btn-press">
                <Save size={15} /> Save Profile
              </button>
            </form>

            <form onSubmit={submitPassword} className="bg-white border border-slate-200 rounded-xl p-6 h-fit shadow-card">
              <div className="flex items-center gap-3 mb-5">
                <div className="w-9 h-9 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center"><Lock size={17} /></div>
                <div><h2 className="text-lg font-bold text-slate-900">Security</h2><p className="text-xs text-slate-500">Change your password</p></div>
              </div>
              {pwMsg && (
                <div className={cn('flex items-center gap-2 p-3 rounded-lg text-sm mb-4', pwMsg.type === 'ok' ? 'bg-green-50 border border-green-200 text-green-700' : 'bg-red-50 border border-red-200 text-red-700')}>
                  {pwMsg.type === 'ok' ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />} {pwMsg.text}
                </div>
              )}
              <div className="space-y-4">
                <PwField label="Current Password" value={pwForm.current} onChange={v => setPwForm({ ...pwForm, current: v })} />
                <PwField label="New Password" value={pwForm.next} onChange={v => setPwForm({ ...pwForm, next: v })} />
                <PwField label="Confirm New Password" value={pwForm.confirm} onChange={v => setPwForm({ ...pwForm, confirm: v })} />
              </div>
              <button type="submit" className="w-full mt-5 bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-lg font-semibold transition-colors flex items-center justify-center gap-2 shadow-sm btn-press">
                <Lock size={15} /> Update Password
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, icon, value, onChange, placeholder }) {
  return (
    <div>
      <label className="text-xs text-slate-600 font-medium mb-1 block">{label}</label>
      <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5 focus-within:border-blue-400 transition">
        <span className="text-slate-400">{icon}</span>
        <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
          className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400" />
      </div>
    </div>
  );
}

function PwField({ label, value, onChange }) {
  return (
    <div>
      <label className="text-xs text-slate-600 font-medium mb-1 block">{label}</label>
      <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5 focus-within:border-amber-400 transition">
        <Lock size={14} className="text-slate-400" />
        <input type="password" value={value} onChange={e => onChange(e.target.value)} placeholder="••••••••"
          className="bg-transparent flex-1 text-sm focus:outline-none text-slate-800 placeholder-slate-400" />
      </div>
    </div>
  );
}

function PermRow({ allow, label }) {
  return (
    <div className={cn('flex items-center gap-2 px-3 py-2 rounded-md border text-sm', allow ? 'bg-green-50 border-green-100 text-green-700' : 'bg-slate-50 border-slate-100 text-slate-400')}>
      {allow ? <CheckCircle2 size={13} className="text-green-500 shrink-0" /> : <AlertCircle size={13} className="text-slate-300 shrink-0" />}
      <span className="font-medium text-xs">{label}</span>
    </div>
  );
}
