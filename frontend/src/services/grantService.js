import api from './api';

const grantService = {
  listGrants: (params = {}) => api.get('/grants', { params }),
  getGrant: (grantId) => api.get(`/grants/${grantId}`),
  getCatalog: () => api.get('/grants/catalog'),
  getCategories: () => api.get('/grants/categories'),
  getRecommendations: (data) => api.post('/grants/recommend', data),
  quickEligibilityCheck: (data) => api.post('/grants/eligibility-check', data),
  getSavedGrants: () => api.get('/grants/saved'),
  saveGrant: (grantId) => api.post(`/grants/${grantId}/save`),
  deleteSavedGrant: (grantId) => api.delete(`/grants/${grantId}/save`),
};

export default grantService;
