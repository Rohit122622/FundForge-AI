import { Link } from 'react-router-dom';
import { Zap, Github, Twitter, Mail } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="border-t border-surface-200 dark:border-surface-800 bg-white/50 dark:bg-surface-950/50 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg gradient-bg flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold gradient-text">FundForge AI</span>
            </div>
            <p className="text-surface-500 dark:text-surface-400 text-sm max-w-sm">
              AI-powered grant discovery, eligibility checking, and proposal generation for Indian startups. 
              Powered by IBM Granite AI.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-surface-900 dark:text-surface-100 mb-3">Product</h3>
            <ul className="space-y-2">
              <li><Link to="/grants" className="text-sm text-surface-500 hover:text-brand-600 transition-colors">Grant Explorer</Link></li>
              <li><Link to="/eligibility" className="text-sm text-surface-500 hover:text-brand-600 transition-colors">Eligibility Checker</Link></li>
              <li><Link to="/proposals/generate" className="text-sm text-surface-500 hover:text-brand-600 transition-colors">Proposal Generator</Link></li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-surface-900 dark:text-surface-100 mb-3">Connect</h3>
            <div className="flex gap-3">
              <a href="#" className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 text-surface-500 hover:text-surface-900 dark:hover:text-surface-100 transition-colors">
                <Github className="w-5 h-5" />
              </a>
              <a href="#" className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 text-surface-500 hover:text-surface-900 dark:hover:text-surface-100 transition-colors">
                <Twitter className="w-5 h-5" />
              </a>
              <a href="#" className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800 text-surface-500 hover:text-surface-900 dark:hover:text-surface-100 transition-colors">
                <Mail className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>

        <div className="mt-8 pt-8 border-t border-surface-200 dark:border-surface-700">
          <p className="text-center text-sm text-surface-400">
            © {new Date().getFullYear()} FundForge AI. Built for Indian Startups.
          </p>
        </div>
      </div>
    </footer>
  );
}
