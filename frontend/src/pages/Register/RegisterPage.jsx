import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, User, Building2, ArrowRight } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { useToast } from '../../contexts/ToastContext';
import Input from '../../components/ui/Input';
import Button from '../../components/ui/Button';

export default function RegisterPage() {
  const { register } = useAuth();
  const { showSuccess, showError } = useToast();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', password: '', confirm_password: '',
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const validate = () => {
    const errs = {};
    if (!form.first_name.trim()) errs.first_name = 'First name is required';
    if (!form.email.trim()) errs.email = 'Email is required';
    if (!form.password) errs.password = 'Password is required';
    else if (form.password.length < 8) errs.password = 'Password must be at least 8 characters';
    if (form.password !== form.confirm_password) errs.confirm_password = 'Passwords do not match';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const { confirm_password, ...data } = form;
      const res = await register(data);
      if (res?.data?.verify_token) {
        showSuccess('Account created and verified automatically! Please sign in.');
      } else {
        showSuccess('Account created successfully! Please verify your email.');
      }
      navigate('/login', { replace: true });
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Registration failed. Please try again.';
      showError(msg);
    } finally {
      setLoading(false);
    }
  };

  const updateField = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  return (
    <div>
      <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50 mb-1">Create your account</h1>
      <p className="text-surface-500 dark:text-surface-400 mb-8">Start finding grants for your startup</p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Input id="reg-first" label="First name" icon={User} placeholder="Rohit" value={form.first_name} onChange={updateField('first_name')} error={errors.first_name} required />
          <Input id="reg-last" label="Last name" icon={User} placeholder="Sharma" value={form.last_name} onChange={updateField('last_name')} />
        </div>
        <Input id="reg-email" label="Email" type="email" icon={Mail} placeholder="you@startup.in" value={form.email} onChange={updateField('email')} error={errors.email} required />
        <Input id="reg-password" label="Password" type="password" icon={Lock} placeholder="Min. 8 characters" value={form.password} onChange={updateField('password')} error={errors.password} required />
        <Input id="reg-confirm" label="Confirm password" type="password" icon={Lock} placeholder="••••••••" value={form.confirm_password} onChange={updateField('confirm_password')} error={errors.confirm_password} required />

        <Button type="submit" loading={loading} className="w-full" iconRight={ArrowRight}>
          Create Account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-surface-500">
        Already have an account?{' '}
        <Link to="/login" className="text-brand-600 hover:text-brand-700 font-semibold">Sign in</Link>
      </p>
    </div>
  );
}
