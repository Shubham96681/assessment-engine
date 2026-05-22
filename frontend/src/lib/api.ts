import axios from 'axios';

// Call backend directly — avoids Next.js proxy socket hang-ups on file uploads
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

/** Default API timeout (ms). */
export const API_TIMEOUT_MS = 120000;

/** POST /assessments/generate should return immediately (background job runs after). */
export const GENERATE_TIMEOUT_MS = 45000;

/** Poll while status=generating — keep each request short. */
export const STATUS_POLL_TIMEOUT_MS = 12000;

/** Full assessment fetch (may include large generation_log). */
export const ASSESSMENT_FETCH_TIMEOUT_MS = 90000;

/** List all assessments (lightweight, no generation_log). */
export const LIST_ASSESSMENTS_TIMEOUT_MS = 20000;

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT_MS,
});

/** True when backend responds on /health */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const base = getApiBaseUrl();
    const res = await axios.get(`${base}/health`, { timeout: 5000 });
    return res.status === 200;
  } catch {
    return false;
  }
}

export function formatApiError(err: unknown): string {
  if (!err || typeof err !== 'object') return 'Request failed';
  const ax = err as { code?: string; message?: string; response?: { data?: { detail?: string } } };
  if (ax.code === 'ERR_NETWORK' || ax.message === 'Network Error') {
    return (
      'Cannot reach the backend at ' +
      API_BASE_URL +
      '. Start Docker Desktop, run "docker compose up -d" in the docker folder, ' +
      'then start the backend: cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload'
    );
  }
  if (ax.code === 'ECONNABORTED') {
    return (
      'Request timed out. If you clicked Generate, open Assessments in the sidebar — ' +
      'the quiz may still have been created. Otherwise start Docker + backend and retry.'
    );
  }
  const detail = ax.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  return ax.message || 'Request failed';
}

/** Base URL for static files (PDFs, figures) — no /api/v1 suffix */
export const getApiBaseUrl = () =>
  (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1').replace('/api/v1', '');

export const getDashboardStats = async () => {
  const res = await api.get('/analytics/dashboard');
  return res.data;
};

export const uploadDocument = async (
  file: File,
  subject: string,
  classLevel: string,
  pageStart?: number,
  pageEnd?: number,
) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('subject', subject);
  formData.append('class_level', classLevel);
  if (pageStart != null) formData.append('page_start', String(pageStart));
  if (pageEnd != null) formData.append('page_end', String(pageEnd));

  const res = await api.post('/documents/upload', formData, { timeout: 300000 });
  return res.data;
};

export const getDocuments = async () => {
  const res = await api.get('/documents');
  return res.data;
};

export type TheoremCoverage = {
  id: string;
  label?: string;
  archetype_id?: string;
  difficulty?: string;
  importance?: string;
  weight?: number;
  cognitive_type?: string;
  combines_with?: string[];
};

export type TopicProfile = {
  document_id: string;
  primary_topic: string;
  locked_chapter: string;
  locked_chapter_source?: string;
  confidence?: number;
  subject?: string;
  class_level?: string;
  subtopics: string[];
  secondary_chapters?: string[];
  required_theorems?: TheoremCoverage[];
  retrieval_confidence?: number;
  generation_mode?: string;
  sample_pages?: number[];
  chunk_count_used?: number;
  total_chunks_db?: number;
  index_status?: string;
};

export const getDocumentTopicProfile = async (
  documentId: string,
  topicFocus?: string,
) => {
  const params = topicFocus ? { topic_focus: topicFocus } : {};
  const res = await api.get(`/documents/${documentId}/topic-profile`, { params });
  return res.data as TopicProfile;
};

export const generateAssessment = async (config: unknown) => {
  const res = await api.post('/assessments/generate', config, {
    timeout: GENERATE_TIMEOUT_MS,
  });
  return res.data;
};

export const getAssessments = async () => {
  const res = await api.get('/assessments', { timeout: LIST_ASSESSMENTS_TIMEOUT_MS });
  return res.data;
};

export const getAssessmentStatus = async (id: string) => {
  const res = await api.get(`/assessments/${id}/status`, {
    timeout: STATUS_POLL_TIMEOUT_MS,
  });
  return res.data;
};

export const getAssessment = async (id: string) => {
  const res = await api.get(`/assessments/${id}`, {
    timeout: ASSESSMENT_FETCH_TIMEOUT_MS,
  });
  return res.data;
};

export const deleteAssessment = async (id: string) => {
  const res = await api.delete(`/assessments/${id}`);
  return res.data;
};

/** Finish a stuck assessment using rag_response.txt already on disk */
export const applyRagResponse = async (assessmentId: string) => {
  const res = await api.post(`/assessments/${assessmentId}/apply-rag-response`, null, {
    timeout: 180000,
  });
  return res.data;
};

export const submitFeedback = async (feedback: unknown) => {
  const res = await api.post('/feedback', feedback);
  return res.data;
};
