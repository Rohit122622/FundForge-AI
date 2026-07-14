import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, FileCheck, FileText, Trophy, ArrowRight, TrendingUp, Bookmark, Clock } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import Card from '../../components/ui/Card';
import { SkeletonCard } from '../../components/ui/Skeleton';
import dashboardService from '../../services/dashboardService';
import trackerService from '../../services/trackerService';

const quickActions = [
  { to: '/grants', label: 'Browse Grants', icon: Search, color: 'from-brand-500 to-brand-700' },
  { to: '/eligibility', label: 'Check Eligibility', icon: FileCheck, color: 'from-accent-500 to-accent-700' },
  { to: '/proposals/generate', label: 'Generate Proposal', icon: FileText, color: 'from-purple-500 to-purple-700' },
  { to: '/tracker', label: 'Track Applications', icon: Trophy, color: 'from-amber-500 to-amber-700' },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sumRes, statRes] = await Promise.allSettled([
          dashboardService.getSummary(),
          trackerService.getStats(),
        ]);
        if (sumRes.status === 'fulfilled') setSummary(sumRes.value.data.data);
        if (statRes.status === 'fulfilled') setStats(statRes.value.data.data);
      } catch (err) {
        console.error('Dashboard fetch error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div>
      <div className="page-header">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="section-title">
            Welcome back, <span className="gradient-text">{user?.first_name || 'Founder'}</span>
          </h1>
          <p className="section-subtitle">Here&apos;s what&apos;s happening with your grant applications.</p>
        </motion.div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {loading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <Card animate delay={0}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-brand-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{summary?.catalog?.total_grants || 0}</p>
                  <p className="text-xs text-surface-500">Total Grants</p>
                </div>
              </div>
            </Card>
            <Card animate delay={0.1}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-accent-100 dark:bg-accent-900/40 flex items-center justify-center">
                  <Search className="w-5 h-5 text-accent-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{summary?.catalog?.open_grants || 0}</p>
                  <p className="text-xs text-surface-500">Open Grants</p>
                </div>
              </div>
            </Card>
            <Card animate delay={0.2}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-900/40 flex items-center justify-center">
                  <Trophy className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{stats?.active || 0}</p>
                  <p className="text-xs text-surface-500">Active Applications</p>
                </div>
              </div>
            </Card>
            <Card animate delay={0.3}>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center">
                  <Bookmark className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{stats?.awarded || 0}</p>
                  <p className="text-xs text-surface-500">Awarded</p>
                </div>
              </div>
            </Card>
          </>
        )}
      </div>

      
      <div className="mb-8">
        <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action, i) => (
            <Link key={action.to} to={action.to}>
              <Card hover animate delay={i * 0.1} className="group">
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${action.color} flex items-center justify-center mb-3 group-hover:shadow-lg transition-shadow`}>
                  <action.icon className="w-5 h-5 text-white" />
                </div>
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-surface-900 dark:text-surface-50">{action.label}</span>
                  <ArrowRight className="w-4 h-4 text-surface-400 group-hover:text-brand-600 group-hover:translate-x-1 transition-all" />
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </div>

      {/* Upcoming Deadlines */}
      {stats?.upcoming_deadlines?.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-surface-900 dark:text-surface-50 mb-4">Upcoming Deadlines</h2>
          <Card>
            <div className="divide-y divide-surface-200 dark:divide-surface-700">
              {stats.upcoming_deadlines.map((item) => (
                <div key={item.id} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                  <div className="flex items-center gap-3">
                    <Clock className="w-4 h-4 text-surface-400" />
                    <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
                      {item.grant?.title || `Grant #${item.grant_id?.substring(0, 8)}`}
                    </span>
                  </div>
                  <span className="text-sm text-surface-500">{item.deadline}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
