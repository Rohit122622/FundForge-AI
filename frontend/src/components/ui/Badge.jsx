import { clsx } from 'clsx';

const variantStyles = {
  brand: 'badge-brand',
  accent: 'badge-accent',
  warning: 'badge-warning',
  danger: 'badge-danger',
  neutral: 'badge-neutral',
  success: 'badge bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300',
  info: 'badge bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300',
};

export default function Badge({ children, variant = 'neutral', className = '', dot = false }) {
  return (
    <span className={clsx(variantStyles[variant], className)}>
      {dot && (
        <span className={clsx(
          'w-1.5 h-1.5 rounded-full',
          variant === 'success' && 'bg-emerald-500',
          variant === 'danger' && 'bg-red-500',
          variant === 'warning' && 'bg-amber-500',
          variant === 'brand' && 'bg-brand-500',
          variant === 'accent' && 'bg-accent-500',
          variant === 'info' && 'bg-blue-500',
          variant === 'neutral' && 'bg-surface-500',
        )} />
      )}
      {children}
    </span>
  );
}
