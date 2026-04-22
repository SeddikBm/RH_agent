import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell
} from 'recharts';
import {
  ArrowLeft, AlertTriangle, CheckCircle, XCircle,
  Clock, Star, TrendingUp, Award, Zap, ChevronDown, ChevronUp, Download
} from 'lucide-react';
import toast from 'react-hot-toast';
import { analysisApi, pollAnalysis } from '../api/client';

const MATCH_COLORS = {
  excellent: { bg: 'rgba(16,185,129,0.2)', text: '#34d399', label: 'EXCELLENT' },
  bon: { bg: 'rgba(99,102,241,0.2)', text: '#818cf8', label: 'BON' },
  partiel: { bg: 'rgba(245,158,11,0.2)', text: '#fbbf24', label: 'PARTIEL' },
  faible: { bg: 'rgba(239,68,68,0.15)', text: '#f87171', label: 'FAIBLE' },
  absent: { bg: 'rgba(148,163,184,0.1)', text: '#94a3b8', label: 'ABSENT' },
};

const REC_CONFIG = {
  'Entretien recommandé': {
    icon: CheckCircle, iconColor: '#34d399',
    class: 'entretien',
    bg: 'rgba(16,185,129,0.05)',
  },
  'À considérer': {
    icon: Clock, iconColor: '#fbbf24',
    class: 'considerer',
    bg: 'rgba(245,158,11,0.05)',
  },
  'Profil insuffisant': {
    icon: XCircle, iconColor: '#f87171',
    class: 'insuffisant',
    bg: 'rgba(239,68,68,0.05)',
  },
};

function ScoreGauge({ value, size = 140 }) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;
  const color = value >= 70 ? '#10b981' : value >= 50 ? '#f59e0b' : '#ef4444';

  return (
    <div className="score-gauge-wrapper">
      <svg width={size} height={size} viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="12" />
        <circle
          cx="60" cy="60" r={radius} fill="none"
          stroke={color} strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 60 60)"
          style={{ transition: 'stroke-dashoffset 1.2s cubic-bezier(0.4,0,0.2,1)', filter: `drop-shadow(0 0 8px ${color})` }}
        />
        <text x="60" y="60" textAnchor="middle" dominantBaseline="middle"
          fill={color} fontSize="22" fontWeight="800" fontFamily="Inter, sans-serif">
          {value.toFixed(0)}
        </text>
        <text x="60" y="78" textAnchor="middle" fill="#475569" fontSize="9"
          fontFamily="Inter, sans-serif" fontWeight="600">
          / 100
        </text>
      </svg>
    </div>
  );
}

