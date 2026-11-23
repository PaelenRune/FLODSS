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
import { ExportCenterCard } from '../components/ExportCenterCard';
import { AlgorithmRunnerCard } from '../components/AlgorithmRunnerCard';
import { LayoutEvaluationCard } from '../components/LayoutEvaluationCard';
import { ProblemDefinitionCard } from '../components/ProblemDefinitionCard';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { LoginModal } from '../components/LoginModal';
import { InvitationAcceptModal } from '../components/InvitationAcceptModal';
import { UserManagementModal } from '../components/UserManagementModal';
import { NewProjectWizardModal } from '../components/NewProjectWizardModal';
import { ProjectManagerCard } from '../components/ProjectManagerCard';
import { CockpitOverview, type QuickSolverId } from '../components/cockpit/CockpitOverview';
import { useCockpitScenarios } from '../components/cockpit/liveScenarios';
import { CockpitSidebar } from '../components/cockpit/CockpitSidebar';

import {
  fetchExampleProblems,
  fetchExampleProblem,
  fetchExampleLayouts,
  fetchExampleLayout,
  evaluateLayout,
  validateLayout,
  solveGeneticAlgorithm,
  solveFeasibleGenerator,
  solveCRAFT,
  solveCORELAP,
  solveALDEP,
} from '../services/api';

import {
  FacilityLayoutProblem,
  ContinuousLayout,
  EvaluationReport,
  LayoutValidationResult,
  ProblemSummary,
} from '../types/api';

