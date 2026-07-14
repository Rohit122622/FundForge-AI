import { clsx } from 'clsx';
import { motion } from 'framer-motion';

export default function Card({ 
  children, 
  className = '', 
  hover = false, 
  padding = 'p-6',
  animate = false,
  delay = 0,
  onClick,
  ...props 
}) {
  const Component = animate ? motion.div : 'div';
  const animateProps = animate ? {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.4, delay, ease: 'easeOut' },
  } : {};

  return (
    <Component
      className={clsx(
        hover ? 'glass-card-hover cursor-pointer' : 'glass-card',
        padding,
        className,
      )}
      onClick={onClick}
      {...animateProps}
      {...props}
    >
      {children}
    </Component>
  );
}
