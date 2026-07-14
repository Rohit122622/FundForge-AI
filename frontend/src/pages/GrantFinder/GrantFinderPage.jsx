import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Search, Filter, ExternalLink, IndianRupee, Clock, Building2, Bookmark } from 'lucide-react';
import Card from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Pagination from '../../components/ui/Pagination';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonCard } from '../../components/ui/Skeleton';
import Input from '../../components/ui/Input';
import grantService from '../../services/grantService';
import { useToast } from '../../contexts/ToastContext';

export default function GrantFinderPage() {
  const { showSuccess, showError } = useToast();
  const [allGrants, setAllGrants] = useState([]);
  const [categories, setCategories] = useState({ sectors: [], stages: [], instruments: [] });
  const [savedGrants, setSavedGrants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({});
  const [fundingFilter, setFundingFilter] = useState('all');
  const [sortBy, setSortBy] = useState('name_asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const [grantsRes, catRes, savedRes] = await Promise.all([
          grantService.listGrants({ page: 1, per_page: 500 }),
          grantService.getCategories(),
          grantService.getSavedGrants().catch(() => ({ data: { data: [] } }))
        ]);
        setAllGrants(grantsRes.data.data || []);
        setCategories(catRes.data.data || { sectors: [], stages: [], instruments: [] });
        setSavedGrants(savedRes.data.data || []);
      } catch (err) {
        console.error('Failed to load grants explorer data:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const handleSaveToggle = async (e, grantId, isCurrentlySaved) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      if (isCurrentlySaved) {
        await grantService.deleteSavedGrant(grantId);
        setSavedGrants(prev => prev.filter(sg => sg.grant_slug !== grantId && sg.grant_id !== grantId));
        showSuccess('Grant removed from bookmarks');
      } else {
        await grantService.saveGrant(grantId);
        
        const savedRes = await grantService.getSavedGrants();
        setSavedGrants(savedRes.data.data || []);
        showSuccess('Grant saved to bookmarks');
      }
    } catch (err) {
      showError('Failed to update bookmark');
    }
  };

  const filteredAndSortedGrants = useMemo(() => {
    let result = [...allGrants];

    
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(g =>
        (g.name || '').toLowerCase().includes(q) ||
        (g.short_name || '').toLowerCase().includes(q) ||
        (g.description || '').toLowerCase().includes(q) ||
        (g.administering_body || '').toLowerCase().includes(q) ||
        (g.tags || []).some(t => t.toLowerCase().includes(q))
      );
    }

    
    if (filters.sector) {
      result = result.filter(g =>
        (g.target_sectors || []).some(sec => sec.toLowerCase() === filters.sector.toLowerCase())
      );
    }

    
    if (filters.stage) {
      result = result.filter(g =>
        (g.eligible_stages || []).some(stg => stg.toLowerCase() === filters.stage.toLowerCase())
      );
    }

    
    if (filters.instrument) {
      result = result.filter(g =>
        (g.instrument || '').toLowerCase() === filters.instrument.toLowerCase()
      );
    }

    
    if (fundingFilter !== 'all') {
      result = result.filter(g => {
        const max = g.max_amount_inr || g.typical_amount_inr || 0;
        if (fundingFilter === 'under_10l') return max < 1000000;
        if (fundingFilter === '10l_50l') return max >= 1000000 && max <= 5000000;
        if (fundingFilter === '50l_1cr') return max >= 5000000 && max <= 10000000;
        if (fundingFilter === 'above_1cr') return max > 10000000;
        return true;
      });
    }

    
    result.sort((a, b) => {
      if (sortBy === 'name_asc') return (a.name || '').localeCompare(b.name || '');
      if (sortBy === 'name_desc') return (b.name || '').localeCompare(a.name || '');
      if (sortBy === 'funding_desc') {
        const amtA = a.max_amount_inr || a.typical_amount_inr || 0;
        const amtB = b.max_amount_inr || b.typical_amount_inr || 0;
        return amtB - amtA;
      }
      if (sortBy === 'funding_asc') {
        const amtA = a.max_amount_inr || a.typical_amount_inr || 0;
        const amtB = b.max_amount_inr || b.typical_amount_inr || 0;
        return amtA - amtB;
      }
      if (sortBy === 'deadline') {
        if (!a.deadline) return 1;
        if (!b.deadline) return -1;
        return new Date(a.deadline) - new Date(b.deadline);
      }
      return 0;
    });

    return result;
  }, [allGrants, search, filters, fundingFilter, sortBy]);

  const ITEMS_PER_PAGE = 12;
  const paginatedGrants = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredAndSortedGrants.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredAndSortedGrants, currentPage]);

  const totalPages = Math.ceil(filteredAndSortedGrants.length / ITEMS_PER_PAGE);

  
  useEffect(() => {
    setCurrentPage(1);
  }, [search, filters, fundingFilter, sortBy]);

  return (
    <div>
      <div className="page-header">
        <h1 className="section-title">Grant Explorer</h1>
        <p className="section-subtitle">Discover government grants and funding opportunities for your startup.</p>
      </div>

      {/* Search & Filter Controls */}
      <div className="flex flex-col md:flex-row gap-3 mb-6">
        <div className="flex-1">
          <Input
            icon={Search}
            placeholder="Search grants by name, sector, or organization..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            className="input-field max-w-[180px]"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="name_asc">Name (A-Z)</option>
            <option value="name_desc">Name (Z-A)</option>
            <option value="funding_desc">Funding (High-Low)</option>
            <option value="funding_asc">Funding (Low-High)</option>
            <option value="deadline">Deadline (Soonest)</option>
          </select>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`btn-secondary ${showFilters ? 'bg-brand-100 dark:bg-brand-900/40 border-brand-300' : ''}`}
          >
            <Filter className="w-4 h-4" /> Filters
          </button>
        </div>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="glass-card p-4 mb-6"
        >
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div>
              <label className="label-text">Sector</label>
              <select
                className="input-field"
                value={filters.sector || ''}
                onChange={(e) => setFilters({ ...filters, sector: e.target.value || undefined })}
              >
                <option value="">All Sectors</option>
                {categories.sectors.map((s) => (
                  <option key={s} value={s}>{(s || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label-text">Stage</label>
              <select
                className="input-field"
                value={filters.stage || ''}
                onChange={(e) => setFilters({ ...filters, stage: e.target.value || undefined })}
              >
                <option value="">All Stages</option>
                {categories.stages.map((s) => (
                  <option key={s} value={s}>{(s || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label-text">Instrument</label>
              <select
                className="input-field"
                value={filters.instrument || ''}
                onChange={(e) => setFilters({ ...filters, instrument: e.target.value || undefined })}
              >
                <option value="">All Types</option>
                {categories.instruments.map((i) => (
                  <option key={i} value={i}>{(i || '').replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label-text">Funding Amount</label>
              <select
                className="input-field"
                value={fundingFilter}
                onChange={(e) => setFundingFilter(e.target.value)}
              >
                <option value="all">Any Amount</option>
                <option value="under_10l">Under ₹10 Lakhs</option>
                <option value="10l_50l">₹10 Lakhs – ₹50 Lakhs</option>
                <option value="50l_1cr">₹50 Lakhs – ₹1 Crore</option>
                <option value="above_1cr">Above ₹1 Crore</option>
              </select>
            </div>
          </div>
        </motion.div>
      )}

      {/* Results */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : filteredAndSortedGrants.length === 0 ? (
        <EmptyState
          icon={Search}
          title="No grants found"
          description="Try adjusting your search or filters to find matching grants."
          actionLabel="Reset Filters"
          onAction={() => { setSearch(''); setFilters({}); setFundingFilter('all'); setSortBy('name_asc'); }}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {paginatedGrants.map((grant, i) => {
              const isSaved = savedGrants.some(sg => 
                sg.grant_slug === grant.id || 
                sg.grant_slug === grant.slug || 
                sg.grant_id === grant.id || 
                sg.grant_id === grant.slug
              );

              return (
                <Link key={grant.id || i} to={`/grants/${grant.id || grant.short_name}`}>
                  <Card hover animate delay={i * 0.05} className="h-full group flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between mb-3">
                        <Badge variant={grant.is_open ? 'success' : 'neutral'} dot>
                          {grant.is_open ? 'Open' : 'Closed'}
                        </Badge>
                        <div className="flex items-center gap-1.5 z-10">
                          <button
                            type="button"
                            onClick={(e) => handleSaveToggle(e, grant.id || grant.slug, isSaved)}
                            className="p-1 rounded-full text-surface-400 hover:text-brand-600 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors"
                          >
                            <Bookmark className={`w-4 h-4 ${isSaved ? 'fill-brand-600 text-brand-600' : ''}`} />
                          </button>
                          <ExternalLink className="w-4 h-4 text-surface-400 group-hover:text-brand-600 transition-colors" />
                        </div>
                      </div>
                      <h3 className="font-semibold text-surface-900 dark:text-surface-50 mb-1 line-clamp-2 group-hover:text-brand-600 transition-colors">
                        {grant.name || grant.short_name}
                      </h3>
                      <p className="text-sm text-surface-500 dark:text-surface-400 mb-4 line-clamp-2">
                        {grant.description}
                      </p>
                    </div>
                  <div className="space-y-2 mt-4 pt-4 border-t border-surface-100 dark:border-surface-800">
                    <div className="flex items-center gap-2 text-xs text-surface-500">
                      <Building2 className="w-3.5 h-3.5 text-surface-400" />
                      <span className="truncate">{grant.administering_body}</span>
                    </div>
                    {(grant.min_amount_inr || grant.max_amount_inr) && (
                      <div className="flex items-center gap-2 text-xs text-surface-500">
                        <IndianRupee className="w-3.5 h-3.5 text-surface-400" />
                        <span>
                          {grant.min_amount_inr ? `₹${(grant.min_amount_inr / 100000).toFixed(0)}L` : ''}
                          {grant.min_amount_inr && grant.max_amount_inr ? ' – ' : ''}
                          {grant.max_amount_inr ? `₹${(grant.max_amount_inr / 10000000).toFixed(1)}Cr` : ''}
                        </span>
                      </div>
                    )}
                    {grant.instrument && (
                      <Badge variant="brand" className="mt-2">
                        {grant.instrument.replace(/_/g, ' ')}
                      </Badge>
                    )}
                  </div>
                </Card>
              </Link>
              );
            })}
          </div>

          {totalPages > 1 && (
            <Pagination
              page={currentPage}
              totalPages={totalPages}
              onPageChange={(p) => setCurrentPage(p)}
            />
          )}
        </>
      )}
    </div>
  );
}
