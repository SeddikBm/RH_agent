import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import {
  Upload as UploadIcon, FileText, Briefcase, Play, X, CheckCircle,
  ChevronRight, Loader, Trophy, Medal, Award, TrendingUp
} from 'lucide-react';
import toast from 'react-hot-toast';
import { cvApi, jobApi, analysisApi, pollBatch } from '../api/client';

const STEPS = [
  { id: 1, label: 'Fiche de Poste', icon: Briefcase },
  { id: 2, label: 'CVs Candidats', icon: FileText },
  { id: 3, label: 'Résultats', icon: Trophy },
];

const RANK_ICONS = [
  { icon: Trophy, color: '#f59e0b' },
  { icon: Medal, color: '#94a3b8' },
  { icon: Award, color: '#cd7f32' },
];

export default function Upload() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [jobs, setJobs] = useState([]);
  const [selectedJobId, setSelectedJobId] = useState('');
  const [cvFiles, setCvFiles] = useState([]); // [{file, status, cvId, name}]
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [batchResult, setBatchResult] = useState(null);

  useEffect(() => {
    jobApi.list().then(setJobs).catch(() => toast.error('Erreur chargement des postes'));
  }, []);

  // ── Dropzone multi-fichiers ───────────────────────────────
  const onDrop = useCallback((acceptedFiles) => {
    const newFiles = acceptedFiles.map(f => ({
      file: f,
      name: f.name,
      status: 'pending', // pending | uploading | done | error
      cvId: null,
      error: null,
    }));
    setCvFiles(prev => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    multiple: true,
  });

  const removeFile = (idx) => {
    setCvFiles(prev => prev.filter((_, i) => i !== idx));
  };

  // ── Upload de tous les CVs ────────────────────────────────
  const uploadAllCVs = async () => {
    const pending = cvFiles.filter(f => f.status === 'pending');
    if (!pending.length) return;

    setUploading(true);
    const updated = [...cvFiles];

    for (let i = 0; i < updated.length; i++) {
      if (updated[i].status !== 'pending') continue;
      updated[i] = { ...updated[i], status: 'uploading' };
      setCvFiles([...updated]);

      try {
        const res = await cvApi.upload(updated[i].file);
        updated[i] = { ...updated[i], status: 'done', cvId: res.id };
      } catch (err) {
        updated[i] = { ...updated[i], status: 'error', error: err.message };
      }
      setCvFiles([...updated]);
    }

    setUploading(false);
    const successCount = updated.filter(f => f.status === 'done').length;
    const errCount = updated.filter(f => f.status === 'error').length;
    if (successCount > 0) toast.success(`${successCount} CV(s) uploadé(s) avec succès`);
    if (errCount > 0) toast.error(`${errCount} CV(s) en erreur`);
  };

  // ── Lancer l'analyse batch ────────────────────────────────
  const launchBatch = async () => {
    const readyCvs = cvFiles.filter(f => f.status === 'done' && f.cvId);
    if (!selectedJobId) { toast.error('Sélectionnez une fiche de poste'); return; }
    if (!readyCvs.length) { toast.error('Au moins 1 CV doit être uploadé'); return; }

    setAnalyzing(true);
    try {
      const { batch_id } = await analysisApi.runBatch(selectedJobId, readyCvs.map(f => f.cvId));
      setStep(3);

      pollBatch(batch_id, (data) => {
        setBatchResult(data);
        if (data.statut === 'attente_selection') {
          setAnalyzing(false);
          toast.success('Classement terminé. Veuillez sélectionner les candidats.');
        } else if (data.statut === 'termine') {
          setAnalyzing(false);
          toast.success('Analyse LangGraph terminée !');
        } else if (data.statut === 'erreur') {
          setAnalyzing(false);
          toast.error('Erreur lors de l\'analyse');
        }
      });
    } catch (err) {
      toast.error('Erreur lancement: ' + err.message);
      setAnalyzing(false);
    }
  };

  const launchLanggraph = async (selectedIds) => {
    setAnalyzing(true);
    try {
      await analysisApi.runLanggraph(batchResult.id, selectedIds);
      toast.success('Analyse approfondie lancée ! Redirection vers les analyses…');
      // Navigate to analyses page filtered by job so user can watch progress
      setTimeout(() => navigate(`/analyses?job=${selectedJobId}`), 1200);
    } catch (err) {
      toast.error('Erreur lancement LangGraph: ' + err.message);
      setAnalyzing(false);
    }
  };

  const selectedJob = jobs.find(j => j.id === selectedJobId);
  const readyCount = cvFiles.filter(f => f.status === 'done').length;
  const canAnalyze = selectedJobId && readyCount > 0;

  // ── Render ────────────────────────────────────────────────
  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Analyse par Poste</h1>
        <p className="page-subtitle">Déposez vos CVs pour ce poste — le système identifie les meilleurs profils</p>
      </div>

      {/* ── Stepper ── */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 36, gap: 0 }}>
        {STEPS.map((s, idx) => {
          const Icon = s.icon;
          const isActive = step === s.id;
          const isDone = step > s.id;
          return (
            <div key={s.id} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 10,
                opacity: isDone || isActive ? 1 : 0.4,
                transition: 'opacity 0.3s',
              }}>
                <div style={{
                  width: 36, height: 36, borderRadius: '50%',
                  background: isDone ? 'var(--color-success)' : isActive ? 'var(--gradient-primary)' : 'var(--color-bg-secondary)',
                  border: `2px solid ${isDone ? 'var(--color-success)' : isActive ? 'var(--color-primary)' : 'var(--color-border)'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.3s',
                }}>
                  {isDone
                    ? <CheckCircle size={16} color="white" />
                    : <Icon size={16} color={isActive ? 'white' : 'var(--color-text-muted)'} />
                  }
                </div>
                <span style={{
                  fontSize: 13, fontWeight: isActive ? 700 : 500,
                  color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-secondary)',
                }}>
                  {s.label}
                </span>
              </div>
              {idx < STEPS.length - 1 && (
                <div style={{
                  flex: 1, height: 2, margin: '0 16px',
                  background: step > s.id ? 'var(--color-success)' : 'var(--color-border)',
                  transition: 'background 0.3s',
                }} />
              )}
            </div>
          );
        })}
      </div>

      {/* ══════════════════════════════════════ */}
      {/* ÉTAPE 1 — Sélection du poste          */}
      {/* ══════════════════════════════════════ */}
      {step === 1 && (
        <div className="card animate-slide-in">
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 20, color: 'var(--color-text-primary)' }}>
            <Briefcase size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />
            Sélectionnez la fiche de poste
          </h2>

          {jobs.length === 0 ? (
            <div className="empty-state" style={{ padding: '32px 0' }}>
              <div className="empty-state-icon">📋</div>
              <div className="empty-state-title">Aucune fiche de poste</div>
              <p className="empty-state-text">Créez une fiche de poste avant de lancer une analyse</p>
              <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={() => navigate('/postes')}>
                Créer une fiche de poste
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>
              {jobs.map(job => (
                <div
                  key={job.id}
                  onClick={() => setSelectedJobId(job.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 16,
                    padding: '14px 18px',
                    border: `2px solid ${selectedJobId === job.id ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    borderRadius: 'var(--radius-lg)',
                    cursor: 'pointer',
                    background: selectedJobId === job.id ? 'rgba(99,102,241,0.08)' : 'var(--color-bg-secondary)',
                    transition: 'all 0.2s',
                  }}
                >
                  <div style={{
                    width: 40, height: 40, borderRadius: 'var(--radius-md)',
                    background: selectedJobId === job.id ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.05)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    <Briefcase size={18} color={selectedJobId === job.id ? 'var(--color-primary-light)' : 'var(--color-text-muted)'} />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-text-primary)' }}>{job.titre}</div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 2 }}>
                      {[job.entreprise, job.type_contrat, job.localisation].filter(Boolean).join(' · ')}
                    </div>
                  </div>
                  {selectedJobId === job.id && <CheckCircle size={20} color="var(--color-primary-light)" />}
                </div>
              ))}
            </div>
          )}

          <button
            className="btn btn-primary"
            disabled={!selectedJobId}
            onClick={() => setStep(2)}
            style={{ width: '100%', justifyContent: 'center' }}
          >
            Continuer <ChevronRight size={16} />
          </button>
        </div>
      )}

      {/* ══════════════════════════════════════ */}
      {/* ÉTAPE 2 — Upload des CVs              */}
      {/* ══════════════════════════════════════ */}
      {step === 2 && (
        <div className="animate-slide-in">
          {selectedJob && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '10px 16px',
              background: 'rgba(99,102,241,0.08)',
              border: '1px solid var(--color-primary)',
              borderRadius: 'var(--radius-md)',
              marginBottom: 20,
            }}>
              <Briefcase size={16} color="var(--color-primary-light)" />
              <span style={{ fontSize: 13, color: 'var(--color-text-secondary)' }}>Poste sélectionné :</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)' }}>{selectedJob.titre}</span>
              <button
                className="btn btn-secondary btn-sm"
                style={{ marginLeft: 'auto' }}
                onClick={() => setStep(1)}
              >
                Changer
              </button>
            </div>
          )}

          <div className="card" style={{ marginBottom: 20 }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: 'var(--color-text-primary)' }}>
              <UploadIcon size={18} style={{ marginRight: 8, verticalAlign: 'middle' }} />
              Déposez les CVs des candidats
            </h2>

            {/* Dropzone */}
            <div
              {...getRootProps()}
              style={{
                border: `2px dashed ${isDragActive ? 'var(--color-primary)' : 'var(--color-border)'}`,
                borderRadius: 'var(--radius-lg)',
                padding: '40px 20px',
                textAlign: 'center',
                background: isDragActive ? 'rgba(99,102,241,0.06)' : 'var(--color-bg-secondary)',
                cursor: 'pointer',
                transition: 'all 0.2s',
                marginBottom: 20,
              }}
            >
              <input {...getInputProps()} />
              <UploadIcon size={40} color={isDragActive ? 'var(--color-primary-light)' : 'var(--color-text-muted)'} style={{ margin: '0 auto 12px' }} />
              <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-text-primary)', margin: '0 0 4px' }}>
                {isDragActive ? 'Relâchez pour ajouter' : 'Glissez vos CVs ici'}
              </p>
              <p style={{ fontSize: 13, color: 'var(--color-text-muted)', margin: 0 }}>
                PDF, DOCX ou TXT — plusieurs fichiers acceptés
              </p>
            </div>

            {/* Liste des fichiers */}
            {cvFiles.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }}>
                {cvFiles.map((f, idx) => (
                  <div key={idx} style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 14px',
                    background: 'var(--color-bg-secondary)',
                    border: `1px solid ${f.status === 'done' ? 'var(--color-success)' : f.status === 'error' ? 'var(--color-danger)' : 'var(--color-border)'}`,
                    borderRadius: 'var(--radius-md)',
                  }}>
                    <FileText size={16} color={
                      f.status === 'done' ? 'var(--color-success)' :
                      f.status === 'error' ? 'var(--color-danger)' :
                      'var(--color-text-muted)'
                    } />
                    <span style={{ flex: 1, fontSize: 13, color: 'var(--color-text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {f.name}
                    </span>
                    {f.status === 'uploading' && <div className="spinner" style={{ width: 14, height: 14, flexShrink: 0 }} />}
                    {f.status === 'done' && <CheckCircle size={14} color="var(--color-success)" />}
                    {f.status === 'error' && <span style={{ fontSize: 11, color: 'var(--color-danger)' }}>Erreur</span>}
                    {f.status === 'pending' && (
                      <button
                        onClick={() => removeFile(idx)}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                      >
                        <X size={14} color="var(--color-text-muted)" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Actions */}
            <div style={{ display: 'flex', gap: 12 }}>
              {cvFiles.some(f => f.status === 'pending') && (
                <button
                  className="btn btn-secondary"
                  onClick={uploadAllCVs}
                  disabled={uploading}
                  style={{ flex: 1 }}
                >
                  {uploading
                    ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Téléversement...</>
                    : <><UploadIcon size={14} /> Téléverser les CVs</>
                  }
                </button>
              )}
              <button
                className="btn btn-primary"
                onClick={launchBatch}
                disabled={!canAnalyze || analyzing}
                style={{ flex: 1, justifyContent: 'center' }}
              >
                {analyzing
                  ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Analyse en cours...</>
                  : <><Play size={14} fill="white" /> Analyser {readyCount} CV{readyCount > 1 ? 's' : ''}</>
                }
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════ */}
      {/* ÉTAPE 3 — Résultats du batch          */}
      {/* ══════════════════════════════════════ */}
      {step === 3 && (
        <div className="animate-slide-in">
          {(!batchResult || (batchResult.statut === 'en_cours' && !batchResult.classement?.length)) ? (
            <BatchProgress batchResult={batchResult} title="Calcul du classement en cours..." text="Le système parse les CVs, extrait les sections et effectue le matching RAG." />
          ) : batchResult.statut === 'erreur' ? (
            <div className="card" style={{ textAlign: 'center', padding: 48 }}>
              <p style={{ color: 'var(--color-danger)' }}>Erreur: {batchResult.message_erreur}</p>
              <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={() => setStep(2)}>
                Réessayer
              </button>
            </div>
          ) : batchResult.statut === 'attente_selection' ? (
            <BatchSelection batchResult={batchResult} onLaunch={launchLanggraph} />
          ) : batchResult.statut === 'en_cours' && batchResult.classement?.length ? (
            <BatchProgress batchResult={batchResult} title="Analyse approfondie en cours..." text="Le pipeline LangGraph génère les rapports détaillés pour les candidats sélectionnés." />
          ) : (
            <BatchResults batchResult={batchResult} navigate={navigate} onReset={() => { setCvFiles([]); setStep(1); setBatchResult(null); }} />
          )}
        </div>
      )}
    </div>
  );
}


// ── Composant : Progression du batch ──────────────────────

function BatchProgress({ batchResult, title = "Analyse en cours...", text="Veuillez patienter." }) {
  const progress = batchResult;
  const ranking = progress?.classement || [];

  return (
    <div className="card" style={{ textAlign: 'center', padding: '48px 32px' }}>
      <div style={{
        width: 72, height: 72, borderRadius: '50%',
        background: 'var(--gradient-primary)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        margin: '0 auto 20px',
        animation: 'pulse-glow 2s ease-in-out infinite',
      }}>
        <TrendingUp size={32} color="white" />
      </div>
      <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>{title}</h2>
      <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', marginBottom: 32 }}>
        {text}
      </p>

      {ranking.length > 0 && (
        <div style={{ maxWidth: 400, margin: '0 auto', textAlign: 'left' }}>
          <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase' }}>
            Classement RAG (préliminaire)
          </div>
          {ranking.slice(0, 5).map((item, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 12px',
              background: i < 3 ? 'rgba(99,102,241,0.08)' : 'transparent',
              borderRadius: 'var(--radius-md)',
              marginBottom: 4,
            }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-muted)', width: 24 }}>#{i + 1}</span>
              <span style={{ flex: 1, fontSize: 13, color: 'var(--color-text-primary)' }}>
                {item.nom_candidat || 'Candidat #' + (i + 1)}
              </span>
              <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-primary-light)' }}>
                {item.score_rag_global?.toFixed(0)}/100
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


// ── Composant : Résultats du batch ─────────────────────────

function BatchResults({ batchResult, navigate, onReset }) {
  const ranking = batchResult?.classement || [];
  const top3 = batchResult?.top3_analyses || [];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--color-text-primary)' }}>
          🏆 Résultats de l'Analyse
        </h2>
        <span className="badge badge-success">
          {ranking.length} CVs classés
        </span>
      </div>

      {/* Podium Top 3 */}
      {top3.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 32 }}>
          {top3.map((analyse, i) => {
            const { icon: RankIcon, color } = RANK_ICONS[i] || RANK_ICONS[2];
            const rapport = analyse.rapport;
            const score = rapport?.scores?.score_global ?? 0;
            const rec = rapport?.recommandation;
            return (
              <div
                key={analyse.id}
                className="card"
                onClick={() => navigate(`/analyses/${analyse.id}`)}
                style={{
                  cursor: 'pointer',
                  border: `2px solid ${i === 0 ? 'rgba(245,158,11,0.4)' : 'var(--color-border)'}`,
                  transition: 'var(--transition-base)',
                  position: 'relative',
                  textAlign: 'center',
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--color-border-bright)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = i === 0 ? 'rgba(245,158,11,0.4)' : 'var(--color-border)'}
              >
                <div style={{
                  position: 'absolute', top: -14, left: '50%', transform: 'translateX(-50%)',
                  padding: '2px 10px',
                  background: 'var(--color-bg-primary)',
                  border: `2px solid ${color}`,
                  borderRadius: 20,
                  fontSize: 12, fontWeight: 700, color,
                }}>
                  #{analyse.rang || i + 1}
                </div>
                <div style={{
                  width: 52, height: 52, borderRadius: '50%',
                  background: `${color}22`, border: `2px solid ${color}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '16px auto 12px',
                }}>
                  <RankIcon size={24} color={color} />
                </div>
                <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 4 }}>
                  {analyse.nom_candidat || 'Candidat'}
                </div>
                <div style={{ fontSize: 24, fontWeight: 800, color, marginBottom: 4 }}>
                  {score.toFixed(0)}<span style={{ fontSize: 14, fontWeight: 400, color: 'var(--color-text-muted)' }}>/100</span>
                </div>
                {rec && (
                  <span className={`badge ${rec === 'Entretien recommandé' ? 'badge-success' : rec === 'À considérer' ? 'badge-warning' : 'badge-danger'}`} style={{ fontSize: 10 }}>
                    {rec}
                  </span>
                )}
                <div style={{ marginTop: 12, fontSize: 11, color: 'var(--color-text-muted)' }}>
                  Voir le rapport →
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Classement complet */}
      <div className="card">
        <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16, color: 'var(--color-text-primary)' }}>
          Classement Complet — Score RAG pondéré
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {ranking.map((item, i) => (
            <div key={i} style={{
              display: 'grid', gridTemplateColumns: '36px 1fr 80px 80px 80px 80px',
              alignItems: 'center', gap: 8,
              padding: '8px 12px',
              background: i < 3 ? 'rgba(99,102,241,0.06)' : 'transparent',
              borderRadius: 'var(--radius-md)',
              borderLeft: i < 3 ? '3px solid var(--color-primary)' : '3px solid transparent',
            }}>
              <span style={{ fontSize: 13, fontWeight: 700, color: i < 3 ? 'var(--color-primary-light)' : 'var(--color-text-muted)', textAlign: 'center' }}>
                #{item.rang}
              </span>
              <span style={{ fontSize: 13, color: 'var(--color-text-primary)', fontWeight: i < 3 ? 600 : 400 }}>
                {item.nom_candidat || 'Candidat'}
              </span>
              <ScoreCell label="Tech" value={item.scores_sections?.competences} />
              <ScoreCell label="Exp" value={item.scores_sections?.experience} />
              <ScoreCell label="Form" value={item.scores_sections?.formation} />
              <span style={{ fontSize: 14, fontWeight: 800, color: item.score_rag_global >= 70 ? 'var(--color-success)' : item.score_rag_global >= 50 ? 'var(--color-warning)' : 'var(--color-danger)', textAlign: 'right' }}>
                {item.score_rag_global?.toFixed(0)}
              </span>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '36px 1fr 80px 80px 80px 80px', gap: 8, padding: '6px 12px', marginTop: 8, borderTop: '1px solid var(--color-border)' }}>
          <span /><span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontWeight: 600 }}>Candidat</span>
          <span style={{ fontSize: 10, color: 'var(--color-text-muted)', textAlign: 'center' }}>Tech 40%</span>
          <span style={{ fontSize: 10, color: 'var(--color-text-muted)', textAlign: 'center' }}>Exp 30%</span>
          <span style={{ fontSize: 10, color: 'var(--color-text-muted)', textAlign: 'center' }}>Form 20%</span>
          <span style={{ fontSize: 11, color: 'var(--color-text-muted)', fontWeight: 600, textAlign: 'right' }}>Score</span>
        </div>
      </div>

      <button
        className="btn btn-secondary"
        style={{ marginTop: 20 }}
        onClick={onReset}
      >
        Nouvelle Analyse
      </button>
    </div>
  );
}

function ScoreCell({ label, value }) {
  const v = value ?? 0;
  const color = v >= 70 ? 'var(--color-success)' : v >= 50 ? 'var(--color-warning)' : 'var(--color-danger)';
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 12, fontWeight: 700, color }}>{v.toFixed(0)}</div>
    </div>
  );
}

// ── Composant : Sélection du Top X ─────────────────────────

function BatchSelection({ batchResult, onLaunch }) {
  const ranking = batchResult?.classement || [];
  // Par défaut, sélectionner les 3 premiers
  const [selectedIds, setSelectedIds] = useState(() => ranking.slice(0, 3).map(r => r.cv_id));

  const toggleSelect = (cvId) => {
    setSelectedIds(prev =>
      prev.includes(cvId) ? prev.filter(id => id !== cvId) : [...prev, cvId]
    );
  };

  return (
    <div>
      <div className="card" style={{ marginBottom: 20 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12, color: 'var(--color-text-primary)' }}>
          📊 Classement Préliminaire (RAG)
        </h2>
        <p style={{ fontSize: 14, color: 'var(--color-text-secondary)', marginBottom: 20 }}>
          Veuillez sélectionner les candidats à envoyer à l'analyseur approfondi (LangGraph). Par défaut, les 3 meilleurs sont sélectionnés.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {ranking.map((item, i) => {
            const isSelected = selectedIds.includes(item.cv_id);
            return (
              <div
                key={item.cv_id}
                onClick={() => toggleSelect(item.cv_id)}
                style={{
                  display: 'grid', gridTemplateColumns: '40px 36px 1fr 80px 80px 80px 80px',
                  alignItems: 'center', gap: 8,
                  padding: '10px 12px',
                  background: isSelected ? 'rgba(99,102,241,0.06)' : 'var(--color-bg-secondary)',
                  borderRadius: 'var(--radius-md)',
                  border: `1px solid ${isSelected ? 'var(--color-primary)' : 'var(--color-border)'}`,
                  cursor: 'pointer',
                  transition: 'background 0.2s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'center' }}>
                  <div style={{
                    width: 20, height: 20, borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    border: `2px solid ${isSelected ? 'var(--color-primary)' : 'var(--color-text-muted)'}`,
                    background: isSelected ? 'var(--color-primary)' : 'transparent',
                  }}>
                    {isSelected && <CheckCircle size={14} color="white" />}
                  </div>
                </div>
                <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-muted)', textAlign: 'center' }}>
                  #{item.rang}
                </span>
                <span style={{ fontSize: 13, color: 'var(--color-text-primary)', fontWeight: 600 }}>
                  {item.nom_candidat || 'Candidat'}
                </span>
                <ScoreCell label="Tech" value={item.scores_sections?.competences} />
                <ScoreCell label="Exp" value={item.scores_sections?.experience} />
                <ScoreCell label="Form" value={item.scores_sections?.formation} />
                <span style={{ fontSize: 14, fontWeight: 800, color: item.score_rag_global >= 70 ? 'var(--color-success)' : item.score_rag_global >= 50 ? 'var(--color-warning)' : 'var(--color-danger)', textAlign: 'right' }}>
                  {item.score_rag_global?.toFixed(0)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          className="btn btn-primary"
          disabled={selectedIds.length === 0}
          onClick={() => onLaunch(selectedIds)}
          style={{ width: '100%', justifyContent: 'center', fontSize: 15 }}
        >
          <Play size={16} fill="white" style={{ marginRight: 8 }}/>
          Lancer l'analyse approfondie ({selectedIds.length} candidat{selectedIds.length > 1 ? 's' : ''})
        </button>
      </div>
    </div>
  );
}
