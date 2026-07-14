import { Outlet } from 'react-router-dom';
import { Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useTheme } from '../contexts/ThemeContext';
import { Sun, Moon } from 'lucide-react';

export default function AuthLayout() {
  const { isDark, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-surface-50 via-brand-50/30 to-accent-50/20 dark:from-surface-950 dark:via-surface-900 dark:to-surface-950 p-4">
      <div className="absolute top-4 right-4">
        <button onClick={toggleTheme} className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors">
          {isDark ? <Sun className="w-5 h-5 text-amber-500" /> : <Moon className="w-5 h-5 text-surface-600" />}
        </button>
      </div>

      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 group">
            <div className="w-10 h-10 rounded-xl gradient-bg flex items-center justify-center shadow-glow group-hover:shadow-glow transition-shadow">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <span className="text-2xl font-bold gradient-text">FundForge AI</span>
          </Link>
        </div>
        <div className="glass-card p-8">
          <Outlet />
        </div>
      </div>

      <div className="fixed inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-1/2 -left-1/2 w-full h-full rounded-full bg-brand-500/5 blur-3xl animate-float" />
        <div className="absolute -bottom-1/2 -right-1/2 w-full h-full rounded-full bg-accent-500/5 blur-3xl animate-float" style={{ animationDelay: '3s' }} />
      </div>
    </div>
  );
}
