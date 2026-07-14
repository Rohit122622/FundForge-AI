import { createContext, useContext, useState, useCallback } from 'react';
import toast from 'react-hot-toast';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const showSuccess = useCallback((message) => {
    toast.success(message, {
      duration: 4000,
      style: {
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(20px)',
        border: '1px solid var(--glass-border)',
        color: 'inherit',
        borderRadius: '12px',
        fontSize: '14px',
        fontWeight: 500,
      },
    });
  }, []);

  const showError = useCallback((message) => {
    toast.error(message, {
      duration: 5000,
      style: {
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(20px)',
        border: '1px solid var(--glass-border)',
        color: 'inherit',
        borderRadius: '12px',
        fontSize: '14px',
        fontWeight: 500,
      },
    });
  }, []);

  const showInfo = useCallback((message) => {
    toast(message, {
      duration: 4000,
      icon: 'ℹ️',
      style: {
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(20px)',
        border: '1px solid var(--glass-border)',
        color: 'inherit',
        borderRadius: '12px',
        fontSize: '14px',
        fontWeight: 500,
      },
    });
  }, []);

  const showLoading = useCallback((message) => {
    return toast.loading(message, {
      style: {
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(20px)',
        border: '1px solid var(--glass-border)',
        color: 'inherit',
        borderRadius: '12px',
        fontSize: '14px',
        fontWeight: 500,
      },
    });
  }, []);

  const dismissToast = useCallback((id) => {
    toast.dismiss(id);
  }, []);

  const value = { showSuccess, showError, showInfo, showLoading, dismissToast };

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export default ToastContext;
