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
  create: (data) => request('POST', '/jobs', data),
  list: () => request('GET', '/jobs/list'),
  get: (id) => request('GET', `/jobs/${id}`),
  update: (id, data) => request('PUT', `/jobs/${id}`, data),
  delete: (id) => request('DELETE', `/jobs/${id}`),
};

// ── Analyses ───────────────────────────────────────────────

export const analysisApi = {
  run: (cvId, jobId) => request('POST', '/analysis/run', { cv_id: cvId, job_id: jobId }),
  get: (id) => request('GET', `/analysis/${id}`),
  list: () => request('GET', '/analysis/list/all'),
  delete: (id) => request('DELETE', `/analysis/${id}`),
};

// ── Polling utilitaire ─────────────────────────────────────

/**
 * Poll l'état d'une analyse jusqu'à ce qu'elle soit terminée ou en erreur.
 * @param {string} analyseId
 * @param {function} onUpdate - appelé à chaque mise à jour
 * @param {number} intervalMs - intervalle de polling en ms
 * @returns {function} stopPolling - fonction pour arrêter le polling
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
