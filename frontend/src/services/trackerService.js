import api from './api';

const trackerService = {
  createApplication: (data) => api.post('/tracker', data),
  listApplications: (params = {}) => api.get('/tracker', { params }),
  getApplication: (appId) => api.get(`/tracker/${appId}`),
  updateApplication: (appId, data) => api.patch(`/tracker/${appId}`, data),
  transitionStatus: (appId, data) => api.post(`/tracker/${appId}/transition`, data),
  deleteApplication: (appId) => api.delete(`/tracker/${appId}`),
  getStats: () => api.get('/tracker/stats'),
};

export default trackerService;
