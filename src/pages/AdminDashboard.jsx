import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Settings, Bus, MapPin, Plus, Pencil, Trash2, RefreshCw, X, Check } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import Loader from '../components/Loader';

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl w-full max-w-md animate-slide-up border border-slate-200 dark:border-slate-700">
        <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-slate-800">
          <h3 className="font-bold text-lg text-slate-900 dark:text-white">{title}</h3>
          <button onClick={onClose} className="w-8 h-8 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center">
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export default function AdminDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [tab, setTab] = useState('stops');
  const [stops, setStops] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // { type: 'stop'|'route', data: null|{} }
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [s, r] = await Promise.all([api.get('/stops'), api.get('/routes/all')]);
      setStops(s.data);
      setRoutes(r.data);
    } catch (err) {
      if (err.response?.status === 401) { logout(); navigate('/login'); }
      else toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user || user.role !== 'admin') { navigate('/login'); return; }
    loadAll();
  }, [user]);

  const openModal = (type, data = null) => {
    setModal({ type, data });
    if (data) {
      if (type === 'stop') setForm({ name: data.name, lat: data.lat, lng: data.lng, address: data.address || '' });
      else setForm({ routeNumber: data.routeNumber, busName: data.busName, description: data.description || '', stops: (data.stops || []).map(s => s._id || s).join(',') });
    } else {
      setForm({});
    }
  };

  const closeModal = () => { setModal(null); setForm({}); };

  const handleSaveStop = async () => {
    if (!form.name || form.lat === '' || form.lng === '') { toast.error('Name, lat, lng are required'); return; }
    setSaving(true);
    try {
      if (modal.data) {
        await api.put(`/stops/${modal.data._id}`, { ...form, lat: parseFloat(form.lat), lng: parseFloat(form.lng) });
        toast.success('Stop updated!');
      } else {
        await api.post('/stops', { ...form, lat: parseFloat(form.lat), lng: parseFloat(form.lng) });
        toast.success('Stop added!');
      }
      closeModal();
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveRoute = async () => {
    if (!form.routeNumber || !form.busName) { toast.error('Route number and bus name are required'); return; }
    setSaving(true);
    try {
      const stopsArr = form.stops ? form.stops.split(',').map(s => s.trim()).filter(Boolean) : [];
      if (modal.data) {
        await api.put(`/routes/${modal.data._id}`, { ...form, stops: stopsArr });
        toast.success('Route updated!');
      } else {
        await api.post('/routes', { ...form, stops: stopsArr });
        toast.success('Route added!');
      }
      closeModal();
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (type, id) => {
    if (!window.confirm('Are you sure you want to delete this?')) return;
    setDeletingId(id);
    try {
      await api.delete(`/${type}/${id}`);
      toast.success('Deleted successfully');
      loadAll();
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to delete');
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) return <Loader text="Loading admin dashboard..." />;

  const tabs = [
    { key: 'stops', label: 'Bus Stops', icon: <MapPin size={16} /> },
    { key: 'routes', label: 'Bus Routes', icon: <Bus size={16} /> },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 gradient-bg rounded-xl flex items-center justify-center shadow-md">
          <Settings size={20} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Admin Dashboard</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">Manage stops, routes, and system settings</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="card flex items-center gap-3 p-4">
          <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/20 rounded-xl flex items-center justify-center"><MapPin size={18} className="text-purple-500" /></div>
          <div><div className="text-2xl font-black text-slate-900 dark:text-white">{stops.length}</div><div className="text-xs text-slate-500">Bus Stops</div></div>
        </div>
        <div className="card flex items-center gap-3 p-4">
          <div className="w-10 h-10 bg-brand/10 dark:bg-brand/20 rounded-xl flex items-center justify-center"><Bus size={18} className="text-brand" /></div>
          <div><div className="text-2xl font-black text-slate-900 dark:text-white">{routes.length}</div><div className="text-xs text-slate-500">Bus Routes</div></div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl mb-6">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all ${
              tab === t.key ? 'bg-white dark:bg-slate-900 shadow-sm text-slate-900 dark:text-white' : 'text-slate-500 dark:text-slate-400'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === 'stops' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-semibold text-slate-900 dark:text-white">All Bus Stops</h2>
            <button onClick={() => openModal('stop')} className="btn-primary flex items-center gap-2 text-sm">
              <Plus size={16} /> Add Stop
            </button>
          </div>
          <div className="space-y-2">
            {stops.map(stop => (
              <div key={stop._id} className="card p-4 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-9 h-9 bg-purple-100 dark:bg-purple-900/20 rounded-xl flex items-center justify-center shrink-0"><MapPin size={16} className="text-purple-500" /></div>
                  <div className="min-w-0">
                    <p className="font-semibold text-slate-900 dark:text-white truncate">{stop.name}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {stop.address} • {stop.lat?.toFixed(4)}, {stop.lng?.toFixed(4)}
                      {stop.stopId != null && <span className="ml-1 text-slate-400">• ID: {stop.stopId}</span>}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => openModal('stop', stop)} className="w-8 h-8 bg-brand/10 hover:bg-brand/20 rounded-lg flex items-center justify-center text-brand transition-colors">
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete('stops', stop._id)}
                    disabled={deletingId === stop._id}
                    className="w-8 h-8 bg-rose-100 dark:bg-rose-900/20 hover:bg-rose-200 rounded-lg flex items-center justify-center text-rose-500 transition-colors"
                  >
                    {deletingId === stop._id ? <RefreshCw size={14} className="animate-spin" /> : <Trash2 size={14} />}
                  </button>
                </div>
              </div>
            ))}
            {stops.length === 0 && <p className="text-center text-slate-400 py-10">No stops yet. Add one!</p>}
          </div>
        </div>
      )}

      {tab === 'routes' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="font-semibold text-slate-900 dark:text-white">All Bus Routes</h2>
            <button onClick={() => openModal('route')} className="btn-primary flex items-center gap-2 text-sm">
              <Plus size={16} /> Add Route
            </button>
          </div>
          <div className="space-y-2">
            {routes.map(route => (
              <div key={route._id} className="card p-4 flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 min-w-0">
                  <div className="w-9 h-9 bg-brand/10 dark:bg-brand/20 rounded-xl flex items-center justify-center shrink-0"><Bus size={16} className="text-brand" /></div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-bold text-slate-900 dark:text-white">{route.busDetails || route.busName}</p>
                      {!route.isActive && <span className="badge bg-slate-100 text-slate-500 dark:bg-slate-700">Inactive</span>}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">{route.description}</p>
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {(route.stops || []).map((s, i) => (
                        <span key={i} className="text-xs bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded-md text-slate-600 dark:text-slate-300">{s.name || s}</span>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button onClick={() => openModal('route', route)} className="w-8 h-8 bg-brand/10 hover:bg-brand/20 rounded-lg flex items-center justify-center text-brand transition-colors">
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete('routes', route._id)}
                    disabled={deletingId === route._id}
                    className="w-8 h-8 bg-rose-100 dark:bg-rose-900/20 hover:bg-rose-200 rounded-lg flex items-center justify-center text-rose-500 transition-colors"
                  >
                    {deletingId === route._id ? <RefreshCw size={14} className="animate-spin" /> : <Trash2 size={14} />}
                  </button>
                </div>
              </div>
            ))}
            {routes.length === 0 && <p className="text-center text-slate-400 py-10">No routes yet. Add one!</p>}
          </div>
        </div>
      )}

      {/* Modals */}
      {modal?.type === 'stop' && (
        <Modal title={modal.data ? 'Edit Bus Stop' : 'Add Bus Stop'} onClose={closeModal}>
          <div className="space-y-3">
            <input className="input-field" placeholder="Stop name *" value={form.name || ''} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            <input className="input-field" placeholder="Address" value={form.address || ''} onChange={e => setForm(f => ({ ...f, address: e.target.value }))} />
            <div className="grid grid-cols-2 gap-2">
              <input className="input-field" placeholder="Latitude *" type="number" step="any" value={form.lat ?? ''} onChange={e => setForm(f => ({ ...f, lat: e.target.value }))} />
              <input className="input-field" placeholder="Longitude *" type="number" step="any" value={form.lng ?? ''} onChange={e => setForm(f => ({ ...f, lng: e.target.value }))} />
            </div>
            <div className="flex gap-2 pt-2">
              <button onClick={closeModal} className="btn-secondary flex-1">Cancel</button>
              <button onClick={handleSaveStop} disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2">
                {saving ? <RefreshCw size={16} className="animate-spin" /> : <Check size={16} />}
                {saving ? 'Saving...' : 'Save Stop'}
              </button>
            </div>
          </div>
        </Modal>
      )}

      {modal?.type === 'route' && (
        <Modal title={modal.data ? 'Edit Route' : 'Add Route'} onClose={closeModal}>
          <div className="space-y-3">
            <input className="input-field" placeholder="Route number (e.g. 1A) *" value={form.routeNumber || ''} onChange={e => setForm(f => ({ ...f, routeNumber: e.target.value }))} />
            <input className="input-field" placeholder="Bus name *" value={form.busName || ''} onChange={e => setForm(f => ({ ...f, busName: e.target.value }))} />
            <input className="input-field" placeholder="Description" value={form.description || ''} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            <div>
              <label className="text-xs text-slate-500 dark:text-slate-400 mb-1 block">Stops (comma-separated Stop IDs)</label>
              <select multiple className="input-field h-28" onChange={(e) => {
                const selected = Array.from(e.target.selectedOptions, o => o.value);
                setForm(f => ({ ...f, stops: selected.join(',') }));
              }}>
                {stops.map(s => <option key={s._id} value={s._id} selected={(form.stops || '').includes(s._id)}>{s.name}</option>)}
              </select>
              <p className="text-xs text-slate-400 mt-1">Hold Ctrl/Cmd to select multiple stops</p>
            </div>
            <div className="flex gap-2 pt-2">
              <button onClick={closeModal} className="btn-secondary flex-1">Cancel</button>
              <button onClick={handleSaveRoute} disabled={saving} className="btn-primary flex-1 flex items-center justify-center gap-2">
                {saving ? <RefreshCw size={16} className="animate-spin" /> : <Check size={16} />}
                {saving ? 'Saving...' : 'Save Route'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
