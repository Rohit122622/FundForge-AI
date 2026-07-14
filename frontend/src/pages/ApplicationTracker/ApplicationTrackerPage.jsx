import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, Plus, Clock, Trash2, Edit2, ExternalLink, Calendar, AlertCircle, X } from 'lucide-react';
import Card from '../../components/ui/Card';
import Badge from '../../components/ui/Badge';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonCard } from '../../components/ui/Skeleton';
import trackerService from '../../services/trackerService';
import grantService from '../../services/grantService';
import { useToast } from '../../contexts/ToastContext';

const statusColors = {
  saved: 'neutral',
  researching: 'info',
  in_progress: 'warning',
  submitted: 'brand',
  under_review: 'accent',
  awarded: 'success',
  rejected: 'danger',
  withdrawn: 'neutral',
  abandoned: 'neutral',
};

const ALLOWED_TRANSITIONS = {
  saved: ['researching', 'in_progress', 'abandoned'],
  researching: ['in_progress', 'abandoned', 'withdrawn'],
  in_progress: ['submitted', 'abandoned', 'withdrawn'],
  submitted: ['under_review', 'withdrawn', 'abandoned'],
  under_review: ['awarded', 'rejected', 'withdrawn'],
  awarded: [],
  rejected: [],
  withdrawn: [],
  abandoned: [],
};

