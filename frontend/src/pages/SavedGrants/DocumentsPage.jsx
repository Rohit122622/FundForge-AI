import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Upload, FolderOpen, Trash2, Download, FileIcon, Loader2, Eye } from 'lucide-react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Badge from '../../components/ui/Badge';
import EmptyState from '../../components/ui/EmptyState';
import { SkeletonCard } from '../../components/ui/Skeleton';
import documentService from '../../services/documentService';
import { useToast } from '../../contexts/ToastContext';

export default function DocumentsPage() {
  const { showSuccess, showError } = useToast();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const fetchDocuments = async () => {
    try {
      const res = await documentService.listDocuments({ _t: Date.now() });
      setDocuments(res.data.data?.documents || []);
    } catch { setDocuments([]); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchDocuments(); }, []);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      await documentService.upload(formData);
      showSuccess('Document uploaded!');
      await fetchDocuments();
    } catch (err) { showError(err.response?.data?.error?.message || 'Upload failed'); }
    finally { setUploading(false); e.target.value = ''; }
  };

  const handleDelete = async (docId) => {
    try {
      await documentService.deleteDocument(docId);
      showSuccess('Document deleted');
      await fetchDocuments();
    } catch {
      showError('Failed to delete document');
    }
  };

  const handleDownload = async (docId, filename) => {
    try {
      const res = await documentService.downloadDocument(docId);
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
    } catch { showError('Download failed'); }
  };

  const handlePreview = async (docId) => {
    try {
      const res = await documentService.downloadDocument(docId);
      const url = URL.createObjectURL(res.data);
      window.open(url, '_blank');
    } catch { showError('Failed to load preview'); }
  };

  return (
    <div>
      <div className="page-header flex items-start justify-between">
        <div><h1 className="section-title">Documents</h1><p className="section-subtitle">Upload and manage your startup documents.</p></div>
        <label className="btn-primary cursor-pointer">
          {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
          {uploading ? 'Uploading...' : 'Upload'}
          <input type="file" className="hidden" onChange={handleUpload} accept=".pdf,.doc,.docx,.png,.jpg,.jpeg" />
        </label>
      </div>

      {loading ? (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}</div>
      ) : documents.length === 0 ? (
        <EmptyState icon={FolderOpen} title="No documents" description="Upload incorporation certificates, PAN cards, and other documents needed for grant applications." />
      ) : (
        <div className="space-y-3">
          {documents.map((doc, i) => (
            <motion.div key={doc.id || i} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Card className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center"><FileIcon className="w-5 h-5 text-brand-600" /></div>
                  <div>
                    <p className="font-medium text-surface-900 dark:text-surface-50">{doc.display_name || doc.original_filename}</p>
                    <p className="text-xs text-surface-500">{doc.mime_type || doc.content_type} • {((doc.file_size_bytes || doc.file_size || 0) / 1024).toFixed(1)} KB</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="accent">{doc.status || 'uploaded'}</Badge>
                  <button onClick={() => handlePreview(doc.id)} className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800" title="Preview"><Eye className="w-4 h-4 text-surface-500" /></button>
                  <button onClick={() => handleDownload(doc.id, doc.original_filename)} className="p-2 rounded-lg hover:bg-surface-100 dark:hover:bg-surface-800" title="Download"><Download className="w-4 h-4 text-surface-500" /></button>
                  <button onClick={() => handleDelete(doc.id)} className="p-2 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20" title="Delete"><Trash2 className="w-4 h-4 text-red-500" /></button>
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
