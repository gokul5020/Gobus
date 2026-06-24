import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';

// Context
import { AuthProvider, useAuth } from './context/AuthContext';
import { SocketProvider } from './context/SocketContext';
import { ThemeProvider } from './context/ThemeContext';

// Components
import Navbar from './components/Navbar';
import Loader from './components/Loader';

// Pages
import HomePage from './pages/HomePage';
import PassengerLoginPage from './pages/PassengerLoginPage';
import RequestPage from './pages/RequestPage';
import StatusPage from './pages/StatusPage';
import LoginPage from './pages/LoginPage';
import DepotDashboard from './pages/DepotDashboard';
import AdminDashboard from './pages/AdminDashboard';

function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();

  if (loading) return <Loader text="Checking authentication..." />;
  if (!user) return <Navigate to={allowedRoles.includes('passenger') ? '/passenger-login' : '/login'} />;
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/" />;

  return children;
}

function AppContent() {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
      <Navbar />
      <main className="pb-16 md:pb-0"> {/* Mobile padding for bottom nav */}
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<HomePage />} />
          <Route path="/passenger-login" element={<PassengerLoginPage />} />
          <Route path="/login" element={<LoginPage />} />

          {/* Passenger Routes */}
          <Route path="/request" element={<ProtectedRoute allowedRoles={['passenger']}><RequestPage /></ProtectedRoute>} />
          <Route path="/status" element={<ProtectedRoute allowedRoles={['passenger']}><StatusPage /></ProtectedRoute>} />

          {/* Operator Routes */}
          <Route path="/depot" element={<ProtectedRoute allowedRoles={['depot', 'admin']}><DepotDashboard /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute allowedRoles={['admin']}><AdminDashboard /></ProtectedRoute>} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
      <Toaster 
        position="top-center" 
        toastOptions={{ 
          className: 'dark:bg-slate-800 dark:text-white border border-slate-200 dark:border-slate-700 shadow-xl rounded-xl',
          duration: 4000
        }} 
      />
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <SocketProvider>
          <BrowserRouter>
            <AppContent />
          </BrowserRouter>
        </SocketProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
