import api from './api';

const eligibilityService = {
  checkEligibility: (data) => api.post('/eligibility/check', data),
  checkReadiness: (data) => api.post('/eligibility/readiness', data),
  getRecommendations: (data) => api.post('/eligibility/recommend', data),
  getDocumentRequirements: (grantId) => api.get(`/eligibility/documents/${grantId}`),
  checkDocuments: (data) => api.post('/eligibility/documents/check', data),
  getRules: () => api.get('/eligibility/rules'),
};

export default eligibilityService;