type TabId =
  | 'cockpit'
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
  const [activeTab, setActiveTab] = useState<TabId>('cockpit');
  const [classicMode, setClassicMode] = useState<boolean>(false);
  const [viewMode, setViewMode] = useState<'workspace' | 'all'>('workspace');
  const [quickSolving, setQuickSolving] = useState<boolean>(false);
  const [quickStatus, setQuickStatus] = useState<string | null>(null);

  // Shared Core State
  const [availableProblems, setAvailableProblems] = useState<ProblemSummary[]>([]);
  const [customProblems, setCustomProblems] = useState<Record<string, FacilityLayoutProblem>>(() => {
    try {
      const raw = typeof window !== 'undefined' ? localStorage.getItem('flodss_custom_projects_v1') : null;
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === 'object' ? parsed : {};
    } catch {
      return {};
    }
  });
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
  const cockpitScenarios = useCockpitScenarios(problem, layout, evaluation, executionInfo?.algorithm, validation);

  const problemVersionRef = React.useRef<number>(0);

  const { user, isLoading: authLoading } = useAuth();
  const { t } = useLanguage();
  const [showLoginModal, setShowLoginModal] = useState<boolean>(false);
  const [showInviteModal, setShowInviteModal] = useState<boolean>(false);
  const [showUserMgmtModal, setShowUserMgmtModal] = useState<boolean>(false);
  const [showNewProjectModal, setShowNewProjectModal] = useState<boolean>(false);

  useEffect(() => {
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem('flodss_custom_projects_v1', JSON.stringify(customProblems));
      }
    } catch (err) {
      console.warn('Failed to persist custom projects:', err);
    }
  }, [customProblems]);

  const combinedProblems: ProblemSummary[] = React.useMemo(() => {
    const customSummaries: ProblemSummary[] = Object.values(customProblems).map((cp) => {
      const facArea = (cp.facility?.width || 0) * (cp.facility?.height || 0);
      const totalReq = cp.departments.reduce((s, d) => s + (d.required_area || 0), 0);
      return {
        id: cp.id,
        name: `${t('[Özel]', '[Custom]')} ${cp.name}`,
        facility_width: cp.facility?.width || 0,
        facility_height: cp.facility?.height || 0,
        facility_area: facArea,
        department_count: cp.departments.length,
        total_required_area: totalReq,
        area_utilization: facArea > 0 ? totalReq / facArea : 0,
        flow_count: cp.flows?.length || 0,
        relationship_count: cp.relationships?.length || 0,
        constraint_count: cp.constraints?.length || 0,
      };
    });
    return [...customSummaries, ...availableProblems];
  }, [customProblems, availableProblems, t]);

  // Initial Load: Problem catalog & default Industrial 10 benchmark when authenticated
  useEffect(() => {
    if (!user) {
      problemVersionRef.current += 1;
      setAvailableProblems([]);
      setProblem(null);
      setLayout(null);
      setValidation(null);
      setEvaluation(null);
      return;
    }
    setShowLoginModal(false);

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
            const targetLayout = exampleLayouts.find((l) => l.problem_id === targetId);
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

  // Handle benchmark or custom project loading
  const handleLoadExample = async (problemId: string) => {
    problemVersionRef.current += 1;
    const currentVersion = problemVersionRef.current;
    setLayout(null);
    setValidation(null);
    setEvaluation(null);
    setExecutionInfo(null);
    setQuickStatus(null);
    const custom = customProblems[problemId];
    if (custom) {
      setProblem(custom);
      return;
    }
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
      alert(t(`'${problemId}' kıyaslama problemi yüklenemedi: ${err?.message}`, `Failed to load benchmark problem '${problemId}': ${err?.message}`));
    }
  };

  const handleUpdateProblem = (updatedProblem: FacilityLayoutProblem) => {
    setProblem(updatedProblem);
    setCustomProblems((prev) => (
      prev[updatedProblem.id]
        ? { ...prev, [updatedProblem.id]: updatedProblem }
        : prev
    ));
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
    metadata?: Record<string, any> | null,
    problemOverride?: FacilityLayoutProblem
  ) => {
    const targetProblem = problemOverride ?? problem;
    setLayout(newLayout);
    setEvaluation(null);
    setValidation(null);
    if (newValidation) {
      setValidation(newValidation);
    } else if (targetProblem) {
      validateLayout(targetProblem.id, newLayout, targetProblem).then(setValidation).catch(() => {});
    }
    if (newEvaluation) {
      setEvaluation(newEvaluation);
    } else if (targetProblem) {
      evaluateLayout(targetProblem.id, newLayout, undefined, targetProblem).then(setEvaluation).catch(() => {});
    }
    if (metadata) {
      setExecutionInfo({
        algorithm: metadata.algorithm || t('Özel Çözücü', 'Custom Solver'),
        seed: metadata.seed,
        durationMs: metadata.duration_ms,
        config: metadata,
      });
    }
  };

  const handleImportLayout = async (importedLayout: ContinuousLayout) => {
    setLayout(importedLayout);
    setEvaluation(null);
    setValidation(null);
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

  const handleQuickSolve = async (algo: QuickSolverId, problemOverride?: FacilityLayoutProblem) => {
    const targetProblem = problemOverride ?? problem;
    if (!targetProblem || quickSolving) return;
    setQuickSolving(true);
    setQuickStatus(t('Çözücü çalışıyor...', 'Running solver...'));
    const t0 = performance.now();
    try {
      if (algo === 'ga') {
        const res = await solveGeneticAlgorithm({
          problem_id: targetProblem.id,
          problem: targetProblem,
          config: { population_size: 30, generations: 25, random_seed: 42, max_runtime_seconds: 15.0 },
        });
        const t1 = performance.now();
        if (res.continuous_layout) {
          handleSolutionGenerated(res.continuous_layout, res.validation, res.evaluation, {
            algorithm: 'Genetic Algorithm v1',
            seed: 42,
            duration_ms: t1 - t0,
          }, targetProblem);
          setQuickStatus(
            res.validation?.is_valid
              ? t(`GA tamamlandı (${Math.round(t1 - t0)} ms)`, `GA finished (${Math.round(t1 - t0)} ms)`)
              : t('GA tamamlandı (uygunluk sınırı aşıldı)', 'GA finished (infeasible)')
          );
        } else {
          setQuickStatus(t('GA uygun yerleşim üretemedi', 'GA could not find a layout'));
        }
      } else if (algo === 'feasible_generator') {
        const res = await solveFeasibleGenerator({
          problem_id: targetProblem.id,
          problem: targetProblem,
          config: { random_seed: 42, max_runtime_seconds: 10.0 },
        });
        const t1 = performance.now();
        const layoutObj = res.result?.layout || res.continuous_layout;
        if (layoutObj) {
          handleSolutionGenerated(layoutObj, res.validation, res.evaluation, {
            algorithm: 'Feasible Rectangular Generator (Guillotine)',
            seed: 42,
            duration_ms: t1 - t0,
          }, targetProblem);
          setQuickStatus(
            res.result?.feasible
              ? t(`Uygun yerleşim üretildi (${Math.round(t1 - t0)} ms)`, `Feasible layout generated (${Math.round(t1 - t0)} ms)`)
              : t('Kısmi sonuç (uygunluk doğrulanmadı)', 'Partial result (infeasible)')
          );
        } else {
          setQuickStatus(t('Uygun yerleşim üretilemedi', 'Could not generate feasible layout'));
        }
      } else if (algo === 'craft') {
        const matchingLayout = !problemOverride && layout && (!layout.problem_id || layout.problem_id === targetProblem.id)
          ? layout
          : null;
        const res = await solveCRAFT({
          problem_id: targetProblem.id,
          problem: targetProblem,
          initial_layout: matchingLayout
            ? { placements: matchingLayout.placements, facility_width: matchingLayout.facility_width, facility_height: matchingLayout.facility_height }
            : undefined,
          config: { max_iterations: 25 },
        });
        const t1 = performance.now();
        handleSolutionGenerated(res.continuous_layout, null, res.final_evaluation, {
          algorithm: 'CRAFT',
          duration_ms: t1 - t0,
        }, targetProblem);
        setQuickStatus(t(`CRAFT tamamlandı (${Math.round(t1 - t0)} ms)`, `CRAFT finished (${Math.round(t1 - t0)} ms)`));
      } else if (algo === 'corelap') {
        const res = await solveCORELAP({ problem_id: targetProblem.id, problem: targetProblem });
        const t1 = performance.now();
        handleSolutionGenerated(res.continuous_layout, res.validation, res.evaluation, {
          algorithm: 'CORELAP',
          duration_ms: t1 - t0,
        }, targetProblem);
        setQuickStatus(
          res.validation?.is_valid
            ? t(`CORELAP tamamlandı (${Math.round(t1 - t0)} ms)`, `CORELAP finished (${Math.round(t1 - t0)} ms)`)
            : t('CORELAP tamamlandı (çakışma uyarısı)', 'CORELAP finished (infeasible)')
        );
      } else if (algo === 'aldep') {
        const res = await solveALDEP({ problem_id: targetProblem.id, problem: targetProblem });
        const t1 = performance.now();
        handleSolutionGenerated(res.continuous_layout, res.validation, res.evaluation, {
          algorithm: 'ALDEP',
          duration_ms: t1 - t0,
        }, targetProblem);
        setQuickStatus(
          res.validation?.is_valid
            ? t(`ALDEP tamamlandı (${Math.round(t1 - t0)} ms)`, `ALDEP finished (${Math.round(t1 - t0)} ms)`)
            : t('ALDEP tamamlandı (uygunluk uyarısı)', 'ALDEP finished (infeasible)')
        );
      }
    } catch (err: any) {
      setQuickStatus(err?.message || t('Çözücü çalıştırılamadı', 'Solver execution failed'));
    } finally {
      setQuickSolving(false);
    }
  };

  const handleCreateCustomProject = async (newProblem: FacilityLayoutProblem, autoOptimize: boolean) => {
    problemVersionRef.current += 1;
    setCustomProblems((prev) => ({ ...prev, [newProblem.id]: newProblem }));
    setProblem(newProblem);
    setLayout(null);
    setValidation(null);
    setEvaluation(null);
    setExecutionInfo(null);
    setSelectedDeptId(null);
    setActiveTab('cockpit');
    setViewMode('workspace');
    setQuickStatus(t('Yeni özel proje oluşturuldu', 'Custom project created'));
    if (autoOptimize) {
      await handleQuickSolve('ga', newProblem);
    }
  };

  const handleCreateSampleLayout = async () => {
    if (!problem || quickSolving) return;
    try {
      const exampleLayouts = await fetchExampleLayouts();
      const matching = exampleLayouts.find((l) => l.problem_id === problem.id);
      if (matching) {
        const loadedLayout = await fetchExampleLayout(matching.id);
        handleSolutionGenerated(loadedLayout, null, null, { algorithm: t('Örnek Başlangıç Yerleşimi', 'Sample Reference Layout') });
        setQuickStatus(t('Örnek yerleşim yüklendi', 'Sample layout loaded'));
        return;
      }
    } catch (_) {}
    await handleQuickSolve('ga');
  };

  const activeScenario = cockpitScenarios.scenarios.find((s) => s.id === cockpitScenarios.selected) ?? null;
  const activeEditorLayout = activeScenario?.layout ?? layout;
  const activePlanLabel = !activeEditorLayout
    ? null
    : activeScenario?.name?.startsWith('Solver Layout · ')
      ? activeScenario.name.slice('Solver Layout · '.length).trim()
      : activeScenario?.name === 'Baseline Layout'
        ? t('İlk yerleşim', 'Baseline layout')
        : activeScenario?.id === 0
          ? t('İlk yerleşim', 'Baseline layout')
          : activeScenario && activeScenario.name.startsWith('What-If')
            ? t('Senaryo denemesi', 'What-If scenario')
            : activeScenario && activeScenario.id > 0
              ? t('Optimize edilmiş', 'Optimized')
              : t('Aktif yerleşim', 'Active layout');

  const handleEditScenarioPlan = (scenarioId: number) => {
    cockpitScenarios.select(scenarioId);
    setActiveTab('layout');
    setViewMode('workspace');
    if (typeof window !== 'undefined') {
      window.requestAnimationFrame(() => {
        document.querySelector('.cockpit-workbench')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
  };

  const tabs: TabItem[] = [
    { id: 'problem', label: t('1. Problem Tanımı', '1. Problem Editor'), icon: <Sliders size={16} /> },
    { id: 'matrices', label: t('2. Akış ve REL Matrisleri', '2. Flow & REL'), icon: <Grid size={16} /> },
    { id: 'constraints', label: t('3. Kısıtlar', '3. Constraints'), icon: <ShieldAlert size={16} /> },
    { id: 'solvers', label: t('4. Optimizasyon', '4. Optimization'), icon: <Play size={16} />, badge: t('6 Çözücü', '6 Solvers') },
    { id: 'layout', label: t('5. Yerleşimi Düzenle', '5. Edit Layout'), icon: <Maximize2 size={16} />, badge: layout ? t('Aktif', 'Active') : undefined },
    { id: 'pareto', label: t('6. Pareto ve Ödünleşimler', '6. Pareto & Trade-offs'), icon: <TrendingUp size={16} /> },
    { id: 'decision', label: t('7. Strateji ve Kısıt Analizi', '7. Strategy & Constraints'), icon: <Sparkles size={16} /> },
    { id: 'export', label: t('8. Dışa Aktarım', '8. Export Center'), icon: <Package size={16} />, badge: 'v1.0' },
    { id: 'overview', label: t('Sistem Özeti', 'System Overview'), icon: <LayoutDashboard size={16} /> },
  ];

  const activeTabInfo = tabs.find((tab) => tab.id === activeTab);

  const renderWorkbenchContent = (tab: TabId) => {
    if (tab === 'problem') {
      return (
        <ProblemEditorCard
          problem={problem}
          onUpdateProblem={handleUpdateProblem}
          onLoadExample={handleLoadExample}
          availableExamples={combinedProblems}
        />
      );
    }
    if (tab === 'matrices') {
      return (
        <MatrixEditorCard
          problem={problem}
          onUpdateProblem={handleUpdateProblem}
        />
      );
    }
    if (tab === 'constraints') {
      return (
        <ConstraintEditorCard
          problem={problem}
          onUpdateProblem={handleUpdateProblem}
        />
      );
    }
    if (tab === 'solvers') {
      return (
        <OptimizationWorkspaceCard
          problem={problem}
          currentLayout={layout}
          onSolutionGenerated={handleSolutionGenerated}
          onNavigateToViewer={() => setActiveTab('layout')}
          onPreviewOnCockpit={!classicMode ? () => {
            if (typeof document !== 'undefined') {
              document.querySelector('.live-factory-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          } : undefined}
          onNavigateToPareto={() => setActiveTab('pareto')}
        />
      );
    }
    if (tab === 'layout') {
      return (
        <div style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          borderRadius: '12px',
          padding: '1.5rem',
          marginBottom: '2rem',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', flexWrap: 'wrap' }}>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
                  {t('Etkileşimli 2D Tesis Yerleşimi Görünümü', 'Interactive 2D Facility Layout Viewer')}
                </h2>
                {activePlanLabel && (
                  <span className="editing-plan-pill">
                    {t('Düzenlenen plan', 'Editing plan')} · {activePlanLabel}
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
                {t(
                  'Sürekli 1:1 koordinat düzlemi • Gerçek zamanlı yakınlaştırma ve kaydırma • Çakışma ve sabit konum denetimi',
                  'Continuous 1:1 solver coordinates • Real-time zoom & pan • Overlap & fixed position detection'
                )}
              </p>
            </div>
            {activeEditorLayout && (
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
                  {t('Çözümü Dışa Aktar', 'Export Solution')}
                </button>
              </div>
            )}
          </div>

          <DecisionGuidanceBox mode="layout" defaultOpen={false} />

          <LayoutCanvas
            layout={activeEditorLayout}
            problem={problem}
            validation={validation}
            selectedDeptId={selectedDeptId}
            onSelectDept={setSelectedDeptId}
          />
        </div>
      );
    }
    if (tab === 'pareto') {
      return (
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
      );
    }
    if (tab === 'decision') {
      return (
        <div>
          <AdaptiveStrategyCard
            problem={problem}
            currentLayout={activeEditorLayout}
            evaluation={evaluation}
          />
        </div>
      );
    }
    if (tab === 'export') {
      return (
        <div>
          {!classicMode && user && (
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
                handleSolutionGenerated(restoredLayout);
                setActiveTab('cockpit');
              }}
            />
          )}
          <ExportCenterCard
            problem={problem}
            layout={layout}
            evaluation={evaluation}
            validation={validation}
            executionInfo={executionInfo}
            onImportLayout={handleImportLayout}
          />
        </div>
      );
    }
    if (tab === 'overview') {
      return (
        <div>
          {!classicMode && user && (
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
                handleSolutionGenerated(restoredLayout);
                setActiveTab('cockpit');
              }}
            />
          )}
          <div style={{ marginBottom: '2rem' }}>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.025em', marginBottom: '0.5rem' }}>
              {t(
                'Tesis Yerleşimi Optimizasyonu ve Karar Destek Sistemi (FLODSS)',
                'Facility Layout Optimization & Decision Support System (FLODSS)'
              )}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: '850px', lineHeight: 1.6 }}>
              {t(
                'Modüler tesis yerleşimi üretimi (FLP), çok ölçütlü algoritmik değerlendirme (MHC, TCR, Komşuluk, Ölü Alan) ve açıklanabilir karar destek için geliştirilmiş ileri seviye Yöneylem Araştırması ve Endüstri Mühendisliği platformu.',
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
      );
    }
    return null;
  };

  return (
    <div className={`industrial-app ${!classicMode ? 'is-cockpit' : ''}`} style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', backgroundColor: 'var(--bg-primary)' }}>
      <CockpitSidebar
        active={activeTab}
        onNavigate={(id) => {
          const next = id as TabId;
          setActiveTab(next);
          if (next === 'cockpit') setClassicMode(false);
          setViewMode('workspace');
        }}
        onNewProject={() => setShowNewProjectModal(true)}
        onLogin={() => setShowLoginModal(true)}
        online={!!status && !healthError}
      />
      <div className="engineering-header">
      {/* Top Header with Release Candidate and Local-First Badges */}
      <Header
        status={status ? status.status : null}
        loading={healthLoading}
        error={healthError}
        onOpenUserManagement={() => setShowUserMgmtModal(true)}
        onOpenLogin={() => setShowLoginModal(true)}
      />
      </div>

      {/* Controlled Research Access Modals */}
      {(!user && !authLoading && !showInviteModal && classicMode) || (showLoginModal && !showInviteModal) ? (
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

      <NewProjectWizardModal
        isOpen={showNewProjectModal}
        onClose={() => setShowNewProjectModal(false)}
        onCreateProject={handleCreateCustomProject}
      />

      {/* Main Workspace */}
      <main className="industrial-main" style={{
        maxWidth: '1440px',
        width: '100%',
        margin: '0 auto',
        padding: '1.5rem 1.5rem 3rem 1.5rem',
        flex: 1,
      }}>
        {!classicMode && (
          <CockpitOverview
            problem={problem}
            layout={layout}
            evaluation={evaluation}
            validation={validation}
            liveScenarios={cockpitScenarios}
            availableProblems={combinedProblems}
            onLoadExample={handleLoadExample}
            onQuickSolve={handleQuickSolve}
            onCreateSampleLayout={handleCreateSampleLayout}
            onOpenNewProject={() => setShowNewProjectModal(true)}
            onEditPlan={handleEditScenarioPlan}
            quickSolving={quickSolving}
            quickStatus={quickStatus}
            activePanel={activeTab}
            onSelectPanel={(panelId) => setActiveTab(panelId as TabId)}
            workbench={activeTab !== 'cockpit' ? renderWorkbenchContent(activeTab) : undefined}
            workbenchTitle={activeTabInfo?.label}
            onOpenWorkspace={() => {
              setClassicMode(true);
              if (activeTab === 'cockpit') setActiveTab('layout');
            }}
          />
        )}
        <div style={{ display: !classicMode ? 'none' : undefined }}>
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
              handleSolutionGenerated(restoredLayout);
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
                  : t('Sekmeli Görünüm', 'Tabbed Workspace')}
              </span>
            </button>
          </div>
        </div>

        {/* WORKSPACE VIEW: Single Focused Tab */}
        {viewMode === 'workspace' && classicMode && (
          <div>
            {renderWorkbenchContent(activeTab)}
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
              availableExamples={combinedProblems}
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
        </div>
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
          <span>{t('Özel Araştırma ve Tez Pilot Sürümü', 'Confidential Private Research Release Candidate')}</span>
          <span>&bull;</span>
          <span style={{ color: '#34d399' }}>{t('Yerel Öncelikli Çalışma', 'Local-First Execution')}</span>
        </div>
        <div>
          Python 3.12+ (FastAPI / Pydantic / NumPy / SciPy) &bull; React 18 / TypeScript / Vite
        </div>
      </footer>
    </div>
  );
};
