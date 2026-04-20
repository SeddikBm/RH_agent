import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { analysisApi, jobApi } from '../api/client';
import { Search, Trash2, ChevronDown, ChevronUp, Briefcase, Clock, Loader } from 'lucide-react';
import toast from 'react-hot-toast';

const STATUS_CONFIG = {
  termine: { label: 'Terminé', class: 'badge-success' },
  en_cours: { label: 'En cours', class: 'badge-info' },
  en_attente: { label: 'En attente', class: 'badge-neutral' },
  erreur: { label: 'Erreur', class: 'badge-danger' },
};

const REC_CONFIG = {
  'Entretien recommandé': { class: 'badge-success', short: '✓ Entretien' },
  'À considérer': { class: 'badge-warning', short: '⟳ À considérer' },
  'Profil insuffisant': { class: 'badge-danger', short: '✗ Insuffisant' },
};

function ScoreBadge({ score }) {
  if (score == null) return <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>—</span>;
  const color = score >= 70 ? 'var(--color-success)' : score >= 50 ? 'var(--color-warning)' : 'var(--color-danger)';
  return (
    <span style={{ fontSize: 22, fontWeight: 800, color, fontFamily: 'var(--font-mono, monospace)' }}>
      {score.toFixed(0)}
    </span>
  );
}

function AnalysisRow({ a, onDelete, onClick }) {
  const statusConf = STATUS_CONFIG[a.statut] || STATUS_CONFIG.en_attente;
  const recConf = a.recommandation ? REC_CONFIG[a.recommandation] : null;
  const medals = ['🥇', '🥈', '🥉'];

  return (
    <div
      onClick={onClick}
      style={{
        display: 'grid',
        gridTemplateColumns: '32px 1fr 200px 100px 140px 110px 48px',
        alignItems: 'center',
        padding: '14px 16px',
        background: 'var(--gradient-card)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-lg)',
        cursor: a.statut === 'termine' ? 'pointer' : 'default',
        transition: 'var(--transition-base)',
        gap: 0,
      }}
      className="analysis-list-item"
      onMouseEnter={e => { if (a.statut === 'termine') e.currentTarget.style.borderColor = 'var(--color-border-bright)'; }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--color-border)'; }}
    >
      {/* Rang */}
      <div style={{ fontSize: 18, textAlign: 'center' }}>
        {a.rang && a.rang <= 3 ? medals[a.rang - 1] : (a.rang ? `#${a.rang}` : '—')}
      </div>

      {/* Candidat */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0, paddingLeft: 8 }}>
        <div className="analysis-avatar" style={{ width: 36, height: 36, fontSize: 14, flexShrink: 0 }}>
          {(a.nom_candidat || '?')[0].toUpperCase()}
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {a.nom_candidat || 'Anonyme'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
            {a.date_creation ? new Date(a.date_creation).toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit', year: '2-digit' }) : ''}
          </div>
        </div>
      </div>

      {/* Recommandation */}
      <div>
        {recConf
          ? <span className={`badge ${recConf.class}`}>{recConf.short}</span>
          : <span style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>—</span>}
      </div>

      {/* Score */}
      <div><ScoreBadge score={a.score_global} /></div>

      {/* Statut */}
      <div>
        <span className={`badge ${statusConf.class}`}>
          {a.statut === 'en_cours' && <span className="spinner" style={{ width: 10, height: 10, marginRight: 4 }} />}
          {statusConf.label}
        </span>
      </div>

      {/* Durée */}
      <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
        {a.duree_secondes ? `${a.duree_secondes.toFixed(0)}s` : '—'}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 4 }}>
        <button
          className="btn btn-icon btn-danger btn-sm"
          onClick={(e) => { e.stopPropagation(); onDelete(a.id); }}
          title="Supprimer"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}

