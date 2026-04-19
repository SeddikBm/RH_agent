import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, FileText, CheckCircle, Clock,
  TrendingUp, ArrowRight, Zap
} from 'lucide-react';
import { analysisApi } from '../api/client';
import { formatDistanceToNow } from 'date-fns';
import { fr } from 'date-fns/locale';
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
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    analysisApi.list()
      .then(setAnalyses)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const terminated = analyses.filter(a => a.statut === 'termine');
  const inProgress = analyses.filter(a => a.statut === 'en_cours');
  const avgScore = terminated.length > 0
    ? (terminated.reduce((s, a) => s + (a.score_global || 0), 0) / terminated.length).toFixed(0)
    : '--';

  const recommended = terminated.filter(a => a.recommandation === 'Entretien recommandé').length;

  // Données pour le radar global
  const radarData = [
    { subject: 'Compétences', value: 72 },
    { subject: 'Expérience', value: 65 },
    { subject: 'Formation', value: 80 },
    { subject: 'Soft Skills', value: 70 },
  ];

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Tableau de Bord</h1>
        <p className="page-subtitle">
          Vue d'ensemble de vos analyses de candidatures
        </p>
      </div>

      {/* ── Stats ── */}
      <div className="grid-4" style={{ marginBottom: 32 }}>
        <StatCard icon={FileText} value={analyses.length} label="Analyses totales" colorClass="purple" />
        <StatCard icon={CheckCircle} value={terminated.length} label="Terminées" colorClass="green" />
        <StatCard icon={Clock} value={inProgress.length} label="En cours" colorClass="cyan" />
        <StatCard icon={TrendingUp} value={avgScore} label="Score moyen" colorClass="orange" />
      </div>

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
              <p className="empty-state-text">Uploadez un CV pour commencer</p>
              <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => navigate('/upload')}>
                <Zap size={14} /> Analyser un CV
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

        {/* Radar chart + info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div className="card">
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 16 }}>
              Profil Moyen des Candidats
            </h2>
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
