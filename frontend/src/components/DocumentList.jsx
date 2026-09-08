import { deleteDocument, getErrorMessage } from '../services/api';

const STATUS_STYLES = {
  UPLOADED: 'bg-slate-100 text-slate-700',
  PROCESSING: 'bg-amber-100 text-amber-800',
  PROCESSED: 'bg-emerald-100 text-emerald-800',
  FAILED: 'bg-red-100 text-red-800',
};

export default function DocumentList({ documents, onChanged }) {
  const handleDelete = async (id) => {
    try {
      await deleteDocument(id);
      onChanged?.();
    } catch (err) {
      alert(getErrorMessage(err, 'Failed to delete document'));
    }
  };

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h2 className="text-lg font-semibold text-slate-800 mb-4">Uploaded Documents</h2>
      {documents.length === 0 ? (
        <p className="text-sm text-slate-500">No documents uploaded yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-2 pr-3">Filename</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Upload status</th>
                <th className="py-2 pr-3">Processing</th>
                <th className="py-2 pr-3">Chunks</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-b border-slate-100">
                  <td className="py-2 pr-3 font-medium">{doc.file_name}</td>
                  <td className="py-2 pr-3 uppercase">{doc.file_type}</td>
                  <td className="py-2 pr-3">Stored</td>
                  <td className="py-2 pr-3">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        STATUS_STYLES[doc.processing_status] || STATUS_STYLES.UPLOADED
                      }`}
                    >
                      {doc.processing_status}
                    </span>
                    {doc.processing_status === 'FAILED' && doc.error_message && (
                      <p className="text-xs text-red-600 mt-1">{doc.error_message}</p>
                    )}
                  </td>
                  <td className="py-2 pr-3">{doc.chunk_count ?? 0}</td>
                  <td className="py-2">
                    <button
                      type="button"
                      onClick={() => handleDelete(doc.id)}
                      className="text-red-600 hover:text-red-800 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
