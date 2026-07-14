import { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation, useSearchParams } from 'react-router-dom';
import { Mail, Lock, ArrowRight } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';

export default function LoginPage() {
  const { login } = useAuth();
  const { showSuccess, showError } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const from = location.state?.from?.pathname || '/dashboard';

  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (searchParams.get('expired') === 'true') {
      showError('Session expired. Please log in again.');
    }
  }, [searchParams]);

  const validate = () => {
    const errs = {};
    if (!form.email) errs.email = 'Email is required';
    if (!form.password) errs.password = 'Password is required';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (loading) return;
    if (!validate()) return;

    setLoading(true);
    try {
      await login(form);
      showSuccess('Welcome back!');
      navigate(from, { replace: true });
    } catch (err) {
      setForm(prev => ({ ...prev, password: '' }));
      let msg = 'Login failed. Please try again.';
      if (err.message === "Network Error" || !err.response) {
        msg = 'Network failure. Please check your internet connection.';
      } else if (err.response?.data?.error?.message) {
        msg = err.response.data.error.message;
      } else if (err.response?.data?.message) {
        msg = err.response.data.message;
      }
      showError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50 mb-1">Welcome back</h1>
      <p className="text-surface-500 dark:text-surface-400 mb-8">Sign in to your FundForge account</p>

      <form onSubmit={handleSubmit} className="space-y-5">
        <Input
          id="login-email"
          label="Email address"
          type="email"
          icon={Mail}
          placeholder="you@startup.in"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          error={errors.email}
          required
        />
        <Input
          id="login-password"
          label="Password"
          type="password"
          icon={Lock}
          placeholder="••••••••"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          error={errors.password}
          required
        />

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="w-4 h-4 rounded border-surface-300 text-brand-600 focus:ring-brand-500" />
            <span className="text-surface-600 dark:text-surface-400">Remember me</span>
          </label>
          <Link to="/forgot-password" className="text-sm text-brand-600 hover:text-brand-700 font-medium">
            Forgot password?
          </Link>
        </div>

        <Button type="submit" loading={loading} disabled={loading} className="w-full" iconRight={ArrowRight}>
          Sign In
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-surface-500">
        Don&apos;t have an account?{' '}
        <Link to="/register" className="text-brand-600 hover:text-brand-700 font-semibold">
          Create one
        </Link>
      </p>
    </div>
  );
}
