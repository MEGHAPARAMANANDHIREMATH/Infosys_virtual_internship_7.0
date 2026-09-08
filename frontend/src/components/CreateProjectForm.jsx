import { useState } from 'react';
import { createProject, getErrorMessage } from '../services/api';

const STATUSES = ['PLANNING', 'ACTIVE', 'ON_HOLD', 'COMPLETED'];

export default function CreateProjectForm({ onCreated }) {
  const [form, setForm] = useState({
    name: '',
    description: '',
    start_date: '',
    end_date: '',
    status: 'PLANNING',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.name.trim()) return;
    setLoading(true);
    setError('');
    try {
      const payload = {
        ...form,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
      };
      const res = await createProject(payload);
      onCreated?.(res.data);
      setForm({
        name: '',
        description: '',
        start_date: '',
        end_date: '',
        status: 'PLANNING',
      });
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to create project'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h2 className="text-lg font-semibold text-slate-800 mb-4">Create Project</h2>
      <form onSubmit={handleSubmit} className="grid gap-3 md:grid-cols-2">
        <input
          required
          value={form.name}
          onChange={(e) => update('name', e.target.value)}
          placeholder="Project name"
          className="md:col-span-2 border border-slate-300 rounded-lg px-3 py-2"
        />
        <textarea
          value={form.description}
          onChange={(e) => update('description', e.target.value)}
          placeholder="Description"
          rows={3}
          className="md:col-span-2 border border-slate-300 rounded-lg px-3 py-2"
        />
        <label className="text-sm text-slate-600">
          Start date
          <input
            type="date"
            value={form.start_date}
            onChange={(e) => update('start_date', e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2"
          />
        </label>
        <label className="text-sm text-slate-600">
          Expected completion date
          <input
            type="date"
            value={form.end_date}
            onChange={(e) => update('end_date', e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2"
          />
        </label>
        <label className="text-sm text-slate-600 md:col-span-2">
          Status
          <select
            value={form.status}
            onChange={(e) => update('status', e.target.value)}
            className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2"
          >
            {STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
        {error && <p className="md:col-span-2 text-red-600 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={loading || !form.name.trim()}
          className="md:col-span-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Creating...' : 'Create Project'}
        </button>
      </form>
    </section>
  );
}
