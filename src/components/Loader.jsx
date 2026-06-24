export default function Loader({ text = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 rounded-full border-4 border-slate-200 dark:border-slate-700" />
        <div className="absolute inset-0 rounded-full border-4 border-brand border-t-transparent animate-spin" />
      </div>
      <p className="text-slate-500 dark:text-slate-400 text-sm font-medium">{text}</p>
    </div>
  );
}
