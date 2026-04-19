import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Menu, X, User, LogOut, Shield, Star, Bell, Check, Trash2, ChevronDown } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';

const NAV_LINKS = [
  { path: '/', label: 'Home' },
  { path: '/stocks', label: 'Stocks' },
  { path: '/news', label: 'News' },
  { path: '/ai', label: 'AI Assistant' },
  { path: '/about', label: 'About' },
  { path: '/contact', label: 'Contact' },
];

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAdmin, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // Admin notification bell
  const [bellOpen, setBellOpen] = useState(false);
  const [notifs, setNotifs] = useState([]);
  const [unread, setUnread] = useState(0);
  const bellRef = useRef(null);

  useEffect(() => {
    if (!isAdmin) { setUnread(0); setNotifs([]); return; }
    let cancelled = false;
    const poll = async () => {
      try {
        const { data } = await api.get('/admin/notifications/unread-count');
        if (!cancelled) setUnread(data?.unread || 0);
      } catch { /* silent */ }
    };
    poll();
    const t = setInterval(poll, 30000);
    return () => { cancelled = true; clearInterval(t); };
  }, [isAdmin]);

  // Close dropdowns on outside click
  useEffect(() => {
    const onClick = (e) => {
      if (bellRef.current && !bellRef.current.contains(e.target)) setBellOpen(false);
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  const openBell = async () => {
    setBellOpen(v => !v);
    if (!bellOpen) {
      try {
        const { data } = await api.get('/admin/notifications?limit=30');
        setNotifs(Array.isArray(data) ? data : []);
      } catch { setNotifs([]); }
    }
  };

  const markRead = async (id) => {
    try {
      await api.post(`/admin/notifications/${id}/read`);
      setNotifs(ns => ns.map(n => n.id === id ? { ...n, is_read: true } : n));
      setUnread(c => Math.max(0, c - 1));
    } catch { /* silent */ }
  };

  const markAllRead = async () => {
    try {
      await api.post('/admin/notifications/read-all');
      setNotifs(ns => ns.map(n => ({ ...n, is_read: true })));
      setUnread(0);
    } catch { /* silent */ }
  };

  const deleteNotif = async (id) => {
    try {
      await api.delete(`/admin/notifications/${id}`);
      setNotifs(ns => ns.filter(n => n.id !== id));
    } catch { /* silent */ }
  };

  const timeAgo = (iso) => {
    if (!iso) return '';
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const eventIcon = (type) => ({
    signup: '👤', login: '🔑', watchlist_add: '⭐', watchlist_remove: '✕',
    contact_message: '✉', password_change: '🔒', profile_update: '📝',
  }[type] || '•');

  const doLogout = () => {
    logout();
    setMenuOpen(false);
    setMobileOpen(false);
    navigate('/');
  };

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-slate-200 shadow-nav">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-sm">
              <svg viewBox="0 0 64 64" fill="none" className="w-8 h-8">
                <polyline points="10,46 22,38 32,42 42,28 54,16" stroke="#fff" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" fill="none" opacity="0.9"/>
                <polyline points="47,14 54,16 52,23" stroke="#fff" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" fill="none"/>
              </svg>
            </div>
            <span className="text-lg font-bold text-slate-900">
              BhaavShare
            </span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map(link => (
              <Link
                key={link.path}
                to={link.path}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors
                  ${isActive(link.path)
                    ? 'text-blue-600 bg-blue-50'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'}`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Right side */}
          <div className="hidden md:flex items-center gap-2">
            {/* Admin bell */}
            {isAdmin && (
              <div className="relative" ref={bellRef}>
                <button
                  onClick={openBell}
                  className="relative p-2 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                  title="Admin notifications"
                >
                  <Bell size={18} />
                  {unread > 0 && (
                    <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center px-1">
                      {unread > 99 ? '99+' : unread}
                    </span>
                  )}
                </button>
                {bellOpen && (
                  <div className="absolute right-0 top-12 w-96 max-h-[70vh] bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden z-50 flex flex-col">
                    <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                      <div>
                        <div className="text-sm font-semibold text-slate-900">Notifications</div>
                        <div className="text-xs text-slate-500">{unread} unread</div>
                      </div>
                      {notifs.some(n => !n.is_read) && (
                        <button
                          onClick={markAllRead}
                          className="text-xs px-2 py-1 rounded-md bg-blue-50 text-blue-600 hover:bg-blue-100 font-medium flex items-center gap-1"
                        >
                          <Check size={12} /> Mark all read
                        </button>
                      )}
                    </div>
                    <div className="overflow-y-auto flex-1">
                      {notifs.length === 0 ? (
                        <div className="px-4 py-8 text-center text-sm text-slate-400">
                          No notifications yet.
                        </div>
                      ) : (
                        notifs.map(n => (
                          <div
                            key={n.id}
                            className={`px-4 py-3 border-b border-slate-50 hover:bg-slate-50 transition ${!n.is_read ? 'bg-blue-50/40' : ''}`}
                          >
                            <div className="flex items-start gap-2.5">
                              <span className="text-sm leading-none pt-0.5 w-5 text-center">{eventIcon(n.event_type)}</span>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <div className="text-sm font-medium text-slate-800 truncate">{n.title}</div>
                                  {!n.is_read && <span className="w-2 h-2 rounded-full bg-blue-500 shrink-0" />}
                                </div>
                                {n.body && <div className="text-xs text-slate-500 mt-0.5 line-clamp-2">{n.body}</div>}
                                <div className="text-[11px] text-slate-400 mt-1">{timeAgo(n.created_at)}</div>
                              </div>
                              <div className="flex flex-col gap-1">
                                {!n.is_read && (
                                  <button onClick={() => markRead(n.id)} title="Mark read"
                                    className="p-1 rounded hover:bg-blue-100 text-blue-500"><Check size={12} /></button>
                                )}
                                <button onClick={() => deleteNotif(n.id)} title="Delete"
                                  className="p-1 rounded hover:bg-red-50 text-slate-400 hover:text-red-500"><Trash2 size={12} /></button>
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {!user ? (
              <>
                <Link to="/login" className="text-sm text-slate-600 hover:text-slate-900 transition px-3 py-2 font-medium">
                  Sign In
                </Link>
                <Link to="/signup" className="text-sm bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors shadow-sm btn-press">
                  Get Started
                </Link>
              </>
            ) : (
              <div className="relative" ref={menuRef}>
                <button onClick={() => setMenuOpen(v => !v)}
                  className="flex items-center gap-2 hover:bg-slate-100 px-2.5 py-1.5 rounded-lg text-sm text-slate-700 transition-colors">
                  {user.avatar_url ? (
                    <img src={user.avatar_url} alt="" className="w-7 h-7 rounded-full object-cover ring-2 ring-slate-200"
                      onError={(e) => { e.target.style.display = 'none'; }} />
                  ) : (
                    <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center font-bold text-xs text-white">
                      {(user.full_name || user.email)[0]?.toUpperCase()}
                    </div>
                  )}
                  <span className="max-w-[140px] truncate font-medium">{user.full_name || user.email}</span>
                  {isAdmin && <Shield size={13} className="text-amber-500" />}
                  <ChevronDown size={14} className="text-slate-400" />
                </button>
                {menuOpen && (
                  <div className="absolute right-0 top-12 w-56 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-slate-100">
                      <div className="text-sm font-semibold text-slate-900 truncate">{user.full_name || 'Member'}</div>
                      <div className="text-xs text-slate-500 truncate">{user.email}</div>
                    </div>
                    <Link to="/me" onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors">
                      <User size={14} /> My Profile
                    </Link>
                    <Link to="/me" onClick={() => setMenuOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-700 hover:bg-slate-50 transition-colors">
                      <Star size={14} /> Watchlist
                    </Link>
                    {isAdmin && (
                      <Link to="/admin" onClick={() => setMenuOpen(false)}
                        className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-amber-600 hover:bg-amber-50 transition-colors">
                        <Shield size={14} /> Admin Panel
                      </Link>
                    )}
                    <button onClick={doLogout}
                      className="w-full text-left flex items-center gap-2.5 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 border-t border-slate-100 transition-colors">
                      <LogOut size={14} /> Sign Out
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Mobile Toggle */}
          <button onClick={() => setMobileOpen(!mobileOpen)} className="md:hidden p-2 text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg">
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden bg-white border-t border-slate-200 px-4 pb-4 shadow-lg">
          {NAV_LINKS.map(link => (
            <Link key={link.path} to={link.path} onClick={() => setMobileOpen(false)}
              className={`block px-4 py-3 rounded-lg text-sm font-medium ${isActive(link.path) ? 'text-blue-600 bg-blue-50' : 'text-slate-600'}`}>
              {link.label}
            </Link>
          ))}
          {!user ? (
            <div className="flex gap-2 mt-4 pt-4 border-t border-slate-100">
              <Link to="/login" onClick={() => setMobileOpen(false)} className="flex-1 text-center text-sm text-slate-700 border border-slate-200 py-2.5 rounded-lg font-medium">Sign In</Link>
              <Link to="/signup" onClick={() => setMobileOpen(false)} className="flex-1 text-center text-sm bg-blue-600 text-white py-2.5 rounded-lg font-semibold">Get Started</Link>
            </div>
          ) : (
            <div className="mt-4 pt-4 border-t border-slate-100 space-y-1">
              <Link to="/me" onClick={() => setMobileOpen(false)} className="block text-sm text-slate-700 px-4 py-2.5 rounded-lg hover:bg-slate-50">My Profile</Link>
              {isAdmin && <Link to="/admin" onClick={() => setMobileOpen(false)} className="block text-sm text-amber-600 px-4 py-2.5 rounded-lg hover:bg-amber-50">Admin Panel</Link>}
              <button onClick={doLogout} className="w-full text-left text-sm text-red-600 px-4 py-2.5 rounded-lg hover:bg-red-50">Sign Out</button>
            </div>
          )}
        </div>
      )}
    </nav>
  );
}
