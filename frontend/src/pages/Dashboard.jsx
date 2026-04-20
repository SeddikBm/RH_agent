import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, FileText, CheckCircle, Clock,
  TrendingUp, ArrowRight, Zap, Briefcase, Trophy
} from 'lucide-react';
import { analysisApi, jobApi, cvApi } from '../api/client';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts';

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
  const inProgress = analyses.filter(a => a.statut === 'en_cours');
  const avgScore = terminated.length > 0
    ? (terminated.reduce((s, a) => s + (a.score_global || 0), 0) / terminated.length).toFixed(0)
    : '--';

  // Radar dynamique : moyennes réelles des catégories
  const radarData = (() => {
    const withRapport = terminated.filter(a => a.rapport?.scores);
    if (withRapport.length === 0) {
      return [
        { subject: 'Compétences', value: 0 },
        { subject: 'Expérience', value: 0 },
        { subject: 'Formation', value: 0 },
        { subject: 'Soft Skills', value: 0 },
      ];
    }
    const avg = (key) => Math.round(
      withRapport.reduce((s, a) => s + (a.rapport.scores[key] || 0), 0) / withRapport.length
    );
    return [
      { subject: 'Compétences', value: avg('competences_techniques') },
      { subject: 'Expérience', value: avg('experience') },
      { subject: 'Formation', value: avg('formation') },
      { subject: 'Soft Skills', value: avg('soft_skills') },
    ];
  })();

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

      {/* ── Content ── */}
      <div className="grid-2" style={{ gap: 24 }}>
        {/* Dernières analyses */}
        <div className="card" style={{ gridColumn: '1' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)' }}>
              Dernières Analyses
            </h2>
            <button className="btn btn-sm btn-secondary" onClick={() => navigate('/analyses')}>
              Voir tout <ArrowRight size={14} />
            </button>
          </div>

          {loading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[1, 2, 3].map(i => (
                <div key={i} className="skeleton" style={{ height: 72, borderRadius: 8 }} />
              ))}
            </div>
          ) : analyses.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <div className="empty-state-title">Aucune analyse</div>
              <p className="empty-state-text">Lancez votre première analyse pour commencer</p>
              <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/upload')}>
                <Zap size={14} /> Analyser des CVs
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {analyses.slice(0, 5).map(a => {
                const rec = RECOMMANDATION_CONFIG[a.recommandation] || { class: 'badge-neutral', label: a.statut };
                return (
                  <div
                    key={a.id}
                    className="analysis-list-item"
                    onClick={() => navigate(`/analyses/${a.id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <div className="analysis-avatar">
                      {(a.nom_candidat || '?')[0].toUpperCase()}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 2 }}>
                        {a.nom_candidat || 'Candidat anonyme'}
                      </div>
                      <div style={{ fontSize: 12, color: 'var(--color-text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {a.titre_poste || 'Poste non défini'}
                        {a.rang && <span style={{ marginLeft: 8 }}>• Rang #{a.rang}</span>}
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 6 }}>
                      {a.score_global != null && (
                        <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--color-primary-light)' }}>
                          {a.score_global.toFixed(0)}
                        </span>
                      )}
                      <span className={`badge ${rec.class}`}>{rec.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Radar chart + recommandations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div className="card">
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
              Profil Moyen des Candidats
            </h2>
            <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 16 }}>
              {terminated.length === 0 ? 'Aucune donnée disponible' : `Basé sur ${terminated.length} analyse(s)`}
            </p>
            <div className="radar-wrapper" style={{ height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="rgba(99,102,241,0.15)" />
                  <PolarAngleAxis
                    dataKey="subject"
                    tick={{ fill: 'var(--color-text-secondary)', fontSize: 12 }}
                  />
                  <Radar
                    dataKey="value"
                    stroke="var(--color-primary)"
                    fill="var(--color-primary)"
                    fillOpacity={0.2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 16 }}>
              Résultats de Recommandation
            </h2>
            {['Entretien recommandé', 'À considérer', 'Profil insuffisant'].map(rec => {
              const count = terminated.filter(a => a.recommandation === rec).length;
              const pct = terminated.length > 0 ? (count / terminated.length) * 100 : 0;
              const config = RECOMMANDATION_CONFIG[rec];
              return (
                <div key={rec} style={{ marginBottom: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                    <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{rec}</span>
                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                      {count}
                    </span>
                  </div>
                  <div className="score-bar-track">
                    <div
                      className="score-bar-fill"
                      style={{
                        width: `${pct}%`,
                        background: rec === 'Entretien recommandé'
                          ? 'var(--gradient-success)'
                          : rec === 'À considérer'
                            ? 'var(--gradient-warning)'
                            : 'var(--gradient-danger)',
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
