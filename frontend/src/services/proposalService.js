import api from './api';

const proposalService = {
  generateProposal: (data) => api.post('/proposals/generate', data),
  generateSection: (data) => api.post('/proposals/generate/section', data),
  listProposals: (params = {}) => api.get('/proposals', { params }),
  getProposal: (proposalId) => api.get(`/proposals/${proposalId}`),
  updateProposal: (proposalId, data) => api.patch(`/proposals/${proposalId}`, data),
  deleteProposal: (proposalId) => api.delete(`/proposals/${proposalId}`),
  exportProposal: (proposalId, format = 'markdown') =>
    api.get(`/proposals/${proposalId}/export`, { params: { format } }),
  reviewProposal: (proposalId) => api.post(`/proposals/${proposalId}/review`),
  listTemplates: () => api.get('/proposals/templates'),
  checkReadiness: (data) => api.post('/proposals/readiness', data),
};

export default proposalService;
