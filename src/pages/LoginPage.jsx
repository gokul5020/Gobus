import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, User, Bus, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username || !password) { toast.error('Fill in all fields'); return; }
    setLoading(true);
    try {
      const res = await api.post('/auth/admin-login', { username, password });
      login(res.data.token, res.data.user);
      toast.success(`Welcome, ${res.data.user.name || res.data.user.username}!`);
      navigate(res.data.user.role === 'admin' ? '/admin' : '/depot');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md animate-slide-up">
        <div className="card">
          <div className="w-16 h-16 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
            <Bus className="text-white w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-center text-slate-900 dark:text-white mb-1">Operator Login</h1>
          <p className="text-center text-slate-500 dark:text-slate-400 text-sm mb-8">Admin & Depot access only</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="relative">
              <User size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                className="input-field pl-11"
                placeholder="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
              />
            </div>
            <div className="relative">
              <Lock size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="password"
                className="input-field pl-11"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 py-3">
              {loading ? <RefreshCw size={18} className="animate-spin" /> : <Lock size={18} />}
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}
