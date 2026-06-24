import { Link } from 'react-router-dom';
import { Bus, MapPin, Bell, Zap, Shield, Clock, ArrowRight, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="animate-fade-in">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 gradient-bg opacity-10 dark:opacity-20 pointer-events-none" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-brand/10 dark:bg-brand/20 text-brand rounded-full text-sm font-medium mb-6 animate-bounce-in">
            <Zap size={14} /> Real-time Bus Request System
          </div>
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-extrabold text-slate-900 dark:text-white mb-6 leading-tight">
            Request Your Bus,
            <br />
            <span className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent">
              Go Anywhere.
            </span>
          </h1>
          <p className="text-xl text-slate-600 dark:text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Tell your depot you need a bus. Get notified when it's on the way. 
            Smart, fast, and hassle-free city transit.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            {user?.role === 'passenger' ? (
              <>
                <Link to="/request" className="btn-primary flex items-center gap-2 text-base">
                  <MapPin size={18} /> Request a Bus <ArrowRight size={16} />
                </Link>
                <Link to="/status" className="btn-secondary flex items-center gap-2 text-base">
                  <Clock size={18} /> Check My Status
                </Link>
              </>
            ) : (
              <>
                <Link to="/passenger-login" className="btn-primary flex items-center gap-2 text-base">
                  <Bus size={18} /> Request a Bus <ArrowRight size={16} />
                </Link>
                <Link to="/login" className="btn-secondary flex items-center gap-2 text-base">
                  <Shield size={18} /> Operator Login
                </Link>
              </>
            )}
          </div>

          {/* Illustration */}
          <div className="mt-16 relative">
            <div className="w-full max-w-2xl mx-auto bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
              <div className="bg-gradient-to-r from-indigo-500 to-purple-600 p-4 flex items-center gap-3">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-rose-400" />
                  <div className="w-3 h-3 rounded-full bg-amber-400" />
                  <div className="w-3 h-3 rounded-full bg-emerald-400" />
                </div>
                <span className="text-white text-sm opacity-80">SmartBus Live Dashboard</span>
              </div>
              <div className="p-6 grid grid-cols-3 gap-4">
                {[
                  { label: 'Active Requests', value: '24', color: 'text-brand' },
                  { label: 'Buses Dispatched', value: '8', color: 'text-emerald-500' },
                  { label: 'Avg Wait Time', value: '12m', color: 'text-amber-500' },
                ].map((stat) => (
                  <div key={stat.label} className="text-center p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50">
                    <div className={`text-3xl font-black ${stat.color}`}>{stat.value}</div>
                    <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">{stat.label}</div>
                  </div>
                ))}
              </div>
              <div className="px-6 pb-6 space-y-2">
                {['Central Bus Stand → Route 1A (5 waiting)', 'T. Nagar → Route 21C (3 waiting)', 'Adyar Terminal → Route 15B (7 waiting)'].map((item, i) => (
                  <div key={i} className="flex items-center justify-between px-4 py-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl text-sm">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${i === 2 ? 'bg-rose-500 animate-pulse' : 'bg-amber-400'}`} />
                      <span className="text-slate-700 dark:text-slate-300">{item}</span>
                    </div>
                    <span className={`badge ${i === 2 ? 'badge-alert' : 'badge-pending'}`}>{i === 2 ? 'Alert' : 'Pending'}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-slate-900 dark:text-white mb-3">How It Works</h2>
          <p className="text-slate-500 dark:text-slate-400">Three simple steps to get your bus</p>
        </div>
        <div className="grid sm:grid-cols-3 gap-6">
          {[
            { icon: <MapPin size={28} className="text-brand" />, step: '01', title: 'Select Your Stop', desc: 'Choose your bus stop from the list or let us detect your location automatically.' },
            { icon: <Bus size={28} className="text-purple-500" />, step: '02', title: 'Pick Your Route', desc: 'Search for your bus route number and submit your request to the depot.' },
            { icon: <Bell size={28} className="text-emerald-500" />, step: '03', title: 'Get Notified', desc: 'Receive a real-time notification the moment the bus is dispatched to your stop.' },
          ].map((f) => (
            <div key={f.step} className="card text-center hover:shadow-md transition-shadow">
              <div className="w-14 h-14 mx-auto mb-4 bg-slate-50 dark:bg-slate-800 rounded-2xl flex items-center justify-center">
                {f.icon}
              </div>
              <div className="text-xs font-bold text-slate-400 mb-2 tracking-widest uppercase">Step {f.step}</div>
              <h3 className="font-bold text-lg text-slate-900 dark:text-white mb-2">{f.title}</h3>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Feature highlights */}
      <section className="bg-slate-900 dark:bg-slate-800 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 text-center">
            {[
              { icon: <Zap size={22} className="text-amber-400" />, label: 'Real-time Updates', sub: 'Socket.io powered' },
              { icon: <Shield size={22} className="text-brand-light" />, label: 'Secure OTP Login', sub: 'Mobile verification' },
              { icon: <Bell size={22} className="text-emerald-400" />, label: 'Smart Alerts', sub: 'Threshold detection' },
              { icon: <CheckCircle size={22} className="text-pink-400" />, label: '1 Request Policy', sub: 'Fair for everyone' },
            ].map((f) => (
              <div key={f.label} className="flex flex-col items-center gap-2">
                <div className="w-10 h-10 bg-white/10 rounded-xl flex items-center justify-center">{f.icon}</div>
                <div className="font-semibold text-white">{f.label}</div>
                <div className="text-sm text-slate-400">{f.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
