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

  const { user, isLoading: authLoading } = useAuth();
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
          const prob = await fetchExampleProblem(targetId);
          setProblem(prob);

          // Try to load initial reference layout
          try {
            const exampleLayouts = await fetchExampleLayouts();
            const targetLayout = exampleLayouts.find((l) => l.problem_id === targetId) || exampleLayouts[0];
            if (targetLayout) {
              const loadedLayout = await fetchExampleLayout(targetLayout.id);
              setLayout(loadedLayout);

              // Validate & evaluate
              try {
                const valResult = await validateLayout(targetId, loadedLayout);
                setValidation(valResult);
              } catch (_) {}

              try {
                const evalReport = await evaluateLayout(targetId, loadedLayout);
                setEvaluation(evalReport);
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
    try {
      const prob = await fetchExampleProblem(problemId);
      setProblem(prob);

      // Attempt to find matching layout
      try {
        const exampleLayouts = await fetchExampleLayouts();
        const matching = exampleLayouts.find((l) => l.problem_id === problemId);
        if (matching) {
          const loadedLayout = await fetchExampleLayout(matching.id);
          setLayout(loadedLayout);
          const valResult = await validateLayout(problemId, loadedLayout);
          setValidation(valResult);
          const evalReport = await evaluateLayout(problemId, loadedLayout);
          setEvaluation(evalReport);
        } else {
          setLayout(null);
          setValidation(null);
          setEvaluation(null);
        }
      } catch (_) {}
    } catch (err: any) {
      alert(`Failed to load benchmark problem '${problemId}': ${err?.message}`);
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
    if (newValidation) setValidation(newValidation);
    if (newEvaluation) setEvaluation(newEvaluation);
    if (metadata) {
      setExecutionInfo({
        algorithm: metadata.algorithm || 'Custom Solver',
        seed: metadata.seed,
        durationMs: metadata.duration_ms,
        config: metadata,
      });
    }
  };

  const tabs: TabItem[] = [
    { id: 'problem', label: '1. Problem Editor', icon: <Sliders size={16} /> },
    { id: 'matrices', label: '2. Flow & REL', icon: <Grid size={16} /> },
    { id: 'constraints', label: '3. Constraints', icon: <ShieldAlert size={16} /> },
    { id: 'solvers', label: '4. Optimization', icon: <Play size={16} />, badge: '6 Solvers' },
    { id: 'layout', label: '5. 2D Layout Viewer', icon: <Maximize2 size={16} />, badge: layout ? 'Active' : undefined },
    { id: 'pareto', label: '6. Pareto & Trade-offs', icon: <TrendingUp size={16} /> },
    { id: 'decision', label: '7. AI Decision Support', icon: <Sparkles size={16} /> },
    { id: 'export', label: '8. Export Center', icon: <Package size={16} />, badge: 'v1.0' },
    { id: 'overview', label: 'System Overview', icon: <LayoutDashboard size={16} /> },
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
              <span>{viewMode === 'workspace' ? 'Show All Modules' : 'Tabbed Workspace'}</span>
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
                  onUpdateProblem={setProblem}
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
                  onUpdateProblem={setProblem}
                />
              </div>
            )}

            {/* Tab 3: Spatial Constraints */}
            {activeTab === 'constraints' && (
              <div>
                <ConstraintEditorCard
                  problem={problem}
                  onUpdateProblem={setProblem}
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
                      Interactive 2D Facility Layout Viewer
                    </h2>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
                      Continuous 1:1 solver coordinates &bull; Real-time zoom & pan &bull; Overlap & fixed position detection
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
                        Export Solution
                      </button>
                    </div>
                  )}
                </div>

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
                <ParetoAnalysisCard />
                <div style={{ marginTop: '2rem' }}>
                  <AlgorithmComparisonCard />
                </div>
              </div>
            )}

            {/* Tab 7: AI Decision Explanation */}
            {activeTab === 'decision' && (
              <div>
                <AIExplanationCard />
                <div style={{ marginTop: '2rem' }}>
                  <AdaptiveStrategyCard />
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
                  executionInfo={executionInfo}
                />
              </div>
            )}

            {/* Tab 9: System Overview */}
            {activeTab === 'overview' && (
              <div>
                <div style={{ marginBottom: '2rem' }}>
                  <h1 style={{ fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.025em', marginBottom: '0.5rem' }}>
                    Facility Layout Optimization & Decision Support System (FLODSS)
                  </h1>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: '850px', lineHeight: 1.6 }}>
                    An advanced Operations Research and Industrial Engineering platform for modular facility layout generation,
                    multi-criteria algorithmic evaluation, and explainable decision support.
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
                FLODSS Complete Architecture Overview
              </h1>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', maxWidth: '850px', lineHeight: 1.6 }}>
                Full system diagnostic view displaying all integrated algorithmic and analysis modules.
              </p>
            </div>

            <RoadmapStepper />
            <ProblemEditorCard
              problem={problem}
              onUpdateProblem={setProblem}
              onLoadExample={handleLoadExample}
              availableExamples={availableProblems}
            />
            <MatrixEditorCard problem={problem} onUpdateProblem={setProblem} />
            <ConstraintEditorCard problem={problem} onUpdateProblem={setProblem} />
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
              executionInfo={executionInfo}
            />
            <ParetoAnalysisCard />
            <AlgorithmComparisonCard />
            <AdaptiveStrategyCard />
            <AIExplanationCard />
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
          <span>Confidential Private Research Release Candidate</span>
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
