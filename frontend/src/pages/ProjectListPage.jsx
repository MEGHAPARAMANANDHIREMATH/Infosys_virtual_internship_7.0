import { useEffect, useState } from 'react';
import CreateProjectForm from '../components/CreateProjectForm';
import { getErrorMessage, getProjects } from '../services/api';

export default function ProjectListPage({ onOpenProject }) {
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const loadProjects = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await getProjects();
      setProjects(res.data);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load projects'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <div className="space-y-6">
      <CreateProjectForm onCreated={(project) => setProjects((prev) => [project, ...prev])} />

      <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800">Projects</h2>
          <button
            type="button"
            onClick={loadProjects}
            className="text-sm border border-slate-300 px-3 py-1.5 rounded-lg hover:bg-slate-50"
          >
            Refresh
          </button>
        </div>
        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}
        {loading ? (
          <p className="text-slate-500 text-sm">Loading projects...</p>
        ) : projects.length === 0 ? (
          <p className="text-slate-500 text-sm">No projects yet. Create one to start uploading documents.</p>
        ) : (
          <div className="space-y-3">
            {projects.map((project) => (
              <article
                key={project.id}
                className="border border-slate-200 rounded-lg p-4 flex flex-col md:flex-row md:items-center gap-3 justify-between"
              >
                <div>
                  <h3 className="font-semibold text-slate-900">{project.name}</h3>
                  <p className="text-sm text-slate-600 mt-1">
                    {project.description || 'No description'}
                  </p>
                  <p className="text-xs text-slate-500 mt-2">
                    {project.start_date || 'No start date'} → {project.end_date || 'No end date'} · {project.status}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => onOpenProject(project)}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
                >
                  Open Project
                </button>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
