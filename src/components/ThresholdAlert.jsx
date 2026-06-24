import { useEffect, useRef } from 'react';
import { AlertTriangle, X, Volume2 } from 'lucide-react';

export default function ThresholdAlert({ alerts, onDismiss }) {
  const audioCtxRef = useRef(null);

  useEffect(() => {
    if (alerts.length > 0) {
      // Play an alert beep using Web Audio API (no external files needed)
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        const ctx = new AudioCtx();
        audioCtxRef.current = ctx;
        [0, 150, 300].forEach((delay) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.type = 'square';
          osc.frequency.setValueAtTime(880, ctx.currentTime + delay / 1000);
          gain.gain.setValueAtTime(0.15, ctx.currentTime + delay / 1000);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (delay + 200) / 1000);
          osc.start(ctx.currentTime + delay / 1000);
          osc.stop(ctx.currentTime + (delay + 200) / 1000);
        });
      } catch (e) {
        // Audio not supported
      }
    }
  }, [alerts.length]);

  if (!alerts.length) return null;

  return (
    <div className="fixed top-20 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
      {alerts.map((alert, i) => (
        <div
          key={i}
          className="flex items-start gap-3 p-4 bg-rose-500 text-white rounded-2xl shadow-2xl animate-slide-up border border-rose-400"
        >
          <div className="relative mt-0.5">
            <div className="absolute inset-0 bg-white/30 rounded-full animate-pulse-ring" />
            <AlertTriangle size={20} className="relative" />
          </div>
          <div className="flex-1">
            <p className="font-bold text-sm">Threshold Reached! 🚨</p>
            <p className="text-xs text-rose-100 mt-0.5">{alert.message}</p>
          </div>
          <div className="flex items-center gap-1">
            <Volume2 size={14} className="opacity-70" />
            <button onClick={() => onDismiss(i)} className="hover:bg-white/20 rounded-lg p-0.5 transition-colors">
              <X size={16} />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
