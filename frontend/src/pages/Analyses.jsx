import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { analysisApi } from '../api/client';
import { Search, Filter, Trash2, ChevronRight } from 'lucide-react';
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
    <span style={{
      fontSize: 22, fontWeight: 800, color,
      fontFamily: 'var(--font-mono, monospace)',
    }}>
      {score.toFixed(0)}
    </span>
  );
}

export default function Analyses() {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  const load = () => {
    setLoading(true);
    analysisApi.list()
      .then(setAnalyses)
      .catch(() => toast.error('Erreur chargement des analyses'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const filteredRaw = analyses.filter(a =>
    (a.nom_candidat?.toLowerCase().includes(search.toLowerCase())) ||
    (a.titre_poste?.toLowerCase().includes(search.toLowerCase()))
  );

  const filtered = [...filteredRaw].sort((a, b) => {
    // Trier par score global décroissant
    return (b.score_global || 0) - (a.score_global || 0);
  });

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('Supprimer cette analyse ?')) return;
    try {
      await analysisApi.delete(id);
      toast.success('Analyse supprimée');
      load();
    } catch {
      toast.error('Erreur suppression');
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Analyses de Candidatures</h1>
        <p className="page-subtitle">Résultats de toutes les analyses effectuées</p>
      </div>

      {/* ── Barre de recherche ── */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 24 }}>
        <div style={{ position: 'relative', flex: 1 }}>
          <Search
            size={16}
            style={{
              position: 'absolute', left: 12, top: '50%',
              transform: 'translateY(-50%)',
              color: 'var(--color-text-muted)',
            }}
          />
          <input
            className="form-input"
            style={{ paddingLeft: 38 }}
            placeholder="Rechercher un candidat ou un poste..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* ── Liste ── */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="skeleton" style={{ height: 88, borderRadius: 12 }} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">🔍</div>
          <div className="empty-state-title">Aucune analyse trouvée</div>
          <p className="empty-state-text">
            {search ? 'Modifiez votre recherche' : 'Uploadez un CV pour commencer'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {/* Header */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 200px 120px 140px 120px 48px',
            padding: '8px 20px',
            fontSize: 11,
            fontWeight: 700,
            color: 'var(--color-text-muted)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
          }}>
            <span>Candidat / Poste</span>
            <span>Recommandation</span>
            <span>Score</span>
            <span>Statut</span>
            <span>Date</span>
            <span></span>
          </div>

          {filtered.map(a => {
            const statusConf = STATUS_CONFIG[a.statut] || STATUS_CONFIG.en_attente;
            const recConf = a.recommandation ? REC_CONFIG[a.recommandation] : null;

            return (
              <div
                key={a.id}
                onClick={() => navigate(`/analyses/${a.id}`)}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 200px 120px 140px 120px 48px',
                  alignItems: 'center',
                  padding: '16px 20px',
                  background: 'var(--gradient-card)',
                  border: '1px solid var(--color-border)',
                  borderRadius: 'var(--radius-lg)',
                  cursor: 'pointer',
                  transition: 'var(--transition-base)',
                  gap: 0,
                }}
                className="analysis-list-item"
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--color-border-bright)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--color-border)';
                }}
              >
                {/* Candidat */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                  <div className="analysis-avatar" style={{ width: 40, height: 40, fontSize: 16 }}>
                    {(a.nom_candidat || '?')[0].toUpperCase()}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{
                      fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {a.nom_candidat || 'Anonyme'}
                    </div>
                    <div style={{
                      fontSize: 12, color: 'var(--color-text-muted)',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {a.titre_poste || '—'}
                    </div>
                  </div>
                </div>

                {/* Recommandation */}
                <div>
                  {recConf ? (
                    <span className={`badge ${recConf.class}`}>{recConf.short}</span>
                  ) : <span style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>—</span>}
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

                {/* Date */}
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                  {new Date(a.date_creation).toLocaleDateString('fr-FR', {
                    day: '2-digit', month: '2-digit', year: '2-digit',
                  })}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', gap: 4 }}>
                  <button
                    className="btn btn-icon btn-danger btn-sm"
                    onClick={(e) => handleDelete(e, a.id)}
                    title="Supprimer"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
