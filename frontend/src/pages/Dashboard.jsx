import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  FileText, CheckCircle,
  TrendingUp, Zap, Briefcase, ArrowRight
} from 'lucide-react';

import { analysisApi, jobApi, cvApi } from '../api/client';

const RECOMMANDATION_CONFIG = {
  'Entretien recommandé': { class: 'badge-success', label: '✓ Entretien' },
  'À considérer': { class: 'badge-warning', label: '⟳ À considérer' },
  'Profil insuffisant': { class: 'badge-danger', label: '✗ Insuffisant' },
};

function StatCard({ icon: Icon, value, label, colorClass }) {
  return (
    <div className="stat-card animate-fade-in">
      <div className={`stat-icon ${colorClass}`}><Icon size={22} /></div>
      <div className="stat-content">
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [analyses, setAnalyses] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [cvCount, setCvCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      analysisApi.list(),
      jobApi.list(),
      cvApi.list(),
    ])
      .then(([a, j, c]) => {
        setAnalyses(a);
        setJobs(j);
        setCvCount(c.length);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const terminated = analyses.filter(a => a.statut === 'termine');
  const avgScore = terminated.length > 0
    ? (terminated.reduce((s, a) => s + (a.score_global || 0), 0) / terminated.length).toFixed(0)
    : '--';

  // Top candidats par poste (basé sur les analyses avec rang)
  const topByJob = jobs.map(job => {
    const jobAnalyses = terminated
      .filter(a => a.job_id === job.id && a.rang != null)
      .sort((a, b) => a.rang - b.rang)
      .slice(0, 3);
    return { job, candidates: jobAnalyses };
  }).filter(entry => entry.candidates.length > 0);

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Tableau de Bord</h1>
        <p className="page-subtitle">Vue d'ensemble de vos analyses de candidatures</p>
      </div>

      {/* ── Stats ── */}
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <StatCard icon={FileText} value={cvCount} label="CVs dans la base" colorClass="purple" />
        <StatCard icon={Briefcase} value={jobs.length} label="Postes actifs" colorClass="cyan" />
        <StatCard icon={CheckCircle} value={terminated.length} label="Analyses terminées" colorClass="green" />
        <StatCard icon={TrendingUp} value={avgScore} label="Score moyen" colorClass="orange" />
      </div>

      {/* ── Classement par Poste ── */}
      {topByJob.length > 0 && (
        <div style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)' }}>
              🏆 Top Candidats par Poste
            </h2>
            <button className="btn btn-sm btn-secondary" onClick={() => navigate('/upload')}>
              <Zap size={13} /> Nouvelle Analyse
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {topByJob.map(({ job, candidates }) => (
              <div key={job.id} className="card">
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                  <div style={{
                    width: 32, height: 32, borderRadius: 'var(--radius-sm)',
                    background: 'rgba(99,102,241,0.15)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <Briefcase size={16} color="var(--color-primary-light)" />
                  </div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)' }}>{job.titre}</div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{job.entreprise || 'Entreprise non renseignée'}</div>
                  </div>
                  <button
                    className="btn btn-sm btn-secondary"
                    style={{ marginLeft: 'auto' }}
                    onClick={() => navigate(`/analyses?job=${job.id}`)}
                  >
                    Voir tout <ArrowRight size={12} />
                  </button>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {candidates.map((a, i) => {
                    const medals = ['🥇', '🥈', '🥉'];
                    const rec = RECOMMANDATION_CONFIG[a.recommandation];
                    return (
                      <div
                        key={a.id}
                        onClick={() => navigate(`/analyses/${a.id}`)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 10,
                          padding: '8px 12px',
                          background: i === 0 ? 'rgba(245,158,11,0.06)' : 'var(--color-bg-secondary)',
                          borderRadius: 'var(--radius-md)',
                          border: `1px solid ${i === 0 ? 'rgba(245,158,11,0.2)' : 'var(--color-border)'}`,
                          cursor: 'pointer',
                          transition: 'var(--transition-base)',
                        }}
                        onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-border-bright)'}
                        onMouseLeave={e => e.currentTarget.style.borderColor = i === 0 ? 'rgba(245,158,11,0.2)' : 'var(--color-border)'}
                      >
                        <span style={{ fontSize: 18 }}>{medals[i]}</span>
                        <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                          {a.nom_candidat || 'Candidat'}
                        </span>
                        {a.score_global != null && (
                          <span style={{
                            fontSize: 15, fontWeight: 800,
                            color: a.score_global >= 70 ? 'var(--color-success)' : a.score_global >= 50 ? 'var(--color-warning)' : 'var(--color-danger)',
                          }}>
                            {a.score_global.toFixed(0)}/100
                          </span>
                        )}
                        {rec && <span className={`badge ${rec.class}`} style={{ fontSize: 10 }}>{rec.label}</span>}
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state if no analyses yet */}
      {!loading && terminated.length === 0 && (
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 48 }}>
          <div className="empty-state-icon">📊</div>
          <div className="empty-state-title">Aucune analyse terminée</div>
          <p className="empty-state-text" style={{ textAlign: 'center' }}>Uploadez des CVs et lancez une analyse pour commencer</p>
          <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/upload')}>
            <Zap size={14} /> Analyser des CVs
          </button>
        </div>
      )}
    </div>
  );
}
