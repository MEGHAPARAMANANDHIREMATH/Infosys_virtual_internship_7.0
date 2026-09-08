import { useCallback, useEffect, useState } from 'react';
import DocumentUpload from '../components/DocumentUpload';
import DocumentList from '../components/DocumentList';
import SemanticSearch from '../components/SemanticSearch';
import { getDocuments, getErrorMessage, getProject } from '../services/api';

export default function ProjectWorkspacePage({ project, onBack, onProjectUpdated }) {
  const [documents, setDocuments] = useState([]);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const [docsRes, projectRes] = await Promise.all([
        getDocuments(project.id),
        getProject(project.id),
      ]);
      setDocuments(docsRes.data);
      onProjectUpdated?.(projectRes.data);
      setError('');
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load project workspace'));
    }
  }, [project.id, onProjectUpdated]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <div className="space-y-6">
      <button type="button" onClick={onBack} className="text-sm text-blue-700 hover:underline">
        ← Back to projects
      </button>

      <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-xl font-semibold text-slate-900">{project.name}</h2>
        <p className="text-slate-600 mt-1">{project.description || 'No description'}</p>
        <p className="text-sm text-slate-500 mt-2">
          {project.start_date || 'No start date'} → {project.end_date || 'No end date'} · {project.status}
        </p>
      </section>

      {error && <p className="text-red-600 text-sm">{error}</p>}

      <DocumentUpload projectId={project.id} onUploaded={refresh} />
      <DocumentList documents={documents} onChanged={refresh} />
      <SemanticSearch projectId={project.id} />
    </div>
  );
}
