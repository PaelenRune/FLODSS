import React, { useState, useEffect } from 'react';
import {
  LayoutDashboard,
  Sliders,
  Grid,
  ShieldAlert,
  Play,
  Maximize2,
  TrendingUp,
  Package,
  Layers,
  Sparkles,
} from 'lucide-react';

import { useHealthCheck } from '../hooks/useHealthCheck';
import { Header } from '../components/Header';
import { RoadmapStepper } from '../components/RoadmapStepper';
import { SystemStatusCard } from '../components/SystemStatusCard';
import { ModuleGrid } from '../components/ModuleGrid';
import { ProblemEditorCard } from '../components/ProblemEditorCard';
import { MatrixEditorCard } from '../components/MatrixEditorCard';
import { ConstraintEditorCard } from '../components/ConstraintEditorCard';
import { OptimizationWorkspaceCard } from '../components/OptimizationWorkspaceCard';
import { LayoutCanvas } from '../components/LayoutCanvas';
import { DecisionGuidanceBox } from '../components/DecisionGuidanceBox';
import { LayoutViewerCard } from '../components/LayoutViewerCard';
import { ParetoAnalysisCard } from '../components/ParetoAnalysisCard';
import { AlgorithmComparisonCard } from '../components/AlgorithmComparisonCard';
import { AdaptiveStrategyCard } from '../components/AdaptiveStrategyCard';
import { AIExplanationCard } from '../components/AIExplanationCard';
import { ExportCenterCard } from '../components/ExportCenterCard';
import { AlgorithmRunnerCard } from '../components/AlgorithmRunnerCard';
import { LayoutEvaluationCard } from '../components/LayoutEvaluationCard';
import { ProblemDefinitionCard } from '../components/ProblemDefinitionCard';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { LoginModal } from '../components/LoginModal';
import { InvitationAcceptModal } from '../components/InvitationAcceptModal';
import { UserManagementModal } from '../components/UserManagementModal';
import { ProjectManagerCard } from '../components/ProjectManagerCard';

import {
  fetchExampleProblems,
  fetchExampleProblem,
  fetchExampleLayouts,
  fetchExampleLayout,
  evaluateLayout,
  validateLayout,
} from '../services/api';

import {
  FacilityLayoutProblem,
  ContinuousLayout,
  EvaluationReport,
  LayoutValidationResult,
  ProblemSummary,
} from '../types/api';

type TabId =
  | 'overview'
  | 'problem'
  | 'matrices'
  | 'constraints'
  | 'solvers'
  | 'layout'
  | 'pareto'
  | 'decision'
  | 'export';

interface TabItem {
  id: TabId;
  label: string;
  icon: React.ReactNode;
  badge?: string;
}

