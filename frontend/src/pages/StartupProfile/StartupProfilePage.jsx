import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Building2, Save, Loader2 } from 'lucide-react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import { useToast } from '../../contexts/ToastContext';
import { useProfile } from '../../contexts/ProfileContext';
import profileService from '../../services/profileService';

export default function StartupProfilePage() {
  const { showSuccess, showError } = useToast();
  const { profile, fetchProfile, updateProfileState } = useProfile();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isNew, setIsNew] = useState(false);
  const [form, setForm] = useState({
    company_name: '', industry: '', stage: '', entity_type: '', city: '', state: '',
    founded_year: '', team_size: '', description: '', website: '', dpiit_number: '',
    annual_revenue: '', funding_raised: '', sector: '', pan_number: '', gstin: '',
    country: 'India', is_dpiit_recognised: false,
    tagline: '', problem_statement: '', solution_statement: '', impact_statement: '',
    technology_stack: '', target_market: '', funding_needed: '',
  });

  useEffect(() => {
    if (profile) {
      setForm((prev) => ({
        ...prev,
        ...profile,
        state: profile.state_province || profile.state || '',
        funding_raised: profile.total_funding_raised || profile.funding_raised || '',
        founded_year: profile.founding_year || profile.founded_year || '',
        annual_revenue: profile.annual_revenue || profile.revenue || '',
        pan_number: profile.pan_number || profile.PAN || '',
        gstin: profile.gstin || profile.GST || '',
        tagline: profile.tagline || '',
        problem_statement: profile.problem_statement || '',
        solution_statement: profile.solution_statement || '',
        impact_statement: profile.impact_statement || '',
        technology_stack: profile.technology_stack || '',
        target_market: profile.target_market || '',
        funding_needed: profile.funding_needed || '',
      }));
      setIsNew(false);
      setLoading(false);
    } else {
      setIsNew(true);
      setLoading(false);
    }
  }, [profile]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.company_name) { showError('Company name is required'); return; }
    setSaving(true);
    try {
      let res;
      if (isNew) {
        res = await profileService.createProfile(form);
        showSuccess('Profile created!');
        setIsNew(false);
      } else {
        res = await profileService.updateProfile(form);
        showSuccess('Profile updated!');
      }
      const updatedProfile = res.data.data?.profile;
      if (updatedProfile) {
        updateProfileState(updatedProfile);
      } else {
        await fetchProfile();
      }
    } catch (err) {
      showError(err.response?.data?.error?.message || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field) => (e) => setForm((p) => ({ ...p, [field]: e.target.value }));

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-brand-600" /></div>;

  return (
    <div>
      <div className="page-header"><h1 className="section-title">Startup Profile</h1><p className="section-subtitle">Your profile powers grant matching, eligibility checks, and proposal generation.</p></div>
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <form onSubmit={handleSubmit}>
          <div className="space-y-6">
            <Card>
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Building2 className="w-5 h-5 text-brand-600" /> Company Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Company Name" value={form.company_name} onChange={updateField('company_name')} required placeholder="MyStartup Pvt Ltd" />
                <div><label className="label-text">Industry</label><select className="input-field" value={form.industry} onChange={updateField('industry')}><option value="">Select</option><option value="healthtech">HealthTech</option><option value="fintech">FinTech</option><option value="edtech">EdTech</option><option value="agritech">AgriTech</option><option value="cleantech">CleanTech</option><option value="ecommerce">E-Commerce</option><option value="saas">SaaS</option><option value="deeptech">DeepTech</option></select></div>
                <div><label className="label-text">Stage</label><select className="input-field" value={form.stage} onChange={updateField('stage')}><option value="">Select</option><option value="idea">Idea</option><option value="pre_seed">Pre-Seed</option><option value="seed">Seed</option><option value="series_a">Series A</option><option value="series_b">Series B</option><option value="growth">Growth</option></select></div>
                <div><label className="label-text">Entity Type</label><select className="input-field" value={form.entity_type} onChange={updateField('entity_type')}><option value="">Select</option><option value="private_limited">Private Limited</option><option value="llp">LLP</option><option value="partnership">Partnership</option><option value="proprietorship">Proprietorship</option></select></div>
                <Input label="Founded Year" type="number" value={form.founded_year} onChange={updateField('founded_year')} placeholder="2023" />
                <Input label="Team Size" type="number" value={form.team_size} onChange={updateField('team_size')} placeholder="8" />
              </div>
              <div className="mt-4"><label className="label-text">Description</label><textarea className="input-field min-h-[100px]" value={form.description} onChange={updateField('description')} placeholder="Describe your startup, its mission, and what makes it unique..." /></div>
            </Card>
            <Card>
              <h2 className="text-lg font-semibold mb-4">Location & Legal</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Country" value={form.country} onChange={updateField('country')} placeholder="India" />
                <Input label="State" value={form.state} onChange={updateField('state')} placeholder="Karnataka" />
                <Input label="City" value={form.city} onChange={updateField('city')} placeholder="Bengaluru" />
                <Input label="DPIIT Number" value={form.dpiit_number} onChange={updateField('dpiit_number')} placeholder="DIPP12345" helper="Startup India recognition number" />
                <div className="flex items-center gap-2 mt-6">
                  <input type="checkbox" id="is_dpiit_recognised" checked={!!form.is_dpiit_recognised} onChange={(e) => setForm(p => ({ ...p, is_dpiit_recognised: e.target.checked }))} className="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500" />
                  <label htmlFor="is_dpiit_recognised" className="text-sm font-medium text-surface-700 dark:text-surface-300">DPIIT Recognised Startup</label>
                </div>
                <Input label="Website" value={form.website} onChange={updateField('website')} placeholder="https://mystartup.in" />
                <Input label="PAN Number" value={form.pan_number} onChange={updateField('pan_number')} placeholder="ABCDE1234F" />
                <Input label="GSTIN" value={form.gstin} onChange={updateField('gstin')} placeholder="29ABCDE1234F1Z5" />
              </div>
            </Card>
            <Card>
              <h2 className="text-lg font-semibold mb-4">Financial Information</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input label="Annual Revenue (₹)" type="number" value={form.annual_revenue} onChange={updateField('annual_revenue')} placeholder="500000" />
                <Input label="Funding Raised (₹)" type="number" value={form.funding_raised} onChange={updateField('funding_raised')} placeholder="2000000" />
                <Input label="Sector" value={form.sector} onChange={updateField('sector')} placeholder="artificial_intelligence" />
                <Input label="Funding Needed (₹)" type="number" value={form.funding_needed} onChange={updateField('funding_needed')} placeholder="1500000" />
              </div>
            </Card>
            <Card>
              <h2 className="text-lg font-semibold mb-4">AI Matching & Pitch Details</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                <Input label="One-line Tagline" value={form.tagline} onChange={updateField('tagline')} placeholder="AI-powered diagnostics platform" />
                <Input label="Technology Stack" value={form.technology_stack} onChange={updateField('technology_stack')} placeholder="React, Python, PyTorch, PostgreSQL" />
                <Input label="Target Market" value={form.target_market} onChange={updateField('target_market')} placeholder="Hospitals, diagnostic clinics, healthcare providers" />
              </div>
              <div className="space-y-4">
                <div>
                  <label className="label-text">Problem Statement</label>
                  <textarea className="input-field min-h-[80px]" value={form.problem_statement} onChange={updateField('problem_statement')} placeholder="What major problem does your startup solve?" />
                </div>
                <div>
                  <label className="label-text">Solution Description</label>
                  <textarea className="input-field min-h-[80px]" value={form.solution_statement} onChange={updateField('solution_statement')} placeholder="How does your product solve the problem?" />
                </div>
                <div>
                  <label className="label-text">Impact Statement</label>
                  <textarea className="input-field min-h-[80px]" value={form.impact_statement} onChange={updateField('impact_statement')} placeholder="What social, environmental, or economic impact does this have?" />
                </div>
              </div>
            </Card>
            <div className="flex justify-end"><Button type="submit" loading={saving} icon={Save}>{isNew ? 'Create Profile' : 'Save Changes'}</Button></div>
          </div>
        </form>
      </motion.div>
    </div>
  );
}
