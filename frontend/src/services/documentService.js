import api from './api';

const documentService = {
  upload: (formData) =>
    api.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    }),
  listDocuments: (params = {}) => api.get('/documents', { params }),
  getDocument: (docId) => api.get(`/documents/${docId}`),
  updateDocument: (docId, data) => api.patch(`/documents/${docId}`, data),
  deleteDocument: (docId) => api.delete(`/documents/${docId}`),
  downloadDocument: (docId) =>
    api.get(`/documents/${docId}/download`, { responseType: 'blob' }),
  generatePdf: (data) => api.post('/documents/generate-pdf', data),
};

export default documentService;
