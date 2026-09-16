import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
});

export const getErrorMessage = (error, fallback = 'Request failed') =>
  error?.response?.data?.error || error?.response?.data?.detail || fallback;

export const healthCheck = () => api.get('/api/health/');

export const getProjects = () => api.get('/api/projects/');

export const createProject = (data) => api.post('/api/projects/', data);

export const getProject = (id) => api.get(`/api/projects/${id}/`);

export const updateProject = (id, data) => api.put(`/api/projects/${id}/`, data);

export const deleteProject = (id) => api.delete(`/api/projects/${id}/`);

export const getDocuments = (projectId) =>
  api.get(`/api/projects/${projectId}/documents/`);

export const uploadDocument = (projectId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post(`/api/projects/${projectId}/documents/`, formData, { timeout: 120000 });
};

export const deleteDocument = (documentId) =>
  api.delete(`/api/documents/${documentId}/`);

export const searchProject = (projectId, query, topK = 5) =>
  api.post(`/api/projects/${projectId}/search/`, { query, top_k: topK });

export const analyzeDocument = (projectId, { documentId, agents = 'all', file } = {}) => {
  if (file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('agents', agents);
    return api.post(`/api/projects/${projectId}/intelligence/`, formData, { timeout: 120000 });
  }
  return api.post(`/api/projects/${projectId}/intelligence/`, {
    document_id: documentId,
    agents,
  }, { timeout: 120000 });
};

export const getLatestAnalysis = (projectId, documentId) =>
  api.get(`/api/projects/${projectId}/intelligence/`, { params: { document_id: documentId } });

export default api;
