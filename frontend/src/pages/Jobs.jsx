import { useEffect, useState } from 'react';
import { jobApi } from '../api/client';
import toast from 'react-hot-toast';
import { Plus, Briefcase, Trash2, Edit3, X, Save, ChevronDown, ChevronUp } from 'lucide-react';

const EMPTY_FORM = {
  titre: '', entreprise: '', description: '',
  competences_requises: '', competences_souhaitees: '',
  annees_experience_min: '', formation_requise: '',
  localisation: '', type_contrat: '',
};

export default function Jobs() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [expandedId, setExpandedId] = useState(null);

  const load = () => {
    jobApi.list().then(setJobs).catch(console.error).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async () => {
    if (!form.titre || !form.description) {
      toast.error('Titre et description requis');
      return;
    }
    setSaving(true);
    const payload = {
      ...form,
      competences_requises: form.competences_requises
        ? form.competences_requises.split(',').map(s => s.trim()).filter(Boolean)
        : [],
      competences_souhaitees: form.competences_souhaitees
        ? form.competences_souhaitees.split(',').map(s => s.trim()).filter(Boolean)
        : [],
      annees_experience_min: form.annees_experience_min ? parseInt(form.annees_experience_min) : null,
    };

    try {
      if (editingId) {
        await jobApi.update(editingId, payload);
        toast.success('Fiche mise à jour !');
      } else {
        await jobApi.create(payload);
        toast.success('Fiche créée !');
      }
      setShowForm(false);
      setEditingId(null);
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (job) => {
    setForm({
      titre: job.titre || '',
      entreprise: job.entreprise || '',
      description: job.description || '',
      competences_requises: (job.competences_requises || []).join(', '),
      competences_souhaitees: (job.competences_souhaitees || []).join(', '),
      annees_experience_min: job.annees_experience_min?.toString() || '',
      formation_requise: job.formation_requise || '',
      localisation: job.localisation || '',
      type_contrat: job.type_contrat || '',
    });
    setEditingId(job.id);
    setShowForm(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Supprimer cette fiche de poste ?')) return;
    try {
      await jobApi.delete(id);
      toast.success('Fiche supprimée');
      load();
    } catch { toast.error('Erreur suppression'); }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Fiches de Poste</h1>
          <p className="page-subtitle">Gérez vos offres d'emploi pour le matching de candidatures</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => { setShowForm(!showForm); setEditingId(null); setForm(EMPTY_FORM); }}
        >
          <Plus size={16} /> Nouvelle Fiche
        </button>
      </div>

      {/* ── Formulaire ── */}
      {showForm && (
        <div className="card animate-slide-in" style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-text-primary)' }}>
              {editingId ? '✏️ Modifier la Fiche' : '➕ Nouvelle Fiche de Poste'}
            </h2>
            <button className="btn btn-icon btn-secondary" onClick={() => setShowForm(false)}>
              <X size={16} />
            </button>
          </div>

          <div className="grid-2" style={{ gap: 12, marginBottom: 12 }}>
            <div className="form-group">
              <label className="form-label">Titre du Poste *</label>
              <input className="form-input" placeholder="ex: Lead Développeur Backend" value={form.titre} onChange={e => setForm(p => ({ ...p, titre: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Entreprise</label>
              <input className="form-input" placeholder="ex: InnovateTech SAS" value={form.entreprise} onChange={e => setForm(p => ({ ...p, entreprise: e.target.value }))} />
            </div>
          </div>

          <div className="form-group" style={{ marginBottom: 12 }}>
            <label className="form-label">Description *</label>
            <textarea className="form-textarea" rows={4} placeholder="Décrivez le poste, les missions, le contexte..." value={form.description} onChange={e => setForm(p => ({ ...p, description: e.target.value }))} />
          </div>

          <div className="grid-2" style={{ gap: 12, marginBottom: 12 }}>
            <div className="form-group">
              <label className="form-label">Compétences Requises (virgule)</label>
              <input className="form-input" placeholder="ex: Python, FastAPI, PostgreSQL" value={form.competences_requises} onChange={e => setForm(p => ({ ...p, competences_requises: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Compétences Souhaitées</label>
              <input className="form-input" placeholder="ex: Kubernetes, Terraform" value={form.competences_souhaitees} onChange={e => setForm(p => ({ ...p, competences_souhaitees: e.target.value }))} />
            </div>
          </div>

          <div className="grid-2" style={{ gap: 12, marginBottom: 20 }}>
            <div className="form-group">
              <label className="form-label">Expérience Min. (années)</label>
              <input className="form-input" type="number" placeholder="ex: 3" value={form.annees_experience_min} onChange={e => setForm(p => ({ ...p, annees_experience_min: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Formation Requise</label>
              <input className="form-input" placeholder="ex: Bac+5 Informatique" value={form.formation_requise} onChange={e => setForm(p => ({ ...p, formation_requise: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Localisation</label>
              <input className="form-input" placeholder="ex: Paris (hybride)" value={form.localisation} onChange={e => setForm(p => ({ ...p, localisation: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Type de Contrat</label>
              <input className="form-input" placeholder="ex: CDI, CDD, Freelance" value={form.type_contrat} onChange={e => setForm(p => ({ ...p, type_contrat: e.target.value }))} />
            </div>
          </div>

          <button className="btn btn-primary" onClick={handleSubmit} disabled={saving}>
            {saving ? <><div className="spinner" style={{ width: 16, height: 16 }} /> Enregistrement...</> : <><Save size={16} /> Enregistrer</>}
          </button>
        </div>
      )}

      {/* ── Liste des fiches ── */}
      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[1, 2].map(i => <div key={i} className="skeleton" style={{ height: 80, borderRadius: 12 }} />)}
        </div>
      ) : jobs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <div className="empty-state-title">Aucune fiche de poste</div>
          <p className="empty-state-text">Créez votre première fiche pour commencer les analyses</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {jobs.map(job => {
            const isExpanded = expandedId === job.id;
            return (
              <div key={job.id} className="card" style={{ cursor: 'default' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: 'var(--radius-md)',
                    background: 'rgba(99,102,241,0.15)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    flexShrink: 0,
                  }}>
                    <Briefcase size={20} color="var(--color-primary-light)" />
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                      {job.titre}
                    </div>
                    <div style={{ fontSize: 13, color: 'var(--color-text-muted)', marginTop: 2 }}>
                      {[job.entreprise, job.localisation, job.type_contrat].filter(Boolean).join(' · ')}
                    </div>
                    {job.annees_experience_min && (
                      <div style={{ marginTop: 6 }}>
                        <span className="badge badge-neutral">{job.annees_experience_min}+ ans exp.</span>
                        <span className="badge badge-neutral" style={{ marginLeft: 6 }}>
                          {job.nb_competences_requises || 0} compétences
                        </span>
                      </div>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                    <button
                      className="btn btn-icon btn-secondary btn-sm"
                      onClick={() => setExpandedId(isExpanded ? null : job.id)}
                      title="Détails"
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                    <button className="btn btn-icon btn-secondary btn-sm" onClick={() => handleEdit(job)} title="Modifier">
                      <Edit3 size={14} />
                    </button>
                    <button className="btn btn-icon btn-danger btn-sm" onClick={() => handleDelete(job.id)} title="Supprimer">
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {isExpanded && (
                  <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--color-border)' }}>
                    <p style={{ fontSize: 13, color: 'var(--color-text-secondary)', lineHeight: 1.7, marginBottom: 12 }}>
                      {job.description?.substring(0, 300)}{job.description?.length > 300 ? '...' : ''}
                    </p>
                    {job.formation_requise && (
                      <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 4 }}>
                        Formation requise : <span style={{ color: 'var(--color-text-secondary)', fontWeight: 600 }}>{job.formation_requise}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
