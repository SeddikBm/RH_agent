/**
 * Client API — Wrapper autour de fetch pour communiquer avec le backend FastAPI.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '/api';

async function request(method, path, body = null, isFormData = false) {
  const options = {
    method,
    headers: {},
  };

  if (body !== null) {
    if (isFormData) {
      options.body = body;
    } else {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
  }

  const response = await fetch(`${BASE_URL}${path}`, options);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Erreur réseau' }));
    const error = new Error(errorData.detail || `Erreur HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) return null;
  return response.json();
}

// ── CVs ────────────────────────────────────────────────────

export const cvApi = {
  upload: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('POST', '/cv/upload', formData, true);
  },
  list: () => request('GET', '/cv/list'),
  get: (id) => request('GET', `/cv/${id}`),
  delete: (id) => request('DELETE', `/cv/${id}`),
};

// ── Fiches de Poste ────────────────────────────────────────

export const jobApi = {
  extract: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return request('POST', '/jobs/extract', formData, true);
  },
  create: (data) => request('POST', '/jobs', data),
  list: () => request('GET', '/jobs/list'),
  get: (id) => request('GET', `/jobs/${id}`),
  update: (id, data) => request('PUT', `/jobs/${id}`, data),
  delete: (id) => request('DELETE', `/jobs/${id}`),
};

// ── Analyses ───────────────────────────────────────────────

export const analysisApi = {
  // Analyse individuelle (compatibilité)
  run: (cvId, jobId) => request('POST', '/analysis/run', { cv_id: cvId, job_id: jobId }),

  // Batch : N CVs × 1 Job → RAG
  runBatch: (jobId, cvIds) => request('POST', '/analysis/run-batch', { job_id: jobId, cv_ids: cvIds }),

  // Lancement LangGraph pour le Top X sélectionné
  runLanggraph: (batchId, cvIds) => request('POST', '/analysis/run-langgraph', { batch_id: batchId, cv_ids: cvIds }),

  // Consultation d'un batch
  getBatch: (batchId) => request('GET', `/analysis/batch/${batchId}`),

  // Classement RAG pour un poste
  ranking: (jobId) => request('GET', `/analysis/ranking/${jobId}`),

  // Analyses filtrées par poste
  byJob: (jobId) => request('GET', `/analysis/by-job/${jobId}`),

  // Batches (historique) par poste
  batchesByJob: (jobId) => request('GET', `/analysis/batches/by-job/${jobId}`),

  // Consultation et export
  get: (id) => request('GET', `/analysis/${id}`),
  list: () => request('GET', '/analysis/list/all'),
  delete: (id) => request('DELETE', `/analysis/${id}`),

  downloadPdf: async (id) => {
    const response = await fetch(`${BASE_URL}/analysis/${id}/pdf`);
    if (!response.ok) throw new Error('Erreur lors du téléchargement du PDF');
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = `rapport_${id}.pdf`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  },
};

// ── Polling utilitaire ─────────────────────────────────────

/**
 * Poll l'état d'une analyse jusqu'à ce qu'elle soit terminée ou en erreur.
 */
export function pollAnalysis(analyseId, onUpdate, intervalMs = 2000) {
  let stopped = false;

  const poll = async () => {
    if (stopped) return;
    try {
      const data = await analysisApi.get(analyseId);
      onUpdate(data);
      if (data.statut === 'en_cours' || data.statut === 'en_attente') {
        setTimeout(poll, intervalMs);
      }
    } catch (err) {
      console.error('Erreur polling:', err);
    }
  };

  poll();
  return () => { stopped = true; };
}

/**
 * Poll l'état d'un batch jusqu'à ce qu'il soit terminé ou en erreur.
 */
export function pollBatch(batchId, onUpdate, intervalMs = 3000) {
  let stopped = false;

  const poll = async () => {
    if (stopped) return;
    try {
      const data = await analysisApi.getBatch(batchId);
      onUpdate(data);
      if (data.statut === 'en_cours') {
        setTimeout(poll, intervalMs);
      }
    } catch (err) {
      console.error('Erreur polling batch:', err);
    }
  };

  poll();
  return () => { stopped = true; };
}
