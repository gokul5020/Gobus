import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Phone, KeyRound, Bus, ArrowRight, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';

export default function PassengerLoginPage() {
  const [step, setStep] = useState(1); // 1 = enter mobile, 2 = enter OTP
  const [mobile, setMobile] = useState('');
  const [otp, setOtp] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSendOtp = async (e) => {
    e.preventDefault();
    if (!/^[0-9]{10}$/.test(mobile)) {
      toast.error('Enter a valid 10-digit mobile number');
      return;
    }
    setLoading(true);
    try {
      await api.post('/auth/send-otp', { mobile });
      toast.success('OTP sent!');
      setStep(2);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (!otp || otp.length !== 6) {
      toast.error('Enter the 6-digit OTP');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/auth/verify-otp', { mobile, otp });
      login(res.data.token, { ...res.data.passenger, role: 'passenger' });
      toast.success('Verified! Welcome aboard 🎉');
      navigate('/request');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Invalid OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-64px)] flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md animate-slide-up">
        {/* Card */}
        <div className="card text-center">
          {/* Icon */}
          <div className="w-16 h-16 gradient-bg rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
            <Bus className="text-white w-8 h-8" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white mb-1">Passenger Login</h1>
          <p className="text-slate-500 dark:text-slate-400 text-sm mb-8">
            {step === 1 ? 'Enter your mobile number to get an OTP' : `OTP sent to +91 ${mobile}`}
          </p>

          {/* Step indicators */}
          <div className="flex items-center justify-center gap-3 mb-8">
            <StepDot num={1} active={step >= 1} />
            <div className={`h-px flex-1 max-w-12 transition-colors ${step === 2 ? 'bg-brand' : 'bg-slate-200 dark:bg-slate-700'}`} />
            <StepDot num={2} active={step >= 2} />
          </div>

          {step === 1 ? (
            <form onSubmit={handleSendOtp} className="space-y-4">
              <div className="relative">
                <Phone size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="tel"
                  className="input-field pl-11"
                  placeholder="10-digit mobile number"
                  value={mobile}
                  onChange={(e) => setMobile(e.target.value.replace(/\D/g, '').slice(0, 10))}
                  maxLength={10}
                  required
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
                {loading ? <RefreshCw size={18} className="animate-spin" /> : <ArrowRight size={18} />}
                {loading ? 'Sending OTP...' : 'Send OTP'}
              </button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <div className="relative">
                <KeyRound size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  className="input-field pl-11 tracking-[0.4em] text-center text-lg font-semibold"
                  placeholder="_ _ _ _ _ _"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  maxLength={6}
                  required
                  autoFocus
                />
              </div>
              <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
                {loading ? <RefreshCw size={18} className="animate-spin" /> : <KeyRound size={18} />}
                {loading ? 'Verifying...' : 'Verify OTP'}
              </button>
              <button
                type="button"
                onClick={() => { setStep(1); setOtp(''); }}
                className="w-full text-sm text-slate-500 hover:text-brand transition-colors"
              >
                ← Change number
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

function StepDot({ num, active }) {
  return (
    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${active ? 'bg-brand text-white' : 'bg-slate-200 text-slate-500 dark:bg-slate-700 dark:text-slate-400'
      }`}>
      {num}
    </div>
  );
}
