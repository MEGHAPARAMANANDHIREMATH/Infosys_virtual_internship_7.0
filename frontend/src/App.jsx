import { useEffect, useState } from 'react';
import { healthCheck } from './services/api';
import ProjectListPage from './pages/ProjectListPage';
import ProjectWorkspacePage from './pages/ProjectWorkspacePage';

export default function App() {
  const [selectedProject, setSelectedProject] = useState(null);
  const [apiStatus, setApiStatus] = useState('checking');

  useEffect(() => {
    healthCheck()
      .then(() => setApiStatus('connected'))
      .catch(() => setApiStatus('disconnected'));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              AI Project Intelligence & Risk Advisor
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Milestone 2 — Document intelligence, risk, and action-item analysis
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <span
              className={`inline-block w-2.5 h-2.5 rounded-full ${
                apiStatus === 'connected'
                  ? 'bg-emerald-500'
                  : apiStatus === 'disconnected'
                    ? 'bg-red-500'
                    : 'bg-amber-400'
              }`}
            />
            Backend {apiStatus === 'connected' ? 'connected' : apiStatus}
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        {selectedProject ? (
          <ProjectWorkspacePage
            project={selectedProject}
            onBack={() => setSelectedProject(null)}
            onProjectUpdated={setSelectedProject}
          />
        ) : (
          <ProjectListPage onOpenProject={setSelectedProject} />
        )}
      </main>
    </div>
  );
}
