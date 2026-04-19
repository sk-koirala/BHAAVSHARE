import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2 } from 'lucide-react';

export default function OAuthCallback() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { setTokenFromOAuth } = useAuth();

  useEffect(() => {
    const token = params.get('token');
    if (token) {
      setTokenFromOAuth(token);
      navigate('/me', { replace: true });
    } else {
      navigate('/login', { replace: true });
    }
  }, [params, navigate, setTokenFromOAuth]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center">
      <div className="text-center">
        <Loader2 size={32} className="text-blue-600 animate-spin mx-auto mb-4" />
        <p className="text-slate-600 text-sm font-medium">Completing sign-in…</p>
      </div>
    </div>
  );
}