export default function ApplicationTrackerPage() {
  const { showSuccess, showError } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [applications, setApplications] = useState([]);
  const [grants, setGrants] = useState([]);
  const [loading, setLoading] = useState(true);
  
  
  const [modalOpen, setModalOpen] = useState(false);
  const [editingApp, setEditingApp] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  
  const [form, setForm] = useState({
    grant_id: '',
    priority: 'medium',
    deadline: '',
    notes: '',
    next_action: '',
    next_action_date: '',
    portal_url: '',
  });

  const fetchApps = async () => {
    setLoading(true);
    try {
      const res = await trackerService.listApplications({ page: 1, per_page: 50 });
      setApplications(res.data.data || []);
    } catch (err) {
      setApplications([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchGrants = async () => {
    try {
      const res = await grantService.listGrants({ per_page: 100 });
      setGrants(res.data.data?.grants || res.data.data || []);
    } catch (err) {
      console.error('Failed to load grants:', err);
    }
  };

  useEffect(() => {
    fetchApps();
    fetchGrants();
  }, []);

  
  useEffect(() => {
    const grantIdParam = searchParams.get('grant_id');
    if (grantIdParam && grants.length > 0) {
      
      const selectedGrant = grants.find(g => g.id === grantIdParam || g.slug === grantIdParam);
      setForm({
        grant_id: grantIdParam,
        priority: 'medium',
        deadline: selectedGrant?.deadline || '',
        notes: '',
        next_action: '',
        next_action_date: '',
        portal_url: selectedGrant?.application_url || '',
      });
      setEditingApp(null);
      setModalOpen(true);
      
      setSearchParams({});
    }
  }, [searchParams, grants]);

  const handleOpenNewModal = () => {
    setForm({
      grant_id: '',
      priority: 'medium',
      deadline: '',
      notes: '',
      next_action: '',
      next_action_date: '',
      portal_url: '',
    });
    setEditingApp(null);
    setModalOpen(true);
  };

  const handleOpenEditModal = (app) => {
    
    let portalUrl = app.internal_reference || '';
    if (!portalUrl && app.notes) {
      const match = app.notes.match(/Portal Link:\s*([^\s\n]+)/);
      if (match) portalUrl = match[1];
    }

    
    let cleanNotes = app.notes || '';
    
    setForm({
      grant_id: app.grant_id || '',
      priority: app.priority || 'medium',
      deadline: app.deadline || '',
      notes: cleanNotes,
      next_action: app.next_action || '',
      next_action_date: app.next_action_date || '',
      portal_url: portalUrl,
      status: app.status || 'saved',
    });
    setEditingApp(app);
    setModalOpen(true);
  };

  const handleDelete = async (appId) => {
    if (!confirm('Are you sure you want to stop tracking this application?')) return;
    try {
      await trackerService.deleteApplication(appId);
      showSuccess('Application tracking stopped.');
      fetchApps();
    } catch (err) {
      showError('Failed to delete application.');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.grant_id) {
      showError('Please select a grant.');
      return;
    }
    setSubmitting(true);
    try {
      
      let finalNotes = form.notes || '';
      if (form.portal_url) {
        if (!finalNotes.includes('Portal Link:')) {
          finalNotes = `Portal Link: ${form.portal_url}\n\n${finalNotes}`.trim();
        }
      }

      const payload = {
        grant_id: form.grant_id,
        priority: form.priority,
        deadline: form.deadline || null,
        notes: finalNotes,
        next_action: form.next_action || null,
        next_action_date: form.next_action_date || null,
        internal_reference: form.portal_url || null,
      };

      if (editingApp) {
        
        if (form.status && form.status !== editingApp.status) {
          try {
            await trackerService.transitionStatus(editingApp.id, { 
              new_status: form.status,
              notes: 'Status updated via tracker dashboard.'
            });
          } catch (transitionErr) {
            showError(transitionErr.response?.data?.error?.message || 'Invalid status transition.');
            setSubmitting(false);
            return;
          }
        }

        await trackerService.updateApplication(editingApp.id, payload);
        showSuccess('Application updated successfully.');
      } else {
        await trackerService.createApplication(payload);
        showSuccess('Application added to tracker.');
      }
      
      setModalOpen(false);
      fetchApps();
    } catch (err) {
      showError(err.response?.data?.error?.message || 'Failed to save application tracker.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div className="page-header flex items-start justify-between">
        <div>
          <h1 className="section-title">Application Tracker</h1>
          <p className="section-subtitle">Track your grant applications from discovery to award.</p>
        </div>
        <Button icon={Plus} onClick={handleOpenNewModal}>New Application</Button>
      </div>

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      ) : applications.length === 0 ? (
        <EmptyState
          icon={Trophy}
          title="No applications tracked"
          description="Add a grant to your applications list to monitor deadlines, submission states, and action items."
          actionLabel="Browse Grants"
          onAction={() => window.location.href = '/grants'}
        />
      ) : (
        <div className="space-y-4">
          {applications.map((app, i) => {
            const grantName = app.grant?.title || app.grant?.name || `Grant ID: ${app.grant_id}`;
            const portalLink = app.internal_reference || '';

            return (
              <motion.div
                key={app.id || i}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <Card className="p-6">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-4">
                    <div>
                      <h3 className="font-bold text-lg text-surface-900 dark:text-surface-50">
                        {grantName}
                      </h3>
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        <Badge variant={statusColors[app.status] || 'neutral'}>
                          {app.status?.replace(/_/g, ' ')}
                        </Badge>
                        <Badge variant={app.priority === 'low' ? 'neutral' : app.priority === 'medium' ? 'brand' : 'warning'}>
                          {app.priority} Priority
                        </Badge>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 self-end sm:self-auto">
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={Edit2}
                        onClick={() => handleOpenEditModal(app)}
                      >
                        Edit
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/20"
                        icon={Trash2}
                        onClick={() => handleDelete(app.id)}
                      >
                        Delete
                      </Button>
                    </div>
                  </div>

                  {/* Dates & Follow-ups */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4 text-xs text-surface-500 dark:text-surface-400 border-y border-surface-100 dark:border-surface-800/80 py-3">
                    <div className="flex items-center gap-2">
                      <Calendar className="w-4 h-4 text-surface-400" />
                      <div>
                        <span className="block text-[10px] text-surface-400 uppercase font-semibold">Deadline</span>
                        <span className="font-medium text-surface-800 dark:text-surface-200">{app.deadline || 'None'}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-surface-400" />
                      <div>
                        <span className="block text-[10px] text-surface-400 uppercase font-semibold">Next Action Date</span>
                        <span className="font-medium text-surface-800 dark:text-surface-200">{app.next_action_date || 'None'}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <ExternalLink className="w-4 h-4 text-surface-400" />
                      <div>
                        <span className="block text-[10px] text-surface-400 uppercase font-semibold">Portal Link</span>
                        {portalLink ? (
                          <a href={portalLink} target="_blank" rel="noopener noreferrer" className="font-medium text-brand-600 hover:underline flex items-center gap-0.5">
                            Visit Login <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        ) : (
                          <span className="font-medium text-surface-400">Not set</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Next Action Item */}
                  {app.next_action && (
                    <div className="mb-3 text-sm flex items-start gap-2 bg-amber-50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300 p-3 rounded-lg border border-amber-200/40">
                      <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                      <div>
                        <span className="font-semibold text-xs block uppercase tracking-wider text-amber-600">Pending Task:</span>
                        {app.next_action}
                      </div>
                    </div>
                  )}

                  {/* Notes */}
                  {app.notes && (
                    <div className="text-sm">
                      <span className="block text-xs font-semibold text-surface-400 uppercase tracking-wide mb-1">Journal & Notes:</span>
                      <p className="text-surface-600 dark:text-surface-400 leading-relaxed whitespace-pre-line bg-surface-50 dark:bg-surface-800/10 p-3 rounded-lg border border-surface-100 dark:border-surface-800/40">
                        {app.notes}
                      </p>
                    </div>
                  )}
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Slide-over Modal Form */}
      <AnimatePresence>
        {modalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="bg-surface-0 dark:bg-surface-900 border border-surface-200 dark:border-surface-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between border-b border-surface-100 dark:border-surface-800 pb-3">
                <h2 className="text-lg font-bold text-surface-900 dark:text-surface-50">
                  {editingApp ? 'Edit Application Tracking' : 'Track New Application'}
                </h2>
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="text-surface-400 hover:text-surface-600 dark:hover:text-surface-200"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4 pt-2">
                {/* Select Grant */}
                <div>
                  <label className="label-text">Select Grant Scheme</label>
                  {editingApp ? (
                    <div className="bg-surface-50 dark:bg-surface-800 p-3 rounded-lg border border-surface-200 dark:border-surface-700 text-sm font-semibold">
                      {editingApp.grant?.title || editingApp.grant?.name || editingApp.grant_id}
                    </div>
                  ) : (
                    <select
                      className="input-field"
                      value={form.grant_id}
                      onChange={(e) => setForm(prev => ({ ...prev, grant_id: e.target.value }))}
                      required
                    >
                      <option value="">-- Choose Grant --</option>
                      {grants.map(g => (
                        <option key={g.id} value={g.id || g.slug}>
                          {g.name || g.title}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                {/* Status Dropdown (FSM transitional state) */}
                {editingApp && (
                  <div>
                    <label className="label-text">Application Status</label>
                    {ALLOWED_TRANSITIONS[editingApp.status]?.length > 0 ? (
                      <select
                        className="input-field"
                        value={form.status}
                        onChange={(e) => setForm(prev => ({ ...prev, status: e.target.value }))}
                      >
                        <option value={editingApp.status}>{editingApp.status.replace(/_/g, ' ')} (Current)</option>
                        {ALLOWED_TRANSITIONS[editingApp.status].map(next => (
                          <option key={next} value={next}>
                            {next.replace(/_/g, ' ')}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="mt-1">
                        <Badge variant="neutral">{editingApp.status.replace(/_/g, ' ')}</Badge>
                        <span className="text-xs text-surface-400 block mt-1">This application has reached a terminal status.</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Priority Selection */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="label-text">Priority</label>
                    <select
                      className="input-field"
                      value={form.priority}
                      onChange={(e) => setForm(prev => ({ ...prev, priority: e.target.value }))}
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                    </select>
                  </div>
                  <Input
                    label="Deadline"
                    type="date"
                    value={form.deadline}
                    onChange={(e) => setForm(prev => ({ ...prev, deadline: e.target.value }))}
                  />
                </div>

                {/* Portal Login Link */}
                <Input
                  label="Portal Login URL"
                  type="url"
                  placeholder="https://startupindia.gov.in/portal/..."
                  value={form.portal_url}
                  onChange={(e) => setForm(prev => ({ ...prev, portal_url: e.target.value }))}
                />

                {/* Next Action items */}
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Next Follow-up Task"
                    placeholder="e.g. Upload PAN, complete section 3"
                    value={form.next_action}
                    onChange={(e) => setForm(prev => ({ ...prev, next_action: e.target.value }))}
                  />
                  <Input
                    label="Next Action Date"
                    type="date"
                    value={form.next_action_date}
                    onChange={(e) => setForm(prev => ({ ...prev, next_action_date: e.target.value }))}
                  />
                </div>

                {/* Notes Journal */}
                <div>
                  <label className="label-text">Journal & Notes</label>
                  <textarea
                    className="input-field min-h-[100px]"
                    placeholder="Document portal credentials, meeting details, and submission drafts..."
                    value={form.notes}
                    onChange={(e) => setForm(prev => ({ ...prev, notes: e.target.value }))}
                  />
                </div>

                <div className="flex gap-3 justify-end pt-3 border-t border-surface-100 dark:border-surface-800">
                  <Button variant="ghost" onClick={() => setModalOpen(false)}>Cancel</Button>
                  <Button type="submit" loading={submitting}>
                    {editingApp ? 'Save Changes' : 'Start Tracking'}
                  </Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
