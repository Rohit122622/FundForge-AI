import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FileText, Loader2, Copy, Download, CheckCircle } from 'lucide-react';
import Card from '../../components/ui/Card';
import Button from '../../components/ui/Button';
import Input from '../../components/ui/Input';
import Badge from '../../components/ui/Badge';
import proposalService from '../../services/proposalService';
import documentService from '../../services/documentService';
import { useProfile } from '../../contexts/ProfileContext';
import { useToast } from '../../contexts/ToastContext';


const renderMarkdown = (text) => {
  if (!text) return '';
  
  
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  
  html = html.replace(/^### (.*$)/gim, '<h4 class="text-xs font-bold font-mono text-brand-600 dark:text-brand-400 uppercase tracking-wider mt-4 mb-2">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 class="text-sm font-bold text-surface-900 dark:text-white mt-5 mb-3">$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2 class="text-base font-extrabold text-surface-950 dark:text-white mt-6 mb-4">$1</h2>');

  
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-surface-950 dark:text-white">$1</strong>');

  
  html = html.replace(/\*(.*?)\*/g, '<em class="italic">$1</em>');

  
  html = html.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-surface-100 dark:bg-surface-800 text-brand-600 font-mono text-xs font-semibold">$1</code>');

  
  if (html.includes('|')) {
    const rows = html.split('\n');
    let inTable = false;
    const tableProcessed = [];
    
    for (let r of rows) {
      if (r.trim().startsWith('|') && r.trim().endsWith('|')) {
        if (!inTable) {
          tableProcessed.push('<div class="overflow-x-auto my-3"><table class="w-full text-xs text-left border-collapse border border-surface-200 dark:border-surface-800">');
          inTable = true;
        }
        const cols = r.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
        if (r.includes('---')) continue; 
        
        tableProcessed.push('<tr class="border-b border-surface-200 dark:border-surface-800 bg-surface-50/50 dark:bg-surface-900/50">');
        for (let col of cols) {
          tableProcessed.push(`<td class="p-2 border border-surface-200 dark:border-surface-800 text-surface-800 dark:text-surface-200">${col}</td>`);
        }
        tableProcessed.push('</tr>');
      } else {
        if (inTable) {
          tableProcessed.push('</table></div>');
          inTable = false;
        }
        tableProcessed.push(r);
      }
    }
    if (inTable) {
      tableProcessed.push('</table></div>');
    }
    html = tableProcessed.join('\n');
  }

  
  const lines = html.split('\n');
  let inList = false;
  let listType = ''; 
  const processedLines = [];

  for (let line of lines) {
    const trimmed = line.trim();
    const isBullet = trimmed.startsWith('- ') || trimmed.startsWith('* ');
    const isNum = /^\d+\.\s/.test(trimmed);

    if (isBullet) {
      if (!inList || listType !== 'ul') {
        if (inList) processedLines.push(`</${listType}>`);
        processedLines.push('<ul class="list-disc pl-5 space-y-1.5 my-2 text-surface-700 dark:text-surface-300">');
        inList = true;
        listType = 'ul';
      }
      processedLines.push(`<li>${trimmed.substring(2)}</li>`);
    } else if (isNum) {
      if (!inList || listType !== 'ol') {
        if (inList) processedLines.push(`</${listType}>`);
        processedLines.push('<ol class="list-decimal pl-5 space-y-1.5 my-2 text-surface-700 dark:text-surface-300">');
        inList = true;
        listType = 'ol';
      }
      const match = trimmed.match(/^\d+\.\s(.*)/);
      processedLines.push(`<li>${match ? match[1] : trimmed}</li>`);
    } else {
      if (inList) {
        processedLines.push(`</${listType}>`);
        inList = false;
        listType = '';
      }
      processedLines.push(line);
    }
  }
  if (inList) {
    processedLines.push(`</${listType}>`);
  }

  html = processedLines.join('\n');

  
  html = html.replace(/\n\n/g, '<br/><br/>');

  return <div className="markdown-content space-y-2 leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />;
};

export default function ProposalGeneratorPage() {
  const { showSuccess, showError } = useToast();
  const { profile, loading: profileLoading } = useProfile();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [copied, setCopied] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [downloadingDocx, setDownloadingDocx] = useState(false);
  const [searchParams] = useSearchParams();
  const [form, setForm] = useState({
    grant_id: '',
    tone: 'professional',
    user_instructions: '',
  });

  useEffect(() => {
    const grantIdParam = searchParams.get('grant_id');
    setForm(prev => ({
      ...prev,
      grant_id: grantIdParam || prev.grant_id || '',
    }));
  }, [searchParams]);

  const handleDownloadPdf = async () => {
    if (!result?.proposal_id) return;
    setDownloadingPdf(true);
    try {
      showSuccess('Generating PDF...');
      const pdfPayload = {
        pdf_type: 'proposal',
        proposal_id: result.proposal_id,
        data: {
          proposal: {
            ...(result.draft?.sections || {}),
            sections: result.draft?.sections || {},
          },
          grant: {
            title: result.draft?.grant_name || form.grant_id,
            organization_name: 'Government of India',
          },
          startup: {
            company_name: result.draft?.company_name || (profile?.company_name || 'Startup'),
            tagline: profile?.description?.slice(0, 100) || '',
          }
        }
      };
      const res = await documentService.generatePdf(pdfPayload);
      const docId = res.data?.data?.document?.id;
      if (docId) {
        const blobRes = await documentService.downloadDocument(docId);
        const blob = new Blob([blobRes.data], { type: 'application/pdf' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `${result.draft?.company_name || 'Startup'}_Proposal.pdf`);
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
        window.URL.revokeObjectURL(url);
        showSuccess('PDF downloaded successfully!');
      } else {
        showError('Failed to retrieve PDF ID');
      }
    } catch (err) {
      showError(err.response?.data?.error?.message || 'Failed to download PDF');
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleDownloadDocx = async () => {
    if (!result?.proposal_id) return;
    setDownloadingDocx(true);
    try {
      showSuccess('Generating DOCX...');
      const res = await proposalService.exportProposal(result.proposal_id, 'docx');
      const b64Data = res.data?.data?.content;
      const filename = res.data?.data?.filename || 'Proposal.docx';
      const mimeType = res.data?.data?.content_type || 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
      
      if (b64Data) {
        const byteCharacters = atob(b64Data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        link.parentNode.removeChild(link);
        window.URL.revokeObjectURL(url);
        showSuccess('DOCX downloaded successfully!');
      } else {
        showError('No content returned for DOCX');
      }
    } catch (err) {
      showError(err.response?.data?.error?.message || 'Failed to download DOCX');
    } finally {
      setDownloadingDocx(false);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!form.grant_id) { showError('Grant ID is required'); return; }
    setLoading(true); setResult(null);
    try {
      const res = await proposalService.generateProposal({
        grant_id: form.grant_id,
        tone: form.tone,
        user_instructions: form.user_instructions,
        use_rag: true,
      });
      setResult(res.data.data);
      showSuccess('Proposal generated successfully!');
    } catch (err) {
      showError(err.response?.data?.error?.message || 'Proposal generation failed');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    const sections = result?.draft?.sections || {};
    const text = Object.entries(sections).map(([k, v]) => `## ${k.replace(/_/g, ' ').toUpperCase()}\n\n${v}`).join('\n\n---\n\n');
    navigator.clipboard.writeText(text);
    setCopied(true); showSuccess('Copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  const updateField = (field) => (e) => setForm((p) => ({ ...p, [field]: e.target.value }));

  if (profileLoading) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="w-8 h-8 animate-spin text-brand-600" /></div>;
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="section-title">Proposal Generator</h1>
        <p className="section-subtitle">Generate AI-powered grant proposals tailored to your startup.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        <div className="lg:col-span-2">
          <Card className="sticky top-24">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><FileText className="w-5 h-5 text-brand-600" /> Configure</h2>
            <form onSubmit={handleGenerate} className="space-y-4">
              <Input label="Grant ID" value={form.grant_id} onChange={updateField('grant_id')} required placeholder="sisfs" />
              
              {profile ? (
                <div className="bg-surface-50 dark:bg-surface-850 p-4 rounded-lg border border-surface-200 dark:border-surface-800 space-y-2">
                  <div className="text-[10px] font-semibold text-surface-400 dark:text-surface-500 uppercase tracking-wider">Startup Profile Details</div>
                  <div className="text-sm font-bold text-surface-800 dark:text-surface-200">{profile.company_name}</div>
                  <div className="text-xs text-surface-500 dark:text-surface-400 capitalize">
                    {profile.industry_name || profile.sector} • {(profile.stage || '').replace(/_/g, ' ')}
                  </div>
                </div>
              ) : (
                <div className="bg-amber-50 dark:bg-amber-950/20 text-amber-600 p-3 rounded-lg border border-amber-200 text-xs">
                  No startup profile found. Please <Link to="/profile" className="underline font-bold">create a profile</Link> first.
                </div>
              )}

              <div><label className="label-text">Tone</label><select className="input-field" value={form.tone} onChange={updateField('tone')}><option value="professional">Professional</option><option value="persuasive">Persuasive</option><option value="technical">Technical</option><option value="concise">Concise</option></select></div>
              <div><label className="label-text">Special Instructions</label><textarea className="input-field min-h-[60px]" value={form.user_instructions} onChange={updateField('user_instructions')} placeholder="Focus on AI innovation..." /></div>
              <Button type="submit" loading={loading} disabled={!profile} className="w-full" icon={FileText}>Generate Proposal</Button>
            </form>
          </Card>
        </div>

        <div className="lg:col-span-3">
          {loading && (
            <Card className="flex items-center justify-center py-20">
              <div className="text-center"><Loader2 className="w-10 h-10 animate-spin text-brand-600 mx-auto mb-4" /><p className="text-surface-500 font-medium">IBM Granite is generating your proposal...</p><p className="text-sm text-surface-400 mt-1">This may take 30-60 seconds</p></div>
            </Card>
          )}
          {result && !loading && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              <Card>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <h2 className="text-lg font-semibold">Generated Proposal</h2>
                    <Badge variant="accent">Quality: {result.quality_score}/100</Badge>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="sm" onClick={copyToClipboard} icon={copied ? CheckCircle : Copy}>{copied ? 'Copied' : 'Copy'}</Button>
                    <Button variant="ghost" size="sm" onClick={handleDownloadPdf} loading={downloadingPdf} icon={Download}>Download PDF</Button>
                    <Button variant="ghost" size="sm" onClick={handleDownloadDocx} loading={downloadingDocx} icon={Download}>Download DOCX</Button>
                  </div>
                </div>
                <div className="prose dark:prose-invert max-w-none">
                  {result.draft?.sections && Object.entries(result.draft.sections).map(([key, value]) => (
                    <div key={key} className="mb-6 pb-6 border-b border-surface-100 dark:border-surface-800 last:border-0 last:pb-0">
                      <h3 className="text-md font-semibold text-brand-600 dark:text-brand-400 mb-3 uppercase tracking-wider text-xs font-mono">{key.replace(/_/g, ' ')}</h3>
                      <div className="text-surface-800 dark:text-surface-200 text-sm font-sans">
                        {renderMarkdown(value)}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
              {result.review?.suggestions && (
                <Card>
                  <h3 className="font-semibold mb-3">AI Review & Suggestions</h3>
                  <div className="text-sm text-surface-600 dark:text-surface-400 whitespace-pre-line">{typeof result.review.suggestions === 'string' ? result.review.suggestions : JSON.stringify(result.review.suggestions, null, 2)}</div>
                </Card>
              )}
            </motion.div>
          )}
          {!result && !loading && (
            <Card className="flex items-center justify-center py-20">
              <div className="text-center"><FileText className="w-12 h-12 text-surface-300 mx-auto mb-4" /><h3 className="text-lg font-semibold text-surface-900 dark:text-surface-100 mb-2">No proposal yet</h3><p className="text-surface-500 max-w-sm">Fill in your startup details and click Generate to create an AI-powered grant proposal.</p></div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
