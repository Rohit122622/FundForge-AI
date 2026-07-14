import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Target, Loader2, Star, Building2, MapPin, Users, Calendar, IndianRupee, FileText, CheckCircle2, ChevronRight, ExternalLink } from 'lucide-react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import { useProfile } from '../../contexts/ProfileContext';
import grantService from '../../services/grantService';
import { useToast } from '../../contexts/ToastContext';

export default function RecommendationsPage() {
  const { profile, loading: profileLoading } = useProfile();
  const { showError } = useToast();
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState([]);

  const fetchRecommendations = useCallback(async () => {
    setLoading(true);
    try {
      const res = await grantService.getRecommendations({ top_n: 10 });
      setRecommendations(res.data.data?.recommendations || []);
    } catch (err) {
      showError(err.response?.data?.error?.message || 'Failed to fetch recommendations');
    } finally {
      setLoading(false);
    }
  }, [showError]);

  useEffect(() => {
    if (profile) {
      fetchRecommendations();
    }
  }, [profile, fetchRecommendations]);

  if (profileLoading) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-brand-600" /></div>;
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="section-title">Grant Recommendations</h1>
        <p className="section-subtitle">Get AI-powered grant recommendations tailored to your startup profile.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <div className="lg:col-span-1">
          <Card className="sticky top-24">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Target className="w-5 h-5 text-brand-600" /> Startup Profile
            </h2>
            {profile ? (
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm font-semibold text-surface-500 uppercase tracking-wide">Company</h3>
                  <p className="text-lg font-bold text-surface-900 dark:text-surface-50 mt-0.5">{profile.company_name}</p>
                </div>
                
                <div className="grid grid-cols-2 gap-4 border-t border-surface-100 dark:border-surface-800 pt-3">
                  <div>
                    <h3 className="text-xs font-semibold text-surface-500 uppercase tracking-wide">Sector</h3>
                    <p className="text-sm font-medium text-surface-800 dark:text-surface-200 capitalize mt-0.5">
                      {(profile.sector || '').replace(/_/g, ' ')}
                    </p>
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold text-surface-500 uppercase tracking-wide">Stage</h3>
                    <p className="text-sm font-medium text-surface-800 dark:text-surface-200 capitalize mt-0.5">
                      {(profile.stage || '').replace(/_/g, ' ')}
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4 border-t border-surface-100 dark:border-surface-800 pt-3">
                  <div>
                    <h3 className="text-xs font-semibold text-surface-500 uppercase tracking-wide">Team Size</h3>
                    <p className="text-sm font-medium text-surface-800 dark:text-surface-200 mt-0.5">{profile.team_size} employees</p>
                  </div>
                  <div>
                    <h3 className="text-xs font-semibold text-surface-500 uppercase tracking-wide">Location</h3>
                    <p className="text-sm font-medium text-surface-800 dark:text-surface-200 mt-0.5">
                      {profile.city ? `${profile.city}, ` : ''}{profile.state || 'India'}
                    </p>
                  </div>
                </div>

                <div className="border-t border-surface-100 dark:border-surface-800 pt-3">
                  <h3 className="text-xs font-semibold text-surface-500 uppercase tracking-wide">DPIIT Status</h3>
                  <Badge variant={profile.is_dpiit_recognised ? 'success' : 'warning'} className="mt-1">
                    {profile.is_dpiit_recognised ? 'DPIIT Recognised' : 'Not Recognised'}
                  </Badge>
                </div>

                <div className="pt-2">
                  <Link to="/profile" className="block w-full">
                    <Button variant="secondary" className="w-full">
                      Edit Profile Settings
                    </Button>
                  </Link>
                </div>
              </div>
            ) : (
              <div className="text-center py-6">
                <p className="text-sm text-surface-500 mb-4">Please create a startup profile first.</p>
                <Link to="/profile">
                  <Button icon={Building2}>Create Profile</Button>
                </Link>
              </div>
            )}
          </Card>
        </div>

        {/* Right Side: Recommendations list */}
        <div className="lg:col-span-2">
          {loading ? (
            <Card className="flex items-center justify-center py-16">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin text-brand-600 mx-auto mb-4" />
                <p className="text-surface-500">Scanning matching grants...</p>
              </div>
            </Card>
          ) : !profile ? (
            <EmptyState
              icon={Target}
              title="Startup profile needed"
              description="A startup profile is required to run the AI matching engine."
              actionLabel="Create Startup Profile"
              onAction={() => window.location.href = '/profile'}
            />
          ) : recommendations.length === 0 ? (
            <EmptyState
              icon={Target}
              title="No recommendations found"
              description="We scanned the catalog but didn't find any grants matching your profile criteria."
            />
          ) : (
            <div className="space-y-4">
              {recommendations.map((rec, i) => {
                const meta = rec.grant_meta || {};
                const explanation = rec.explanation || {};
                
                return (
                  <motion.div
                    key={rec.grant_id || i}
                    initial={{ opacity: 0, y: 15 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <Card hover className="p-6">
                      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-4">
                        <div>
                          <h3 className="font-bold text-lg text-surface-900 dark:text-surface-50 flex items-center gap-2">
                            {rec.grant_name}
                            {rec.short_name && (
                              <span className="text-sm font-normal text-surface-400 bg-surface-100 dark:bg-surface-800 px-2 py-0.5 rounded">
                                {rec.short_name}
                              </span>
                            )}
                          </h3>
                          <p className="text-xs text-surface-500 dark:text-surface-400 mt-1">
                            Administered by: {meta.administering_body || 'N/A'}
                          </p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <div className="flex items-center gap-1 bg-amber-50 dark:bg-amber-950/20 text-amber-600 px-3 py-1 rounded-full text-sm font-bold border border-amber-200 dark:border-amber-900/30">
                            <Star className="w-4 h-4 fill-amber-500 text-amber-500" />
                            <span>{rec.match_score || rec.composite}% Match</span>
                          </div>
                        </div>
                      </div>

                      {/* Reasoning Summary */}
                      <div className="space-y-3 mb-4 bg-surface-50 dark:bg-surface-800/20 p-3.5 rounded-lg border border-surface-150 dark:border-surface-800/40">
                        <div>
                          <span className="font-semibold text-brand-600 dark:text-brand-400 block text-[10px] tracking-wider uppercase mb-0.5">Why Recommended</span>
                          <p className="text-sm text-surface-700 dark:text-surface-300">
                            {explanation.summary || rec.reason || rec.match_reason || 'Highly recommended based on industry taxonomy and funding stage alignment.'}
                          </p>
                        </div>
                        {explanation.strengths && explanation.strengths.length > 0 && (
                          <div className="pt-2 border-t border-surface-200/50 dark:border-surface-800/50">
                            <span className="font-semibold text-brand-600 dark:text-brand-400 block text-[10px] tracking-wider uppercase mb-1.5">Key Benefits</span>
                            <div className="flex flex-wrap gap-2">
                              {explanation.strengths.map((st, idx) => {
                                const title = st && typeof st === 'object' ? st.title : st;
                                const detail = st && typeof st === 'object' ? st.detail : '';
                                const score = st && typeof st === 'object' ? st.score : null;
                                return (
                                  <span key={idx} className="text-xs bg-brand-50/50 dark:bg-brand-950/20 text-brand-700 dark:text-brand-400 px-2.5 py-1 rounded border border-brand-200/20 flex flex-col items-start gap-0.5" title={detail}>
                                    <span className="font-medium">{title}</span>
                                    {score && <span className="text-[10px] text-brand-500/80">+{score} points alignment</span>}
                                  </span>
                                );
                              })}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-5 text-xs text-surface-500 dark:text-surface-400">
                        <div className="flex items-center gap-2">
                          <IndianRupee className="w-4 h-4 text-surface-400" />
                          <div>
                            <span className="block text-[10px] text-surface-400 uppercase font-semibold">Funding Offered</span>
                            <span className="font-medium text-surface-800 dark:text-surface-200">
                              {meta.min_amount_inr ? `₹${(meta.min_amount_inr / 100000).toFixed(0)}L` : ''}
                              {meta.min_amount_inr && meta.max_amount_inr ? ' – ' : ''}
                              {meta.max_amount_inr ? `₹${(meta.max_amount_inr / 10000000).toFixed(1)}Cr` : 'Not specified'}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-surface-400" />
                          <div>
                            <span className="block text-[10px] text-surface-400 uppercase font-semibold">Deadline</span>
                            <span className="font-medium text-surface-800 dark:text-surface-200">{meta.deadline || 'Rolling'}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="w-4 h-4 text-surface-400" />
                          <div>
                            <span className="block text-[10px] text-surface-400 uppercase font-semibold">Eligibility Confidence</span>
                            <span className="font-medium text-surface-800 dark:text-surface-200 capitalize">{rec.confidence || 'High'} Match</span>
                          </div>
                        </div>
                      </div>

                      {/* CTA Buttons */}
                      <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-surface-100 dark:border-surface-800/80">
                        {meta.application_url ? (
                          <a href={meta.application_url} target="_blank" rel="noopener noreferrer" className="block">
                            <Button variant="primary" size="sm" icon={ExternalLink}>
                              Apply Now
                            </Button>
                          </a>
                        ) : (
                          <Link to={`/grants/${rec.grant_id}`} className="block">
                            <Button variant="primary" size="sm">
                              Apply (View Details)
                            </Button>
                          </Link>
                        )}
                        <Link to={`/grants/${rec.grant_id}`}>
                          <Button variant="secondary" size="sm">
                            View Details
                          </Button>
                        </Link>
                        <Link to={`/eligibility?grant_id=${rec.grant_id}`}>
                          <Button variant="outline" size="sm">
                            Check Eligibility
                          </Button>
                        </Link>
                        <Link to={`/proposals/generate?grant_id=${rec.grant_id}`}>
                          <Button variant="outline" size="sm" icon={FileText}>
                            Generate Proposal
                          </Button>
                        </Link>
                      </div>
                    </Card>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
