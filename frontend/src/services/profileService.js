import api from './api';

const profileService = {
  createProfile: (data) => api.post('/profile', data),
  getProfile: () => api.get('/profile'),
  updateProfile: (data) => api.patch('/profile', data),
  deleteProfile: () => api.delete('/profile'),
  getProfileById: (profileId) => api.get(`/profile/${profileId}`),
};

export default profileService;
