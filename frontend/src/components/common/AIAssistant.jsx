import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Send, X, Bot, User, Loader2, BookOpen, Clock, Layers, Copy, Check } from 'lucide-react';
import ragService from '../../services/ragService';

const SUGGESTED_QUESTIONS = [
  'What is the eligibility for BIRAC BIG?',
  'Tell me about SISFS seed fund requirements',
  'How to obtain DPIIT recognition for my startup?',
  'What documents do I need to prepare for grant applications?',
];


const renderMarkdown = (text) => {
  if (!text) return '';
  
  
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  
  html = html.replace(/```([\s\S]*?)```/g, '<pre class="p-3 my-2.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 font-mono text-xs overflow-x-auto"><code>$1</code></pre>');

  
  html = html.replace(/^### (.*$)/gim, '<h4 class="text-xs font-bold font-mono text-indigo-400 uppercase tracking-wider mt-4 mb-2">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 class="text-sm font-bold text-white mt-5 mb-3">$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2 class="text-base font-extrabold text-white mt-6 mb-4">$1</h2>');

  
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-white">$1</strong>');

  
  html = html.replace(/\*(.*?)\*/g, '<em class="italic text-slate-350">$1</em>');

  
  html = html.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono text-xs font-semibold">$1</code>');

  
  if (html.includes('|')) {
    const rows = html.split('\n');
    let inTable = false;
    const tableProcessed = [];
    
    for (let r of rows) {
      if (r.trim().startsWith('|') && r.trim().endsWith('|')) {
        if (!inTable) {
          tableProcessed.push('<div class="overflow-x-auto my-3"><table class="w-full text-xs text-left border-collapse border border-slate-800">');
          inTable = true;
        }
        const cols = r.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
        if (r.includes('---')) continue; 
        
        tableProcessed.push('<tr class="border-b border-slate-800 bg-slate-900/40">');
        for (let col of cols) {
          tableProcessed.push(`<td class="p-2 border border-slate-850 text-slate-250">${col}</td>`);
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
        processedLines.push('<ul class="list-disc pl-5 space-y-1.5 my-2 text-slate-300">');
        inList = true;
        listType = 'ul';
      }
      processedLines.push(`<li>${trimmed.substring(2)}</li>`);
    } else if (isNum) {
      if (!inList || listType !== 'ol') {
        if (inList) processedLines.push(`</${listType}>`);
        processedLines.push('<ol class="list-decimal pl-5 space-y-1.5 my-2 text-slate-300">');
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

  return <div className="markdown-content space-y-2 text-slate-200 leading-relaxed font-sans" dangerouslySetInnerHTML={{ __html: html }} />;
};

export default function AIAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('assistant_history');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        console.error('Failed to parse history:', e);
      }
    }
    return [
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Hi! I am your FundForge AI Assistant. Ask me anything about Indian startup grants, eligibility criteria, or how to prepare your proposal.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ];
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  
  useEffect(() => {
    localStorage.setItem('assistant_history', JSON.stringify(messages));
  }, [messages]);

  const handleSend = async (questionText) => {
    const query = questionText || input.trim();
    if (!query) return;

    if (!questionText) {
      setInput('');
    }

    const userMessageId = Date.now().toString();
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages((prev) => [...prev, { id: userMessageId, role: 'user', content: query, timestamp: timeStr }]);
    setLoading(true);

    const assistantMessageId = (Date.now() + 1).toString();
    const startTime = performance.now();

    
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        provider: 'IBM watsonx.ai',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/rag/stream-qa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ question: query, top_k: 5 }),
      });

      if (!response.ok) {
        throw new Error('Streaming failed, invoking backup model');
      }

      setLoading(false); 

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let textAccumulator = '';

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value, { stream: !done });
          textAccumulator += chunk;
          
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId 
                ? { 
                    ...msg, 
                    content: textAccumulator,
                    generationTime: ((performance.now() - startTime) / 1000).toFixed(1),
                    retrievedCount: 0
                  } 
                : msg
            )
          );
        }
      }
    } catch (streamErr) {
      console.warn('Streaming error, falling back to backup API:', streamErr);
      
      
      try {
        const res = await ragService.askQuestion({ question: query, top_k: 5 });
        const data = res.data.data;
        const duration = ((performance.now() - startTime) / 1000).toFixed(1);
        
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content: data.answer,
                  citations: data.citations || [],
                  provider: data.ai_metadata?.provider || data.model_id || 'Gemini/Grok Fallback',
                  generationTime: duration,
                  retrievedCount: data.citations?.length || 0,
                }
              : msg
          )
        );
      } catch (backupErr) {
        
        let fallbackAnswer = 'I am currently having difficulty connecting to my remote brain. ';
        const lowerQ = query.toLowerCase();
        
        if (lowerQ.includes('sisfs') || lowerQ.includes('seed fund')) {
          fallbackAnswer += 'Regarding the Startup India Seed Fund Scheme (SISFS): It provides up to ₹20 Lakhs as a grant for proof of concept/prototype development, and up to ₹50 Lakhs as a debt/convertible debenture for market entry or commercialization. Eligibility requires a DPIIT-recognized startup incorporated less than 2 years ago.';
        } else if (lowerQ.includes('birac') || lowerQ.includes('big')) {
          fallbackAnswer += 'Regarding the BIRAC Biotechnology Ignition Grant (BIG): It offers up to ₹50 Lakhs for biotechnology, healthcare, industrial biotech, and agritech innovations. The project duration is typically up to 18 months.';
        } else {
          fallbackAnswer += 'Please ensure you are connected to the internet. You can find detailed grant rules under the Grant Explorer or catalog in the sidebar.';
        }

        const duration = ((performance.now() - startTime) / 1000).toFixed(1);

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? {
                  ...msg,
                  content: fallbackAnswer,
                  isError: true,
                  provider: 'Offline Rule Engine',
                  generationTime: duration,
                  retrievedCount: 0,
                }
              : msg
          )
        );
      } finally {
        setLoading(false);
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const clearHistory = () => {
    if (confirm('Clear chat history?')) {
      const defaultMsg = [
        {
          id: 'welcome',
          role: 'assistant',
          content: 'Hi! I am your FundForge AI Assistant. Ask me anything about Indian startup grants, eligibility criteria, or how to prepare your proposal.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ];
      setMessages(defaultMsg);
      localStorage.setItem('assistant_history', JSON.stringify(defaultMsg));
    }
  };

  const copyMessageText = (msgId, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(msgId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end">
      
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="w-[360px] sm:w-[420px] h-[600px] rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl flex flex-col mb-4 overflow-hidden"
          >
            
            <div className="p-4 border-b border-slate-800 bg-slate-850 flex items-center justify-between text-white">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-indigo-650 flex items-center justify-center shadow-lg">
                  <Bot className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-white">FundForge AI Assistant</h3>
                  <p className="text-[10px] text-slate-400">Granite, Gemini & Grok Hybrid RAG</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={clearHistory}
                  className="text-xs bg-slate-800 hover:bg-slate-700 px-2.5 py-1.5 rounded-lg font-medium text-slate-100 border border-slate-700 transition-colors"
                  type="button"
                >
                  Clear History
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                  type="button"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Message Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950/40 scrollbar-thin scrollbar-thumb-slate-800 scrollbar-track-slate-900">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role !== 'user' && (
                    <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center flex-shrink-0 self-start">
                      <Bot className="w-4 h-4 text-indigo-400" />
                    </div>
                  )}
                  <div className="space-y-1 max-w-[82%]">
                    <div
                      className={`rounded-2xl p-3.5 text-sm leading-relaxed relative group ${
                        msg.role === 'user'
                          ? 'bg-indigo-650 text-white rounded-tr-none font-medium'
                          : msg.isError
                          ? 'bg-red-950/30 text-red-200 border border-red-900/40 rounded-tl-none'
                          : 'bg-slate-850 border border-slate-750 text-slate-100 rounded-tl-none shadow-md'
                      }`}
                    >
                      {msg.role === 'user' ? (
                        <p className="whitespace-pre-wrap text-white font-medium">{msg.content}</p>
                      ) : (
                        renderMarkdown(msg.content)
                      )}

                      {/* Interactive Citations */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3.5 pt-2.5 border-t border-slate-800">
                          <p className="text-[10px] font-semibold text-slate-450 flex items-center gap-1 mb-1.5 tracking-wider uppercase">
                            <BookOpen className="w-3.5 h-3.5" /> Sources Cited ({msg.citations.length})
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.citations.map((cit, idx) => (
                              <button
                                key={idx}
                                onClick={() => setActiveCitation(activeCitation === cit ? null : cit)}
                                className={`text-[10px] px-2 py-1 rounded border transition-colors text-left flex items-center gap-1 ${
                                  activeCitation === cit
                                    ? 'bg-indigo-950 border-indigo-850 text-indigo-300'
                                    : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-750'
                                }`}
                              >
                                <span>[{idx + 1}]</span>
                                <span className="max-w-[120px] truncate font-medium">{cit.source || cit.grant_id || `Source ${idx + 1}`}</span>
                              </button>
                            ))}
                          </div>
                          
                          {/* Active citation snippet drawer */}
                          <AnimatePresence>
                            {activeCitation && (
                              <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="mt-2.5 p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-[11px] text-slate-300 leading-relaxed font-sans"
                              >
                                <p className="font-semibold text-slate-200 mb-1">
                                  {activeCitation.source || activeCitation.grant_id}
                                </p>
                                <p className="italic">"{activeCitation.snippet}"</p>
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </div>
                      )}

                      {/* Copy Button */}
                      {msg.content && (
                        <button
                          onClick={() => copyMessageText(msg.id, msg.content)}
                          className="absolute right-2 top-2 p-1 rounded bg-slate-900/60 hover:bg-slate-900 border border-slate-800 opacity-0 group-hover:opacity-100 transition-opacity text-slate-350 hover:text-white"
                          title="Copy text"
                          type="button"
                        >
                          {copiedId === msg.id ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      )}
                    </div>
                    
                    <div className="flex items-center justify-between text-[9px] text-slate-450 px-1 select-none">
                      <div className="flex items-center gap-1.5">
                        {msg.timestamp && <span>{msg.timestamp}</span>}
                        {msg.role !== 'user' && msg.provider && (
                          <span className="bg-slate-800 text-slate-300 px-1 py-0.2 rounded font-mono uppercase tracking-wider scale-90 border border-slate-700">
                            {msg.provider}
                          </span>
                        )}
                        {msg.role !== 'user' && msg.retrievedCount > 0 && (
                          <span className="flex items-center gap-0.5">
                            • <Layers className="w-2.5 h-2.5" /> {msg.retrievedCount} chunks
                          </span>
                        )}
                      </div>
                      {msg.role !== 'user' && msg.generationTime && (
                        <span className="flex items-center gap-0.5 font-mono">
                          <Clock className="w-2.5 h-2.5" /> {msg.generationTime}s
                        </span>
                      )}
                    </div>
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-lg bg-indigo-650 flex items-center justify-center flex-shrink-0 self-start shadow-md">
                      <User className="w-4 h-4 text-white" />
                    </div>
                  )}
                </div>
              ))}
              {loading && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center flex-shrink-0 self-start animate-pulse">
                    <Bot className="w-4 h-4 text-indigo-400" />
                  </div>
                  <div className="bg-slate-850 border border-slate-750 rounded-2xl rounded-tl-none p-3.5 shadow-md flex items-center gap-2.5">
                    <div className="flex gap-1.5">
                      <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                    <span className="text-xs text-slate-400 select-none">Thinking...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Suggestions & Input */}
            <div className="p-4 border-t border-slate-800 bg-slate-850">
              {messages.length === 1 && !loading && (
                <div className="mb-4">
                  <p className="text-[10px] font-bold text-slate-450 mb-2 tracking-wider uppercase font-mono">
                    Suggested Questions
                  </p>
                  <div className="flex flex-col gap-2">
                    {SUGGESTED_QUESTIONS.map((q) => (
                      <button
                        key={q}
                        onClick={() => handleSend(q)}
                        className="text-left text-xs bg-slate-800 hover:bg-slate-750 p-2.5 rounded-xl border border-slate-700 transition-colors shadow text-slate-200 font-medium"
                        type="button"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend();
                }}
                className="flex items-end gap-2"
              >
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about grants..."
                  disabled={loading}
                  rows={1}
                  className="flex-1 text-sm rounded-xl py-2.5 px-3 bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 resize-none font-sans"
                />
                <button
                  type="submit"
                  disabled={loading || !input.trim()}
                  className="p-2.5 bg-indigo-650 hover:bg-indigo-600 disabled:opacity-50 disabled:bg-slate-800 text-white rounded-xl transition-all shadow"
                >
                  <Send className="w-4 h-4 text-white" />
                </button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Toggle Button */}
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        className="w-14 h-14 bg-gradient-to-r from-indigo-650 to-purple-650 text-white rounded-full shadow-2xl flex items-center justify-center relative overflow-hidden focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
        type="button"
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <X className="w-6 h-6 text-white" />
            </motion.div>
          ) : (
            <motion.div
              key="open"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="flex items-center justify-center"
            >
              <Sparkles className="w-6 h-6 text-white animate-pulse" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  );
}
