import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import {
  OptimizationRunRecord,
  ContinuousLayout,
} from '../types/api';
import {
  getProjectExperimentsApi,
  getExperimentRunApi,
  saveExperimentApi,
} from '../services/api';

interface ProjectManagerCardProps {
  currentProblemId?: string;
  currentSolution?: ContinuousLayout | null;
  currentMetrics?: Record<string, any> | null;
  currentAlgorithmName?: string;
  onRestoreRun?: (runData: {
    run: OptimizationRunRecord;
    layout: ContinuousLayout;
    metrics: Record<string, any>;
  }) => void;
}

export const ProjectManagerCard: React.FC<ProjectManagerCardProps> = ({
  currentProblemId,
  currentSolution,
  currentMetrics,
  currentAlgorithmName,
  onRestoreRun,
}) => {
  const {
    activeProject,
    projects,
    setActiveProject,
    createProject,
    canEdit,
    refreshProjects,
  } = useAuth();
  const { t } = useLanguage();

  const [runs, setRuns] = useState<OptimizationRunRecord[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [isCreatingProj, setIsCreatingProj] = useState(false);
  const [newProjName, setNewProjName] = useState('');
  const [newProjDesc, setNewProjDesc] = useState('');
  const [isSavingRun, setIsSavingRun] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const loadRuns = useCallback(async (projId: string) => {
    setLoadingRuns(true);
    try {
      const records = await getProjectExperimentsApi(projId);
      setRuns(records);
    } catch (e: any) {
      console.warn('Failed to load project experiments:', e.message);
      setRuns([]);
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  useEffect(() => {
    if (activeProject) {
      loadRuns(activeProject.id);
    } else {
      setRuns([]);
    }
  }, [activeProject, loadRuns]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjName.trim()) return;
    try {
      await createProject(newProjName.trim(), newProjDesc.trim() || undefined);
      setIsCreatingProj(false);
      setNewProjName('');
      setNewProjDesc('');
      setStatusMsg({ text: t('Proje başarıyla oluşturuldu.', 'Project created successfully.'), type: 'success' });
    } catch (e: any) {
      setStatusMsg({ text: e.message || t('Proje oluşturulamadı', 'Failed to create project'), type: 'error' });
    }
  };

  const handleSaveCurrentExperiment = async () => {
    if (!activeProject || !currentProblemId || !currentMetrics) {
      setStatusMsg({
        text: t('Lütfen aktif bir problem ve optimizasyon çözümünün bulunduğundan emin olun.', 'Please ensure a problem and optimization run are active.'),
        type: 'error',
      });
      return;
    }
    setIsSavingRun(true);
    setStatusMsg(null);
    try {
      const req = {
        project_id: activeProject.id,
        problem_id: currentProblemId,
        algorithm_name: currentAlgorithmName || 'Manual/Algorithm',
        algorithm_version: '1.0.0',
        parameters: {},
        random_seed: 42,
        runtime_ms: 500.0,
        problem_hash: `hash_${currentProblemId}`,
        evaluation_config_hash: 'config_default',
        layout_signature: currentSolution ? `sig_${Date.now()}` : 'sig_none',
        is_feasible: Boolean(currentMetrics.is_feasible ?? true),
        canonical_metrics: currentMetrics,
        layout_data: currentSolution || undefined,
      };

      await saveExperimentApi(activeProject.id, req);
      setStatusMsg({ text: t('Deney sonucu proje geçmişine kaydedildi.', 'Experiment run archived to project history.'), type: 'success' });
      await loadRuns(activeProject.id);
      await refreshProjects();
    } catch (e: any) {
      setStatusMsg({ text: e.message || t('Deney sonucu kaydedilemedi.', 'Failed to archive experiment run.'), type: 'error' });
    } finally {
      setIsSavingRun(false);
    }
  };

  const handleLoadRun = async (runId: string) => {
    try {
      const detail = await getExperimentRunApi(runId);
      if (detail.layout && onRestoreRun) {
        onRestoreRun({
          run: detail.run,
          layout: detail.layout as ContinuousLayout,
          metrics: detail.run.canonical_metrics || {},
        });
        setStatusMsg({
          text: t(`Deney (${runId.substring(0, 8)}) 2D Layout kanvasına yüklendi.`, `Experiment run ${runId.substring(0, 8)} restored to canvas.`),
          type: 'success',
        });
      } else {
        setStatusMsg({ text: t('Bu kayda ait geometrik yerleşim verisi bulunamadı.', 'Run does not have associated geometric layout data.'), type: 'error' });
      }
    } catch (e: any) {
      setStatusMsg({ text: e.message || t('Deney detayları yüklenemedi.', 'Failed to load run details.'), type: 'error' });
    }
  };

  return (
    <div
      style={{
        backgroundColor: 'var(--card-bg, #1e293b)',
        border: '1px solid var(--border-color, #334155)',
        borderRadius: '12px',
        padding: '1.25rem 1.5rem',
        marginBottom: '1.5rem',
        color: '#f8fafc',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem', marginBottom: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }}>
          <div style={{
            backgroundColor: '#3b82f620',
            color: '#60a5fa',
            padding: '0.4rem 0.65rem',
            borderRadius: '8px',
            fontWeight: 700,
            fontSize: '1rem',
          }}>
            📁
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>
              {t('Aktif Araştırma Projesi', 'Active Research Project')}
            </h3>
            <p style={{ margin: 0, fontSize: '0.75rem', color: '#94a3b8' }}>
              {t('İzole çalışma alanı & tekrarlanabilir deney (Experiment Run) arşivi', 'Isolated workspace & reproducible experiment run archive')}
            </p>
          </div>
        </div>

        {/* Project Selector & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <select
            value={activeProject?.id || ''}
            onChange={(e) => {
              const selected = projects.find((p) => p.id === e.target.value);
              if (selected) setActiveProject(selected);
            }}
            style={{
              padding: '0.45rem 0.85rem',
              borderRadius: '8px',
              backgroundColor: '#0f172a',
              border: '1px solid #334155',
              color: '#ffffff',
              fontSize: '0.85rem',
              fontWeight: 600,
              minWidth: '220px',
            }}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.run_count} {t('deney', 'runs')})
              </option>
            ))}
            {projects.length === 0 && <option value="">{t('Proje bulunmuyor', 'No projects available')}</option>}
          </select>

          {canEdit && (
            <button
              onClick={() => setIsCreatingProj(!isCreatingProj)}
              style={{
                padding: '0.45rem 0.85rem',
                backgroundColor: isCreatingProj ? '#475569' : '#0284c7',
                color: '#fff',
                borderRadius: '8px',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.825rem',
                cursor: 'pointer',
              }}
            >
              {isCreatingProj ? t('İptal', 'Cancel') : t('+ Yeni Proje', '+ New Project')}
            </button>
          )}

          {canEdit && currentSolution && (
            <button
              onClick={handleSaveCurrentExperiment}
              disabled={isSavingRun || !activeProject}
              style={{
                padding: '0.45rem 0.85rem',
                backgroundColor: '#059669',
                color: '#fff',
                borderRadius: '8px',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.825rem',
                cursor: isSavingRun || !activeProject ? 'not-allowed' : 'pointer',
                opacity: isSavingRun || !activeProject ? 0.7 : 1,
              }}
            >
              {isSavingRun ? t('Kaydediliyor...', 'Archiving...') : t('💾 Mevcut Çözümü Kaydet', '💾 Save Current Run')}
            </button>
          )}
        </div>
      </div>

      {statusMsg && (
        <div
          style={{
            padding: '0.5rem 0.85rem',
            borderRadius: '6px',
            fontSize: '0.8rem',
            marginBottom: '0.85rem',
            backgroundColor: statusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            color: statusMsg.type === 'success' ? '#6ee7b7' : '#fca5a5',
            border: `1px solid ${statusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
          }}
        >
          {statusMsg.type === 'success' ? '✅' : '⚠️'} {statusMsg.text}
        </div>
      )}

      {/* New Project Inline Form */}
      {isCreatingProj && (
        <form onSubmit={handleCreateProject} style={{ backgroundColor: '#0f172a', padding: '1rem', borderRadius: '8px', marginBottom: '1rem', border: '1px solid #334155' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr auto', gap: '0.75rem', alignItems: 'center' }}>
            <input
              type="text"
              value={newProjName}
              onChange={(e) => setNewProjName(e.target.value)}
              placeholder={t('Proje Adı (Örn: Yüksek Lisans Tez Çalışması A)', 'Project Name (e.g. Master Thesis Study A)')}
              required
              style={{ padding: '0.45rem 0.75rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#fff', fontSize: '0.825rem' }}
            />
            <input
              type="text"
              value={newProjDesc}
              onChange={(e) => setNewProjDesc(e.target.value)}
              placeholder={t('Açıklama / Hipotez (isteğe bağlı)', 'Description / Hypothesis (optional)')}
              style={{ padding: '0.45rem 0.75rem', backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '6px', color: '#fff', fontSize: '0.825rem' }}
            />
            <button
              type="submit"
              style={{ padding: '0.45rem 1rem', backgroundColor: '#10b981', color: '#fff', borderRadius: '6px', border: 'none', fontWeight: 600, fontSize: '0.825rem', cursor: 'pointer' }}
            >
              {t('Projeyi Oluştur', 'Create Project')}
            </button>
          </div>
        </form>
      )}

      {/* Experiment Runs Table */}
      {activeProject && (
        <div style={{ marginTop: '0.5rem' }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#94a3b8', marginBottom: '0.4rem', display: 'flex', justifyContent: 'space-between' }}>
            <span>
              {t(`Proje Deney Geçmişi (${runs.length} kayıt)`, `Project Experiment History (${runs.length} runs archived)`)}
            </span>
            {loadingRuns && <span>{t('Yükleniyor...', 'Loading runs...')}</span>}
          </div>

          {runs.length === 0 ? (
            <div style={{ fontSize: '0.775rem', color: '#64748b', fontStyle: 'italic', padding: '0.5rem 0' }}>
              {t(
                'Bu projede henüz kaydedilmiş bir optimizasyon deneyi yok. Bir algoritma çalıştırıp "Mevcut Çözümü Kaydet" butonuna tıklayarak sonuçları arşivleyebilirsiniz.',
                'No optimization runs saved in this project yet. Run an algorithm and click "Save Current Run" to persist results.'
              )}
            </div>
          ) : (
            <div style={{ maxHeight: '180px', overflowY: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.775rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8', textAlign: 'left' }}>
                    <th style={{ padding: '0.4rem' }}>{t('Algoritma', 'Algorithm')}</th>
                    <th style={{ padding: '0.4rem' }}>Problem</th>
                    <th style={{ padding: '0.4rem' }}>MHC Cost</th>
                    <th style={{ padding: '0.4rem' }}>Runtime</th>
                    <th style={{ padding: '0.4rem' }}>Feasibility</th>
                    <th style={{ padding: '0.4rem', textAlign: 'right' }}>{t('İşlem', 'Action')}</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((r) => {
                    const mhc = r.canonical_metrics?.material_handling_cost;
                    return (
                      <tr key={r.id} style={{ borderBottom: '1px solid #1e293b' }}>
                        <td style={{ padding: '0.4rem', fontWeight: 600, color: '#38bdf8' }}>{r.algorithm_name}</td>
                        <td style={{ padding: '0.4rem' }}>{r.problem_id}</td>
                        <td style={{ padding: '0.4rem' }}>{mhc !== undefined ? mhc.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}</td>
                        <td style={{ padding: '0.4rem' }}>{r.runtime_ms.toFixed(1)} ms</td>
                        <td style={{ padding: '0.4rem', color: r.is_feasible ? '#34d399' : '#f87171' }}>{r.is_feasible ? '✓ Feasible' : '✗ Infeasible'}</td>
                        <td style={{ padding: '0.4rem', textAlign: 'right' }}>
                          <button
                            onClick={() => handleLoadRun(r.id)}
                            style={{
                              padding: '0.2rem 0.5rem',
                              backgroundColor: '#2563eb',
                              color: '#fff',
                              borderRadius: '4px',
                              border: 'none',
                              cursor: 'pointer',
                              fontSize: '0.725rem',
                              fontWeight: 600,
                            }}
                          >
                            {t('Kanvasa Yükle', 'Load Run')}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
