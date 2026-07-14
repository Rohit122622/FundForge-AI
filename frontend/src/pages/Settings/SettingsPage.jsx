import { useState } from 'react';
import { motion } from 'framer-motion';
import { Settings as SettingsIcon, Moon, Sun, Bell, Shield, Palette } from 'lucide-react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import { useTheme } from '../../contexts/ThemeContext';
import { useToast } from '../../contexts/ToastContext';

export default function SettingsPage() {
  const { theme, toggleTheme, isDark } = useTheme();
  const { showSuccess } = useToast();
  const [notifications, setNotifications] = useState({ email: true, deadlines: true, updates: false });

  return (
    <div>
      <div className="page-header"><h1 className="section-title">Settings</h1><p className="section-subtitle">Manage your account preferences and configuration.</p></div>
      <div className="space-y-6 max-w-2xl">
        <Card>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Palette className="w-5 h-5 text-brand-600" /> Appearance</h2>
          <div className="flex items-center justify-between">
            <div><p className="font-medium">Theme</p><p className="text-sm text-surface-500">Choose between light and dark mode</p></div>
            <button onClick={toggleTheme} className="flex items-center gap-2 px-4 py-2 rounded-xl border border-surface-200 dark:border-surface-700 hover:bg-surface-100 dark:hover:bg-surface-800 transition-colors">
              {isDark ? <Sun className="w-4 h-4 text-amber-500" /> : <Moon className="w-4 h-4" />}
              <span className="text-sm font-medium">{isDark ? 'Light Mode' : 'Dark Mode'}</span>
            </button>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Bell className="w-5 h-5 text-brand-600" /> Notifications</h2>
          <div className="space-y-4">
            {[
              { key: 'email', label: 'Email Notifications', desc: 'Receive updates about your applications' },
              { key: 'deadlines', label: 'Deadline Reminders', desc: 'Get notified before grant deadlines' },
              { key: 'updates', label: 'Product Updates', desc: 'New features and improvements' },
            ].map((item) => (
              <div key={item.key} className="flex items-center justify-between">
                <div><p className="font-medium text-sm">{item.label}</p><p className="text-xs text-surface-500">{item.desc}</p></div>
                <button
                  onClick={() => setNotifications((n) => ({ ...n, [item.key]: !n[item.key] }))}
                  className={`relative w-11 h-6 rounded-full transition-colors duration-200 ${notifications[item.key] ? 'bg-brand-600' : 'bg-surface-300 dark:bg-surface-600'}`}
                >
                  <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 ${notifications[item.key] ? 'left-[22px]' : 'left-0.5'}`} />
                </button>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Shield className="w-5 h-5 text-brand-600" /> Security</h2>
          <div className="space-y-3">
            <Button variant="secondary" className="w-full justify-start">Change Password</Button>
            <Button variant="secondary" className="w-full justify-start text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20">Delete Account</Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
