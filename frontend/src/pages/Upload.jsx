import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import { Upload as UploadIcon, FileText, X, CheckCircle,
  Briefcase, Zap, AlertCircle, Loader2, UploadCloud
} from 'lucide-react';
import { cvApi, jobApi, analysisApi } from '../api/client';

// ── Étapes du pipeline ────────────────────────────────────
const STEPS = [
  { id: 1, label: 'Upload CV' },
  { id: 2, label: 'Fiche de Poste' },
  { id: 3, label: 'Lancer Analyse' },
];

export default function Upload() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);

  // Étape 1 : Upload CV
  const [uploadedFile, setUploadedFile] = useState(null);
  const [cvRecord, setCvRecord] = useState(null);
  const [uploading, setUploading] = useState(false);

  // Étape 2 : Sélection ou création de fiche de poste
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [showJobForm, setShowJobForm] = useState(false);
  const [jobForm, setJobForm] = useState({
    titre: '', entreprise: '', description: '',
    competences_requises: '', competences_souhaitees: '',
    annees_experience_min: '', formation_requise: '',
    localisation: '', type_contrat: '',
  });
  const [savingJob, setSavingJob] = useState(false);

  // Étape 3 : Analyse
  const [launching, setLaunching] = useState(false);

  // Étape 2 bis : Extraction Job
  const [extractingJob, setExtractingJob] = useState(false);

  const onDropJob = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;
    setExtractingJob(true);
    if (!showJobForm) setShowJobForm(true);
    try {
      const data = await jobApi.extract(file);
      setJobForm(prev => ({
        ...prev,
        titre: data.titre || '',
        entreprise: data.entreprise || '',
        description: data.description || '',
        competences_requises: (data.competences_requises || []).join(', '),
        competences_souhaitees: (data.competences_souhaitees || []).join(', '),
        annees_experience_min: data.annees_experience_min?.toString() || '',
        formation_requise: data.formation_requise || '',
        localisation: data.localisation || '',
        type_contrat: data.type_contrat || '',
      }));
      toast.success('Fiche de poste extraite avec succès !');
    } catch (err) {
      toast.error('Erreur extraction: ' + err.message);
    } finally {
      setExtractingJob(false);
    }
  }, [showJobForm]);

  const { getRootProps: getJobRootProps, getInputProps: getJobInputProps, isDragActive: isJobDragActive } = useDropzone({
    onDrop: onDropJob,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
  });

  // ── Charger les fiches de poste ───────────────────────
  useEffect(() => {
    jobApi.list().then(setJobs).catch(console.error);
  }, []);

  // ── Drag & Drop ───────────────────────────────────────
  const onDrop = useCallback((acceptedFiles) => {
    if (acceptedFiles.length > 0) setUploadedFile(acceptedFiles[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  // ── Upload du CV ─────────────────────────────────────
  const handleUploadCV = async () => {
    if (!uploadedFile) return;
    setUploading(true);
    try {
      const record = await cvApi.upload(uploadedFile);
      setCvRecord(record);
      toast.success('CV uploadé avec succès !');
      setStep(2);
    } catch (err) {
      toast.error(err.message || 'Erreur lors de l\'upload');
    } finally {
      setUploading(false);
    }
  };

  // ── Créer une fiche de poste ──────────────────────────
  const handleSaveJob = async () => {
    if (!jobForm.titre || !jobForm.description) {
      toast.error('Le titre et la description sont requis');
      return;
    }
    setSavingJob(true);
    try {
      const payload = {
        ...jobForm,
        competences_requises: jobForm.competences_requises
          ? jobForm.competences_requises.split(',').map(s => s.trim()).filter(Boolean)
          : [],
        competences_souhaitees: jobForm.competences_souhaitees
          ? jobForm.competences_souhaitees.split(',').map(s => s.trim()).filter(Boolean)
          : [],
        annees_experience_min: jobForm.annees_experience_min
          ? parseInt(jobForm.annees_experience_min)
          : null,
      };
      const newJob = await jobApi.create(payload);
      setJobs(prev => [newJob, ...prev]);
      setSelectedJobId(newJob.id);
      setShowJobForm(false);
      toast.success('Fiche de poste créée !');
    } catch (err) {
      toast.error(err.message || 'Erreur création fiche');
    } finally {
      setSavingJob(false);
    }
  };

  // ── Lancer l'analyse ──────────────────────────────────
  const handleLaunchAnalysis = async () => {
    if (!cvRecord?.id || !selectedJobId) {
      toast.error('Sélectionnez un CV et une fiche de poste');
      return;
    }
    setLaunching(true);
    try {
      const analyse = await analysisApi.run(cvRecord.id, selectedJobId);
      toast.success('Analyse lancée ! Redirection en cours...');
      setTimeout(() => navigate(`/analyses/${analyse.id}`), 1000);
    } catch (err) {
      toast.error(err.message || 'Erreur lancement analyse');
      setLaunching(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: 800, margin: '0 auto' }}>
      <div className="page-header">
        <h1 className="page-title">Analyser un CV</h1>
        <p className="page-subtitle">
          Uploadez un CV et sélectionnez une fiche de poste pour lancer l'analyse IA
        </p>
      </div>

      {/* ── Pipeline Steps ── */}
      <div className="pipeline-steps" style={{ marginBottom: 40 }}>
        {STEPS.map((s, i) => (
          <div
            key={s.id}
            className={`pipeline-step ${step === s.id ? 'active' : step > s.id ? 'done' : ''}`}
          >
            <div className="pipeline-step-dot">
              {step > s.id ? '✓' : s.id}
            </div>
            <span className="pipeline-step-label">{s.label}</span>
          </div>
        ))}
      </div>

      {/* ══ ÉTAPE 1 : Upload CV ══ */}
      {step === 1 && (
        <div className="card animate-slide-in">
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, color: 'var(--color-text-primary)' }}>
            📄 Upload du CV
          </h2>

          {!uploadedFile ? (
            <div
              {...getRootProps()}
              className={`upload-zone ${isDragActive ? 'drag-active' : ''}`}
            >
              <input {...getInputProps()} />
              <div className="upload-zone-icon">
                <UploadIcon size={32} />
              </div>
              <div className="upload-zone-title">
                {isDragActive ? '📥 Déposez le fichier ici' : 'Glissez-déposez votre CV ici'}
              </div>
              <p className="upload-zone-subtitle">
                ou <span style={{ color: 'var(--color-primary-light)', fontWeight: 600 }}>cliquez pour parcourir</span>
              </p>
              <p style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 12 }}>
                PDF, DOCX ou TXT · Max 10 MB
              </p>
            </div>
          ) : (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 16, padding: 20,
              background: 'rgba(99,102,241,0.06)', border: '1px solid var(--color-border-bright)',
              borderRadius: 'var(--radius-lg)',
            }}>
              <FileText size={40} color="var(--color-primary-light)" />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                  {uploadedFile.name}
                </div>
                <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>
                  {(uploadedFile.size / 1024).toFixed(0)} KB
                </div>
              </div>
              <button
                className="btn btn-icon btn-secondary"
                onClick={() => setUploadedFile(null)}
              >
                <X size={16} />
              </button>
            </div>
          )}

          {uploadedFile && (
            <button
              className="btn btn-primary btn-lg"
              style={{ width: '100%', marginTop: 20 }}
              onClick={handleUploadCV}
              disabled={uploading}
            >
              {uploading ? (
                <><div className="spinner" style={{ width: 18, height: 18 }} /> Analyse en cours...</>
              ) : (
                <><CheckCircle size={18} /> Valider et continuer</>
              )}
            </button>
          )}
        </div>
      )}

      {/* ══ ÉTAPE 2 : Fiche de Poste ══ */}
      {step === 2 && (
        <div className="animate-slide-in" style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* CV Validé */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
            background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)',
            borderRadius: 'var(--radius-md)',
          }}>
            <CheckCircle size={18} color="var(--color-success)" />
            <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>
              CV uploadé : <strong style={{ color: 'var(--color-text-primary)' }}>{uploadedFile?.name}</strong>
            </span>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)' }}>
                <Briefcase size={18} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 8 }} />
                Sélectionner une Fiche de Poste
              </h2>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowJobForm(!showJobForm)}
              >
                {showJobForm ? 'Annuler' : '+ Nouvelle fiche'}
              </button>
            </div>

            {/* Formulaire nouvelle fiche */}
            {showJobForm && (
              <div style={{
                background: 'rgba(99,102,241,0.05)',
                border: '1px solid var(--color-border)',
                borderRadius: 'var(--radius-md)',
                padding: 20,
                marginBottom: 20,
              }}>
                <h3 style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-secondary)', marginBottom: 16 }}>
                  Nouvelle Fiche de Poste
                </h3>
                
                <div
                  {...getJobRootProps()}
                  style={{
                    border: `2px dashed ${isJobDragActive ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    padding: '20px',
                    borderRadius: 'var(--radius-md)',
                    textAlign: 'center',
                    backgroundColor: isJobDragActive ? 'rgba(99,102,241,0.05)' : 'rgba(255,255,255,0.02)',
                    cursor: 'pointer',
                    marginBottom: 20,
                    transition: 'all 0.2s',
                  }}
                >
                  <input {...getJobInputProps()} />
                  {extractingJob ? (
                     <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
                        <div className="spinner" style={{ width: 24, height: 24, borderWidth: 3 }}></div>
                        <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>Extraction en cours...</span>
                     </div>
                  ) : (
                    <>
                      <UploadCloud size={24} color={isJobDragActive ? "var(--color-primary)" : "var(--color-text-muted)"} style={{ marginBottom: 8 }} />
                      <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: 'var(--color-text-primary)' }}>Déposez un PDF/DOCX pour auto-remplir la fiche</p>
                    </>
                  )}
                </div>

                <div className="grid-2" style={{ gap: 12, marginBottom: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Titre du Poste *</label>
                    <input
                      className="form-input"
                      placeholder="ex: Développeur Full-Stack Senior"
                      value={jobForm.titre}
                      onChange={e => setJobForm(p => ({ ...p, titre: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Entreprise</label>
                    <input
                      className="form-input"
                      placeholder="ex: TechCorp SAS"
                      value={jobForm.entreprise}
                      onChange={e => setJobForm(p => ({ ...p, entreprise: e.target.value }))}
                    />
                  </div>
                </div>
                <div className="form-group" style={{ marginBottom: 12 }}>
                  <label className="form-label">Description du Poste *</label>
                  <textarea
                    className="form-textarea"
                    placeholder="Décrivez les missions, le contexte, les responsabilités..."
                    value={jobForm.description}
                    onChange={e => setJobForm(p => ({ ...p, description: e.target.value }))}
                    rows={4}
                  />
                </div>
                <div className="grid-2" style={{ gap: 12, marginBottom: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Compétences Requises (séparées par virgule)</label>
                    <input
                      className="form-input"
                      placeholder="ex: React, Python, Docker"
                      value={jobForm.competences_requises}
                      onChange={e => setJobForm(p => ({ ...p, competences_requises: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Compétences Souhaitées</label>
                    <input
                      className="form-input"
                      placeholder="ex: Kubernetes, GraphQL"
                      value={jobForm.competences_souhaitees}
                      onChange={e => setJobForm(p => ({ ...p, competences_souhaitees: e.target.value }))}
                    />
                  </div>
                </div>
                <div className="grid-2" style={{ gap: 12, marginBottom: 12 }}>
                  <div className="form-group">
                    <label className="form-label">Expérience Minimale (ans)</label>
                    <input
                      className="form-input"
                      type="number"
                      placeholder="ex: 3"
                      value={jobForm.annees_experience_min}
                      onChange={e => setJobForm(p => ({ ...p, annees_experience_min: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Formation Requise</label>
                    <input
                      className="form-input"
                      placeholder="ex: Bac+5 Informatique"
                      value={jobForm.formation_requise}
                      onChange={e => setJobForm(p => ({ ...p, formation_requise: e.target.value }))}
                    />
                  </div>
                </div>
                <button
                  className="btn btn-primary"
                  onClick={handleSaveJob}
                  disabled={savingJob}
                >
                  {savingJob ? <><div className="spinner" style={{ width: 16, height: 16 }} /> Enregistrement...</> : '✓ Créer la fiche'}
                </button>
              </div>
            )}

            {/* Liste des fiches existantes */}
            {jobs.length === 0 ? (
              <div className="empty-state" style={{ padding: '32px 16px' }}>
                <div className="empty-state-icon">📋</div>
                <div className="empty-state-title">Aucune fiche de poste</div>
                <p className="empty-state-text">Créez votre première fiche ci-dessus</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {jobs.map(job => (
                  <div
                    key={job.id}
                    onClick={() => setSelectedJobId(job.id)}
                    style={{
                      padding: '14px 16px',
                      border: `1px solid ${selectedJobId === job.id ? 'var(--color-primary)' : 'var(--color-border)'}`,
                      borderRadius: 'var(--radius-md)',
                      cursor: 'pointer',
                      background: selectedJobId === job.id
                        ? 'rgba(99,102,241,0.1)' : 'rgba(255,255,255,0.02)',
                      transition: 'var(--transition-fast)',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                    }}
                  >
                    <div style={{
                      width: 36, height: 36, borderRadius: 8,
                      background: selectedJobId === job.id ? 'var(--gradient-primary)' : 'rgba(99,102,241,0.1)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      flexShrink: 0,
                    }}>
                      <Briefcase size={16} color={selectedJobId === job.id ? 'white' : 'var(--color-primary-light)'} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                        {job.titre}
                      </div>
                      {job.entreprise && (
                        <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                          {job.entreprise} · {job.nb_competences_requises || 0} compétences requises
                        </div>
                      )}
                    </div>
                    {selectedJobId === job.id && (
                      <CheckCircle size={20} color="var(--color-primary)" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-secondary" onClick={() => setStep(1)}>
              ← Retour
            </button>
            <button
              className="btn btn-primary"
              style={{ flex: 1 }}
              onClick={() => selectedJobId && setStep(3)}
              disabled={!selectedJobId}
            >
              Continuer → Lancer l'Analyse
            </button>
          </div>
        </div>
      )}

      {/* ══ ÉTAPE 3 : Confirmation & Lancement ══ */}
      {step === 3 && (
        <div className="card animate-slide-in">
          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 24 }}>
            🚀 Prêt à Lancer l'Analyse
          </h2>

          {/* Récap */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
              background: 'rgba(99,102,241,0.06)', border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
            }}>
              <FileText size={20} color="var(--color-primary-light)" />
              <div>
                <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 2 }}>CV CANDIDAT</div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{uploadedFile?.name}</div>
              </div>
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12, padding: '14px 16px',
              background: 'rgba(6,182,212,0.06)', border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
            }}>
              <Briefcase size={20} color="var(--color-secondary)" />
              <div>
                <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 2 }}>FICHE DE POSTE</div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>
                  {jobs.find(j => j.id === selectedJobId)?.titre || selectedJobId}
                </div>
              </div>
            </div>
          </div>

          {/* Pipeline preview */}
          <div style={{
            background: 'rgba(255,255,255,0.02)', border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-md)', padding: 16, marginBottom: 24,
          }}>
            <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 12 }}>
              PIPELINE D'ANALYSE (LangGraph)
            </div>
            {['1. Extraction des compétences', '2. Matching CV ↔ Poste (RAG)', '3. Scoring multicritère', '4. Génération du rapport'].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                <div style={{
                  width: 24, height: 24, borderRadius: '50%',
                  background: 'rgba(99,102,241,0.2)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700, color: 'var(--color-primary-light)',
                  flexShrink: 0,
                }}>
                  {i + 1}
                </div>
                <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>{s}</span>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-secondary" onClick={() => setStep(2)}>
              ← Retour
            </button>
            <button
              className="btn btn-primary btn-lg"
              style={{ flex: 1 }}
              onClick={handleLaunchAnalysis}
              disabled={launching}
            >
              {launching ? (
                <><div className="spinner" style={{ width: 18, height: 18 }} /> Lancement...</>
              ) : (
                <><Zap size={18} /> Lancer l'Analyse IA</>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
