import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Bus, Sun, Moon, LogOut, LayoutDashboard, Home, MapPin, Settings } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';

export default function Navbar() {
  const { dark, toggle } = useTheme();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  return (
    <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-9 h-9 gradient-bg rounded-xl flex items-center justify-center shadow-md group-hover:scale-105 transition-transform">
              <Bus className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-slate-900 dark:text-white">
              Smart<span className="text-brand">Bus</span>
            </span>
          </Link>

          {/* Nav links */}
          <div className="hidden md:flex items-center gap-1">
            <NavLink to="/" active={pathname === '/'} icon={<Home size={16} />}>Home</NavLink>
            {user?.role === 'passenger' && (
              <>
                <NavLink to="/request" active={pathname === '/request'} icon={<MapPin size={16} />}>Request Bus</NavLink>
                <NavLink to="/status" active={pathname === '/status'} icon={<Bus size={16} />}>My Status</NavLink>
              </>
            )}
            {user?.role === 'depot' && (
              <NavLink to="/depot" active={pathname === '/depot'} icon={<LayoutDashboard size={16} />}>Depot</NavLink>
            )}
            {user?.role === 'admin' && (
              <>
                <NavLink to="/admin" active={pathname === '/admin'} icon={<Settings size={16} />}>Admin</NavLink>
                <NavLink to="/depot" active={pathname === '/depot'} icon={<LayoutDashboard size={16} />}>Dashboard</NavLink>
              </>
            )}
          </div>

          {/* Right actions */}
          <div className="flex items-center gap-2">
            {/* User badge */}
            {user && (
              <span className="hidden sm:block text-xs font-medium px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                {user.role === 'passenger' ? `📱 ${user.mobile}` : `👤 ${user.username || user.name}`}
              </span>
            )}

            {/* Dark mode toggle */}
            <button
              onClick={toggle}
              className="w-9 h-9 rounded-xl flex items-center justify-center hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              aria-label="Toggle dark mode"
            >
              {dark ? <Sun size={18} className="text-amber-400" /> : <Moon size={18} className="text-slate-600" />}
            </button>

            {/* Login / Logout */}
            {user ? (
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
              >
                <LogOut size={16} />
                <span className="hidden sm:block">Logout</span>
              </button>
            ) : (
              <div className="flex gap-2">
                <Link to="/passenger-login" className="btn-primary text-sm py-2 px-4">Request Bus</Link>
                <Link to="/login" className="btn-secondary text-sm py-2 px-4">Operator Login</Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile bottom nav for passenger */}
      {user?.role === 'passenger' && (
        <div className="md:hidden flex border-t border-slate-200 dark:border-slate-800">
          <MobileNavLink to="/" active={pathname === '/'} icon={<Home size={20} />} label="Home" />
          <MobileNavLink to="/request" active={pathname === '/request'} icon={<MapPin size={20} />} label="Request" />
          <MobileNavLink to="/status" active={pathname === '/status'} icon={<Bus size={20} />} label="Status" />
        </div>
      )}
    </nav>
  );
}

function NavLink({ to, active, icon, children }) {
  return (
    <Link
      to={to}
      className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium transition-colors ${
        active
          ? 'bg-brand/10 text-brand dark:bg-brand/20'
          : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
      }`}
    >
      {icon}
      {children}
    </Link>
  );
}

function MobileNavLink({ to, active, icon, label }) {
  return (
    <Link
      to={to}
      className={`flex-1 flex flex-col items-center justify-center py-2 text-xs font-medium transition-colors ${
        active ? 'text-brand' : 'text-slate-500 dark:text-slate-400'
      }`}
    >
      {icon}
      <span className="mt-0.5">{label}</span>
    </Link>
  );
}
