import { useState } from 'react';
import { getErrorMessage, searchProject } from '../services/api';

export default function SemanticSearch({ projectId }) {
  const [query, setQuery] = useState('What are the main project requirements?');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);

  const handleSearch = async (event) => {
    event.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    setResults(null);
    try {
      const res = await searchProject(projectId, query, 5);
      setResults(res.data);
    } catch (err) {
      setError(getErrorMessage(err, 'Unable to perform semantic search. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h2 className="text-lg font-semibold text-slate-800 mb-4">Semantic Search</h2>
      <form onSubmit={handleSearch} className="flex flex-col sm:flex-row gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What are the main project requirements?"
          className="flex-1 border border-slate-300 rounded-lg px-3 py-2"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>
      {error && <p className="text-red-600 text-sm mt-3">{error}</p>}
      {results && (
        <div className="mt-4 space-y-3">
          {results.results.length === 0 ? (
            <p className="text-sm text-slate-500">No matching chunks were found for this project.</p>
          ) : (
            results.results.map((item) => (
              <article key={item.chunk_id} className="border border-slate-200 rounded-lg p-4">
                <p className="text-sm font-medium text-slate-800">{item.file_name}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {item.page_number != null ? `Page ${item.page_number} · ` : ''}
                  Score {item.score != null ? item.score : 'n/a'}
                </p>
                <p className="text-sm text-slate-700 mt-2 whitespace-pre-wrap">{item.content}</p>
              </article>
            ))
          )}
        </div>
      )}
    </section>
  );
}
