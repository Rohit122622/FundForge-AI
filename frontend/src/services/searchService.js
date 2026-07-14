import api from './api';

const searchService = {
  search: (params = {}) => api.get('/search', { params }),
  getSuggestions: (query) => api.get('/search/suggestions', { params: { q: query } }),
};

export default searchService;
