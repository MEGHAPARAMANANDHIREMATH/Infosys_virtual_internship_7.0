import { useState } from 'react';
import { getErrorMessage, uploadDocument } from '../services/api';

const ACCEPTED = '.pdf,.docx,.csv,.txt,.xlsx';

export default function DocumentUpload({ projectId, onUploaded }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [currentFile, setCurrentFile] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const upload = async (file) => {
    if (!file) return;
    setUploading(true);
    setCurrentFile(file.name);
    setError('');
    setSuccess('');
    try {
      const res = await uploadDocument(projectId, file);
      const status = res.data.processing_status;
      if (res.data.duplicate) {
        setSuccess(`${file.name} was already uploaded. Reusing the existing processed file.`);
      } else if (status === 'PROCESSED') {
        setSuccess(`${file.name} processed successfully.`);
      } else if (status === 'FAILED') {
        setError(res.data.error_message || 'Document processing failed. Please retry.');
      } else {
        setSuccess(`${file.name} uploaded. Status: ${status}`);
      }
      onUploaded?.();
    } catch (err) {
      setError(getErrorMessage(err, 'Upload failed'));
    } finally {
      setUploading(false);
    }
  };

  const handleFiles = (fileList) => {
    const files = Array.from(fileList || []);
    files.forEach((file) => upload(file));
  };

  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
      <h2 className="text-lg font-semibold text-slate-800 mb-2">Document Upload</h2>
      <p className="text-sm text-slate-500 mb-4">Supported formats: PDF, DOCX, TXT, XLSX, CSV</p>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`block border-2 border-dashed rounded-xl p-8 text-center cursor-pointer ${
          dragOver ? 'border-blue-500 bg-blue-50' : 'border-slate-300 bg-slate-50'
        }`}
      >
        <p className="text-slate-700 font-medium">
          {uploading ? `Uploading ${currentFile}...` : 'Drag and drop a file, or click to select'}
        </p>
        <p className="text-xs text-slate-500 mt-2">PDF, DOCX, TXT, XLSX, or CSV</p>
        <input
          type="file"
          accept={ACCEPTED}
          className="hidden"
          disabled={uploading}
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = '';
          }}
        />
      </label>
      {currentFile && (
        <p className="text-sm text-slate-600 mt-3">
          Selected: {currentFile} {uploading ? '· uploading' : ''}
        </p>
      )}
      {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
      {success && <p className="text-emerald-700 text-sm mt-2">{success}</p>}
    </section>
  );
}
