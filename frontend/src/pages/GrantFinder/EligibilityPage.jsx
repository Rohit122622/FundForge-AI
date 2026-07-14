import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FileCheck, Loader2, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import Badge from '../../components/ui/Badge';
import eligibilityService from '../../services/eligibilityService';
import profileService from '../../services/profileService';
import { useToast } from '../../contexts/ToastContext';

export default function EligibilityPage() {
  const { showError } = useToast();
  const [grantId, setGrantId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [profile, setProfile] = useState({
    company_name: '', sector: '', stage: '', has_dpiit: false,
    founded_year: '', team_size: '', annual_revenue: '', funding_raised: '',
    state: '', city: '',
  });

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await profileService.getProfile();
        const p = res.data.data?.profile;
        if (p) {
          setProfile({
            company_name: p.company_name || '',
            sector: p.sector || p.industry || '',
            stage: p.stage || '',
            has_dpiit: !!(p.dpiit_number || p.is_dpiit_recognised),
            founded_year: p.founded_year || p.founding_year || '',
            team_size: p.team_size || '',
            annual_revenue: p.annual_revenue || '',
            funding_raised: p.funding_raised || p.total_funding_raised || '',
            state: p.state || p.state_province || '',
            city: p.city || '',
          });
        }
      } catch (err) {
        console.error('Failed to load profile:', err);
      }
    };
    fetchProfile();
  }, []);

  const handleCheck = async (e) => {
    e.preventDefault();
    if (!profile.company_name) { showError('Company name is required'); return; }
    setLoading(true);
    setResult(null);
    try {
      const data = { startup_profile: profile };
      if (grantId) data.grant_id = grantId;
      const res = await eligibilityService.checkReadiness(data);
      setResult(res.data.data);
    } catch (err) {
      showError(err.response?.data?.error?.message || 'Eligibility check failed');
    } finally {
      setLoading(false);
    }
  };

  const updateProfile = (field) => (e) => {
    const val = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
    setProfile((p) => ({ ...p, [field]: val }));
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="section-title">Eligibility Checker</h1>
        <p className="section-subtitle">Check your startup&apos;s eligibility for government grants.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <Card>
            <h2 className="text-lg font-semibold mb-4">Startup Profile</h2>
            <form onSubmit={handleCheck} className="space-y-4">
              <Input label="Company Name" value={profile.company_name} onChange={updateProfile('company_name')} required placeholder="MyStartup Pvt Ltd" />
              <div className="grid grid-cols-2 gap-4">
                <div><label className="label-text">Sector</label><select className="input-field" value={profile.sector} onChange={updateProfile('sector')}><option value="">Select</option><option value="artificial_intelligence">AI/ML</option><option value="healthtech">HealthTech</option><option value="fintech">FinTech</option><option value="edtech">EdTech</option><option value="agritech">AgriTech</option><option value="cleantech">CleanTech</option></select></div>
                <div><label className="label-text">Stage</label><select className="input-field" value={profile.stage} onChange={updateProfile('stage')}><option value="">Select</option><option value="idea">Idea</option><option value="pre_seed">Pre-Seed</option><option value="seed">Seed</option><option value="series_a">Series A</option></select></div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input label="Founded Year" type="number" value={profile.founded_year} onChange={updateProfile('founded_year')} placeholder="2023" />
                <Input label="Team Size" type="number" value={profile.team_size} onChange={updateProfile('team_size')} placeholder="8" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Input label="State" value={profile.state} onChange={updateProfile('state')} placeholder="Karnataka" />
                <Input label="City" value={profile.city} onChange={updateProfile('city')} placeholder="Bengaluru" />
              </div>
              <Input label="Grant ID (optional)" value={grantId} onChange={(e) => setGrantId(e.target.value)} placeholder="sisfs" helper="Leave empty for general readiness check" />
              <label className="flex items-center gap-2"><input type="checkbox" checked={profile.has_dpiit} onChange={updateProfile('has_dpiit')} className="w-4 h-4 rounded border-surface-300 text-brand-600" /><span className="text-sm text-surface-700 dark:text-surface-300">DPIIT Recognized</span></label>
              <Button type="submit" loading={loading} className="w-full" icon={FileCheck}>Check Eligibility</Button>
            </form>
          </Card>
        </div>

        <div>
          {loading && (
            <Card className="flex items-center justify-center py-16">
              <div className="text-center"><Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" /><p className="text-surface-500">Analyzing eligibility...</p></div>
            </Card>
          )}
          {result && !loading && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">Readiness Score</h2>
                  <Badge variant={result.readiness?.total_score >= 70 ? 'success' : result.readiness?.total_score >= 40 ? 'warning' : 'danger'}>
                    {result.readiness?.band || 'Unknown'}
                  </Badge>
                </div>
                <div className="relative h-4 rounded-full bg-surface-200 dark:bg-surface-700 overflow-hidden mb-2">
                  <motion.div
                    className="absolute inset-y-0 left-0 rounded-full gradient-bg"
                    initial={{ width: 0 }}
                    animate={{ width: `${result.readiness?.total_score || 0}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                  />
                </div>
                <p className="text-2xl font-bold text-surface-900 dark:text-surface-50">{result.readiness?.total_score || 0}/100</p>
              </Card>
              {result.eligibility_report && (
                <Card>
                  <h2 className="text-lg font-semibold mb-4 text-brand-600 dark:text-brand-400">
                    Eligibility Report — {result.eligibility_report.grant_name || result.eligibility_report.grant_id}
                  </h2>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-surface-50 dark:bg-surface-800/40">
                      <span className="text-sm font-medium text-surface-700 dark:text-surface-300">Status</span>
                      <Badge variant={result.eligibility_report.overall_eligible ? 'success' : 'danger'}>
                        {result.eligibility_report.overall_eligible ? 'Eligible' : 'Not Eligible'}
                      </Badge>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-lg bg-surface-50 dark:bg-surface-800/40">
                      <span className="text-sm font-medium text-surface-700 dark:text-surface-300">Confidence</span>
                      <Badge variant="brand">{result.eligibility_report.confidence?.toUpperCase() || 'MEDIUM'}</Badge>
                    </div>

                    <div className="flex items-center justify-between p-3 rounded-lg bg-surface-50 dark:bg-surface-800/40">
                      <span className="text-sm font-medium text-surface-700 dark:text-surface-300">Score</span>
                      <span className="font-bold text-lg text-surface-900 dark:text-surface-50">{result.eligibility_report.score || 0}/100</span>
                    </div>

                    {result.eligibility_report.explanation && (
                      <div className="p-3 rounded-lg bg-surface-50 dark:bg-surface-800/40">
                        <span className="block text-xs font-semibold text-surface-500 uppercase mb-1">Explanation</span>
                        <p className="text-sm text-surface-600 dark:text-surface-400">{result.eligibility_report.explanation}</p>
                      </div>
                    )}

                    {result.eligibility_report.action_items?.length > 0 && (
                      <div className="pt-2">
                        <span className="block text-xs font-semibold text-surface-500 uppercase mb-2">Next Steps</span>
                        <div className="space-y-2">
                          {result.eligibility_report.action_items.map((item, idx) => (
                            <div key={idx} className="flex items-start gap-2 text-sm text-surface-700 dark:text-surface-300">
                              <AlertCircle className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                              <span>{item}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </Card>
              )}
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}
