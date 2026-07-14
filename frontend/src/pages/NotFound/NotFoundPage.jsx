import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home, ArrowLeft } from 'lucide-react';
import Button from '../../components/ui/Button';

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} className="text-center max-w-md">
        <div className="text-8xl font-black gradient-text mb-4">404</div>
        <h1 className="text-2xl font-bold text-surface-900 dark:text-surface-50 mb-2">Page not found</h1>
        <p className="text-surface-500 dark:text-surface-400 mb-8">The page you're looking for doesn't exist or has been moved.</p>
        <div className="flex items-center justify-center gap-3">
          <Link to="/"><Button variant="primary" icon={Home}>Go Home</Button></Link>
          <button onClick={() => window.history.back()}><Button variant="secondary" icon={ArrowLeft}>Go Back</Button></button>
        </div>
      </motion.div>
    </div>
  );
}
