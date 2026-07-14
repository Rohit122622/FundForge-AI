import api from './api';

const ragService = {
  retrieve: (data) => api.post('/rag/retrieve', data),
  retrieveForProfile: (data) => api.post('/rag/retrieve/profile', data),
  askQuestion: (data) => api.post('/rag/qa', data),
  getHealth: () => api.get('/rag/health'),
};

export default ragService;
