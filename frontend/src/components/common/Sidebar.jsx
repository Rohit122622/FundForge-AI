import { NavLink, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  LayoutDashboard, Search, Target, FileCheck, FileText,
  Bookmark, FolderOpen, BarChart3, Settings, Trophy, Zap,
} from 'lucide-react';

const sidebarLinks = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/grants', label: 'Grant Explorer', icon: Search },
  { to: '/grants/recommendations', label: 'Recommendations', icon: Target },
  { to: '/eligibility', label: 'Eligibility', icon: FileCheck },
  { to: '/proposals/generate', label: 'Proposals', icon: FileText },
  { to: '/tracker', label: 'Tracker', icon: Trophy },
  { to: '/saved-grants', label: 'Saved Grants', icon: Bookmark },
  { to: '/documents', label: 'Documents', icon: FolderOpen },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar({ collapsed = false }) {
  const location = useLocation();

  return (
    <aside
      className={clsx(
        'hidden lg:flex flex-col h-[calc(100vh-4rem)] sticky top-16',
        'border-r border-surface-200 dark:border-surface-800',
        'bg-white/50 dark:bg-surface-900/50 backdrop-blur-xl',
        collapsed ? 'w-16' : 'w-64',
        'transition-all duration-300',
      )}
    >
      <div className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {sidebarLinks.map((link) => {
          const isActive = location.pathname === link.to || location.pathname.startsWith(link.to + '/');
          return (
            <NavLink
              key={link.to}
              to={link.to}
              className={clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 shadow-sm'
                  : 'text-surface-600 dark:text-surface-400 hover:text-surface-900 dark:hover:text-surface-100 hover:bg-surface-100 dark:hover:bg-surface-800',
              )}
            >
              <link.icon className={clsx('w-5 h-5 flex-shrink-0', isActive && 'text-brand-600 dark:text-brand-400')} />
              {!collapsed && <span>{link.label}</span>}
            </NavLink>
          );
        })}
      </div>

      <div className="p-3 border-t border-surface-200 dark:border-surface-700">
        <div className={clsx(
          'rounded-xl p-3 gradient-bg text-white',
          collapsed && 'flex items-center justify-center',
        )}>
          {collapsed ? (
            <Zap className="w-5 h-5" />
          ) : (
            <>
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-4 h-4" />
                <span className="text-sm font-semibold">AI Powered</span>
              </div>
              <p className="text-xs text-white/80">IBM Granite with auto-fallback to Gemini & Grok</p>
            </>
          )}
        </div>
      </div>
    </aside>
  );
}