export const Dashboard: React.FC = () => {
  const { data: status, loading: healthLoading, error: healthError, refresh: refreshHealth } = useHealthCheck(15000);

  // Active Navigation
  const [activeTab, setActiveTab] = useState<TabId>('problem');
  const [viewMode, setViewMode] = useState<'workspace' | 'all'>('workspace');

  // Shared Core State
  const [availableProblems, setAvailableProblems] = useState<ProblemSummary[]>([]);
  const [problem, setProblem] = useState<FacilityLayoutProblem | null>(null);
  const [layout, setLayout] = useState<ContinuousLayout | null>(null);
  const [validation, setValidation] = useState<LayoutValidationResult | null>(null);
  const [evaluation, setEvaluation] = useState<EvaluationReport | null>(null);
  const [selectedDeptId, setSelectedDeptId] = useState<string | null>(null);
  const [executionInfo, setExecutionInfo] = useState<{
    algorithm: string;
    seed?: number;
    durationMs?: number;
    config?: Record<string, any>;
  } | null>(null);

  const problemVersionRef = React.useRef<number>(0);

  const { user, isLoading: authLoading } = useAuth();
  const { t } = useLanguage();
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);
  const [showInviteModal, setShowInviteModal] = useState<boolean>(false);
  const [showUserMgmtModal, setShowUserMgmtModal] = useState<boolean>(false);

  // Initial Load: Problem catalog & default Industrial 10 benchmark when authenticated
  useEffect(() => {
    if (!user) {
      setAvailableProblems([]);
      setProblem(null);
      setLayout(null);
      setValidation(null);
      setEvaluation(null);
      return;
    }

    async function initPlatform() {
      try {
        const catalog = await fetchExampleProblems();
        setAvailableProblems(catalog);

        const targetId = catalog.some((p) => p.id === 'FLP_INDUSTRIAL_10')
          ? 'FLP_INDUSTRIAL_10'
          : catalog[0]?.id;

        if (targetId) {
          problemVersionRef.current += 1;
          const currentVersion = problemVersionRef.current;
          const prob = await fetchExampleProblem(targetId);
          if (problemVersionRef.current !== currentVersion) return;
          setProblem(prob);

          // Try to load initial reference layout
          try {
            const exampleLayouts = await fetchExampleLayouts();
            const targetLayout = exampleLayouts.find((l) => l.problem_id === targetId) || exampleLayouts[0];
            if (targetLayout) {
              const loadedLayout = await fetchExampleLayout(targetLayout.id);
              if (problemVersionRef.current !== currentVersion) return;
              setLayout(loadedLayout);

              // Validate & evaluate against loaded problem
              try {
                const valResult = await validateLayout(targetId, loadedLayout, prob);
                if (problemVersionRef.current === currentVersion) setValidation(valResult);
              } catch (_) {}

              try {
                const evalReport = await evaluateLayout(targetId, loadedLayout, undefined, prob);
                if (problemVersionRef.current === currentVersion) setEvaluation(evalReport);
              } catch (_) {}
            }
          } catch (_) {}
        }
      } catch (err) {
        console.warn('Initial platform data fetch failed:', err);
      }
    }

    initPlatform();
  }, [user]);

  // Handle benchmark example loading
  const handleLoadExample = async (problemId: string) => {
    problemVersionRef.current += 1;
    const currentVersion = problemVersionRef.current;
    setLayout(null);
    setValidation(null);
    setEvaluation(null);
    setExecutionInfo(null);
    try {
      const prob = await fetchExampleProblem(problemId);
      if (problemVersionRef.current !== currentVersion) return;
      setProblem(prob);

      // Attempt to find matching layout
      try {
        const exampleLayouts = await fetchExampleLayouts();
        const matching = exampleLayouts.find((l) => l.problem_id === problemId);
        if (matching) {
          const loadedLayout = await fetchExampleLayout(matching.id);
          if (problemVersionRef.current !== currentVersion) return;
          setLayout(loadedLayout);
          const valResult = await validateLayout(problemId, loadedLayout, prob);
          if (problemVersionRef.current === currentVersion) setValidation(valResult);
          const evalReport = await evaluateLayout(problemId, loadedLayout, undefined, prob);
          if (problemVersionRef.current === currentVersion) setEvaluation(evalReport);
        }
      } catch (_) {}
    } catch (err: any) {
      alert(`Failed to load benchmark problem '${problemId}': ${err?.message}`);
    }
  };

  const handleUpdateProblem = (updatedProblem: FacilityLayoutProblem) => {
    setProblem(updatedProblem);
    if (layout) {
      validateLayout(updatedProblem.id, layout, updatedProblem)
        .then(setValidation)
        .catch(() => {});
      evaluateLayout(updatedProblem.id, layout, undefined, updatedProblem)
        .then(setEvaluation)
        .catch(() => {});
    }
  };

  // Handle solution generated by solvers
  const handleSolutionGenerated = (
    newLayout: ContinuousLayout,
    newValidation?: LayoutValidationResult | null,
    newEvaluation?: EvaluationReport | null,
    metadata?: Record<string, any> | null
  ) => {
    setLayout(newLayout);
    if (newValidation) {
      setValidation(newValidation);
    } else if (problem) {
      validateLayout(problem.id, newLayout, problem).then(setValidation).catch(() => {});
    }
    if (newEvaluation) {
      setEvaluation(newEvaluation);
    } else if (problem) {
      evaluateLayout(problem.id, newLayout, undefined, problem).then(setEvaluation).catch(() => {});
    }
    if (metadata) {
      setExecutionInfo({
        algorithm: metadata.algorithm || 'Custom Solver',
        seed: metadata.seed,
        durationMs: metadata.duration_ms,
        config: metadata,
      });
    }
  };

  const handleImportLayout = async (importedLayout: ContinuousLayout) => {
    setLayout(importedLayout);
    if (problem) {
      try {
        const valRes = await validateLayout(problem.id, importedLayout, problem);
        setValidation(valRes);
      } catch (_) {}
      try {
        const evalRes = await evaluateLayout(problem.id, importedLayout, undefined, problem);
        setEvaluation(evalRes);
      } catch (_) {}
    }
    setActiveTab('layout');
  };

  const handleSelectParetoCandidate = (cand: any) => {
    if (cand.placements) {
      const placementsMap: Record<string, any> = {};
      for (const [did, p] of Object.entries(cand.placements)) {
        const dp: any = p;
        placementsMap[did] = {
          department_id: did,
          x: dp.x ?? dp.origin?.x ?? 0,
          y: dp.y ?? dp.origin?.y ?? 0,
          width: dp.width ?? dp.dimensions?.width ?? 10,
          height: dp.height ?? dp.dimensions?.height ?? 10,
          orientation_degrees: dp.orientation_degrees ?? 0,
        };
      }
      const newLayout: ContinuousLayout = {
        problem_id: cand.problem_id || problem?.id,
        representation_type: 'continuous',
        facility_width: problem?.facility?.width ?? (problem as any)?.facility_width ?? 150.0,
        facility_height: problem?.facility?.height ?? (problem as any)?.facility_height ?? 80.0,
        placements: placementsMap,
        layout_signature: cand.layout_signature,
      };
      setLayout(newLayout);
      if (problem) {
        validateLayout(problem.id, newLayout, problem).then(setValidation).catch(() => {});
        evaluateLayout(problem.id, newLayout, undefined, problem).then(setEvaluation).catch(() => {});
      }
    }
  };

  const tabs: TabItem[] = [
    { id: 'problem', label: t('1. Problem Tanımı', '1. Problem Editor'), icon: <Sliders size={16} /> },
    { id: 'matrices', label: t('2. Flow & REL Matrisleri', '2. Flow & REL'), icon: <Grid size={16} /> },
    { id: 'constraints', label: t('3. Kısıtlar (Constraints)', '3. Constraints'), icon: <ShieldAlert size={16} /> },
    { id: 'solvers', label: t('4. Optimizasyon', '4. Optimization'), icon: <Play size={16} />, badge: t('6 Çözücü', '6 Solvers') },
    { id: 'layout', label: t('5. 2D Layout Görünümü', '5. 2D Layout Viewer'), icon: <Maximize2 size={16} />, badge: layout ? t('Aktif', 'Active') : undefined },
    { id: 'pareto', label: t('6. Pareto Front & Trade-offs', '6. Pareto & Trade-offs'), icon: <TrendingUp size={16} /> },
    { id: 'decision', label: t('7. AI Karar Destek', '7. AI Decision Support'), icon: <Sparkles size={16} /> },
    { id: 'export', label: t('8. Dışa Aktarım (Export)', '8. Export Center'), icon: <Package size={16} />, badge: 'v1.0' },
    { id: 'overview', label: t('Sistem Özeti', 'System Overview'), icon: <LayoutDashboard size={16} /> },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-primary)' }}>
      {/* Top Header with Release Candidate and Local-First Badges */}
      <Header
        status={status ? status.status : null}
        loading={healthLoading}
        error={healthError}
        onOpenUserManagement={() => setShowUserMgmtModal(true)}
        onOpenLogin={() => setShowLoginModal(true)}
      />

      {/* Controlled Research Access Modals */}
      {(!user && !authLoading && !showInviteModal) || (showLoginModal && !showInviteModal) ? (
        <LoginModal onOpenInvite={() => { setShowLoginModal(false); setShowInviteModal(true); }} />
      ) : null}

      {showInviteModal && (
        <InvitationAcceptModal
          onClose={() => setShowInviteModal(false)}
          onOpenLogin={() => { setShowInviteModal(false); setShowLoginModal(true); }}
        />
      )}

      {showUserMgmtModal && (
        <UserManagementModal onClose={() => setShowUserMgmtModal(false)} />
      )}

      {/* Main Workspace */}
      <main style={{
        maxWidth: '1440px',
        width: '100%',
        margin: '0 auto',
        padding: '1.5rem 1.5rem 3rem 1.5rem',
        flex: 1,
      }}>
        {/* Research Project & Experiment Isolation Card */}
        {user && (
          <ProjectManagerCard
            currentProblemId={problem?.id}
            currentSolution={layout}
            currentMetrics={evaluation ? {
              material_handling_cost: evaluation.material_handling_cost,
              flow_distance: evaluation.flow_distance,
              relationship_satisfaction: evaluation.relationship_satisfaction_percentage,
              soft_penalty: evaluation.soft_penalty,
              is_feasible: evaluation.is_feasible,
            } : null}
            currentAlgorithmName={executionInfo?.algorithm}
            onRestoreRun={({ layout: restoredLayout }) => {
              setLayout(restoredLayout);
              setActiveTab('layout');
            }}
          />
        )}
        {/* Navigation & Mode Bar */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.5rem',
          borderBottom: '1px solid var(--border-color)',
          paddingBottom: '0.75rem',
        }}>
          {/* Engineering Tab Bar */}
          <nav style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.35rem',
            overflowX: 'auto',
            paddingBottom: '0.25rem',
          }}>
            {tabs.map((tab) => {
              const isActive = activeTab === tab.id && viewMode === 'workspace';
              return (
                <button
                  key={tab.id}
                  data-testid={`tab-${tab.id}`}
                  onClick={() => {
                    setActiveTab(tab.id);
                    setViewMode('workspace');
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.45rem',
                    padding: '0.55rem 0.9rem',
                    borderRadius: '8px',
                    border: '1px solid',
                    borderColor: isActive ? 'var(--accent-color)' : 'transparent',
                    backgroundColor: isActive ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-secondary)',
                    color: isActive ? 'var(--accent-color)' : 'var(--text-secondary)',
                    fontSize: '0.825rem',
                    fontWeight: isActive ? 600 : 500,
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                  {tab.badge && (
                    <span style={{
                      fontSize: '0.7rem',
                      padding: '0.1rem 0.4rem',
                      borderRadius: '9999px',
                      backgroundColor: isActive ? 'var(--accent-color)' : 'var(--bg-card)',
                      color: isActive ? '#ffffff' : 'var(--text-muted)',
                      border: '1px solid var(--border-color)',
                      fontWeight: 600,
                    }}>
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* View Mode Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <button
              onClick={() => setViewMode(viewMode === 'workspace' ? 'all' : 'workspace')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.45rem 0.8rem',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                backgroundColor: 'var(--bg-card)',
                color: 'var(--text-secondary)',
                fontSize: '0.775rem',
                cursor: 'pointer',
              }}
            >
              <Layers size={14} />
              <span>
                {viewMode === 'workspace'
                  ? t('Tüm Modülleri Göster', 'Show All Modules')
                  : t('Sekmeli Görünüm (Workspace)', 'Tabbed Workspace')}
              </span>
            </button>
          </div>
        </div>

        {/* WORKSPACE VIEW: Single Focused Tab */}
        {viewMode === 'workspace' && (
          <div>
            {/* Tab 1: Problem Modeling */}
            {activeTab === 'problem' && (
              <div>
                <ProblemEditorCard
                  problem={problem}
                  onUpdateProblem={handleUpdateProblem}
                  onLoadExample={handleLoadExample}
                  availableExamples={availableProblems}
                />
              </div>
            )}

            {/* Tab 2: Flow & REL Matrices */}
            {activeTab === 'matrices' && (
              <div>
                <MatrixEditorCard
                  problem={problem}
                  onUpdateProblem={handleUpdateProblem}
                />
              </div>
            )}

            {/* Tab 3: Spatial Constraints */}
            {activeTab === 'constraints' && (
              <div>
                <ConstraintEditorCard
                  problem={problem}
                  onUpdateProblem={handleUpdateProblem}
                />
              </div>
            )}

            {/* Tab 4: Optimization Workspace */}
            {activeTab === 'solvers' && (
              <div>
                <OptimizationWorkspaceCard
                  problem={problem}
                  currentLayout={layout}
                  onSolutionGenerated={handleSolutionGenerated}
                  onNavigateToViewer={() => setActiveTab('layout')}
                  onNavigateToPareto={() => setActiveTab('pareto')}
                />
              </div>
            )}

            {/* Tab 5: 2D Layout Viewer */}
            {activeTab === 'layout' && (
              <div style={{
                backgroundColor: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                padding: '1.5rem',
                marginBottom: '2rem',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                  <div>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
                      {t('Etkileşimli 2D Facility Layout Görünümü', 'Interactive 2D Facility Layout Viewer')}
                    </h2>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
                      {t(
                        'Continuous 1:1 koordinat düzlemi • Gerçek zamanlı Zoom & Pan • Overlap & Fixed Position denetimi',
                        'Continuous 1:1 solver coordinates • Real-time zoom & pan • Overlap & fixed position detection'
                      )}
                    </p>
                  </div>
                  {layout && (
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={() => setActiveTab('export')}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.4rem',
                          padding: '0.45rem 0.85rem',
                          borderRadius: '6px',
                          border: 'none',
                          backgroundColor: '#2563eb',
                          color: '#ffffff',
                          fontSize: '0.8rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        <Package size={14} />
                        {t('Çözümü Dışa Aktar (Export)', 'Export Solution')}
                      </button>
                    </div>
                  )}
                </div>

                <DecisionGuidanceBox mode="layout" defaultOpen={false} />

                <LayoutCanvas
                  layout={layout}
                  problem={problem}
                  validation={validation}
                  selectedDeptId={selectedDeptId}
                  onSelectDept={setSelectedDeptId}
                />
              </div>
            )}

            {/* Tab 6: Multi-Objective Pareto */}
            {activeTab === 'pareto' && (
              <div>
                <ParetoAnalysisCard
                  problem={problem}
                  activeLayout={layout}
                  onSelectCandidate={handleSelectParetoCandidate}
                />
                <div style={{ marginTop: '2rem' }}>
                  <AlgorithmComparisonCard />
                </div>
              </div>
            )}

            {/* Tab 7: AI Decision Explanation */}
            {activeTab === 'decision' && (
              <div>
                <AIExplanationCard
                  problem={problem}
                  currentLayout={layout}
                  evaluation={evaluation}
                />
                <div style={{ marginTop: '2rem' }}>
                  <AdaptiveStrategyCard
                    problem={problem}
                    currentLayout={layout}
                    evaluation={evaluation}
                  />
                </div>
              </div>
            )}

            {/* Tab 8: Thesis Export & Provenance */}
            {activeTab === 'export' && (
              <div>
                <ExportCenterCard
                  problem={problem}
                  layout={layout}
                  evaluation={evaluation}
                  validation={validation}
                  executionInfo={executionInfo}
                  onImportLayout={handleImportLayout}
                />
              </div>
            )}

            {/* Tab 9: System Overview */}
            {activeTab === 'overview' && (
              <div>
                <div style={{ marginBottom: '2rem' }}>
                  <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.025em', marginBottom: '0.5rem' }}>
                    {t(
                      'Tesis Yerleşim Optimizasyon & Karar Destek Sistemi (FLODSS)',
                      'Facility Layout Optimization & Decision Support System (FLODSS)'
                    )}
                  </h1>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: '850px', lineHeight: 1.6 }}>
                    {t(
                      'Modüler tesis yerleşim üretimi (FLP), çok ölçütlü algoritmik değerlendirme (MHC, TCR, Adjacency, Dead Space) ve açıklanabilir karar destek için geliştirilmiş ileri seviye Yöneylem Araştırması ve Endüstri Mühendisliği platformu.',
                      'An advanced Operations Research and Industrial Engineering platform for modular facility layout generation, multi-criteria algorithmic evaluation, and explainable decision support.'
                    )}
                  </p>
                </div>
                <RoadmapStepper />
                <SystemStatusCard
                  status={status}
                  loading={healthLoading}
                  error={healthError}
                  onRefresh={refreshHealth}
                />
                <ModuleGrid status={status} />
              </div>
            )}
          </div>
        )}

        {/* ALL MODULES VIEW: Scrollable diagnostic overview */}
        {viewMode === 'all' && (
          <div>
            <div style={{ marginBottom: '2rem' }}>
              <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.025em', marginBottom: '0.5rem' }}>
                {t('FLODSS Tam Mimari Görünümü', 'FLODSS Complete Architecture Overview')}
              </h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: '850px', lineHeight: 1.6 }}>
                {t(
                  'Entegre edilmiş tüm algoritmik çözücüleri ve analiz modüllerini gösteren tam sistem görünümü.',
                  'Full system diagnostic view displaying all integrated algorithmic and analysis modules.'
                )}
              </p>
            </div>

            <RoadmapStepper />
            <ProblemEditorCard
              problem={problem}
              onUpdateProblem={handleUpdateProblem}
              onLoadExample={handleLoadExample}
              availableExamples={availableProblems}
            />
            <MatrixEditorCard problem={problem} onUpdateProblem={handleUpdateProblem} />
            <ConstraintEditorCard problem={problem} onUpdateProblem={handleUpdateProblem} />
            <OptimizationWorkspaceCard
              problem={problem}
              currentLayout={layout}
              onSolutionGenerated={handleSolutionGenerated}
              onNavigateToViewer={() => setActiveTab('layout')}
              onNavigateToPareto={() => setActiveTab('pareto')}
            />
            <LayoutViewerCard />
            <ExportCenterCard
              problem={problem}
              layout={layout}
              evaluation={evaluation}
              validation={validation}
              executionInfo={executionInfo}
              onImportLayout={handleImportLayout}
            />
            <ParetoAnalysisCard
              problem={problem}
              activeLayout={layout}
              onSelectCandidate={handleSelectParetoCandidate}
            />
            <AlgorithmComparisonCard />
            <AdaptiveStrategyCard
              problem={problem}
              currentLayout={layout}
              evaluation={evaluation}
            />
            <AIExplanationCard
              problem={problem}
              currentLayout={layout}
              evaluation={evaluation}
            />
            <AlgorithmRunnerCard />
            <LayoutEvaluationCard />
            <ProblemDefinitionCard />
            <SystemStatusCard
              status={status}
              loading={healthLoading}
              error={healthError}
              onRefresh={refreshHealth}
            />
            <ModuleGrid status={status} />
          </div>
        )}
      </main>

      {/* Footer with Release Candidate Version & Security Boundary */}
      <footer style={{
        borderTop: '1px solid var(--border-color)',
        padding: '1.25rem 2rem',
        backgroundColor: 'var(--bg-secondary)',
        fontSize: '0.8rem',
        color: 'var(--text-muted)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <strong>FLODSS v1.0.0-rc.1</strong>
          <span>&bull;</span>
          <span>{t('Özel Araştırma & Tez Pilot Sürümü', 'Confidential Private Research Release Candidate')}</span>
          <span>&bull;</span>
          <span style={{ color: '#34d399' }}>Local-First Execution</span>
        </div>
        <div>
          Python 3.12+ (FastAPI / Pydantic / NumPy / SciPy) &bull; React 18 / TypeScript / Vite
        </div>
      </footer>
    </div>
  );
};
