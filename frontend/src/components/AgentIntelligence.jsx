import { analyzeDocument, getErrorMessage, getLatestAnalysis, uploadDocument } from '../services/api';
import AgentResultsDashboard from './AgentResultsDashboard';
import { useMemo, useState } from 'react';

const AGENT_OPTIONS = [
  { id: 'scope', label: 'Scope & Deliverables' },
  { id: 'risk', label: 'Risk & Delivery Forecast' },
  { id: 'blockers', label: 'Blockers & Action Items' },
  { id: 'all', label: 'Run All Agents' },
];

const ACCEPTED = '.pdf,.docx,.csv,.txt,.xlsx';

export default function AgentIntelligence({ projectId, documents, onDocumentsChanged }) {
  const processed = useMemo(
    () => documents.filter((doc) => doc.processing_status === 'PROCESSED'),
    [documents]
  );
  const [documentId, setDocumentId] = useState('');
  const [pendingFile, setPendingFile] = useState(null);
  const [sourceName, setSourceName] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const selectedProcessed = processed.find((doc) => String(doc.id) === String(documentId));

  const runAgents = async (agent, file) => {
    setLoading(true);
    setError('');
    setStatus(
      agent === 'all'
        ? 'Extracting document text and running all agents...'
        : `Extracting document text and running the ${agent} agent...`
    );
    try {
      let payload;
      if (file) {
        setStatus(`Uploading and validating ${file.name}...`);
        const uploaded = await uploadDocument(projectId, file);
        onDocumentsChanged?.();
        if (uploaded.data.duplicate) {
          setStatus('Duplicate file detected. Reusing the existing processed document...');
        }
        if (uploaded.data.processing_status === 'FAILED') {
          throw new Error(uploaded.data.error_message || 'Document processing failed. Please retry.');
        }
        setDocumentId(String(uploaded.data.id));
        setSourceName(uploaded.data.file_name);
        setStatus('Running AI agent analysis on extracted text...');
        const analysis = await analyzeDocument(projectId, {
          documentId: uploaded.data.id,
          agents: agent,
        });
        payload = analysis.data;
      } else {
        if (!documentId) {
          setError('Select a processed document or upload a file.');
          setLoading(false);
          return;
        }
        const analysis = await analyzeDocument(projectId, {
          documentId,
          agents: agent,
        });
        payload = analysis.data;
        setSourceName(payload.file_name || selectedProcessed?.file_name || '');
      }
      setResult(payload);
      setSourceName(payload.file_name || sourceName);
      if (payload.errors && Object.keys(payload.errors).length) {
        setError(Object.values(payload.errors).join(' '));
        setStatus('Analysis finished with errors.');
      } else {
        setStatus(`Analysis complete using ${payload.provider || 'grounded'} extraction.`);
      }
    } catch (err) {
      setResult(null);
      setError(err?.message?.startsWith('Document processing') ? err.message : getErrorMessage(err, 'Document analysis failed. Please retry.'));
      setStatus('');
    } finally {
      setLoading(false);
    }
  };

  const loadStored = async (id) => {
    setDocumentId(id);
    const doc = processed.find((item) => String(item.id) === String(id));
    setSourceName(doc?.file_name || '');
    if (!id) {
      setResult(null);
      return;
    }
    try {
      const stored = await getLatestAnalysis(projectId, id);
      setResult(stored.data);
      setError('');
    } catch {
      setResult(null);
    }
  };

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-800">Document Intelligence</h2>
        <p className="text-sm text-slate-500 mt-1">
          Milestone 2 — extract scope, risks, delivery forecast, blockers, and action items from an
          uploaded project document.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-sm text-slate-600">
          Source document
          <select
            value={documentId}
            onChange={(e) => loadStored(e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2"
          >
            <option value="">Select a processed document</option>
            {processed.map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.file_name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-slate-600">
          Or upload a document
          <input
            type="file"
            accept={ACCEPTED}
            disabled={loading}
            className="mt-1 w-full text-sm"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = '';
              if (file) {
                setPendingFile(file);
                setSourceName(file.name);
                setError('');
                setStatus(`${file.name} selected. Choose an agent or Run All Agents.`);
              }
            }}
          />
          <span className="block text-xs text-slate-500 mt-1">
            PDF, DOCX, TXT, XLSX, CSV
            {pendingFile ? ` · ready: ${pendingFile.name}` : ''}
          </span>
        </label>
      </div>

      <div className="flex flex-wrap gap-2">
        {AGENT_OPTIONS.map((option) => (
          <button
            key={option.id}
            type="button"
            disabled={loading}
            onClick={() => runAgents(option.id, pendingFile)}
            className={`px-3 py-2 rounded-lg text-sm ${
              option.id === 'all'
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'border border-slate-300 hover:bg-slate-50'
            } disabled:opacity-50`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-blue-700">
          <span className="inline-block w-3 h-3 rounded-full bg-blue-500 animate-pulse" />
          {status || 'Processing...'}
        </div>
      )}
      {!loading && status && <p className="text-sm text-emerald-700">{status}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      <AgentResultsDashboard result={result} sourceName={sourceName} loading={loading} />
    </section>
  );
}
