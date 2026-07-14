import api from './api';

const dashboardService = {
  getSummary: () => api.get('/dashboard/summary'),
  getStats: () => api.get('/dashboard/stats'),
  getCatalogSummary: () => api.get('/dashboard/catalog/summary'),
};

export default dashboardService;
