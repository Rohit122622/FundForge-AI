import { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { Mail, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import authService from '../../services/authService';
import { useToast } from '../../contexts/ToastContext';
import Button from '../../components/ui/Button';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const { showSuccess, showError } = useToast();

  const [status, setStatus] = useState(token ? 'verifying' : 'info');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) return;

    const verify = async () => {
      try {
        const res = await authService.verifyEmail({ token });
        setStatus('success');
        setMessage(res.data?.message || 'Email verified successfully! You can now log in.');
        showSuccess('Email verified successfully!');
      } catch (err) {
        setStatus('error');
        setMessage(err.response?.data?.error?.message || 'Verification failed. The token may be invalid or expired.');
        showError('Email verification failed.');
      }
    };

    verify();
  }, [token, showSuccess, showError]);

  if (status === 'verifying') {
    return (
      <div className="text-center py-6">
        <Loader2 className="w-12 h-12 animate-spin text-brand-600 mx-auto mb-4" />
        <h2 className="text-xl font-bold text-surface-900 dark:text-surface-50 mb-2">Verifying your email</h2>
        <p className="text-surface-500 dark:text-surface-400">Please wait while we confirm your verification link...</p>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="text-center py-6">
        <CheckCircle2 className="w-16 h-16 text-emerald-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-50 mb-2">Verification Successful</h2>
        <p className="text-surface-600 dark:text-surface-400 mb-8">{message}</p>
        <Link to="/login">
          <Button className="w-full">Sign In</Button>
        </Link>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="text-center py-6">
        <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-50 mb-2">Verification Failed</h2>
        <p className="text-surface-600 dark:text-surface-400 mb-8">{message}</p>
        <div className="space-y-3">
          <Link to="/login">
            <Button variant="outline" className="w-full">Back to Sign In</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="text-center py-6">
      <Mail className="w-16 h-16 text-brand-600 mx-auto mb-4" />
      <h2 className="text-2xl font-bold text-surface-900 dark:text-surface-50 mb-2">Check your inbox</h2>
      <p className="text-surface-600 dark:text-surface-400 mb-8">
        We have sent a verification link to your email address. Please open it to activate your account.
      </p>
      <Link to="/login">
        <Button variant="outline" className="w-full">Back to Sign In</Button>
      </Link>
    </div>
  );
}
