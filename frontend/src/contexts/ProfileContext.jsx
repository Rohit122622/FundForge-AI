import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import profileService from '../services/profileService';
import { useAuth } from './AuthContext';

const ProfileContext = createContext(null);

export function ProfileProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = useCallback(async () => {
    if (!isAuthenticated) {
      setProfile(null);
      setLoading(false);
      return null;
    }
    setLoading(true);
    try {
      const res = await profileService.getProfile();
      const p = res.data.data?.profile;
      if (p) {
        
        const normalized = {
          ...p,
          state: p.state_province || p.state || '',
          funding_raised: p.total_funding_raised || p.funding_raised || '',
          founded_year: p.founding_year || p.founded_year || '',
          revenue: p.annual_revenue || p.revenue || '',
          PAN: p.pan_number || p.PAN || '',
          GST: p.gstin || p.GST || '',
          country: p.country || 'India',
        };
        setProfile(normalized);
        return normalized;
      } else {
        setProfile(null);
        return null;
      }
    } catch {
      setProfile(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const updateProfileState = useCallback((newProfile) => {
    if (newProfile) {
      setProfile({
        ...newProfile,
        state: newProfile.state_province || newProfile.state || '',
        funding_raised: newProfile.total_funding_raised || newProfile.funding_raised || '',
        founded_year: newProfile.founding_year || newProfile.founded_year || '',
        revenue: newProfile.annual_revenue || newProfile.revenue || '',
        PAN: newProfile.pan_number || newProfile.PAN || '',
        GST: newProfile.gstin || newProfile.GST || '',
        country: newProfile.country || 'India',
      });
    } else {
      setProfile(null);
    }
  }, []);

  const value = {
    profile,
    loading,
    fetchProfile,
    updateProfileState,
  };

  return <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>;
}

export function useProfile() {
  const context = useContext(ProfileContext);
  if (!context) {
    throw new Error('useProfile must be used within a ProfileProvider');
  }
  return context;
}

export default ProfileContext;
