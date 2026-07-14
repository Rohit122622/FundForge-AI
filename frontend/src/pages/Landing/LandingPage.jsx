import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Search, FileCheck, FileText, Zap, Shield, BarChart3, IndianRupee, Award, Users } from 'lucide-react';

const fadeUp = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.6 },
};

const stagger = {
  animate: { transition: { staggerChildren: 0.15 } },
};

const features = [
  { icon: Search, title: 'Smart Discovery', desc: 'AI-powered grant matching from 50+ Indian government schemes tailored to your startup profile.' },
  { icon: FileCheck, title: 'Eligibility Engine', desc: 'Instant eligibility checks against DPIIT, sector, stage, and documentation requirements.' },
  { icon: FileText, title: 'Proposal Generator', desc: 'Generate winning proposals with IBM Granite AI. Professional, grant-specific, and ready to submit.' },
  { icon: Shield, title: 'RAG Knowledge Base', desc: 'Retrieval-augmented generation from curated Indian grant documentation and guidelines.' },
  { icon: BarChart3, title: 'Application Tracker', desc: 'Track every application from discovery to award with FSM-powered status management.' },
  { icon: Zap, title: 'AI Fallback Chain', desc: 'IBM Granite → Gemini → Grok. Automatic failover ensures zero downtime for AI features.' },
];

const stats = [
  { value: '50+', label: 'Indian Grants', icon: Award },
  { value: '₹500Cr+', label: 'Funding Available', icon: IndianRupee },
  { value: '15+', label: 'Sectors Covered', icon: BarChart3 },
  { value: '10K+', label: 'Startups Served', icon: Users },
];

export default function LandingPage() {
  return (
    <div className="overflow-hidden">
      
      <section className="relative pt-20 pb-28 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto text-center">
          <motion.div {...fadeUp}>
            <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 text-sm font-medium mb-6">
              <Zap className="w-4 h-4" />
              Powered by IBM Granite AI
            </span>
          </motion.div>

          <motion.h1
            className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-surface-900 dark:text-surface-50 mb-6 text-balance"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            Find & Win{' '}
            <span className="gradient-text">Government Grants</span>
            <br />for Your Indian Startup
          </motion.h1>

          <motion.p
            className="text-lg sm:text-xl text-surface-500 dark:text-surface-400 max-w-2xl mx-auto mb-10 text-balance"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            Discover 50+ government grants, check eligibility instantly, and generate
            winning proposals — all powered by AI that understands Indian startup funding.
          </motion.p>

          <motion.div
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
          >
            <Link to="/register" className="btn-primary text-base px-8 py-3 shadow-glow">
              Start Finding Grants <ArrowRight className="w-5 h-5" />
            </Link>
            <Link to="/grants" className="btn-secondary text-base px-8 py-3">
              Browse Grant Catalog
            </Link>
          </motion.div>
        </div>

        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute top-0 left-1/4 w-96 h-96 rounded-full bg-brand-500/10 blur-3xl animate-float" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 rounded-full bg-accent-500/10 blur-3xl animate-float" style={{ animationDelay: '3s' }} />
        </div>
      </section>

      {/* Stats */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-y border-surface-200 dark:border-surface-800 bg-surface-100/50 dark:bg-surface-900/50">
        <div className="max-w-5xl mx-auto">
          <motion.div
            className="grid grid-cols-2 md:grid-cols-4 gap-6"
            variants={stagger}
            initial="initial"
            whileInView="animate"
            viewport={{ once: true }}
          >
            {stats.map((stat) => (
              <motion.div key={stat.label} variants={fadeUp} className="text-center">
                <div className="w-12 h-12 rounded-xl bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center mx-auto mb-3">
                  <stat.icon className="w-6 h-6 text-brand-600 dark:text-brand-400" />
                </div>
                <div className="text-2xl sm:text-3xl font-bold text-surface-900 dark:text-surface-50">{stat.value}</div>
                <div className="text-sm text-surface-500">{stat.label}</div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-surface-900 dark:text-surface-50 mb-4">
              Everything You Need to{' '}<span className="gradient-text">Win Funding</span>
            </h2>
            <p className="text-lg text-surface-500 max-w-2xl mx-auto">
              From discovery to proposal submission — FundForge AI handles the entire grant application lifecycle.
            </p>
          </div>

          <motion.div
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            variants={stagger}
            initial="initial"
            whileInView="animate"
            viewport={{ once: true }}
          >
            {features.map((feature) => (
              <motion.div
                key={feature.title}
                variants={fadeUp}
                className="glass-card-hover p-6"
              >
                <div className="w-12 h-12 rounded-xl gradient-bg flex items-center justify-center mb-4 shadow-glow">
                  <feature.icon className="w-6 h-6 text-white" />
                </div>
                <h3 className="text-lg font-semibold text-surface-900 dark:text-surface-50 mb-2">
                  {feature.title}
                </h3>
                <p className="text-surface-500 dark:text-surface-400 text-sm leading-relaxed">
                  {feature.desc}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            className="glass-card p-12 bg-gradient-to-br from-brand-600/5 to-accent-500/5 dark:from-brand-600/10 dark:to-accent-500/10"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl font-bold text-surface-900 dark:text-surface-50 mb-4">
              Ready to Find Your Next Grant?
            </h2>
            <p className="text-lg text-surface-500 mb-8 max-w-xl mx-auto">
              Join thousands of Indian startups using AI to discover and win government funding.
            </p>
            <Link to="/register" className="btn-primary text-lg px-10 py-3.5 shadow-glow">
              Get Started Free <ArrowRight className="w-5 h-5" />
            </Link>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
