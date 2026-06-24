import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, RefreshCw, Bus, MapPin, Users, TrendingUp, Send, CheckCircle2 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import { useSocket } from '../context/SocketContext';
import Loader from '../components/Loader';
import ThresholdAlert from '../components/ThresholdAlert';

const THRESHOLD = 5;

export default function DepotDashboard() {
  const { user, logout } = useAuth();
  const { socket } = useSocket();
  const navigate = useNavigate();

  const [data, setData] = useState({ requests: [], grouped: [] });
  const [loading, setLoading] = useState(true);
  const [sendingId, setSendingId] = useState(null);
  const [sendingAll, setSendingAll] = useState(null);
  const [alerts, setAlerts] = useState([]);

  const loadData = useCallback(async () => {
    try {
      const res = await api.get('/requests?status=pending');
      setData(res.data);
    } catch (err) {
      if (err.response?.status === 401) { logout(); navigate('/login'); }
      else toast.error('Failed to load requests');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user || !['depot', 'admin'].includes(user.role)) { navigate('/login'); return; }
    loadData();
  }, [user]);

  useEffect(() => {
    if (!socket) return;

    socket.on('new-request', () => loadData());
    socket.on('request-updated', () => loadData());
    socket.on('bulk-updated', () => loadData());
    socket.on('threshold-alert', (alert) => {
      setAlerts(prev => [...prev, alert]);
    });

    return () => {
      socket.off('new-request');
      socket.off('request-updated');
      socket.off('bulk-updated');
      socket.off('threshold-alert');
    };
  }, [socket, loadData]);

  const handleSendBus = async (requestId) => {
    setSendingId(requestId);
    try {
      await api.patch(`/requests/${requestId}/send-bus`);
      toast.success('Bus dispatched! Passenger notified. 🚌');
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to dispatch');
    } finally {
      setSendingId(null);
    }
  };

  const handleSendAll = async (stopId, routeId, groupKey) => {
    setSendingAll(groupKey);
    try {
      const res = await api.patch('/requests/send-all', { stopId, routeId });
      toast.success(res.data.message);
      loadData();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to dispatch');
    } finally {
      setSendingAll(null);
    }
  };

  if (loading) return <Loader text="Loading depot dashboard..." />;

  const totalPending = data.requests.length;
  const aboveThreshold = data.grouped.filter(g => g.count >= THRESHOLD).length;

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 animate-fade-in">
      <ThresholdAlert alerts={alerts} onDismiss={(i) => setAlerts(prev => prev.filter((_, idx) => idx !== i))} />

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 gradient-bg rounded-xl flex items-center justify-center shadow-md">
            <LayoutDashboard size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Depot Dashboard</h1>
            <p className="text-sm text-slate-500 dark:text-slate-400">Real-time bus request management</p>
          </div>
        </div>
        <button onClick={loadData} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw size={16} /> Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Pending Requests', value: totalPending, icon: <Users size={20} className="text-brand" />, bg: 'bg-brand/10 dark:bg-brand/20' },
          { label: 'Stop Groups', value: data.grouped.length, icon: <MapPin size={20} className="text-purple-500" />, bg: 'bg-purple-100 dark:bg-purple-900/20' },
          { label: 'Above Threshold', value: aboveThreshold, icon: <TrendingUp size={20} className="text-rose-500" />, bg: 'bg-rose-100 dark:bg-rose-900/20' },
          { label: 'Threshold', value: `≥${THRESHOLD} req`, icon: <Bus size={20} className="text-emerald-500" />, bg: 'bg-emerald-100 dark:bg-emerald-900/20' },
        ].map((s) => (
          <div key={s.label} className="card flex items-center gap-3 p-4">
            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${s.bg}`}>{s.icon}</div>
            <div>
              <div className="text-2xl font-black text-slate-900 dark:text-white">{s.value}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">{s.label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Grouped Requests */}
      {data.grouped.length === 0 ? (
        <div className="card text-center py-16">
          <CheckCircle2 size={40} className="text-emerald-400 mx-auto mb-4" />
          <p className="font-semibold text-slate-700 dark:text-slate-300">All clear! No pending requests.</p>
          <p className="text-sm text-slate-400 mt-1">New requests will appear here in real-time.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {data.grouped.map((group) => {
            const isAlert = group.count >= THRESHOLD;
            const stopId = group.stop?._id;
            const routeId = group.route?._id;
            const gKey = `${stopId}-${routeId}`;
            return (
              <div key={gKey} className={`card border-2 ${isAlert ? 'border-rose-300 dark:border-rose-700' : 'border-transparent'}`}>
                {/* Group header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${isAlert ? 'bg-rose-100 dark:bg-rose-900/30' : 'bg-slate-100 dark:bg-slate-800'}`}>
                      <MapPin size={18} className={isAlert ? 'text-rose-500' : 'text-slate-500'} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-bold text-slate-900 dark:text-white">{group.stop?.name}</h3>
                        <span className={`badge ${isAlert ? 'badge-alert' : 'badge-pending'}`}>
                          {group.count} {group.count === 1 ? 'request' : 'requests'}
                        </span>
                        {isAlert && <span className="text-xs font-bold text-rose-600 dark:text-rose-400 animate-pulse">🚨 THRESHOLD REACHED</span>}
                      </div>
                      <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">
                        {group.route?.busDetails || `${group.route?.routeNumber} – ${group.route?.busName}`}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleSendAll(stopId, routeId, gKey)}
                    disabled={sendingAll === gKey}
                    className="btn-success flex items-center gap-2 shrink-0"
                  >
                    {sendingAll === gKey ? <RefreshCw size={16} className="animate-spin" /> : <Send size={16} />}
                    {sendingAll === gKey ? 'Dispatching...' : `Send Bus to All (${group.count})`}
                  </button>
                </div>

                {/* Individual requests */}
                <div className="space-y-2">
                  {group.requests.map((req) => (
                    <div key={req._id} className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl gap-3">
                      <div className="flex items-center gap-2 text-sm min-w-0">
                        <div className="w-7 h-7 bg-brand/10 dark:bg-brand/20 rounded-full flex items-center justify-center shrink-0">
                          <Users size={12} className="text-brand" />
                        </div>
                        <span className="font-mono text-slate-600 dark:text-slate-300 truncate">📱 {req.passenger?.mobile}</span>
                        <span className="text-xs text-slate-400 shrink-0">{new Date(req.createdAt).toLocaleTimeString()}</span>
                      </div>
                      <button
                        onClick={() => handleSendBus(req._id)}
                        disabled={sendingId === req._id}
                        className="btn-success text-xs py-1.5 px-3 shrink-0"
                      >
                        {sendingId === req._id ? <RefreshCw size={12} className="animate-spin" /> : <Send size={12} />}
                        {sendingId === req._id ? '...' : 'Send'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
