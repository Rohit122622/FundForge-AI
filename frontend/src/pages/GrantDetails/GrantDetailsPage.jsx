import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, ExternalLink, IndianRupee, Calendar, Building2, Target, FileCheck, FileText, Globe, FileIcon } from 'lucide-react';
import Card from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import { SkeletonCard } from '../../components/ui/Skeleton';
import { useToast } from '../../contexts/ToastContext';
import grantService from '../../services/grantService';
import eligibilityService from '../../services/eligibilityService';

export default function GrantDetailsPage() {
  const { id } = useParams();
  const { showSuccess, showError } = useToast();
  const [grant, setGrant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSaved, setIsSaved] = useState(false);
  const [savingBookmark, setSavingBookmark] = useState(false);
  const [requiredDocs, setRequiredDocs] = useState([]);

  useEffect(() => {
    const fetchGrant = async () => {
      try {
        const [res, savedRes, docsRes] = await Promise.all([
          grantService.getGrant(id),
          grantService.getSavedGrants(),
          eligibilityService.getDocumentRequirements(id).catch(() => ({ data: { data: { requirements: [] } } }))
        ]);
        const grantObj = res.data.data?.grant;
        setGrant(grantObj);
        
        const savedList = savedRes.data.data || [];
        const found = savedList.some(sg => sg.grant_slug === id || sg.grant_slug === grantObj?.id);
        setIsSaved(found);

        setRequiredDocs(docsRes.data.data?.requirements || []);
      } catch (err) {
        console.error('Failed to fetch grant:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchGrant();
  }, [id]);

  const handleToggleSave = async () => {
    setSavingBookmark(true);
    try {
      if (isSaved) {
        await grantService.deleteSavedGrant(id);
        setIsSaved(false);
        showSuccess('Grant removed from bookmarks');
      } else {
        await grantService.saveGrant(id);
        setIsSaved(true);
        showSuccess('Grant saved to bookmarks');
      }
    } catch (err) {
      showError('Failed to update bookmark');
    } finally {
      setSavingBookmark(false);
    }
  };

  if (loading) return <div className="space-y-4"><SkeletonCard /><SkeletonCard /></div>;
  if (!grant) return <div className="text-center py-16"><h2 className="text-xl font-semibold">Grant not found</h2><Link to="/grants" className="btn-primary mt-4 inline-flex">Back to Grants</Link></div>;

  return (
    <div>
      <Link to="/grants" className="inline-flex items-center gap-2 text-sm text-surface-500 hover:text-brand-600 mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Grants
      </Link>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-start justify-between mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Badge variant={grant.is_open ? 'success' : 'neutral'} dot>{grant.is_open ? 'Open' : 'Closed'}</Badge>
              {grant.instrument && <Badge variant="brand">{grant.instrument.replace(/_/g, ' ')}</Badge>}
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-surface-900 dark:text-surface-50">{grant.name}</h1>
            <p className="text-surface-500 mt-1">{grant.short_name}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <h2 className="text-lg font-semibold mb-3">Description</h2>
              <p className="text-surface-600 dark:text-surface-400 leading-relaxed">{grant.description}</p>
            </Card>

            {grant.eligibility_summary && grant.eligibility_summary.length > 0 && (
              <Card>
                <h2 className="text-lg font-semibold mb-3">Eligibility Details</h2>
                <ul className="list-disc pl-5 space-y-2 text-surface-600 dark:text-surface-400">
                  {grant.eligibility_summary.map((criteria, idx) => (
                    <li key={idx}>{criteria}</li>
                  ))}
                </ul>
              </Card>
            )}

            {requiredDocs && requiredDocs.length > 0 && (
              <Card>
                <h2 className="text-lg font-semibold mb-3">Required Documents</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {requiredDocs.map((doc, idx) => {
                    const getDocLabel = (d) => {
                      if (!d) return 'Required Document';
                      if (typeof d === 'string') {
                        return d.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                      }
                      if (typeof d === 'object') {
                        const name = d.name || d.doc_id || d.title;
                        if (typeof name === 'string') {
                          return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                        }
                      }
                      return String(d);
                    };
                    return (
                      <div key={idx} className="flex items-center gap-2 p-2.5 rounded-lg border border-surface-200 dark:border-surface-800 bg-surface-50/50 dark:bg-surface-900/50">
                        <FileIcon className="w-4 h-4 text-brand-600 dark:text-brand-400 flex-shrink-0" />
                        <span className="text-xs font-medium text-surface-700 dark:text-surface-300 truncate">{getDocLabel(doc)}</span>
                      </div>
                    );
                  })}
                </div>
              </Card>
            )}
          </div>

          <div className="space-y-4">
            <Card>
              <h3 className="text-sm font-semibold text-surface-500 mb-4 uppercase tracking-wide">Details</h3>
              <div className="space-y-4">
                <div className="flex items-center gap-3"><Building2 className="w-4 h-4 text-surface-400" /><div><p className="text-xs text-surface-500">Administering Body</p><p className="text-sm font-medium">{grant.administering_body}</p></div></div>
                {(grant.min_amount_inr || grant.max_amount_inr) && (
                  <div className="flex items-center gap-3"><IndianRupee className="w-4 h-4 text-surface-400" /><div><p className="text-xs text-surface-500">Funding Range</p><p className="text-sm font-medium">
                    {grant.min_amount_inr ? `₹${(grant.min_amount_inr / 100000).toFixed(0)}L` : ''}
                    {grant.min_amount_inr && grant.max_amount_inr ? ' – ' : ''}
                    {grant.max_amount_inr ? `₹${(grant.max_amount_inr / 10000000).toFixed(1)}Cr` : ''}
                  </p></div></div>
                )}
                {grant.deadline && (
                  <div className="flex items-center gap-3"><Calendar className="w-4 h-4 text-surface-400" /><div><p className="text-xs text-surface-500">Deadline</p><p className="text-sm font-medium">{grant.deadline}</p></div></div>
                )}
                {grant.application_url && (
                  <div className="flex items-center gap-3"><Globe className="w-4 h-4 text-surface-400" /><div><p className="text-xs text-surface-500">Website</p><a href={grant.application_url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-brand-600 hover:underline flex items-center gap-1">Visit <ExternalLink className="w-3 h-3" /></a></div></div>
                )}
              </div>
            </Card>

            <div className="space-y-2">
              <Button 
                variant={isSaved ? "secondary" : "primary"} 
                className="w-full" 
                loading={savingBookmark} 
                onClick={handleToggleSave}
              >
                {isSaved ? "Remove Saved Grant" : "Save Grant"}
              </Button>
              <Link to={`/eligibility?grant_id=${id}`} className="block"><Button className="w-full" variant="outline" icon={FileCheck}>Check Eligibility</Button></Link>
              <Link to={`/proposals/generate?grant_id=${id}`} className="block"><Button variant="outline" className="w-full" icon={FileText}>Generate Proposal</Button></Link>
              <Link to={`/tracker?grant_id=${id}`} className="block"><Button variant="outline" className="w-full" icon={Target}>Track Application</Button></Link>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
