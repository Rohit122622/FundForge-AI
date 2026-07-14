import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, Trash2, Calendar, IndianRupee, Building2, ExternalLink } from 'lucide-react';
import Card from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonCard } from '../../components/ui/Skeleton';
import { useToast } from '../../contexts/ToastContext';
import grantService from '../../services/grantService';

export default function SavedGrantsPage() {
  const { showSuccess, showError } = useToast();
  const [loading, setLoading] = useState(true);
  const [savedGrants, setSavedGrants] = useState([]);

  const fetchSavedGrants = async () => {
    try {
      const res = await grantService.getSavedGrants();
      setSavedGrants(res.data.data || []);
    } catch (err) {
      console.error('Failed to fetch saved grants:', err);
      setSavedGrants([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSavedGrants();
  }, []);

  const handleRemove = async (grantSlug) => {
    try {
      await grantService.deleteSavedGrant(grantSlug);
      showSuccess('Grant removed from bookmarks');
      fetchSavedGrants();
    } catch {
      showError('Failed to remove grant');
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="section-title">Saved Grants</h1>
        <p className="section-subtitle">Your bookmarked grants for quick access.</p>
      </div>
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : savedGrants.length === 0 ? (
        <EmptyState
          icon={Bookmark}
          title="No saved grants"
          description="Browse the grant catalog and save grants you're interested in."
          actionLabel="Browse Grants"
          onAction={() => window.location.href = '/grants'}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {savedGrants.map((sg, i) => {
            const g = sg.grant || {};
            return (
              <Card key={sg.id || i} hover className="flex flex-col justify-between h-full">
                <div>
                  <div className="flex items-start justify-between mb-3">
                    <Badge variant={g.is_open ? 'success' : 'neutral'} dot>
                      {g.is_open ? 'Open' : 'Closed'}
                    </Badge>
                    <Link to={`/grants/${sg.grant_slug}`} className="text-surface-400 hover:text-brand-600 transition-colors">
                      <ExternalLink className="w-4 h-4" />
                    </Link>
                  </div>
                  <h3 className="font-semibold text-lg text-surface-900 dark:text-surface-50 mb-1">
                    {g.name || g.short_name || `Grant #${(sg.grant_slug || '').substring(0, 8)}`}
                  </h3>
                  <p className="text-sm text-surface-500 dark:text-surface-400 mb-4 line-clamp-2">
                    {g.description}
                  </p>
                  
                  <div className="space-y-2 mb-4 text-xs text-surface-500 dark:text-surface-400 border-t border-surface-100 dark:border-surface-800 pt-3">
                    <div className="flex items-center gap-2">
                      <Building2 className="w-3.5 h-3.5 text-surface-400" />
                      <span>{g.administering_body || 'N/A'}</span>
                    </div>
                    {(g.min_amount_inr || g.max_amount_inr) && (
                      <div className="flex items-center gap-2">
                        <IndianRupee className="w-3.5 h-3.5 text-surface-400" />
                        <span>
                          {g.min_amount_inr ? `₹${(g.min_amount_inr / 100000).toFixed(0)}L` : ''}
                          {g.min_amount_inr && g.max_amount_inr ? ' – ' : ''}
                          {g.max_amount_inr ? `₹${(g.max_amount_inr / 10000000).toFixed(1)}Cr` : ''}
                        </span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <Calendar className="w-3.5 h-3.5 text-surface-400" />
                      <span>Deadline: {g.deadline || 'Rolling'}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex justify-between items-center mt-auto pt-3 border-t border-surface-100 dark:border-surface-800">
                  <Link to={`/grants/${sg.grant_slug}`} className="text-sm font-semibold text-brand-600 hover:text-brand-700 transition-colors">
                    View Details
                  </Link>
                  <button
                    onClick={() => handleRemove(sg.grant_slug)}
                    className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-red-500 transition-colors"
                    title="Remove Bookmark"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
