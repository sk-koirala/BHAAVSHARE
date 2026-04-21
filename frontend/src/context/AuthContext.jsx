import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import api from '../utils/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('bhaav_user');
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  });
  const [loading, setLoading] = useState(false);

  const persist = (token, u) => {
    if (token) localStorage.setItem('bhaav_token', token);
    if (u) localStorage.setItem('bhaav_user', JSON.stringify(u));
    setUser(u);
  };

  const login = useCallback(async (email, password) => {
    setLoading(true);
    try {
      const { data } = await api.post('/auth/login', { email, password });
      persist(data.access_token, data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e?.response?.data?.detail || 'Login failed' };
    } finally { setLoading(false); }
  }, []);

  const signup = useCallback(async (payload) => {
    setLoading(true);
    try {
      const { data } = await api.post('/auth/signup', payload);
      persist(data.access_token, data.user);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e?.response?.data?.detail || 'Signup failed' };
    } finally { setLoading(false); }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('bhaav_token');
    localStorage.removeItem('bhaav_user');
    setUser(null);
  }, []);

  const updateProfile = useCallback(async (updates) => {
    try {
      const { data } = await api.put('/auth/me', updates);
      persist(null, data);
      return { ok: true, user: data };
    } catch (e) {
      return { ok: false, error: e?.response?.data?.detail || 'Update failed' };
    }
  }, []);

  const changePassword = useCallback(async (current_password, new_password) => {
    try {
      await api.post('/auth/change-password', { current_password, new_password });
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e?.response?.data?.detail || 'Password change failed' };
    }
  }, []);

  const uploadAvatar = useCallback(async (data_url) => {
    try {
      const { data } = await api.post('/auth/avatar', { data_url });
      persist(null, data);
      return { ok: true, user: data };
    } catch (e) {
      return { ok: false, error: e?.response?.data?.detail || 'Avatar upload failed' };
    }
  }, []);

  // OAuth: set token directly from callback URL
  const setTokenFromOAuth = useCallback(async (token) => {
    localStorage.setItem('bhaav_token', token);
    try {
      const { data } = await api.get('/auth/me');
      persist(null, data);
    } catch {
      logout();
    }
  }, [logout]);

  // Refresh user on mount if token exists
  useEffect(() => {
    const token = localStorage.getItem('bhaav_token');
    if (token && !user) {
      api.get('/auth/me').then(r => persist(null, r.data)).catch(() => logout());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <AuthContext.Provider value={{
      user, loading, login, signup, logout,
      updateProfile, changePassword, uploadAvatar,
      setTokenFromOAuth,
      isAdmin: !!user?.is_admin,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
