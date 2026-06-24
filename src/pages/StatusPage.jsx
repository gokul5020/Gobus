import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, CheckCircle, Bus, MapPin, RefreshCw, AlertCircle, Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import { useSocket } from '../context/SocketContext';
import Loader from '../components/Loader';
import LiveBusMap from '../components/LiveBusMap';

const STATUS_META = {
  pending: { label: 'Waiting for Bus', color: 'badge-pending', icon: <Clock size={14} />, bgColor: 'bg-amber-50 dark:bg-amber-950/20', borderColor: 'border-amber-200 dark:border-amber-800' },
  sent: { label: 'Bus is on the Way! 🚌', color: 'badge-sent', icon: <Bus size={14} />, bgColor: 'bg-emerald-50 dark:bg-emerald-950/20', borderColor: 'border-emerald-200 dark:border-emerald-800' },
  completed: { label: 'Completed', color: 'badge-sent', icon: <CheckCircle size={14} />, bgColor: 'bg-slate-50 dark:bg-slate-800', borderColor: 'border-slate-200 dark:border-slate-700' },
};

export default function StatusPage() {
  const { user } = useAuth();
  const { socket } = useSocket();
  const navigate = useNavigate();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadRequests = useCallback(async () => {
    try {
      const res = await api.get('/requests/my');
      setRequests(res.data);
    } catch {
      toast.error('Failed to load your requests');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user || user.role !== 'passenger') { navigate('/passenger-login'); return; }
    loadRequests();
  }, [user]);

  useEffect(() => {
    if (!socket) return;
    const handler = (data) => {
      setRequests((prev) =>
        prev.map((r) => r._id === data.requestId ? { ...r, status: 'sent', sentAt: new Date() } : r)
      );
      toast.success(data.message, { icon: '🚌', duration: 6000 });
    };
    socket.on('bus-sent', handler);
    return () => socket.off('bus-sent', handler);
  }, [socket]);

  if (loading) return <Loader text="Loading your requests..." />;

  const activeReq = requests.find(r => r.status === 'pending');

  return (
    <div className="max-w-2xl mx-auto px-4 py-10 animate-slide-up">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">My Requests</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Track your live bus request status</p>
        </div>
        <div className="flex gap-2">
          <button onClick={loadRequests} className="btn-secondary p-2.5" title="Refresh">
            <RefreshCw size={18} />
          </button>
          {!activeReq && (
            <button onClick={() => navigate('/request')} className="btn-primary flex items-center gap-1.5 text-sm">
              <Plus size={16} /> New Request
            </button>
          )}
        </div>
      </div>

      {activeReq && (
        <div className="mb-8">
          <LiveBusMap center={activeReq.stop} isTracking={activeReq.status === 'sent'} />
        </div>
      )}

      {requests.length === 0 ? (
        <div className="card text-center py-16">
          <AlertCircle size={40} className="text-slate-300 dark:text-slate-600 mx-auto mb-4" />
          <p className="text-slate-500 dark:text-slate-400 font-medium">No requests yet</p>
          <p className="text-sm text-slate-400 dark:text-slate-500 mt-1">Make your first bus request!</p>
          <button onClick={() => navigate('/request')} className="btn-primary mt-6 flex items-center gap-2 mx-auto">
            <MapPin size={16} /> Request a Bus
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map((req) => {
            const meta = STATUS_META[req.status] || STATUS_META.pending;
            const isPending = req.status === 'pending';
            return (
              <div
                key={req._id}
                className={`rounded-2xl border-2 p-5 transition-all ${meta.bgColor} ${meta.borderColor} ${isPending ? 'shadow-md' : 'opacity-80'}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="space-y-2 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`badge ${meta.color} flex items-center gap-1`}>
                        {meta.icon} {meta.label}
                      </span>
                      {isPending && (
                        <span className="relative flex h-2.5 w-2.5">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                          <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
                        </span>
                      )}
                    </div>

                    <div className="flex flex-col sm:flex-row gap-3 text-sm">
                      <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                        <MapPin size={14} className="text-slate-400 shrink-0" />
                        <span className="font-medium">{req.stop?.name || 'Unknown Stop'}</span>
                      </div>
                      <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
                        <Bus size={14} className="text-slate-400 shrink-0" />
                        <span>Route {req.route?.routeNumber} – {req.route?.busName}</span>
                      </div>
                    </div>

                    <div className="flex gap-4 text-xs text-slate-400 dark:text-slate-500">
                      <span><Clock size={11} className="inline mr-1" />Requested: {new Date(req.createdAt).toLocaleString()}</span>
                      {req.sentAt && <span>✅ Dispatched: {new Date(req.sentAt).toLocaleString()}</span>}
                    </div>
                  </div>
                </div>

                {req.status === 'sent' && (
                  <div className="mt-4 p-3 bg-emerald-500/10 rounded-xl flex items-center gap-2">
                    <Bus size={20} className="text-emerald-500 animate-bounce" />
                    <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-400">Your bus is on the way! Please be at the stop.</p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {activeReq && (
        <div className="mt-6 p-4 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded-2xl text-sm text-amber-700 dark:text-amber-400">
          <strong>Note:</strong> You have one active pending request. You can make a new request once it's fulfilled.
        </div>
      )}
    </div>
  );
}
