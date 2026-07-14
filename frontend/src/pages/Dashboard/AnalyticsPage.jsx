import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BarChart3, TrendingUp, Award, Clock, CheckCircle2, XCircle, Send, PieChart as PieIcon, Briefcase } from 'lucide-react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonCard } from '../../components/ui/Skeleton';
import dashboardService from '../../services/dashboardService';
import trackerService from '../../services/trackerService';
import { useProfile } from '../../contexts/ProfileContext';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899'];

export default function AnalyticsPage() {
  const { profile } = useProfile();
  const [stats, setStats] = useState(null);
  const [apps, setApps] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, listRes] = await Promise.allSettled([
          trackerService.getStats(),
          trackerService.listApplications({ limit: 1000 }),
        ]);

        if (statsRes.status === 'fulfilled') {
          setStats(statsRes.value.data.data);
        }
        if (listRes.status === 'fulfilled') {
          const fetchedApps = listRes.value.data.data?.items || listRes.value.data.data || [];
          setApps(fetchedApps);
        }
      } catch (err) {
        console.error('Analytics fetch error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const formatCurrency = (val) => {
    if (!val) return '₹0';
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(2)} L`;
    return `₹${val.toLocaleString('en-IN')}`;
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      </div>
    );
  }

  
  const totalApps = apps.length;
  const activeApps = apps.filter(app => ['saved', 'researching', 'in_progress', 'submitted', 'under_review'].includes(app.status)).length;
  const submittedApps = apps.filter(app => app.status === 'submitted' || app.status === 'under_review').length;
  const approvedApps = apps.filter(app => app.status === 'awarded').length;
  const rejectedApps = apps.filter(app => app.status === 'rejected').length;
  
  const completedCount = approvedApps + rejectedApps;
  const successRate = completedCount > 0 ? ((approvedApps / completedCount) * 100).toFixed(1) : '0.0';
  const fundingSecured = stats?.total_funding_secured || 0;

  
  const monthlyCounts = {};
  apps.forEach(app => {
    const dateStr = app.created_at || app.updated_at;
    if (dateStr) {
      const month = dateStr.substring(0, 7); 
      monthlyCounts[month] = (monthlyCounts[month] || 0) + 1;
    }
  });
  
  const appsByMonthData = Object.entries(monthlyCounts)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, count]) => ({ month, count }));

  
  const resolveGrantName = (app) => {
    const rawName = app.grant?.title || app.grant?.name;
    if (rawName && !rawName.startsWith('Grant ID:') && !/^[0-9a-fA-F-]{36}$/.test(rawName)) {
      return rawName;
    }
    
    const slug = (app.grant?.slug || app.grant_id || '').toLowerCase();
    if (slug.includes('sisfs') || slug.includes('seed_fund') || slug.includes('seed-fund')) {
      return 'Startup India Seed Fund';
    }
    if (slug.includes('birac') || slug.includes('big')) {
      return 'BIRAC BIG Scheme';
    }
    if (slug.includes('msme') || slug.includes('idea')) {
      return 'MSME Idea Hackathon';
    }
    if (slug.includes('samridh')) {
      return 'SAMRIDH Accelerator';
    }
    if (slug.includes('sis') || slug.includes('nidhi')) {
      return 'NIDHI Prayas Scheme';
    }
    return rawName || `Grant #${(app.grant_id || '').substring(0, 8)}`;
  };

  const grantCounts = {};
  apps.forEach(app => {
    const name = resolveGrantName(app);
    grantCounts[name] = (grantCounts[name] || 0) + 1;
  });
  const grantDistributionData = Object.entries(grantCounts).map(([name, value]) => ({ name, value }));

  
  const sectorCounts = {};
  apps.forEach(app => {
    let sector = app.grant?.vertical || app.grant?.category || '';
    if (!sector || sector.toLowerCase() === 'general') {
      sector = profile?.sector || profile?.industry || 'Deep Tech';
    }
    const cleanSector = sector.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    sectorCounts[cleanSector] = (sectorCounts[cleanSector] || 0) + 1;
  });
  const sectorDistributionData = Object.entries(sectorCounts).map(([name, value]) => ({ name, value }));

  const statusData = [
    { name: 'Active', value: activeApps },
    { name: 'Submitted', value: submittedApps },
    { name: 'Approved', value: approvedApps },
    { name: 'Rejected', value: rejectedApps }
  ].filter(d => d.value > 0);

  const fundingData = stats?.funding_by_month || [];

  if (totalApps === 0) {
    return (
      <div>
        <div className="page-header">
          <h1 className="section-title">Analytics</h1>
          <p className="section-subtitle">Real-time insights into your grant applications progress and funding pipeline.</p>
        </div>
        <EmptyState
          icon={BarChart3}
          title="No analytics data available"
          description="Track your first grant application to unlock advanced real-time pipeline charts, monthly breakdowns, and success ratios."
          actionLabel="Go to Grant Explorer"
          onAction={() => window.location.href = '/grants'}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="section-title">Analytics Dashboard</h1>
        <p className="section-subtitle">Real-time insights into your grant applications progress and funding pipeline.</p>
      </div>

      {/* Metrics Row 1 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card animate delay={0}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{totalApps}</p>
              <p className="text-xs text-surface-500 font-medium">Total Applications</p>
            </div>
          </div>
        </Card>
        
        <Card animate delay={0.05}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
              <Clock className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{activeApps}</p>
              <p className="text-xs text-surface-500 font-medium">Active Pipeline</p>
            </div>
          </div>
        </Card>

        <Card animate delay={0.1}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center">
              <Award className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">
                {formatCurrency(fundingSecured)}
              </p>
              <p className="text-xs text-surface-500 font-medium">Funding Secured</p>
            </div>
          </div>
        </Card>

        <Card animate delay={0.15}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{successRate}%</p>
              <p className="text-xs text-surface-500 font-medium">Success Rate</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Metrics Row 2: Breakdowns */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <Card className="bg-surface-50/50 dark:bg-surface-900/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Send className="w-4 h-4 text-indigo-500" />
              <span className="text-xs font-semibold text-surface-500 uppercase">Submitted</span>
            </div>
            <Badge variant="indigo">{submittedApps}</Badge>
          </div>
        </Card>
        <Card className="bg-surface-50/50 dark:bg-surface-900/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
              <span className="text-xs font-semibold text-surface-500 uppercase">Approved</span>
            </div>
            <Badge variant="success">{approvedApps}</Badge>
          </div>
        </Card>
        <Card className="bg-surface-50/50 dark:bg-surface-900/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-500" />
              <span className="text-xs font-semibold text-surface-500 uppercase">Rejected</span>
            </div>
            <Badge variant="danger">{rejectedApps}</Badge>
          </div>
        </Card>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Applications By Month Chart */}
        {appsByMonthData.length > 0 && (
          <Card>
            <h2 className="text-sm font-semibold mb-4 text-surface-800 dark:text-surface-200">Applications Submitted by Month</h2>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={appsByMonthData}>
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                <Tooltip formatter={(val) => [val, 'Applications']} />
                <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        )}

        {/* Monthly Funding Chart */}
        {fundingData.length > 0 && (
          <Card>
            <h2 className="text-sm font-semibold mb-4 text-surface-800 dark:text-surface-200">Funding Secured by Month</h2>
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={fundingData}>
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tickFormatter={(val) => val >= 10000000 ? `${(val/10000000).toFixed(0)}Cr` : val >= 100000 ? `${(val/100000).toFixed(0)}L` : val} tick={{ fontSize: 10 }} />
                <Tooltip formatter={(val) => [formatCurrency(val), 'Secured']} />
                <Bar dataKey="amount" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        )}

        {/* Sector Distribution Chart */}
        {sectorDistributionData.length > 0 && (
          <Card>
            <h2 className="text-sm font-semibold mb-4 text-surface-800 dark:text-surface-200">Sector Distribution</h2>
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <div className="w-full sm:w-1/2">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={sectorDistributionData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={4} dataKey="value">
                      {sectorDistributionData.map((_, index) => (
                        <Cell key={index} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="w-full sm:w-1/2 flex flex-wrap sm:flex-col gap-2">
                {sectorDistributionData.map((item, i) => (
                  <div key={item.name} className="flex items-center gap-2 text-xs text-surface-600 dark:text-surface-400">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                    <span className="truncate font-medium">{item.name}:</span>
                    <span className="font-bold text-surface-800 dark:text-surface-200">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        )}

        {/* Grant Distribution Chart */}
        {grantDistributionData.length > 0 && (
          <Card>
            <h2 className="text-sm font-semibold mb-4 text-surface-800 dark:text-surface-200">Grant Distribution</h2>
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <div className="w-full sm:w-1/2">
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={grantDistributionData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={4} dataKey="value">
                      {grantDistributionData.map((_, index) => (
                        <Cell key={index} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="w-full sm:w-1/2 flex flex-wrap sm:flex-col gap-2">
                {grantDistributionData.map((item, i) => (
                  <div key={item.name} className="flex items-center gap-2 text-xs text-surface-600 dark:text-surface-400">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                    <span className="truncate font-medium max-w-[120px] inline-block">{item.name}:</span>
                    <span className="font-bold text-surface-800 dark:text-surface-200">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