export default function Analyses() {
  const [analyses, setAnalyses] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedJobs, setExpandedJobs] = useState({});
  const [filterJobId, setFilterJobId] = useState('');
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const load = () => {
    setLoading(true);
    Promise.all([analysisApi.list(), jobApi.list()])
      .then(([a, j]) => {
        setAnalyses(a);
        setJobs(j);
        // Auto-expand all job groups initially
        const expanded = {};
        j.forEach(job => { expanded[job.id] = true; });
        setExpandedJobs(expanded);
      })
      .catch(() => toast.error('Erreur chargement des analyses'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    // Read ?job= param from URL for auto-filter after redirect from Upload
    const jobParam = searchParams.get('job');
    if (jobParam) setFilterJobId(jobParam);
    load();
  }, []); // eslint-disable-line

  // Auto-refresh every 5s if any analysis is in-progress
  useEffect(() => {
    const hasInProgress = analyses.some(a => a.statut === 'en_cours' || a.statut === 'en_attente');
    if (!hasInProgress) return;
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [analyses]);

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cette analyse ?')) return;
    try {
      await analysisApi.delete(id);
      toast.success('Analyse supprimée');
      load();
    } catch {
      toast.error('Erreur suppression');
    }
  };

  const toggleJob = (jobId) => {
    setExpandedJobs(prev => ({ ...prev, [jobId]: !prev[jobId] }));
  };

  // Group analyses by job
  const filteredAnalyses = analyses.filter(a => {
    const matchSearch = !search ||
      (a.nom_candidat?.toLowerCase().includes(search.toLowerCase())) ||
      (a.titre_poste?.toLowerCase().includes(search.toLowerCase()));
    const matchJob = !filterJobId || a.job_id === filterJobId;
    return matchSearch && matchJob;
  });

  // Build job groups
  const jobGroups = jobs
    .filter(job => !filterJobId || job.id === filterJobId)
    .map(job => {
      const jobAnalyses = filteredAnalyses
        .filter(a => a.job_id === job.id)
        .sort((a, b) => {
          // In-progress first, then by score desc, then by rank
          if (a.statut === 'en_cours' && b.statut !== 'en_cours') return -1;
          if (b.statut === 'en_cours' && a.statut !== 'en_cours') return 1;
          if (a.rang != null && b.rang != null) return a.rang - b.rang;
          return (b.score_global || 0) - (a.score_global || 0);
        });
      return { job, analyses: jobAnalyses };
    })
    .filter(g => g.analyses.length > 0);

  // Analyses not linked to any known job
  const knownJobIds = new Set(jobs.map(j => j.id));
  const orphanAnalyses = filteredAnalyses.filter(a => !knownJobIds.has(a.job_id));

  const inProgressCount = analyses.filter(a => a.statut === 'en_cours').length;

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
          <h1 className="page-title">Analyses par Poste</h1>
          {inProgressCount > 0 && (
            <span style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--color-primary-light)' }}>
              <Loader size={14} style={{ animation: 'spin 1s linear infinite' }} />
              {inProgressCount} en cours…
            </span>
          )}
        </div>
        <p className="page-subtitle">Résultats groupés par fiche de poste</p>
      </div>

      {/* ── Filtres ── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 220 }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
          <input
            className="form-input"
            style={{ paddingLeft: 36 }}
            placeholder="Rechercher un candidat..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select
          className="form-input"
          style={{ maxWidth: 260 }}
          value={filterJobId}
          onChange={e => setFilterJobId(e.target.value)}
        >
          <option value="">Tous les postes</option>
          {jobs.map(j => (
            <option key={j.id} value={j.id}>{j.titre}</option>
          ))}
        </select>
      </div>

      {/* ── Contenu ── */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {[1, 2].map(i => <div key={i} className="skeleton" style={{ height: 160, borderRadius: 12 }} />)}
        </div>
      ) : jobGroups.length === 0 && orphanAnalyses.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <div className="empty-state-title">Aucune analyse trouvée</div>
          <p className="empty-state-text">
            {search || filterJobId ? 'Modifiez vos filtres' : 'Lancez votre première analyse depuis la page Upload'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {jobGroups.map(({ job, analyses: jobAnalyses }) => {
            const isOpen = expandedJobs[job.id] !== false;
            const terminated = jobAnalyses.filter(a => a.statut === 'termine');
            const inProg = jobAnalyses.filter(a => a.statut === 'en_cours' || a.statut === 'en_attente');
            const bestScore = terminated.length > 0 ? Math.max(...terminated.map(a => a.score_global || 0)) : null;

            return (
              <div key={job.id} className="card" style={{ padding: 0, overflow: 'hidden' }}>
                {/* Job header */}
                <div
                  onClick={() => toggleJob(job.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 14,
                    padding: '16px 20px',
                    cursor: 'pointer',
                    background: 'rgba(99,102,241,0.04)',
                    borderBottom: isOpen ? '1px solid var(--color-border)' : 'none',
                    userSelect: 'none',
                  }}
                >
                  <div style={{
                    width: 38, height: 38, borderRadius: 'var(--radius-md)',
                    background: 'rgba(99,102,241,0.15)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <Briefcase size={18} color="var(--color-primary-light)" />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text-primary)' }}>{job.titre}</div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>
                      {[job.entreprise, job.type_contrat, job.localisation].filter(Boolean).join(' · ')}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span className="badge badge-neutral" style={{ fontSize: 11 }}>{jobAnalyses.length} analyse{jobAnalyses.length > 1 ? 's' : ''}</span>
                    {inProg.length > 0 && (
                      <span className="badge badge-info" style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Clock size={10} /> {inProg.length} en cours
                      </span>
                    )}
                    {bestScore != null && (
                      <span style={{
                        fontSize: 14, fontWeight: 800,
                        color: bestScore >= 70 ? 'var(--color-success)' : bestScore >= 50 ? 'var(--color-warning)' : 'var(--color-danger)',
                      }}>
                        Top: {bestScore.toFixed(0)}/100
                      </span>
                    )}
                    {isOpen ? <ChevronUp size={18} color="var(--color-text-muted)" /> : <ChevronDown size={18} color="var(--color-text-muted)" />}
                  </div>
                </div>

                {/* Analyses list */}
                {isOpen && (
                  <div style={{ padding: '12px 16px 16px' }}>
                    {/* Column header */}
                    <div style={{
                      display: 'grid',
                      gridTemplateColumns: '32px 1fr 200px 100px 140px 110px 48px',
                      padding: '4px 16px 8px',
                      fontSize: 10, fontWeight: 700,
                      color: 'var(--color-text-muted)',
                      textTransform: 'uppercase', letterSpacing: '0.08em',
                    }}>
                      <span style={{ textAlign: 'center' }}>Rang</span>
                      <span style={{ paddingLeft: 46 }}>Candidat</span>
                      <span>Recommandation</span>
                      <span>Score</span>
                      <span>Statut</span>
                      <span>Durée</span>
                      <span />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {jobAnalyses.map(a => (
                        <AnalysisRow
                          key={a.id}
                          a={a}
                          onDelete={handleDelete}
                          onClick={() => { if (a.statut === 'termine') navigate(`/analyses/${a.id}`); }}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}

          {/* Orphan analyses (job deleted) */}
          {orphanAnalyses.length > 0 && (
            <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '14px 20px', background: 'rgba(148,163,184,0.05)', borderBottom: '1px solid var(--color-border)' }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-muted)' }}>Poste supprimé</span>
              </div>
              <div style={{ padding: '12px 16px 16px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                {orphanAnalyses.map(a => (
                  <AnalysisRow
                    key={a.id}
                    a={a}
                    onDelete={handleDelete}
                    onClick={() => { if (a.statut === 'termine') navigate(`/analyses/${a.id}`); }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
