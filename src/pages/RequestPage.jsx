import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { MapPin, Bus, Navigation, Search, Send, RefreshCw, ChevronDown } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import Loader from '../components/Loader';
import LiveBusMap from '../components/LiveBusMap';

export default function RequestPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [stops, setStops] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [selectedStop, setSelectedStop] = useState('');
  const [selectedRoute, setSelectedRoute] = useState('');
  const [stopSearch, setStopSearch] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [searching, setSearching] = useState(false);

  // Filtered stops list based on the stop search input
  const filteredStops = useMemo(() => {
    if (!stopSearch.trim()) return stops;
    const q = stopSearch.toLowerCase();
    return stops.filter(s => s.name.toLowerCase().includes(q) || (s.address || '').toLowerCase().includes(q));
  }, [stops, stopSearch]);
  const [locating, setLocating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [userCoords, setUserCoords] = useState(null);

  useEffect(() => {
    if (!user || user.role !== 'passenger') {
      navigate('/passenger-login');
      return;
    }
    loadData();
  }, [user]);

  // Handle route filtering when selected stop changes
  useEffect(() => {
    fetchFilteredRoutes();
  }, [selectedStop]);

  const loadData = async () => {
    try {
      const [stopsRes, routesRes] = await Promise.all([
        api.get('/stops'), 
        api.get('/routes')
      ]);
      setStops(stopsRes.data);
      setRoutes(routesRes.data);
    } catch {
      toast.error('Failed to load stops/routes');
    } finally {
      setLoading(false);
    }
  };

  const fetchFilteredRoutes = async () => {
    try {
      const url = selectedStop ? `/routes?stopId=${selectedStop}` : '/routes';
      const res = await api.get(url);
      setRoutes(res.data);
      // Automatically select the first route if there's only one
      if (res.data.length === 1) {
        setSelectedRoute(res.data[0]._id);
      } else if (!res.data.find(r => r._id === selectedRoute)) {
        // Clear route selection if the previously selected route is no longer in the list
        setSelectedRoute('');
      }
    } catch {
      toast.error('Failed to update routes');
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await api.get(`/routes/search?q=${searchQuery}`);
      setRoutes(res.data);
      if (res.data.length === 0) toast.error('No routes found');
    } catch {
      toast.error('Search failed');
    } finally {
      setSearching(false);
    }
  };

  const handleGeolocate = () => {
    if (!navigator.geolocation) {
      toast.error('Geolocation not supported');
      return;
    }
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
          const { latitude, longitude } = pos.coords;
          setUserCoords({ lat: latitude, lng: longitude });
          // Find nearest stop using Euclidean distance
          let nearest = null;
          let minDist = Infinity;
          stops.forEach((stop) => {
            const d = Math.pow(stop.lat - latitude, 2) + Math.pow(stop.lng - longitude, 2);
            if (d < minDist) { minDist = d; nearest = stop; }
          });
        if (nearest) {
          setSelectedStop(nearest._id);
          toast.success(`Nearest stop: ${nearest.name}`);
        }
        setLocating(false);
      },
      (err) => {
        let msg = 'Could not get your location.';
        if (err.code === 1) msg = 'Location access denied. Please enable it in browser settings.';
        else if (err.code === 2) msg = 'Position unavailable. Try selecting manually.';
        else if (err.code === 3) msg = 'Location request timed out.';
        
        toast.error(msg, { id: 'geo-error' });
        setLocating(false);
      },
      { timeout: 10000 }
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedStop || !selectedRoute) {
      toast.error('Please select both a stop and a route');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/requests', { routeId: selectedRoute, stopId: selectedStop });
      toast.success('Request sent successfully! 🚌');
      navigate('/status');
    } catch (err) {
      const msg = err.response?.data?.message || 'Failed to send request';
      if (err.response?.status === 409) {
        toast.error(msg, { duration: 5000 });
        setTimeout(() => navigate('/status'), 2000);
      } else {
        toast.error(msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <Loader text="Loading stops and routes..." />;

  return (
    <div className="max-w-2xl mx-auto px-4 py-10 animate-slide-up">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Request a Bus</h1>
        <p className="text-slate-500 dark:text-slate-400">Select your stop and route to send a request to the depot.</p>
      </div>

      <div className="mb-8">
        <LiveBusMap 
          center={stops.find(s => s._id === selectedStop)} 
          userCoords={userCoords}
        />
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Stop selection */}
        <div className="card space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 bg-brand/10 dark:bg-brand/20 rounded-lg flex items-center justify-center">
              <MapPin size={16} className="text-brand" />
            </div>
            <h2 className="font-semibold text-slate-900 dark:text-white">Bus Stop</h2>
          </div>

          {/* Stop search filter */}
          <div className="relative">
            <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              className="input-field pl-9 text-sm"
              placeholder="Search stop by name…"
              value={stopSearch}
              onChange={(e) => setStopSearch(e.target.value)}
            />
          </div>

          <div className="relative">
            <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <select
              className="input-field appearance-none pr-10"
              value={selectedStop}
              onChange={(e) => { setSelectedStop(e.target.value); setStopSearch(''); }}
              size={stopSearch ? Math.min(filteredStops.length + 1, 6) : 1}
            >
              <option value="">— Select a bus stop —</option>
              {filteredStops.map((s) => (
                <option key={s._id} value={s._id}>{s.name}</option>
              ))}
            </select>
          </div>

          <button
            type="button"
            onClick={handleGeolocate}
            disabled={locating}
            className="w-full flex items-center justify-center gap-2 py-3 rounded-xl border-2 border-dashed border-brand/40 text-brand hover:bg-brand/5 dark:hover:bg-brand/10 transition-colors font-medium text-sm disabled:opacity-50"
          >
            {locating ? <RefreshCw size={16} className="animate-spin" /> : <Navigation size={16} />}
            {locating ? 'Detecting location...' : 'Auto-detect Nearest Stop'}
          </button>
        </div>

        {/* Route selection */}
        <div className="card space-y-4">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <Bus size={16} className="text-purple-500" />
            </div>
            <h2 className="font-semibold text-slate-900 dark:text-white">Bus Route</h2>
          </div>

          {/* Search */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                className="input-field pl-10"
                placeholder="Search route number or bus name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleSearch())}
              />
            </div>
            <button type="button" onClick={handleSearch} disabled={searching} className="btn-secondary px-4">
              {searching ? <RefreshCw size={16} className="animate-spin" /> : <Search size={16} />}
            </button>
          </div>

          <div className="relative">
            <ChevronDown size={16} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
            <select
              className="input-field appearance-none pr-10"
              value={selectedRoute}
              onChange={(e) => setSelectedRoute(e.target.value)}
            >
              <option value="">— Select a route —</option>
              {routes.map((r) => (
                <option key={r._id} value={r._id}>
                  {r.busDetails || r.busName}
                </option>
              ))}
            </select>
          </div>

          {/* Route stops preview */}
          {selectedRoute && (() => {
            const route = routes.find(r => r._id === selectedRoute);
            return route ? (
              <div className="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
                <p className="text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">Route covers:</p>
                <div className="flex flex-wrap gap-1">
                  {route.stops?.map((s, i) => (
                    <span key={i} className="text-xs px-2 py-0.5 bg-white dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-300">
                      {s.name || s}
                    </span>
                  ))}
                </div>
              </div>
            ) : null;
          })()}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={submitting || !selectedStop || !selectedRoute}
          className="btn-primary w-full flex items-center justify-center gap-2 py-4 text-base"
        >
          {submitting ? <RefreshCw size={20} className="animate-spin" /> : <Send size={20} />}
          {submitting ? 'Sending Request...' : 'Send Bus Request'}
        </button>
      </form>
    </div>
  );
}
