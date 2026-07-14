import { createContext, useContext, useState, useCallback } from 'react';
import grantService from '../services/grantService';

const GrantContext = createContext(null);

export function GrantProvider({ children }) {
  const [grants, setGrants] = useState([]);
  const [categories, setCategories] = useState({ sectors: [], stages: [], instruments: [] });
  const [pagination, setPagination] = useState({ page: 1, per_page: 12, total: 0, total_pages: 0 });
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({});

  const fetchGrants = useCallback(async (params = {}) => {
    setLoading(true);
    try {
      const res = await grantService.listGrants({ ...filters, ...params });
      setGrants(res.data.data || []);
      if (res.data.pagination) {
        setPagination(res.data.pagination);
      }
    } catch (err) {
      console.error('Failed to fetch grants:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const fetchCategories = useCallback(async () => {
    try {
      const res = await grantService.getCategories();
      setCategories(res.data.data || { sectors: [], stages: [], instruments: [] });
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  }, []);

  const updateFilters = useCallback((newFilters) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilters({});
  }, []);

  const value = {
    grants,
    categories,
    pagination,
    loading,
    filters,
    fetchGrants,
    fetchCategories,
    updateFilters,
    clearFilters,
    setGrants,
  };

  return <GrantContext.Provider value={value}>{children}</GrantContext.Provider>;
}

export function useGrants() {
  const context = useContext(GrantContext);
  if (!context) {
    throw new Error('useGrants must be used within a GrantProvider');
  }
  return context;
}

export default GrantContext;