function AnalysisInProgress() {
  const steps = [
    { label: 'Extraction des compétences', icon: '🔍' },
    { label: 'Matching CV ↔ Fiche de poste', icon: '🔗' },
    { label: 'Scoring multicritère', icon: '📊' },
    { label: 'Génération du rapport', icon: '📝' },
  ];
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep(prev => (prev + 1) % steps.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="card" style={{ textAlign: 'center', padding: '64px 32px' }}>
      <div style={{
        width: 80, height: 80, borderRadius: '50%',
        background: 'var(--gradient-primary)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 24px',
        animation: 'pulse-glow 2s ease-in-out infinite',
      }}>
        <Zap size={36} color="white" />
      </div>

      <h2 style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 8 }}>
        Analyse en cours...
      </h2>
      <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', marginBottom: 40 }}>
        Le pipeline LangGraph analyse ce CV. Cela prend généralement 20-60 secondes.
      </p>

      <div style={{ maxWidth: 360, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {steps.map((step, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 12,
            padding: '12px 16px',
            background: i === currentStep ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.02)',
            border: `1px solid ${i === currentStep ? 'var(--color-primary)' : 'var(--color-border)'}`,
            borderRadius: 'var(--radius-md)',
            transition: 'var(--transition-base)',
          }}>
            <span style={{ fontSize: 20 }}>{step.icon}</span>
            <span style={{
              fontSize: 13, fontWeight: i === currentStep ? 600 : 400,
              color: i === currentStep ? 'var(--color-primary-light)' : 'var(--color-text-secondary)',
            }}>
              {step.label}
            </span>
            {i === currentStep && (
              <div className="spinner" style={{ width: 16, height: 16, marginLeft: 'auto' }} />
            )}
            {i < currentStep && (
              <CheckCircle size={16} color="var(--color-success)" style={{ marginLeft: 'auto' }} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Report() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedSection, setExpandedSection] = useState('skills');
  const [downloading, setDownloading] = useState(false);

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      await analysisApi.downloadPdf(id);
      toast.success('PDF téléchargé avec succès');
    } catch (err) {
      toast.error('Erreur téléchargement: ' + err.message);
    } finally {
      setDownloading(false);
    }
  };

  useEffect(() => {
    const stop = pollAnalysis(id, (updated) => {
      setData(updated);
      setLoading(false);
    });
    return stop;
  }, [id]);

  if (loading) {
    return (
      <div className="card" style={{ display: 'flex', justifyContent: 'center', padding: 64 }}>
        <div className="spinner" />
      </div>
    );
  }

  if (!data) return <div>Analyse non trouvée</div>;

  if (data.statut === 'en_cours' || data.statut === 'en_attente') {
    return (
      <div className="animate-fade-in">
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/analyses')} style={{ marginBottom: 24 }}>
          <ArrowLeft size={14} /> Retour
        </button>
        <AnalysisInProgress />
      </div>
    );
  }

  if (data.statut === 'erreur') {
    return (
      <div className="animate-fade-in">
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/analyses')} style={{ marginBottom: 24 }}>
          <ArrowLeft size={14} /> Retour
        </button>
        <div className="card" style={{ textAlign: 'center', padding: 48 }}>
          <XCircle size={48} color="var(--color-danger)" style={{ margin: '0 auto 16px' }} />
          <h2 style={{ color: 'var(--color-danger)', marginBottom: 8 }}>Analyse échouée</h2>
          <p style={{ color: 'var(--color-text-secondary)' }}>{data.message_erreur}</p>
        </div>
      </div>
    );
  }

  const rapport = data.rapport;
  if (!rapport) return <div>Rapport non disponible</div>;

  const scores = rapport.scores || {};
  const rec = REC_CONFIG[rapport.recommandation] || REC_CONFIG['À considérer'];
  const RecIcon = rec.icon;

  // Données pour RadarChart
  const radarData = [
    { subject: 'Compétences', value: Math.round(scores.competences_techniques || 0) },
    { subject: 'Expérience', value: Math.round(scores.experience || 0) },
    { subject: 'Formation', value: Math.round(scores.formation || 0) },
    { subject: 'Soft Skills', value: Math.round(scores.soft_skills || 0) },
  ];

  // Données pour BarChart
  const barData = [
    { name: 'Tech. (40%)', score: Math.round(scores.competences_techniques || 0), fill: '#6366f1' },
    { name: 'Expé. (30%)', score: Math.round(scores.experience || 0), fill: '#06b6d4' },
    { name: 'Form. (20%)', score: Math.round(scores.formation || 0), fill: '#a855f7' },
    { name: 'Soft (10%)', score: Math.round(scores.soft_skills || 0), fill: '#10b981' },
  ];

  const SectionToggle = ({ id: sectionId, title, children }) => {
    const isOpen = expandedSection === sectionId;
    return (
      <div className="card" style={{ marginBottom: 16 }}>
        <button
          style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            width: '100%', background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--color-text-primary)', padding: 0,
          }}
          onClick={() => setExpandedSection(isOpen ? null : sectionId)}
        >
          <span style={{ fontSize: 16, fontWeight: 700 }}>{title}</span>
          {isOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
        {isOpen && <div style={{ marginTop: 20 }}>{children}</div>}
      </div>
    );
  };

  return (
    <div className="animate-fade-in">
      {/* ── Actions globales ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/analyses')}>
          <ArrowLeft size={14} /> Retour aux analyses
        </button>
        <button className="btn btn-primary btn-sm" onClick={handleDownloadPdf} disabled={downloading}>
          {downloading ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <Download size={14} />}
          Télécharger le PDF
        </button>
      </div>

      {/* ── Disclaimer ── */}
      <div className="guardrail-banner" style={{ marginBottom: 24 }}>
        <AlertTriangle size={18} className="guardrail-banner-icon" />
        <p className="guardrail-banner-text">
          <strong>AVERTISSEMENT :</strong> {rapport.disclaimer}
        </p>
      </div>

      {/* ── Header Rapport ── */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          {/* Info candidat */}
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              RAPPORT D'ANALYSE
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 800, color: 'var(--color-text-primary)', marginBottom: 6 }}>
              {data.nom_candidat || 'Candidat anonyme'}
            </h1>
            <div style={{ fontSize: 14, color: 'var(--color-text-secondary)', marginBottom: 12 }}>
              Poste : <strong>{data.titre_poste}</strong>
            </div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span className="badge badge-purple">
                Durée : {data.duree_secondes ? `${data.duree_secondes.toFixed(0)}s` : '—'}
              </span>
              <span className="badge badge-info">LangGraph · GPT-4o-mini</span>
            </div>
          </div>

          {/* Score global */}
          <div style={{ textAlign: 'center' }}>
            <ScoreGauge value={scores.score_global || 0} />
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4, fontWeight: 600 }}>
              SCORE GLOBAL
            </div>
          </div>

          {/* Recommandation */}
          <div className={`recommendation-card ${rec.class}`} style={{ minWidth: 220 }}>
            <RecIcon size={28} color={rec.iconColor} style={{ flexShrink: 0 }} />
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-text-muted)', marginBottom: 4, textTransform: 'uppercase' }}>
                RECOMMANDATION
              </div>
              <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 6 }}>
                {rapport.recommandation}
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>
                {rapport.justification_recommandation}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Scores Détaillés ── */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 20 }}>
            📊 Scores par Critère
          </h2>
          {barData.map(({ name, score, fill }) => (
            <div key={name} className="score-bar-row">
              <div className="score-bar-label">{name}</div>
              <div className="score-bar-track">
                <div
                  className="score-bar-fill"
                  style={{ width: `${score}%`, background: fill }}
                />
              </div>
              <div className="score-bar-value">{score}</div>
            </div>
          ))}
        </div>

        <div className="card">
          <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 16 }}>
            🎯 Profil Radar
          </h2>
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(99,102,241,0.15)" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--color-text-secondary)', fontSize: 11 }} />
                <Radar dataKey="value" stroke="var(--color-primary)" fill="var(--color-primary)" fillOpacity={0.2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Adéquation ── */}
      <div className="card" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 12 }}>
          💬 Adéquation au Poste
        </h2>
        <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', lineHeight: 1.8 }}>
          {rapport.adequation_poste}
        </p>
      </div>

      {/* ── Points Forts & Faibles ── */}
      <div className="grid-2" style={{ marginBottom: 24 }}>
        <div className="card">
          <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-success)', marginBottom: 16 }}>
            ✅ Points Forts
          </h2>
          {(rapport.points_forts || []).map((p, i) => (
            <div key={i} style={{
              display: 'flex', gap: 12, padding: '10px 0',
              borderBottom: i < rapport.points_forts.length - 1 ? '1px solid var(--color-border)' : 'none',
            }}>
              <Star size={16} color="var(--color-success)" style={{ flexShrink: 0, marginTop: 2 }} />
              <span style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>{p}</span>
            </div>
          ))}
        </div>

        <div className="card">
          <h2 style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-warning)', marginBottom: 16 }}>
            ⚠️ Points d'Amélioration
          </h2>
          {(rapport.points_faibles || []).map((p, i) => (
            <div key={i} style={{
              display: 'flex', gap: 12, padding: '10px 0',
              borderBottom: i < rapport.points_faibles.length - 1 ? '1px solid var(--color-border)' : 'none',
            }}>
              <AlertTriangle size={16} color="var(--color-warning)" style={{ flexShrink: 0, marginTop: 2 }} />
              <span style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.6 }}>{p}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Matching Compétences ── */}
      <SectionToggle id="skills" title="🔗 Matching Compétences par Compétence">
        {(rapport.correspondances_competences || []).length === 0 ? (
          <p style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>Aucun matching disponible</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {rapport.correspondances_competences.map((m, i) => {
              const matchConf = MATCH_COLORS[m.niveau_match] || MATCH_COLORS.absent;
              return (
                <div key={i} className="match-item">
                  <span
                    className="match-level-badge"
                    style={{ background: matchConf.bg, color: matchConf.text }}
                  >
                    {matchConf.label}
                  </span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)', marginBottom: 2 }}>
                      {m.competence_requise}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                      {m.justification}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </SectionToggle>
    </div>
  );
}
