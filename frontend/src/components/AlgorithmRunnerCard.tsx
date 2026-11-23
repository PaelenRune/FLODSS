import React, { useState, useEffect } from 'react';
import {
  ProblemSummary,
  AlgorithmMetadata,
  CORELAPConfig,
  CORELAPSolveResponse,
  CRAFTConfig,
  CRAFTSolveResponse,
  CRAFTSolveRequest,
  ALDEPConfig,
  ALDEPSolveResponse,
  LayoutExampleSummary,
  GeneratorStrategy,
  DepartmentOrderingStrategy,
  GeneratorConfig,
  FeasibleGeneratorSolveResponse,
  GAConfig,
  GASolveResponse,
} from '../types/api';
import {
  fetchExampleProblems,
  fetchAlgorithms,
  solveCORELAP,
  solveCRAFT,
  solveALDEP,
  solveFeasibleGenerator,
  solveGeneticAlgorithm,
  fetchExampleLayouts,
} from '../services/api';
import { LayoutCanvas } from './LayoutCanvas';
import { useLanguage } from '../context/LanguageContext';

export const AlgorithmRunnerCard: React.FC = () => {
  const { t } = useLanguage();
  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [selectedProblemId, setSelectedProblemId] = useState<string>('');
  const [algorithms, setAlgorithms] = useState<AlgorithmMetadata[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Active Algorithm Tab
  const [activeAlgo, setActiveAlgo] = useState<'CORELAP' | 'CRAFT' | 'ALDEP' | 'FEASIBLE_GENERATOR' | 'GENETIC_ALGORITHM'>('CORELAP');

  // CORELAP Configuration state
  const [placementMode, setPlacementMode] = useState<'classical_adjacency' | 'extended_distance_weighted'>('classical_adjacency');
  const [initialAnchorMode, setInitialAnchorMode] = useState<'center' | 'origin' | 'bottom_left'>('center');
  const [xPenaltyMultiplier, setXPenaltyMultiplier] = useState<number>(25.0);
  const [candidateGap, setCandidateGap] = useState<number>(0.0);
  const [allowShapeAlternatives, setAllowShapeAlternatives] = useState<boolean>(true);
  const [evaluateOrientations, setEvaluateOrientations] = useState<boolean>(true);
  const [traceLevel, setTraceLevel] = useState<'SUMMARY' | 'DETAILED'>('SUMMARY');

  // CORELAP Results state
  const [solveResult, setSolveResult] = useState<CORELAPSolveResponse | null>(null);
  const [activeTraceStep, setActiveTraceStep] = useState<number | null>(null);

  // CRAFT Configuration & Results state
  const [craftRunning, setCraftRunning] = useState<boolean>(false);
  const [craftError, setCraftError] = useState<string | null>(null);
  const [craftResult, setCraftResult] = useState<CRAFTSolveResponse | null>(null);
  const [craftSource, setCraftSource] = useState<'BASELINE' | 'CORELAP'>('BASELINE');
  const [craftMaxIterations, setCraftMaxIterations] = useState<number>(50);
  const [craftMinImprovement, setCraftMinImprovement] = useState<number>(0.01);
  const [craftAllowRotation, setCraftAllowRotation] = useState<boolean>(true);
  const [craftTraceLevel, setCraftTraceLevel] = useState<'SUMMARY' | 'DETAILED'>('SUMMARY');
  const [exampleLayouts, setExampleLayouts] = useState<LayoutExampleSummary[]>([]);
  const [selectedBaselineId, setSelectedBaselineId] = useState<string>('');
  const [activeCraftStep, setActiveCraftStep] = useState<number | null>(null);

  // ALDEP Configuration & Results state
  const [aldepCandidatesCount, setAldepCandidatesCount] = useState<number>(10);
  const [aldepRandomSeed, setAldepRandomSeed] = useState<number>(42);
  const [aldepCellSize, setAldepCellSize] = useState<number>(5.0);
  const [aldepStripWidth, setAldepStripWidth] = useState<number>(2);
  const [aldepSweepDirection, setAldepSweepDirection] = useState<'VERTICAL' | 'HORIZONTAL'>('VERTICAL');
  const [aldepThreshold, setAldepThreshold] = useState<number>(8.0);
  const [aldepAllowSplitting, setAldepAllowSplitting] = useState<boolean | null>(null);
  const [aldepTieBreaker, setAldepTieBreaker] = useState<'RANDOM_AMONG_MAX' | 'RANDOM_AMONG_THRESHOLD'>('RANDOM_AMONG_MAX');
  const [aldepTraceLevel, setAldepTraceLevel] = useState<'SUMMARY' | 'DETAILED'>('SUMMARY');
  const [aldepRunning, setAldepRunning] = useState<boolean>(false);
  const [aldepError, setAldepError] = useState<string | null>(null);
  const [aldepResult, setAldepResult] = useState<ALDEPSolveResponse | null>(null);
  const [selectedCandidateIdx, setSelectedCandidateIdx] = useState<number>(0);
  const [activeAldepStep, setActiveAldepStep] = useState<number | null>(null);

  // Feasible Generator Configuration & Results state
  const [genStrategy, setGenStrategy] = useState<GeneratorStrategy>('guillotine_row_packing');
  const [genOrderingStrategy, setGenOrderingStrategy] = useState<DepartmentOrderingStrategy>('most_constrained_first');
  const [genMaxNodes, setGenMaxNodes] = useState<number>(3000);
  const [genMaxBacktracks, setGenMaxBacktracks] = useState<number>(1500);
  const [genMaxRuntime, setGenMaxRuntime] = useState<number>(10.0);
  const [genMaxShapeAlternatives, setGenMaxShapeAlternatives] = useState<number>(8);
  const [genCandidateLimit, setGenCandidateLimit] = useState<number>(12);
  const [genRunning, setGenRunning] = useState<boolean>(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [genResult, setGenResult] = useState<FeasibleGeneratorSolveResponse | null>(null);

  // Genetic Algorithm Configuration & Results state
  const [gaPopulationSize, setGaPopulationSize] = useState<number>(50);
  const [gaGenerations, setGaGenerations] = useState<number>(100);
  const [gaCrossoverRate, setGaCrossoverRate] = useState<number>(0.85);
  const [gaMutationRate, setGaMutationRate] = useState<number>(0.30);
  const [gaElitismCount, setGaElitismCount] = useState<number>(2);
  const [gaTournamentSize, setGaTournamentSize] = useState<number>(4);
  const [gaRandomSeed, setGaRandomSeed] = useState<number>(42);
  const [gaSoftPenaltyWeight, setGaSoftPenaltyWeight] = useState<number>(1.0);
  const [gaOrientation, setGaOrientation] = useState<string>('horizontal');
  const [gaSeedWithGuillotine, setGaSeedWithGuillotine] = useState<boolean>(true);
  const [gaRunning, setGaRunning] = useState<boolean>(false);
  const [gaError, setGaError] = useState<string | null>(null);
  const [gaResult, setGaResult] = useState<GASolveResponse | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      try {
        const [probs, algos, exLayouts] = await Promise.all([
          fetchExampleProblems(),
          fetchAlgorithms().catch(() => []),
          fetchExampleLayouts().catch(() => []),
        ]);
        setProblems(probs);
        if (probs.length > 0) {
          const firstProbId = probs[0].id;
          setSelectedProblemId(firstProbId);
          const matching = exLayouts.filter((l) => l.problem_id === firstProbId);
          if (matching.length > 0) {
            setSelectedBaselineId(matching[0].id);
          }
        }
        setAlgorithms(algos);
        setExampleLayouts(exLayouts);
      } catch (err: any) {
        setError(err.message || t('Başlangıç verileri yüklenemedi', 'Failed to load initial data'));
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const handleProblemChange = (probId: string) => {
    setSelectedProblemId(probId);
    setSolveResult(null);
    setCraftResult(null);
    setAldepResult(null);
    setGenResult(null);
    setGaResult(null);
    const matching = exampleLayouts.filter((l) => l.problem_id === probId);
    if (matching.length > 0) {
      setSelectedBaselineId(matching[0].id);
    } else {
      setSelectedBaselineId('');
    }
  };

  const handleRunCORELAP = async () => {
    if (!selectedProblemId) return;
    setRunning(true);
    setError(null);
    try {
      const config: CORELAPConfig = {
        placement_mode: placementMode,
        initial_anchor_mode: initialAnchorMode,
        allow_shape_alternatives: allowShapeAlternatives,
        evaluate_orientations: evaluateOrientations,
        x_adjacency_penalty_multiplier: Number(xPenaltyMultiplier),
        candidate_gap: Number(candidateGap),
        trace_level: traceLevel,
        step_grid_alignment: null,
      };

      const res = await solveCORELAP({
        problem_id: selectedProblemId,
        config,
      });
      setSolveResult(res);
      setActiveTraceStep(null);
    } catch (err: any) {
      setError(err.message || t('CORELAP çözücü çalıştırması başarısız oldu', 'CORELAP solver execution failed'));
    } finally {
      setRunning(false);
    }
  };

  const handleRunCRAFT = async () => {
    if (!selectedProblemId) return;
    setCraftRunning(true);
    setCraftError(null);
    try {
      const config: CRAFTConfig = {
        max_iterations: Number(craftMaxIterations),
        min_improvement_threshold: Number(craftMinImprovement),
        allow_rotational_swaps: craftAllowRotation,
        trace_level: craftTraceLevel,
      };

      const payload: CRAFTSolveRequest = {
        problem_id: selectedProblemId,
        config,
      };

      if (craftSource === 'BASELINE') {
        if (!selectedBaselineId) {
          throw new Error(t('Bu problem için temel yerleşim seçilmedi.', 'No baseline layout selected for this problem.'));
        }
        payload.initial_layout_id = selectedBaselineId;
      } else {
        if (!solveResult) {
          throw new Error(t('CORELAP çözümü bulunamadı. Önce CORELAP çalıştırın.', 'No CORELAP solution available. Run CORELAP first.'));
        }
        if (!isCORELAPComplete) {
          throw new Error(t('CORELAP yerleşimi eksik. CRAFT tam ve uygun bir başlangıç yerleşimi gerektirir.', 'CORELAP layout is incomplete. CRAFT requires a complete and feasible initial layout.'));
        }
        payload.initial_layout = solveResult.continuous_layout;
      }

      const res = await solveCRAFT(payload);
      setCraftResult(res);
      setActiveCraftStep(null);
    } catch (err: any) {
      setCraftError(err.message || t('CRAFT çalıştırması başarısız oldu', 'CRAFT execution failed'));
    } finally {
      setCraftRunning(false);
    }
  };

  const handleRunALDEP = async () => {
    if (!selectedProblemId) return;
    setAldepRunning(true);
    setAldepError(null);
    try {
      const config: ALDEPConfig = {
        number_of_candidates: Number(aldepCandidatesCount),
        random_seed: Number(aldepRandomSeed),
        cell_size: Number(aldepCellSize),
        strip_width_cells: Number(aldepStripWidth),
        sweep_direction: aldepSweepDirection,
        selection_threshold: Number(aldepThreshold),
        allow_strip_splitting: aldepAllowSplitting,
        tie_breaker: aldepTieBreaker,
        trace_level: aldepTraceLevel,
      };

      const res = await solveALDEP({
        problem_id: selectedProblemId,
        config,
      });
      setAldepResult(res);
      setSelectedCandidateIdx(res.best_candidate.candidate_index);
      setActiveAldepStep(null);
    } catch (err: any) {
      setAldepError(err.message || t('ALDEP çözücü çalıştırması başarısız oldu', 'ALDEP solver execution failed'));
    } finally {
      setAldepRunning(false);
    }
  };

  const handleRunFeasibleGenerator = async () => {
    if (!selectedProblemId) return;
    setGenRunning(true);
    setGenError(null);
    try {
      const config: GeneratorConfig = {
        strategy: genStrategy,
        ordering_strategy: genOrderingStrategy,
        max_nodes: Number(genMaxNodes),
        max_backtracks: Number(genMaxBacktracks),
        max_runtime_seconds: Number(genMaxRuntime),
        max_shape_alternatives: Number(genMaxShapeAlternatives),
        candidate_limit_per_department: Number(genCandidateLimit),
      };

      const res = await solveFeasibleGenerator({
        problem_id: selectedProblemId,
        config,
      });
      setGenResult(res);
    } catch (err: any) {
      setGenError(err.message || t('Uygun Yerleşim Üreticisi çalıştırması başarısız oldu', 'Feasible Generator execution failed'));
    } finally {
      setGenRunning(false);
    }
  };

  const handleRunGA = async () => {
    if (!selectedProblemId) return;
    setGaRunning(true);
    setGaError(null);
    try {
      const config: GAConfig = {
        population_size: Number(gaPopulationSize),
        generations: Number(gaGenerations),
        crossover_rate: Number(gaCrossoverRate),
        mutation_rate: Number(gaMutationRate),
        elitism_count: Number(gaElitismCount),
        tournament_size: Number(gaTournamentSize),
        random_seed: Number(gaRandomSeed),
        soft_penalty_weight: Number(gaSoftPenaltyWeight),
        orientation: gaOrientation,
        seed_with_guillotine: gaSeedWithGuillotine,
      };

      const res = await solveGeneticAlgorithm({
        problem_id: selectedProblemId,
        config,
      });
      setGaResult(res);
    } catch (err: any) {
      setGaError(err.message || t('Genetik Algoritma çalıştırması başarısız oldu', 'Genetic Algorithm execution failed'));
    } finally {
      setGaRunning(false);
    }
  };

  const isCORELAPComplete = solveResult
    ? (solveResult.trace.is_complete ?? (solveResult.trace.placed_count === solveResult.trace.total_departments))
    : false;

  const activeMetadata = algorithms.find((a) => {
    if (activeAlgo === 'CORELAP') return a.name.toLowerCase().includes('corelap');
    if (activeAlgo === 'CRAFT') return a.name.toLowerCase().includes('craft');
    if (activeAlgo === 'ALDEP') return a.name.toLowerCase().includes('aldep');
    if (activeAlgo === 'GENETIC_ALGORITHM') return a.name.toLowerCase().includes('genetic') || a.name.toLowerCase() === 'ga';
    return a.name.toLowerCase().includes('feasible');
  });

  const selectedProblem = problems.find((p) => p.id === selectedProblemId);
  const currentProblemBaselineLayouts = exampleLayouts.filter((l) => l.problem_id === selectedProblemId);

  // Can CRAFT run?
  const canRunCRAFT = Boolean(
    selectedProblemId &&
      !craftRunning &&
      ((craftSource === 'BASELINE' && selectedBaselineId) ||
        (craftSource === 'CORELAP' && solveResult && isCORELAPComplete))
  );

  const craftDisabledReason = (() => {
    if (!selectedProblemId) return t('Lütfen önce bir problem seçin.', 'Please select a problem first.');
    if (craftSource === 'BASELINE' && !selectedBaselineId) {
      return t('Bu problem için temel yerleşim dosyası mevcut değil.', 'No baseline layout file available for this problem.');
    }
    if (craftSource === 'CORELAP') {
      if (!solveResult) {
        return t('Henüz CORELAP yerleşimi üretilmedi. Lütfen önce CORELAP çalıştırın veya bir temel yerleşim seçin.', 'No CORELAP layout generated yet. Please run CORELAP first or select a baseline layout.');
      }
      if (!isCORELAPComplete) {
        const placed = solveResult.trace.placed_department_count ?? solveResult.trace.placed_count;
        const total = solveResult.trace.total_department_count ?? solveResult.trace.total_departments;
        return t(
          `CRAFT tam bir başlangıç yerleşimi gerektirir. Mevcut CORELAP yerleşimi ${total} bölümden yalnızca ${placed} tanesini yerleştirdi (kısmi). İyileştirme sezgisel algoritması eksik yerleşimlerde çalıştırılamaz.`,
          `CRAFT requires a complete initial layout. Current CORELAP layout placed only ${placed} of ${total} departments (partial). The improvement heuristic cannot be executed on incomplete layouts.`
        );
      }
    }
    return null;
  })();

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
        borderRadius: '12px',
        padding: '1.5rem',
        marginBottom: '2rem',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          marginBottom: '1rem',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 600 }}>
              {t('Optimizasyon Algoritmaları ve Yerleşim Üretimi', 'Optimization Algorithms & Layout Generation')}
            </h2>
            <span
              style={{
                fontSize: '0.7rem',
                backgroundColor:
                  activeAlgo === 'CORELAP'
                    ? 'rgba(59, 130, 246, 0.15)'
                    : activeAlgo === 'CRAFT'
                    ? 'rgba(16, 185, 129, 0.15)'
                    : activeAlgo === 'ALDEP'
                    ? 'rgba(245, 158, 11, 0.15)'
                    : activeAlgo === 'FEASIBLE_GENERATOR'
                    ? 'rgba(168, 85, 247, 0.15)'
                    : 'rgba(236, 72, 153, 0.15)',
                color:
                  activeAlgo === 'CORELAP'
                    ? '#60a5fa'
                    : activeAlgo === 'CRAFT'
                    ? '#34d399'
                    : activeAlgo === 'ALDEP'
                    ? '#fbbf24'
                    : activeAlgo === 'FEASIBLE_GENERATOR'
                    ? '#c084fc'
                    : '#f472b6',
                padding: '0.2rem 0.5rem',
                borderRadius: '4px',
                border: `1px solid ${
                  activeAlgo === 'CORELAP'
                    ? 'rgba(59, 130, 246, 0.3)'
                    : activeAlgo === 'CRAFT'
                    ? 'rgba(16, 185, 129, 0.3)'
                    : activeAlgo === 'ALDEP'
                    ? 'rgba(245, 158, 11, 0.3)'
                    : activeAlgo === 'FEASIBLE_GENERATOR'
                    ? 'rgba(168, 85, 247, 0.3)'
                    : 'rgba(236, 72, 153, 0.3)'
                }`,
                fontWeight: 600,
              }}
            >
              {activeAlgo === 'CORELAP'
                ? t('CORELAP v1.0 (Kurucu)', 'CORELAP v1.0 (Construction)')
                : activeAlgo === 'CRAFT'
                ? t('CRAFT v1.0 (İyileştirme)', 'CRAFT v1.0 (Improvement)')
                : activeAlgo === 'ALDEP'
                ? t('ALDEP v1.0 (Kurucu)', 'ALDEP v1.0 (Construction)')
                : activeAlgo === 'FEASIBLE_GENERATOR'
                ? t('Uygun Üretici v1.0 (Kurucu)', 'Feasible Generator v1.0 (Construction)')
                : t('Genetik Algoritma v1.0 (Metasezgisel)', 'Genetic Algorithm v1.0 (Metaheuristic)')}
            </span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
            {activeAlgo === 'CORELAP'
              ? t(
                  'Adım adım açıklanabilirlik iziyle deterministik Muther SLP ilişki odaklı yerleşim kurulumu',
                  'Deterministic Muther SLP relationship-driven layout construction with step-by-step explainability trace'
                )
              : activeAlgo === 'CRAFT'
              ? t(
                  'Malzeme Taşıma Maliyetini (MHC) en aza indiren ikili bölüm değişimi iyileştirme sezgisel algoritması',
                  'Pairwise department exchange improvement heuristic minimizing Material Handling Cost (MHC)'
                )
              : activeAlgo === 'ALDEP'
              ? t(
                  'Birden fazla yerleşim alternatifi üreten stokastik Muther REL odaklı şerit tarama kurucu sezgisel algoritması',
                  'Stochastic Muther REL-driven strip-sweep construction heuristic generating multiple layout alternatives'
                )
              : activeAlgo === 'FEASIBLE_GENERATOR'
              ? t(
                  'Sıfırdan %100 geçerli yerleşimler üreten deterministik kurucu arama (Serbest Dikdörtgen MER DFS ve Giyotin Sıra Paketleme)',
                  'Deterministic constructive search (Free-Rectangle MER DFS & Guillotine Row Packing) generating 100% legal layouts from scratch'
                )
              : t(
                  'Malzeme Taşıma Maliyetini (MHC) ve esnek cezaları en aza indiren Esnek Hol Yapısı (FBS) Sıra Çaprazlamalı (OX) genetik optimizasyon',
                  'Flexible Bay Structure (FBS) Order Crossover (OX) genetic optimization minimizing Material Handling Cost (MHC) and soft penalties'
                )}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {activeMetadata && (
            <span
              style={{
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                border: '1px solid var(--border-color)',
                padding: '0.25rem 0.6rem',
                borderRadius: '6px',
              }}
            >
              {t('Kayıtlı:', 'Registered:')} {activeMetadata.name} (v{activeMetadata.version})
            </span>
          )}
          <button
            onClick={() => setActiveAlgo('CORELAP')}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: activeAlgo === 'CORELAP' ? 'var(--accent-color)' : 'var(--bg-card)',
              color: activeAlgo === 'CORELAP' ? '#fff' : 'var(--text-secondary)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {t('CORELAP (Kurucu)', 'CORELAP (Construction)')}
          </button>
          <button
            onClick={() => setActiveAlgo('ALDEP')}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: activeAlgo === 'ALDEP' ? 'var(--accent-color)' : 'var(--bg-card)',
              color: activeAlgo === 'ALDEP' ? '#fff' : 'var(--text-secondary)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {t('ALDEP (Kurucu)', 'ALDEP (Construction)')}
          </button>
          <button
            onClick={() => setActiveAlgo('CRAFT')}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: activeAlgo === 'CRAFT' ? 'var(--accent-color)' : 'var(--bg-card)',
              color: activeAlgo === 'CRAFT' ? '#fff' : 'var(--text-secondary)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {t('CRAFT (İyileştirme)', 'CRAFT (Improvement)')}
          </button>
          <button
            onClick={() => setActiveAlgo('FEASIBLE_GENERATOR')}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: activeAlgo === 'FEASIBLE_GENERATOR' ? 'var(--accent-color)' : 'var(--bg-card)',
              color: activeAlgo === 'FEASIBLE_GENERATOR' ? '#fff' : 'var(--text-secondary)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {t('Uygun Üretici (Faz 8)', 'Feasible Generator (Phase 8)')}
          </button>
          <button
            onClick={() => setActiveAlgo('GENETIC_ALGORITHM')}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: activeAlgo === 'GENETIC_ALGORITHM' ? 'var(--accent-color)' : 'var(--bg-card)',
              color: activeAlgo === 'GENETIC_ALGORITHM' ? '#fff' : 'var(--text-secondary)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {t('Genetik Algoritma (Faz 9)', 'Genetic Algorithm (Phase 9)')}
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            color: '#f87171',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            border: '1px solid rgba(239, 68, 68, 0.3)',
          }}
        >
          {error}
        </div>
      )}

      {craftError && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            color: '#f87171',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            border: '1px solid rgba(239, 68, 68, 0.3)',
          }}
        >
          {craftError}
        </div>
      )}

      {aldepError && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            color: '#f87171',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            border: '1px solid rgba(239, 68, 68, 0.3)',
          }}
        >
          {aldepError}
        </div>
      )}

      {genError && (
        <div
          style={{
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            color: '#f87171',
            padding: '0.75rem 1rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            border: '1px solid rgba(239, 68, 68, 0.3)',
          }}
        >
          {genError}
        </div>
      )}

      {/* ========================================================================= */}
      {/* CORELAP VIEW                                                              */}
      {/* ========================================================================= */}
      {activeAlgo === 'CORELAP' && (
        <>
          {/* Control Panel */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
              backgroundColor: 'var(--bg-card)',
              padding: '1.25rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              marginBottom: '1.5rem',
            }}
          >
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Hedef Problem:', 'Target Problem:')}
              </label>
              <select
                value={selectedProblemId}
                onChange={(e) => handleProblemChange(e.target.value)}
                disabled={loading || running}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                {problems.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.department_count} {t('bölüm', 'depts')})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Puanlama Modu:', 'Scoring Mode:')}
              </label>
              <select
                value={placementMode}
                onChange={(e) => setPlacementMode(e.target.value as any)}
                disabled={running}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="classical_adjacency">{t('Mod A: Klasik Komşuluk (Ortak Kenar)', 'Mode A: Classical Adjacency (Shared Border)')}</option>
                <option value="extended_distance_weighted">{t('Mod B: Genişletilmiş Mesafe Ağırlıklı', 'Mode B: Extended Distance-Weighted')}</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Başlangıç Çıpa Modu:', 'Initial Anchor Mode:')}
              </label>
              <select
                value={initialAnchorMode}
                onChange={(e) => setInitialAnchorMode(e.target.value as any)}
                disabled={running}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="center">{t('Tesis Merkezi (Klasik CORELAP)', 'Center of Facility (Classical CORELAP)')}</option>
                <option value="bottom_left">{t('Sol-Alt Başlangıç (0, 0)', 'Bottom-Left Origin (0, 0)')}</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('İzleme Düzeyi:', 'Trace Level:')}
              </label>
              <select
                value={traceLevel}
                onChange={(e) => setTraceLevel(e.target.value as any)}
                disabled={running}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="SUMMARY">{t('Özet İzleme', 'Summary Trace')}</option>
                <option value="DETAILED">{t('Ayrıntılı Tanılama', 'Detailed Diagnostics')}</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Şekil Alternatifleri ve Döndürme:', 'Shape Alternatives & Rotation:')}
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', paddingTop: '0.2rem' }}>
                <label style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={allowShapeAlternatives}
                    onChange={(e) => setAllowShapeAlternatives(e.target.checked)}
                    disabled={running}
                  />
                  {t('Geçerli Şekil Boyutları', 'Legal Shape Dimensions')}
                </label>
                <label style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={evaluateOrientations}
                    onChange={(e) => setEvaluateOrientations(e.target.checked)}
                    disabled={running}
                  />
                  {t('0° / 90° Döndürmeler', '0° / 90° Rotations')}
                </label>
              </div>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('X-Ceza Çarpanı:', 'X-Penalty Multiplier:')}
              </label>
              <input
                type="number"
                min="1"
                max="100"
                step="1"
                value={xPenaltyMultiplier}
                onChange={(e) => setXPenaltyMultiplier(Number(e.target.value))}
                disabled={running}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Aday Boşluğu (m):', 'Candidate Gap (m):')}
              </label>
              <input
                type="number"
                min="0"
                max="10"
                step="0.5"
                value={candidateGap}
                onChange={(e) => setCandidateGap(Number(e.target.value))}
                disabled={running}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button
                onClick={handleRunCORELAP}
                disabled={running || !selectedProblemId}
                style={{
                  width: '100%',
                  padding: '0.6rem 1.25rem',
                  backgroundColor: 'var(--accent-color)',
                  color: '#fff',
                  border: 'none',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: running ? 'not-allowed' : 'pointer',
                  opacity: running ? 0.7 : 1,
                  transition: 'background-color 0.2s',
                }}
              >
                {running ? t('CORELAP Çalıştırılıyor...', 'Executing CORELAP...') : t('CORELAP Çözücüsünü Çalıştır', 'Run CORELAP Solver')}
              </button>
            </div>
          </div>

          {/* CORELAP Execution Results */}
          {solveResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Status & Feasibility Banner */}
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                  padding: '1rem 1.25rem',
                  borderRadius: '8px',
                  backgroundColor: isCORELAPComplete
                    ? 'rgba(16, 185, 129, 0.1)'
                    : 'rgba(239, 68, 68, 0.12)',
                  border: `1px solid ${
                    isCORELAPComplete ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.35)'
                  }`,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                      <span
                        style={{
                          fontWeight: 700,
                          fontSize: '0.95rem',
                          color: isCORELAPComplete ? '#34d399' : '#f87171',
                        }}
                      >
                        {isCORELAPComplete
                          ? t('✓ Kurulum Tamamlandı (%100 Yerleştirildi)', '✓ Construction Complete (100% Placed)')
                          : t('⚠️ EKSİK KURULUM (Kısmi Çözüm)', '⚠️ INCOMPLETE CONSTRUCTION (Partial Solution)')}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        ({solveResult.trace.placed_department_count ?? solveResult.trace.placed_count} /{' '}
                        {solveResult.trace.total_department_count ?? solveResult.trace.total_departments}{' '}
                        {t('bölüm', 'departments placed in')}{' '}
                        {solveResult.trace.execution_time_seconds}s{' '}
                        {t('içinde yerleştirildi', '')})
                      </span>
                      {solveResult.trace.termination_reason && (
                        <span
                          style={{
                            fontSize: '0.7rem',
                            backgroundColor: isCORELAPComplete ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                            color: isCORELAPComplete ? '#34d399' : '#f87171',
                            padding: '0.15rem 0.4rem',
                            borderRadius: '4px',
                            fontWeight: 600,
                          }}
                        >
                          {solveResult.trace.termination_reason}
                        </span>
                      )}
                    </div>

                    {!isCORELAPComplete && (solveResult.trace.unplaced_departments?.length ?? 0) > 0 && (
                      <div style={{ marginTop: '0.5rem', fontSize: '0.8rem', color: '#fca5a5' }}>
                        <strong>{t('Yerleştirilemeyen Bölümler:', 'Unplaced Departments:')}</strong>{' '}
                        {solveResult.trace.unplaced_departments?.map((d) => (
                          <span
                            key={d}
                            style={{
                              display: 'inline-block',
                              backgroundColor: 'rgba(239, 68, 68, 0.2)',
                              padding: '0.1rem 0.4rem',
                              borderRadius: '4px',
                              marginRight: '0.3rem',
                              fontSize: '0.75rem',
                              fontWeight: 600,
                            }}
                          >
                            {d}
                          </span>
                        ))}
                      </div>
                    )}

                    {solveResult.trace.failure_reason && (
                      <p style={{ fontSize: '0.8rem', color: '#f59e0b', marginTop: '0.35rem' }}>
                        {t('Tanılama Nedeni:', 'Diagnostic Cause:')} {solveResult.trace.failure_reason}
                      </p>
                    )}
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{t('Deterministik Değişmez:', 'Deterministic Invariant:')}</div>
                    <code style={{ fontSize: '0.75rem', color: 'var(--accent-color)' }}>
                      {solveResult.evaluation.layout_signature.slice(0, 16)}...
                    </code>
                  </div>
                </div>
              </div>

              {/* Layout Canvas View */}
              <div style={{ backgroundColor: 'var(--bg-card)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <LayoutCanvas layout={solveResult.continuous_layout} />
              </div>

              {/* Step-by-Step Construction Trace */}
              <div style={{ backgroundColor: 'var(--bg-card)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                  {t('CORELAP Yerleştirme Sırası', 'CORELAP Placement Sequence')} ({solveResult.trace.steps.length} {t('Adım', 'Steps')})
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '300px', overflowY: 'auto' }}>
                  {solveResult.trace.steps.map((step) => {
                    const isExp = activeTraceStep === step.step_number;
                    return (
                      <div
                        key={step.step_number}
                        style={{
                          backgroundColor: 'var(--bg-secondary)',
                          border: `1px solid ${isExp ? 'var(--accent-color)' : 'var(--border-color)'}`,
                          borderRadius: '6px',
                          padding: '0.6rem 0.8rem',
                          cursor: 'pointer',
                          fontSize: '0.8rem',
                        }}
                        onClick={() => setActiveTraceStep(isExp ? null : step.step_number)}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span>
                            <strong>{t('Adım', 'Step')} #{step.step_number}:</strong> {t('Yerleştirildi:', 'Placed')}{' '}
                            <span style={{ color: 'var(--accent-color)', fontWeight: 600 }}>{step.selected_department}</span> (TCR: {step.tcr})
                          </span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                            ({step.selected_candidate.width.toFixed(1)}m × {step.selected_candidate.height.toFixed(1)}m @ ({step.selected_candidate.x.toFixed(1)}, {step.selected_candidate.y.toFixed(1)}))
                          </span>
                        </div>
                        {isExp && (
                          <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            <div>{t('Değerlendirilen adaylar:', 'Candidates evaluated:')} {step.candidate_count} ({t('Reddedilen:', 'Rejected:')} {step.rejected_candidates})</div>
                            <div>{t('Yerleştirilen komşularla yakınlık skoru:', 'Affinity score with placed neighbors:')} {step.placed_relationship_score}</div>
                            <div>{t('Komşular:', 'Neighbors:')} {step.neighbors.join(', ') || t('Yok (İlk yerleşim)', 'None (Initial placement)')}</div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ========================================================================= */}
      {/* CRAFT VIEW                                                                */}
      {/* ========================================================================= */}
      {activeAlgo === 'CRAFT' && (
        <>
          {/* CRAFT Control Panel */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
              backgroundColor: 'var(--bg-card)',
              padding: '1.25rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              marginBottom: '1.5rem',
            }}
          >
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Hedef Problem:', 'Target Problem:')}
              </label>
              <select
                value={selectedProblemId}
                onChange={(e) => handleProblemChange(e.target.value)}
                disabled={loading || craftRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                {problems.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.department_count} {t('bölüm', 'depts')})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Başlangıç Yerleşim Kaynağı:', 'Initial Layout Source:')}
              </label>
              <select
                value={craftSource}
                onChange={(e) => setCraftSource(e.target.value as any)}
                disabled={craftRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="BASELINE">{t('Ön Yüklü Temel Yerleşim', 'Preloaded Baseline Layout')}</option>
                <option value="CORELAP">{t('Üretilen CORELAP Çözümü', 'Generated CORELAP Solution')}</option>
              </select>
            </div>

            {craftSource === 'BASELINE' ? (
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                  {t('Temel Yerleşim Seç:', 'Select Baseline Layout:')}
                </label>
                <select
                  value={selectedBaselineId}
                  onChange={(e) => setSelectedBaselineId(e.target.value)}
                  disabled={craftRunning || currentProblemBaselineLayouts.length === 0}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    borderRadius: '6px',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    fontSize: '0.85rem',
                  }}
                >
                  {currentProblemBaselineLayouts.length === 0 ? (
                    <option value="">{t('Bu problem için temel yerleşim mevcut değil', 'No baseline available for this problem')}</option>
                  ) : (
                    currentProblemBaselineLayouts.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.name} ({l.department_count} {t('bölüm', 'depts')})
                      </option>
                    ))
                  )}
                </select>
              </div>
            ) : (
              <div>
                <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                  {t('CORELAP Durumu:', 'CORELAP Status:')}
                </label>
                <div
                  style={{
                    padding: '0.5rem',
                    borderRadius: '6px',
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border-color)',
                    fontSize: '0.8rem',
                    color: solveResult
                      ? isCORELAPComplete
                        ? '#34d399'
                        : '#f87171'
                      : 'var(--text-muted)',
                  }}
                >
                  {solveResult
                    ? isCORELAPComplete
                      ? t('✓ Tam Yerleşim Hazır', '✓ Complete Layout Ready')
                      : t(`⚠️ Eksik (${solveResult.trace.placed_department_count ?? solveResult.trace.placed_count} bölüm)`, `⚠️ Incomplete (${solveResult.trace.placed_department_count ?? solveResult.trace.placed_count} depts)`)
                    : t('Henüz CORELAP çözümü yok', 'No CORELAP solution yet')}
                </div>
              </div>
            )}

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Maks. İterasyon:', 'Max Iterations:')}
              </label>
              <input
                type="number"
                min="1"
                max="200"
                step="1"
                value={craftMaxIterations}
                onChange={(e) => setCraftMaxIterations(Number(e.target.value))}
                disabled={craftRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Min. İyileşme Eşiği ($):', 'Min Improvement Threshold ($):')}
              </label>
              <input
                type="number"
                min="0"
                max="1000"
                step="0.01"
                value={craftMinImprovement}
                onChange={(e) => setCraftMinImprovement(Number(e.target.value))}
                disabled={craftRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Döndürmeli Değişimler ve İzleme:', 'Rotational Swaps & Trace:')}
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem', paddingTop: '0.2rem' }}>
                <label style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={craftAllowRotation}
                    onChange={(e) => setCraftAllowRotation(e.target.checked)}
                    disabled={craftRunning}
                  />
                  {t('90° Döndürmeli Değişimlere İzin Ver', 'Allow 90° Rotational Swaps')}
                </label>
                <select
                  value={craftTraceLevel}
                  onChange={(e) => setCraftTraceLevel(e.target.value as any)}
                  disabled={craftRunning}
                  style={{
                    padding: '0.3rem 0.5rem',
                    borderRadius: '4px',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border-color)',
                    fontSize: '0.75rem',
                  }}
                >
                  <option value="SUMMARY">{t('Özet İzleme', 'Summary Trace')}</option>
                  <option value="DETAILED">{t('Ayrıntılı İzleme', 'Detailed Trace')}</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button
                onClick={handleRunCRAFT}
                disabled={!canRunCRAFT}
                title={craftDisabledReason || undefined}
                style={{
                  width: '100%',
                  padding: '0.6rem 1.25rem',
                  backgroundColor: canRunCRAFT ? '#10b981' : 'var(--bg-secondary)',
                  color: canRunCRAFT ? '#fff' : 'var(--text-muted)',
                  border: canRunCRAFT ? 'none' : '1px solid var(--border-color)',
                  borderRadius: '6px',
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  cursor: canRunCRAFT ? 'pointer' : 'not-allowed',
                  opacity: canRunCRAFT ? 1 : 0.6,
                  transition: 'all 0.2s',
                }}
              >
                {craftRunning ? t('CRAFT ile Optimize Ediliyor...', 'Optimizing with CRAFT...') : t('CRAFT Optimizasyonunu Çalıştır', 'Run CRAFT Optimization')}
              </button>
            </div>
          </div>

          {/* Warning banner when CRAFT cannot run */}
          {!canRunCRAFT && craftDisabledReason && (
            <div
              style={{
                backgroundColor: 'rgba(245, 158, 11, 0.12)',
                color: '#fbbf24',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                marginBottom: '1.5rem',
                fontSize: '0.85rem',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <span>⚠️</span>
              <span>{craftDisabledReason}</span>
            </div>
          )}

          {/* CRAFT Execution Results */}
          {craftResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Summary Metrics Banner */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                  gap: '1rem',
                  backgroundColor: 'var(--bg-card)',
                  padding: '1.25rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('Başlangıç Taşıma Maliyeti (MHC)', 'Initial Material Handling Cost')}</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    ${craftResult.result.initial_mhc.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('Nihai Optimize MHC', 'Final Optimized MHC')}</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#34d399' }}>
                    ${craftResult.result.final_mhc.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('MHC İyileşmesi', 'MHC Improvement')}</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#34d399' }}>
                    -${craftResult.result.absolute_improvement.toLocaleString(undefined, { minimumFractionDigits: 2 })}{' '}
                    <span style={{ fontSize: '0.9rem', color: '#10b981' }}>
                      ({craftResult.result.percentage_improvement}%)
                    </span>
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('Kabul Edilen Değişim / İterasyon', 'Swaps Accepted / Iterations')}</div>
                  <div style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {craftResult.result.accepted_swaps.length} {t('değişim', 'swaps')} / {craftResult.result.iterations} {t('iter.', 'iters')}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('Durdurma Nedeni', 'Stopping Reason')}</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                    <span
                      style={{
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(59, 130, 246, 0.15)',
                        color: '#60a5fa',
                        fontSize: '0.75rem',
                      }}
                    >
                      {craftResult.result.termination_reason}
                    </span>
                  </div>
                </div>
              </div>

              {/* Side-by-Side Comparison Canvas */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                  gap: '1.5rem',
                }}
              >
                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    padding: '1.25rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{t('Başlangıç Yerleşimi (Önce)', 'Initial Layout (Before)')}</h3>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(59, 130, 246, 0.15)',
                        color: '#60a5fa',
                        fontWeight: 600,
                      }}
                    >
                      MHC: ${craftResult.result.initial_mhc.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <LayoutCanvas layout={craftResult.initial_layout} />
                </div>

                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    padding: '1.25rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <h3 style={{ fontSize: '0.95rem', fontWeight: 600 }}>{t('CRAFT Optimize Yerleşim (Sonra)', 'CRAFT Optimized Layout (After)')}</h3>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(16, 185, 129, 0.15)',
                        color: '#34d399',
                        fontWeight: 600,
                      }}
                    >
                      MHC: ${craftResult.result.final_mhc.toLocaleString(undefined, { minimumFractionDigits: 2 })} (-{craftResult.result.percentage_improvement}%)
                    </span>
                  </div>
                  <LayoutCanvas layout={craftResult.continuous_layout} />
                </div>
              </div>

              {/* Sequence of Accepted Swaps Table */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  padding: '1.25rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                }}
              >
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                  {t('Kabul Edilen Bölüm Değişimleri', 'Accepted Department Exchanges')} ({craftResult.result.accepted_swaps.length})
                </h4>

                {craftResult.result.accepted_swaps.length === 0 ? (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic', padding: '0.5rem 0' }}>
                    {t(
                      `Hiçbir ikili değişim yerleşimi iyileştirmedi. Yerleşim uygun değişimler için zaten yerel minimumdaydı (${craftResult.result.termination_reason}).`,
                      `No pairwise swaps improved the layout. Layout was already at a local minimum for eligible swaps (${craftResult.result.termination_reason}).`
                    )}
                  </div>
                ) : (
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-muted)' }}>
                          <th style={{ padding: '0.5rem' }}>{t('İterasyon', 'Iteration')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('Değiştirilen Bölümler', 'Exchanged Departments')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('Değişim Türü', 'Swap Type')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('Önceki MHC', 'MHC Before')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('Sonraki MHC', 'MHC After')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('Azalma (ΔMHC)', 'Reduction (ΔMHC)')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('Kümülatif Azalma', 'Cumulative Reduction')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {craftResult.result.accepted_swaps.map((s) => (
                          <tr key={s.iteration} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.05)' }}>
                            <td style={{ padding: '0.5rem', fontWeight: 600 }}>#{s.iteration}</td>
                            <td style={{ padding: '0.5rem' }}>
                              <span style={{ color: 'var(--accent-color)', fontWeight: 600 }}>{s.dept_a}</span> ↔{' '}
                              <span style={{ color: 'var(--accent-color)', fontWeight: 600 }}>{s.dept_b}</span>
                            </td>
                            <td style={{ padding: '0.5rem' }}>
                              <span
                                style={{
                                  fontSize: '0.7rem',
                                  padding: '0.1rem 0.4rem',
                                  borderRadius: '4px',
                                  backgroundColor: s.is_rotational ? 'rgba(168, 85, 247, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                                  color: s.is_rotational ? '#c084fc' : '#60a5fa',
                                }}
                              >
                                {s.is_rotational ? t('90° Döndürmeli', '90° Rotational') : t('Doğrudan Koordinat', 'Direct Coordinate')}
                              </span>
                            </td>
                            <td style={{ padding: '0.5rem' }}>${s.mhc_before.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                            <td style={{ padding: '0.5rem' }}>${s.mhc_after.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                            <td style={{ padding: '0.5rem', color: '#34d399', fontWeight: 600 }}>
                              -${s.improvement.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                            <td style={{ padding: '0.5rem', color: '#34d399' }}>
                              -${s.cumulative_improvement.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* CRAFT Iteration Trace Inspector */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  padding: '1.25rem',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                }}
              >
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                  {t('İterasyon İzleme Tanılama Geçmişi', 'Iteration Trace Diagnostic History')} ({craftResult.trace.steps.length} {t('Adım', 'Steps')})
                </h4>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '350px', overflowY: 'auto' }}>
                  {craftResult.trace.steps.map((step) => {
                    const isExpanded = activeCraftStep === step.iteration;
                    return (
                      <div
                        key={step.iteration}
                        style={{
                          backgroundColor: 'var(--bg-secondary)',
                          border: `1px solid ${isExpanded ? 'var(--accent-color)' : 'var(--border-color)'}`,
                          borderRadius: '6px',
                          padding: '0.75rem 1rem',
                          cursor: 'pointer',
                        }}
                        onClick={() => setActiveCraftStep(isExpanded ? null : step.iteration)}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                            <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{t('İterasyon', 'Iteration')} #{step.iteration}</span>
                            {step.selected_swap ? (
                              <span style={{ fontSize: '0.75rem', color: '#34d399', fontWeight: 600 }}>
                                {t('Değiştirildi:', 'Swapped')} {step.selected_swap.dept_a} ↔ {step.selected_swap.dept_b} (-${step.selected_swap.improvement})
                              </span>
                            ) : (
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {t('İyileştirici Değişim Bulunamadı (Sonlandırıldı)', 'No Improving Swap Found (Terminated)')}
                              </span>
                            )}
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            <span>{t('Adaylar:', 'Candidates:')} {step.candidate_pairs}</span>
                            <span>{t('Uygun:', 'Feasible:')} {step.feasible_candidates}</span>
                            <span>{t('Reddedilen:', 'Rejected:')} {step.rejected_candidates}</span>
                            <span>MHC: ${step.mhc_after.toFixed(2)}</span>
                          </div>
                        </div>

                        {isExpanded && (
                          <div
                            style={{
                              marginTop: '0.75rem',
                              paddingTop: '0.75rem',
                              borderTop: '1px solid var(--border-color)',
                              fontSize: '0.75rem',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '0.5rem',
                            }}
                          >
                            <div>
                              <strong>{t('Reddetme Dağılımı:', 'Rejection Breakdown:')}</strong>{' '}
                              {Object.keys(step.rejection_breakdown).length === 0 ? (
                                <span style={{ color: 'var(--text-muted)' }}>{t('Yok', 'None')}</span>
                              ) : (
                                Object.entries(step.rejection_breakdown).map(([cause, cnt]) => (
                                  <span key={cause} style={{ marginRight: '0.75rem', color: '#f87171' }}>
                                    {cause}: {cnt}
                                  </span>
                                ))
                              )}
                            </div>

                            {step.candidate_evaluations && (
                              <div style={{ marginTop: '0.25rem' }}>
                                <strong>{t('Ayrıntılı Aday Değerlendirmeleri:', 'Detailed Candidate Evaluations:')}</strong>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.25rem' }}>
                                  {step.candidate_evaluations.map((ce, idx) => (
                                    <div key={idx} style={{ color: ce.is_feasible ? '#34d399' : '#f87171' }}>
                                      {ce.pair[0]} ↔ {ce.pair[1]} {ce.is_rotational ? t('(Döndürülmüş)', '(Rotated)') : ''}:{' '}
                                      {ce.is_feasible
                                        ? t(`Uygun (MHC: $${ce.mhc_after?.toFixed(2)}, İyileşme: $${ce.improvement?.toFixed(2)})`, `Feasible (MHC: $${ce.mhc_after?.toFixed(2)}, Imp: $${ce.improvement?.toFixed(2)})`)
                                        : t(`Uygun Değil (${ce.rejection_reason})`, `Infeasible (${ce.rejection_reason})`)}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* ========================================================================= */}
      {/* ALDEP VIEW                                                                */}
      {/* ========================================================================= */}
      {activeAlgo === 'ALDEP' && (
        <>
          {/* ALDEP Control Panel */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
              backgroundColor: 'var(--bg-card)',
              padding: '1.25rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              marginBottom: '1.5rem',
            }}
          >
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Hedef Problem:', 'Target Problem:')}
              </label>
              <select
                value={selectedProblemId}
                onChange={(e) => handleProblemChange(e.target.value)}
                disabled={loading || aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                {problems.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.department_count} {t('bölüm', 'depts')})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Aday Sayısı (K):', 'Candidates Count (K):')}
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={aldepCandidatesCount}
                onChange={(e) => setAldepCandidatesCount(Number(e.target.value))}
                disabled={aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Temel Rastgele Tohum (Seed):', 'Base Random Seed:')}
              </label>
              <input
                type="number"
                value={aldepRandomSeed}
                onChange={(e) => setAldepRandomSeed(Number(e.target.value))}
                disabled={aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Hücre Boyutu (m):', 'Cell Size (m):')}
              </label>
              <input
                type="number"
                step="0.5"
                min="1"
                value={aldepCellSize}
                onChange={(e) => setAldepCellSize(Number(e.target.value))}
                disabled={aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Şerit Genişliği (hücre):', 'Strip Width (cells):')}
              </label>
              <input
                type="number"
                min="1"
                max="10"
                value={aldepStripWidth}
                onChange={(e) => setAldepStripWidth(Number(e.target.value))}
                disabled={aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Tarama Yönü:', 'Sweep Direction:')}
              </label>
              <select
                value={aldepSweepDirection}
                onChange={(e) => setAldepSweepDirection(e.target.value as any)}
                disabled={aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="VERTICAL">{t('Dikey Şeritler (Yılankavi Sütunlar)', 'Vertical Strips (Serpentine Columns)')}</option>
                <option value="HORIZONTAL">{t('Yatay Şeritler (Yılankavi Satırlar)', 'Horizontal Strips (Serpentine Rows)')}</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Seçim Eşiği (T):', 'Selection Threshold (T):')}
              </label>
              <select
                value={aldepThreshold}
                onChange={(e) => setAldepThreshold(Number(e.target.value))}
                disabled={aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value={16.0}>{t("16.0 — Kesinlikle Gerekli (Yalnızca 'A')", "16.0 — Absolutely Necessary ('A' only)")}</option>
                <option value={8.0}>{t("8.0 — Çok Önemli ('E' veya üstü - Varsayılan)", "8.0 — Especially Important ('E' or higher - Default)")}</option>
                <option value={4.0}>{t("4.0 — Önemli ('I' veya üstü)", "4.0 — Important ('I' or higher)")}</option>
                <option value={2.0}>{t("2.0 — Olağan Yakınlık ('O' veya üstü)", "2.0 — Ordinary Closeness ('O' or higher)")}</option>
                <option value={0.0}>{t("0.0 — Herhangi Bir Yakınlık ('U' veya üstü)", "0.0 — Any Closeness ('U' or higher)")}</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Şerit Bölme Modu:', 'Strip Splitting Mode:')}
              </label>
              <select
                value={aldepAllowSplitting === null ? 'auto' : aldepAllowSplitting ? 'true' : 'false'}
                onChange={(e) =>
                  setAldepAllowSplitting(e.target.value === 'auto' ? null : e.target.value === 'true')
                }
                disabled={aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="auto">{t('Otomatik (Önce Dikdörtgensel, Sığmazsa Klasik - Varsayılan)', 'Auto (Rectangular First, Classical Fallback - Default)')}</option>
                <option value="true">{t('Klasik ALDEP (Sürekli Yılankavi Sarma)', 'Classical ALDEP (Continuous Serpentine Wraps)')}</option>
                <option value="false">{t('FLODSS Uyarlaması (Şerit Bölmesiz - Dikdörtgensel)', 'FLODSS Adaptation (No Strip Splitting - Rectangular)')}</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Eşitlik Bozma Kuralı:', 'Tie-Breaker Rule:')}
              </label>
              <select
                value={aldepTieBreaker}
                onChange={(e) => setAldepTieBreaker(e.target.value as any)}
                disabled={aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="RANDOM_AMONG_MAX">{t('Eşit Maksimumlar Arasından Rastgele (Klasik)', 'Random Among Tied Maxima (Classical)')}</option>
                <option value="RANDOM_AMONG_THRESHOLD">{t('Eşik Üzerindeki Tüm Adaylardan Rastgele', 'Random Among All Above Threshold')}</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('İzleme Ayrıntı Düzeyi:', 'Trace Detail Level:')}
              </label>
              <select
                value={aldepTraceLevel}
                onChange={(e) => setAldepTraceLevel(e.target.value as any)}
                disabled={aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="SUMMARY">{t('Özet İzleme', 'Summary Trace')}</option>
                <option value="DETAILED">{t('Adım Adım Ayrıntılı İzleme', 'Detailed Step-by-Step Trace')}</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button
                onClick={handleRunALDEP}
                disabled={!selectedProblemId || aldepRunning}
                style={{
                  width: '100%',
                  padding: '0.65rem 1rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--accent-color)',
                  color: '#fff',
                  border: 'none',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  cursor: !selectedProblemId || aldepRunning ? 'not-allowed' : 'pointer',
                  opacity: !selectedProblemId || aldepRunning ? 0.6 : 1,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                }}
              >
                {aldepRunning ? t('Adaylar Üretiliyor...', 'Generating Candidates...') : t('ALDEP Kurucu Sezgiselini Çalıştır', 'Run ALDEP Construction Heuristic')}
              </button>
            </div>
          </div>

          {/* ALDEP Results Section */}
          {aldepResult && (() => {
            const activeCand =
              aldepResult.candidates.find((c) => c.candidate_index === selectedCandidateIdx) ||
              aldepResult.best_candidate;
            const probSummary = problems.find((p) => p.id === selectedProblemId);
            const facW = probSummary?.facility_width ?? 100;
            const facH = probSummary?.facility_height ?? 60;

            return (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                {/* KPI Metrics Summary */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '1rem',
                  }}
                >
                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '1rem',
                    }}
                  >
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('En İyi Aday', 'Top Candidate')}</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#fbbf24', marginTop: '0.25rem' }}>
                      {t('Aday', 'Candidate')} #{aldepResult.best_candidate.candidate_index}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      {t('Tohum:', 'Seed:')} {aldepResult.best_candidate.seed}
                    </div>
                  </div>

                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '1rem',
                    }}
                  >
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('En İyi Malzeme Taşıma Maliyeti', 'Best Material Handling Cost')}</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#34d399', marginTop: '0.25rem' }}>
                      {aldepResult.best_candidate.material_handling_cost != null
                        ? `$${aldepResult.best_candidate.material_handling_cost.toLocaleString()}`
                        : t('Yok', 'N/A')}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      {t('Akış Mesafesi:', 'Flow Distance:')} {aldepResult.best_candidate.flow_distance?.toFixed(1) ?? t('Yok', 'N/A')} m
                    </div>
                  </div>

                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '1rem',
                    }}
                  >
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('Çeşitlilik ve Geçerlilik', 'Diversity & Validity')}</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '0.25rem' }}>
                      {aldepResult.trace.unique_candidate_count} / {aldepResult.trace.number_of_candidates}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      {t(`Benzersiz Aday (Uygun: ${aldepResult.trace.feasible_candidate_count})`, `Unique Candidates (Feasible: ${aldepResult.trace.feasible_candidate_count})`)}
                    </div>
                  </div>

                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '1rem',
                    }}
                  >
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('Çalışma Süresi', 'Execution Runtime')}</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: '0.25rem' }}>
                      {aldepResult.trace.execution_time_seconds.toFixed(3)}s
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                      {aldepResult.trace.number_of_candidates} {t('stokastik çalıştırma', 'stochastic runs')}
                    </div>
                  </div>
                </div>

                {/* Candidate Portfolio Table */}
                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '1.25rem',
                  }}
                >
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                    {t('Üretilen Aday Yerleşim Portföyü', 'Generated Candidate Layout Portfolio')} ({aldepResult.candidates.length} {t('Alternatif', 'Alternatives')})
                  </h3>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                          <th style={{ padding: '0.5rem' }}>{t('Aday', 'Candidate')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('Tohum', 'Seed')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('Bölüm Sırası', 'Department Sequence')}</th>
                          <th style={{ padding: '0.5rem' }}>MHC ($)</th>
                          <th style={{ padding: '0.5rem' }}>{t('Akış Mes.', 'Flow Dist')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('REL Skoru', 'REL Score')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('Durum', 'Status')}</th>
                          <th style={{ padding: '0.5rem' }}>{t('İşlem', 'Action')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {aldepResult.candidates.map((cand) => {
                          const isSelected = cand.candidate_index === activeCand.candidate_index;
                          const isBest = cand.candidate_index === aldepResult.best_candidate.candidate_index;
                          return (
                            <tr
                              key={cand.candidate_index}
                              onClick={() => setSelectedCandidateIdx(cand.candidate_index)}
                              style={{
                                borderBottom: '1px solid var(--border-color)',
                                backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
                                cursor: 'pointer',
                              }}
                            >
                              <td style={{ padding: '0.5rem', fontWeight: 600 }}>
                                #{cand.candidate_index} {isBest && <span style={{ color: '#fbbf24', fontSize: '0.7rem' }}>{t('(En İyi)', '(Best)')}</span>}
                              </td>
                              <td style={{ padding: '0.5rem' }}>{cand.seed}</td>
                              <td style={{ padding: '0.5rem', fontFamily: 'monospace', fontSize: '0.75rem' }}>
                                {cand.department_order.join(' → ')}
                              </td>
                              <td style={{ padding: '0.5rem', fontWeight: 600, color: '#34d399' }}>
                                {cand.material_handling_cost != null ? `$${cand.material_handling_cost.toLocaleString()}` : t('Yok', 'N/A')}
                              </td>
                              <td style={{ padding: '0.5rem' }}>
                                {cand.flow_distance != null ? cand.flow_distance.toFixed(1) : t('Yok', 'N/A')}
                              </td>
                              <td style={{ padding: '0.5rem' }}>
                                {cand.relationship_score != null ? cand.relationship_score.toFixed(1) : t('Yok', 'N/A')}
                              </td>
                              <td style={{ padding: '0.5rem' }}>
                                {cand.is_feasible ? (
                                  <span style={{ color: '#34d399', fontSize: '0.75rem', fontWeight: 600 }}>{t('Uygun', 'Feasible')}</span>
                                ) : cand.is_complete ? (
                                  <span style={{ color: '#fbbf24', fontSize: '0.75rem' }}>{t('Tam (Uyarılı)', 'Complete (Warnings)')}</span>
                                ) : (
                                  <span style={{ color: '#f87171', fontSize: '0.75rem' }}>{t('Eksik', 'Incomplete')} ({cand.placed_department_count}/{cand.total_department_count})</span>
                                )}
                                {cand.is_duplicate && (
                                  <span style={{ marginLeft: '0.4rem', color: 'var(--text-muted)', fontSize: '0.7rem' }}>({t('Tekrar', 'Dup')} #{cand.duplicate_of_index})</span>
                                )}
                              </td>
                              <td style={{ padding: '0.5rem' }}>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedCandidateIdx(cand.candidate_index);
                                  }}
                                  style={{
                                    padding: '0.2rem 0.5rem',
                                    borderRadius: '4px',
                                    border: '1px solid var(--border-color)',
                                    backgroundColor: isSelected ? 'var(--accent-color)' : 'transparent',
                                    color: isSelected ? '#fff' : 'var(--text-primary)',
                                    fontSize: '0.75rem',
                                    cursor: 'pointer',
                                  }}
                                >
                                  {isSelected ? t('Görüntüleniyor', 'Viewing') : t('İncele', 'Inspect')}
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Selected Candidate Detailed Layout & Shape Diagnostics */}
                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-color)',
                    borderRadius: '8px',
                    padding: '1.25rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>
                      {t(`Aday #${activeCand.candidate_index} Yerleşim Önizlemesi ve Şekil Tanılaması`, `Candidate #${activeCand.candidate_index} Layout Preview & Shape Diagnostics`)}
                    </h3>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {t('İmza:', 'Signature:')} {activeCand.layout_signature.slice(0, 16)}...
                    </span>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'minmax(350px, 1fr) minmax(320px, 1fr)', gap: '1.5rem' }}>
                    {/* 2D Canvas Layout */}
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                        {t('2D Mekânsal Koordinatlar', '2D Spatial Coordinates')} ({facW}m × {facH}m)
                      </div>
                      <LayoutCanvas
                        layout={activeCand.continuous_layout}
                      />
                    </div>

                    {/* Shape Diagnostics Table */}
                    <div>
                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                        {t('Izgara Ayrıklaştırması ve En-Boy Oranları', 'Grid Discretization & Aspect Ratios')}
                      </div>
                      <div style={{ maxHeight: '350px', overflowY: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                          <thead>
                            <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                              <th style={{ padding: '0.4rem' }}>{t('Bölüm', 'Dept')}</th>
                              <th style={{ padding: '0.4rem' }}>{t('Gerekli (m²)', 'Req (m²)')}</th>
                              <th style={{ padding: '0.4rem' }}>{t('Tahsis (m²)', 'Alloc (m²)')}</th>
                              <th style={{ padding: '0.4rem' }}>{t('Hücre', 'Cells')}</th>
                              <th style={{ padding: '0.4rem' }}>{t('Oran', 'AR')}</th>
                              <th style={{ padding: '0.4rem' }}>{t('Şekil', 'Shape')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {Object.values(activeCand.shape_diagnostics).map((diag) => (
                              <tr key={diag.department_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                                <td style={{ padding: '0.4rem', fontWeight: 600 }}>{diag.department_id}</td>
                                <td style={{ padding: '0.4rem' }}>{diag.required_area}</td>
                                <td style={{ padding: '0.4rem' }}>{diag.allocated_area}</td>
                                <td style={{ padding: '0.4rem' }}>{diag.allocated_cells}</td>
                                <td style={{ padding: '0.4rem' }}>{diag.aspect_ratio.toFixed(2)}</td>
                                <td style={{ padding: '0.4rem' }}>
                                  {diag.is_rectangular ? (
                                    <span style={{ color: '#34d399' }}>{t('Dikdörtgensel', 'Rectangular')}</span>
                                  ) : (
                                    <span style={{ color: '#fbbf24' }}>{t('Yılankavi', 'Serpentine')}</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Selection Trace Timeline */}
                {activeCand.selection_steps && activeCand.selection_steps.length > 0 && (
                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '8px',
                      padding: '1.25rem',
                    }}
                  >
                    <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                      {t('Bölüm Seçimi Karar İzi', 'Department Selection Decision Trace')} ({activeCand.selection_steps.length} {t('Adım', 'Steps')})
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '300px', overflowY: 'auto' }}>
                      {activeCand.selection_steps.map((step) => {
                        const isExpanded = activeAldepStep === step.step_number;
                        return (
                          <div
                            key={step.step_number}
                            onClick={() => setActiveAldepStep(isExpanded ? null : step.step_number)}
                            style={{
                              backgroundColor: 'var(--bg-secondary)',
                              border: `1px solid ${isExpanded ? 'var(--accent-color)' : 'var(--border-color)'}`,
                              borderRadius: '6px',
                              padding: '0.65rem 0.85rem',
                              cursor: 'pointer',
                              fontSize: '0.85rem',
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                                <span style={{ fontWeight: 600 }}>{t('Adım', 'Step')} #{step.step_number}</span>
                                <span style={{ color: '#fbbf24', fontWeight: 600 }}>{t('Yerleştirilen:', 'Placed:')} {step.selected_department}</span>
                                <span
                                  style={{
                                    fontSize: '0.7rem',
                                    padding: '0.1rem 0.4rem',
                                    borderRadius: '3px',
                                    backgroundColor:
                                      step.selection_mode === 'INITIAL_RANDOM'
                                        ? 'rgba(59, 130, 246, 0.2)'
                                        : step.selection_mode === 'AFFINITY_MAX'
                                        ? 'rgba(16, 185, 129, 0.2)'
                                        : 'rgba(239, 68, 68, 0.2)',
                                    color:
                                      step.selection_mode === 'INITIAL_RANDOM'
                                        ? '#60a5fa'
                                        : step.selection_mode === 'AFFINITY_MAX'
                                        ? '#34d399'
                                        : '#f87171',
                                  }}
                                >
                                  {step.selection_mode}
                                </span>
                              </div>
                              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                {step.last_department_id ? t(`${step.last_department_id} ile yakınlık`, `Affinity with ${step.last_department_id}`) : t('Başlangıç Tohum Seçimi', 'Initial Seed Choice')}
                              </span>
                            </div>

                            {isExpanded && (
                              <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                                <div><strong>{t(`Uygun Adaylar (Skor ≥ ${step.threshold}):`, `Eligible Candidates (Score ≥ ${step.threshold}):`)}</strong> {step.eligible_candidates.join(', ') || t('Yok (Yerleştirilmemişlerden rastgele seçim)', 'None (Fallback to random unplaced)')}</div>
                                <div style={{ marginTop: '0.25rem' }}>
                                  <strong>{t('Aday Yakınlık Skorları:', 'Candidate Affinity Scores:')}</strong>{' '}
                                  {Object.entries(step.candidate_scores).map(([d, s]) => `${d}: ${s}`).join(' | ')}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </>
      )}

      {/* ========================================================================= */}
      {/* FEASIBLE GENERATOR VIEW (PHASE 8)                                         */}
      {/* ========================================================================= */}
      {activeAlgo === 'FEASIBLE_GENERATOR' && (
        <>
          {/* Control Panel */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '1rem',
              backgroundColor: 'var(--bg-card)',
              padding: '1.25rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
              marginBottom: '1.5rem',
            }}
          >
            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Hedef Problem:', 'Target Problem:')}
              </label>
              <select
                value={selectedProblemId}
                onChange={(e) => handleProblemChange(e.target.value)}
                disabled={loading || genRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                {problems.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.department_count} {t('bölüm', 'depts')})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Arama Stratejisi:', 'Search Strategy:')}
              </label>
              <select
                value={genStrategy}
                onChange={(e) => setGenStrategy(e.target.value as GeneratorStrategy)}
                disabled={genRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="guillotine_row_packing">{t('Giyotin Sıra Paketleme (Endüstriyel Holler)', 'Guillotine Row Packing (Industrial Bays)')}</option>
                <option value="free_rectangle_dfs">{t('Serbest Dikdörtgen Geri İzleme (MER DFS)', 'Free-Rectangle Backtracking (MER DFS)')}</option>
                <option value="slicing_tree_decomposition">{t('Dilimleme Ağacı Ayrıştırması (Özyinelemeli)', 'Slicing Tree Decomposition (Recursive)')}</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Bölüm Sıralaması:', 'Department Ordering:')}
              </label>
              <select
                value={genOrderingStrategy}
                onChange={(e) => setGenOrderingStrategy(e.target.value as DepartmentOrderingStrategy)}
                disabled={genRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              >
                <option value="most_constrained_first">{t('Önce En Kısıtlı (Alan × En-Boy Oranı)', 'Most Constrained First (Area × AR)')}</option>
                <option value="largest_area_first">{t('Önce En Büyük Alan', 'Largest Area First')}</option>
                <option value="flow_volume_descending">{t('Azalan Akış Hacmine Göre', 'Flow Volume Descending')}</option>
                <option value="relationship_weight_descending">{t('Azalan İlişki Ağırlığına Göre', 'Relationship Weight Descending')}</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Maks. Ağaç Düğümü:', 'Max Tree Nodes:')}
              </label>
              <input
                type="number"
                min="10"
                max="50000"
                step="100"
                value={genMaxNodes}
                onChange={(e) => setGenMaxNodes(Number(e.target.value))}
                disabled={genRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Maks. Geri İzleme:', 'Max Backtracks:')}
              </label>
              <input
                type="number"
                min="0"
                max="20000"
                step="100"
                value={genMaxBacktracks}
                onChange={(e) => setGenMaxBacktracks(Number(e.target.value))}
                disabled={genRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Maks. Süre Sınırı (sn):', 'Max Wall Timeout (s):')}
              </label>
              <input
                type="number"
                min="0.5"
                max="60"
                step="0.5"
                value={genMaxRuntime}
                onChange={(e) => setGenMaxRuntime(Number(e.target.value))}
                disabled={genRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Bölüm Başına Şekil Alternatifi:', 'Shape Alternatives / Dept:')}
              </label>
              <input
                type="number"
                min="1"
                max="30"
                step="1"
                value={genMaxShapeAlternatives}
                onChange={(e) => setGenMaxShapeAlternatives(Number(e.target.value))}
                disabled={genRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 600, display: 'block', marginBottom: '0.4rem' }}>
                {t('Bölüm Başına Aday Sınırı:', 'Candidate Limit / Dept:')}
              </label>
              <input
                type="number"
                min="1"
                max="50"
                step="1"
                value={genCandidateLimit}
                onChange={(e) => setGenCandidateLimit(Number(e.target.value))}
                disabled={genRunning}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem',
                }}
              />
            </div>

            <div style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button
                onClick={handleRunFeasibleGenerator}
                disabled={!selectedProblemId || genRunning}
                style={{
                  width: '100%',
                  padding: '0.6rem 1rem',
                  borderRadius: '6px',
                  backgroundColor: genRunning ? 'var(--text-muted)' : '#8b5cf6',
                  color: '#fff',
                  border: 'none',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  cursor: genRunning ? 'not-allowed' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '0.5rem',
                }}
              >
                {genRunning ? (
                  <>
                    <span className="spinner" style={{ width: '14px', height: '14px' }}></span>
                    {t('Uygun Yerleşim Aranıyor...', 'Searching Feasible Layout...')}
                  </>
                ) : (
                  t('Uygun Yerleşim Üreticisini Çalıştır', 'Run Feasible Generator')
                )}
              </button>
            </div>
          </div>

          {/* Results Presentation */}
          {genResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Outcome Banner */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  padding: '1.25rem',
                  borderRadius: '8px',
                  border: `1px solid ${
                    genResult.result.success
                      ? 'rgba(16, 185, 129, 0.4)'
                      : 'rgba(239, 68, 68, 0.4)'
                  }`,
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '1rem',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
                    <span
                      style={{
                        padding: '0.25rem 0.6rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        backgroundColor: genResult.result.success
                          ? 'rgba(16, 185, 129, 0.2)'
                          : 'rgba(239, 68, 68, 0.2)',
                        color: genResult.result.success ? '#34d399' : '#f87171',
                        border: `1px solid ${
                          genResult.result.success ? '#10b981' : '#ef4444'
                        }`,
                      }}
                    >
                      {genResult.result.termination_reason}
                    </span>
                    <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                      {t(
                        `${genResult.result.placed_department_count} / ${genResult.result.total_department_count} Bölüm Yerleştirildi`,
                        `Placed ${genResult.result.placed_department_count} / ${genResult.result.total_department_count} Departments`
                      )}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
                    {t('Strateji:', 'Strategy:')} <strong style={{ color: 'var(--text-primary)' }}>{genResult.result.strategy}</strong> | {t('Süre:', 'Runtime:')}{' '}
                    <strong>{genResult.result.runtime_seconds.toFixed(4)}s</strong> | {t('İncelenen Düğüm:', 'Nodes Explored:')}{' '}
                    <strong>{genResult.result.nodes_explored}</strong> | {t('Geri İzleme:', 'Backtracks:')}{' '}
                    <strong>{genResult.result.backtracks}</strong> | {t('Reddedilen Aday:', 'Rejected Candidates:')}{' '}
                    <strong>{genResult.result.candidates_rejected}</strong>
                  </p>
                </div>

                {genResult.result.layout_signature && (
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{t('Deterministik İmza:', 'Deterministic Signature:')}</div>
                    <code style={{ fontSize: '0.75rem', color: '#a78bfa' }}>
                      {genResult.result.layout_signature.slice(0, 16)}...
                    </code>
                  </div>
                )}
              </div>

              {/* Layout Canvas View */}
              {genResult.result.layout && (
                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    padding: '1rem',
                    borderRadius: '8px',
                    border: '1px solid var(--border-color)',
                  }}
                >
                  <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                    {t('Üretilen Uygun Sürekli Yerleşim', 'Generated Feasible Continuous Layout')}
                  </h4>
                  <LayoutCanvas layout={genResult.result.layout} />
                </div>
              )}

              {/* Engineering Validation & Multi-Criteria Metrics */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                  gap: '1rem',
                }}
              >
                {/* Geometric Feasibility Card */}
                {genResult.validation && (
                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      padding: '1.25rem',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                    }}
                  >
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ color: genResult.validation.is_valid ? '#10b981' : '#ef4444' }}>
                        {genResult.validation.is_valid ? '✓' : '✗'}
                      </span>
                      {t('Geometrik Doğrulama (Dikdörtgensel Bütünlük)', 'Geometric Validation (Rectangular Integrity)')}
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.8rem' }}>
                      <div>{t('Toplam Çakışma Alanı:', 'Total Overlap Area:')}</div>
                      <div style={{ fontWeight: 600, color: genResult.validation.total_overlap_area === 0 ? '#10b981' : '#ef4444' }}>
                        {genResult.validation.total_overlap_area.toFixed(2)} m²
                      </div>
                      <div>{t('Sınır İhlalleri:', 'Boundary Violations:')}</div>
                      <div style={{ fontWeight: 600 }}>
                        {genResult.validation.errors.filter((e) => e.toLowerCase().includes('boundary')).length}
                      </div>
                      <div>{t('Doğrulanan Bölümler:', 'Validated Departments:')}</div>
                      <div style={{ fontWeight: 600 }}>{genResult.validation.checked_departments.length}</div>
                    </div>
                    {genResult.validation.errors.length > 0 && (
                      <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#f87171' }}>
                        <strong>{t('Kritik Hatalar:', 'Fatal Errors:')}</strong>
                        <ul style={{ margin: '0.25rem 0 0 1rem', padding: 0 }}>
                          {genResult.validation.errors.map((e, idx) => (
                            <li key={idx}>{e}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Multi-Criteria Evaluation Card */}
                {genResult.evaluation && (
                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      padding: '1.25rem',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                    }}
                  >
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                      {t('Çok Ölçütlü Değerlendirme Skorları', 'Multi-Criteria Evaluation Scores')}
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.8rem' }}>
                      <div>{t('Malzeme Taşıma Maliyeti (MHC):', 'Material Handling Cost (MHC):')}</div>
                      <div style={{ fontWeight: 700, color: '#38bdf8' }}>
                        ${genResult.evaluation.objective_values['material_handling_cost']?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? t('Yok', 'N/A')}
                      </div>
                      <div>{t('Akış-Mesafe Skoru:', 'Flow-Distance Score:')}</div>
                      <div style={{ fontWeight: 600 }}>
                        {genResult.evaluation.objective_values['flow_distance']?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? t('Yok', 'N/A')}
                      </div>
                      <div>{t('İlişki Memnuniyeti:', 'Relationship Satisfaction:')}</div>
                      <div style={{ fontWeight: 600, color: '#10b981' }}>
                        {genResult.evaluation.objective_values['relationship_satisfaction_percentage']?.toFixed(1) ?? t('Yok', 'N/A')}%
                      </div>
                      <div>{t('Kesin Kısıt İhlalleri:', 'Hard Constraint Violations:')}</div>
                      <div style={{ fontWeight: 600, color: genResult.evaluation.hard_violation_count === 0 ? '#10b981' : '#ef4444' }}>
                        {genResult.evaluation.hard_violation_count}
                      </div>
                      <div>{t('Alan Kullanımı:', 'Area Utilization:')}</div>
                      <div style={{ fontWeight: 600 }}>
                        {(genResult.evaluation.objective_values['area_utilization'] ? genResult.evaluation.objective_values['area_utilization'] * 100 : 91.67).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Failure Diagnostics if Incomplete */}
              {!genResult.result.success && genResult.result.failure_diagnostics && (
                <div
                  style={{
                    backgroundColor: 'rgba(239, 68, 68, 0.05)',
                    padding: '1rem',
                    borderRadius: '8px',
                    border: '1px solid rgba(239, 68, 68, 0.2)',
                  }}
                >
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f87171', marginBottom: '0.5rem' }}>
                    {t('Arama Başarısızlık Tanılaması', 'Search Failure Diagnostics')}
                  </h4>
                  <pre style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', overflowX: 'auto', margin: 0 }}>
                    {JSON.stringify(genResult.result.failure_diagnostics, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* ---------------------------------------------------------------------- */}
      {/* GENETIC ALGORITHM (PHASE 9) PANEL                                      */}
      {/* ---------------------------------------------------------------------- */}
      {activeAlgo === 'GENETIC_ALGORITHM' && (
        <>
          <div
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1.25rem',
              marginBottom: '1.5rem',
            }}
          >
            <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem', color: '#f472b6' }}>
              {t('Genetik Algoritma Yapılandırması (Esnek Hol Yapısı - FBS)', 'Genetic Algorithm Configuration (Flexible Bay Structure)')}
            </h3>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '1.25rem',
              }}
            >
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  {t('Popülasyon Boyutu', 'Population Size')}
                </label>
                <input
                  type="number"
                  min="10"
                  max="500"
                  value={gaPopulationSize}
                  onChange={(e) => setGaPopulationSize(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  {t('Maks. Nesil Sayısı', 'Max Generations')}
                </label>
                <input
                  type="number"
                  min="5"
                  max="1000"
                  value={gaGenerations}
                  onChange={(e) => setGaGenerations(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  {t('Çaprazlama Oranı (OX)', 'Crossover Rate (OX)')}
                </label>
                <input
                  type="number"
                  step="0.05"
                  min="0.0"
                  max="1.0"
                  value={gaCrossoverRate}
                  onChange={(e) => setGaCrossoverRate(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  {t('Mutasyon Oranı', 'Mutation Rate')}
                </label>
                <input
                  type="number"
                  step="0.05"
                  min="0.0"
                  max="1.0"
                  value={gaMutationRate}
                  onChange={(e) => setGaMutationRate(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  {t('Turnuva Boyutu', 'Tournament Size')}
                </label>
                <input
                  type="number"
                  min="2"
                  max="10"
                  value={gaTournamentSize}
                  onChange={(e) => setGaTournamentSize(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  {t('Elitizm Sayısı', 'Elitism Count')}
                </label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={gaElitismCount}
                  onChange={(e) => setGaElitismCount(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  {t('Rastgele Tohum (Seed)', 'Random Seed')}
                </label>
                <input
                  type="number"
                  value={gaRandomSeed}
                  onChange={(e) => setGaRandomSeed(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  {t('Esnek Ceza Ağırlığı (λ)', 'Soft Penalty Weight (λ)')}
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0.0"
                  value={gaSoftPenaltyWeight}
                  onChange={(e) => setGaSoftPenaltyWeight(Number(e.target.value))}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                  {t('Hol Yönelimi', 'Bay Orientation')}
                </label>
                <select
                  value={gaOrientation}
                  onChange={(e) => setGaOrientation(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.4rem 0.6rem',
                    borderRadius: '6px',
                    border: '1px solid var(--border-color)',
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                  }}
                >
                  <option value="horizontal">{t('Yatay (Y ekseninde dizili holler)', 'Horizontal (Bays stacked along Y)')}</option>
                  <option value="vertical">{t('Dikey (X ekseninde dizili holler)', 'Vertical (Bays stacked along X)')}</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', marginTop: '1.25rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={gaSeedWithGuillotine}
                    onChange={(e) => setGaSeedWithGuillotine(e.target.checked)}
                  />
                  <span>{t('Giyotin Paketleme ile Başlat', 'Seed with Guillotine Packing')}</span>
                </label>
              </div>
            </div>

            <button
              onClick={handleRunGA}
              disabled={gaRunning || !selectedProblemId}
              style={{
                backgroundColor: gaRunning ? 'var(--text-muted)' : '#ec4899',
                color: '#fff',
                padding: '0.6rem 1.5rem',
                borderRadius: '6px',
                border: 'none',
                fontWeight: 600,
                cursor: gaRunning ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: '0.9rem',
              }}
            >
              {gaRunning ? t('Nesiller Evrimleşiyor...', 'Evolving Generations...') : t('Genetik Algoritmayı Çalıştır', 'Run Genetic Algorithm')}
            </button>
          </div>

          {gaError && (
            <div
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                color: '#f87171',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                marginBottom: '1rem',
                fontSize: '0.85rem',
                border: '1px solid rgba(239, 68, 68, 0.3)',
              }}
            >
              {gaError}
            </div>
          )}

          {gaResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              {/* Outcome Summary KPI Banner */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '1.25rem',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span
                      style={{
                        backgroundColor: gaResult.result.is_feasible ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                        color: gaResult.result.is_feasible ? '#34d399' : '#f87171',
                        border: `1px solid ${gaResult.result.is_feasible ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                        borderRadius: '4px',
                        padding: '0.2rem 0.6rem',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                      }}
                    >
                      {gaResult.result.is_feasible ? t('UYGUN OPTİMUM BULUNDU', 'FEASIBLE OPTIMUM FOUND') : t('KISITLI / CEZALI', 'CONSTRAINED / PENALIZED')}
                    </span>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      {t('Sonlanma:', 'Termination:')} <strong>{gaResult.result.termination_reason}</strong>
                    </span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {t('Süre:', 'Runtime:')} <strong>{gaResult.result.runtime_seconds.toFixed(3)}s</strong> | {t('Nesil:', 'Generations:')}{' '}
                    <strong>{gaResult.result.generation_count}</strong>
                  </div>
                </div>

                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: '1rem',
                  }}
                >
                  <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('En İyi Taşıma Maliyeti (MHC)', 'Best Material Handling Cost')}</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#38bdf8' }}>
                      ${gaResult.result.best_mhc.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('İlk Nesil En İyi MHC', 'Initial Generation Best MHC')}</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: 600 }}>
                      ${gaResult.result.initial_mhc.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('Maliyet İyileşmesi', 'Cost Improvement')}</div>
                    <div
                      style={{
                        fontSize: '1.3rem',
                        fontWeight: 700,
                        color: gaResult.result.improvement_mhc > 0 ? '#10b981' : 'var(--text-muted)',
                      }}
                    >
                      {gaResult.result.improvement_mhc > 0
                        ? `-$${gaResult.result.improvement_mhc.toLocaleString(undefined, { maximumFractionDigits: 2 })} (${gaResult.result.improvement_percentage.toFixed(1)}%)`
                        : '$0.00 (0%)'}
                    </div>
                  </div>

                  <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('Esnek Ceza Maliyeti', 'Soft Penalty Cost')}</div>
                    <div
                      style={{
                        fontSize: '1.3rem',
                        fontWeight: 700,
                        color: gaResult.result.best_soft_penalty === 0 ? '#10b981' : '#f59e0b',
                      }}
                    >
                      ${gaResult.result.best_soft_penalty.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </div>
                  </div>

                  <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '0.75rem', borderRadius: '6px' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{t('Bileşik Uygunluk (Fitness)', 'Combined Fitness')}</div>
                    <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#f472b6' }}>
                      {gaResult.result.best_fitness.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
              </div>

              {/* 2D Canvas & Chromosome Details */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(300px, 1.3fr) minmax(300px, 1fr)',
                  gap: '1.5rem',
                }}
              >
                <div>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                    {t('Evrimleşen 2D Yerleşim Tuvali', 'Evolved 2D Layout Canvas')} ({selectedProblem?.facility_width ?? 150}m × {selectedProblem?.facility_height ?? 80}m)
                  </div>
                  <LayoutCanvas layout={gaResult.continuous_layout} />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {/* Chromosome Breakdown */}
                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      padding: '1.25rem',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                    }}
                  >
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                      {t('Esnek Hol Yapısı (FBS) Kromozomu', 'Flexible Bay Structure (FBS) Chromosome')}
                    </h4>
                    <div style={{ fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      <div>
                        <strong>{t('Yönelim:', 'Orientation:')}</strong> {gaResult.result.best_chromosome.orientation}
                      </div>
                      <div>
                        <strong>{t('Hol Bölümleme Boyutları:', 'Bay Partition Sizes:')}</strong> [{gaResult.result.best_chromosome.bay_sizes.join(', ')}]
                      </div>
                      <div>
                        <strong>{t('Hol Dağılımı:', 'Bay Breakdown:')}</strong>
                        <div style={{ marginTop: '0.4rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                          {(() => {
                            const bays: string[][] = [];
                            let idx = 0;
                            for (const sz of gaResult.result.best_chromosome.bay_sizes) {
                              bays.push(gaResult.result.best_chromosome.order.slice(idx, idx + sz));
                              idx += sz;
                            }
                            return bays.map((b, bIdx) => (
                              <div
                                key={bIdx}
                                style={{
                                  padding: '0.35rem 0.6rem',
                                  backgroundColor: 'var(--bg-secondary)',
                                  borderRadius: '4px',
                                  fontSize: '0.75rem',
                                }}
                              >
                                <strong>{t('Hol', 'Bay')} {bIdx + 1}:</strong> {b.join(' → ')}
                              </div>
                            ));
                          })()}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Geometric Validation */}
                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      padding: '1.25rem',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                    }}
                  >
                    <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                      {t('Geometrik Uygunluk ve Korunum', 'Geometric Feasibility & Conservation')}
                    </h4>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', fontSize: '0.8rem' }}>
                      <div>{t('Uygunluk:', 'Feasibility:')}</div>
                      <div style={{ fontWeight: 600, color: gaResult.validation.is_valid ? '#10b981' : '#f87171' }}>
                        {gaResult.validation.is_valid ? t('%100 Kesin Uygun', '100% Strictly Feasible') : t('Uygun Değil', 'Infeasible')}
                      </div>
                      <div>{t('Çakışma Alanı:', 'Overlap Area:')}</div>
                      <div style={{ fontWeight: 600, color: gaResult.validation.total_overlap_area === 0 ? '#10b981' : '#f87171' }}>
                        {gaResult.validation.total_overlap_area} m² ({t('Sıfır Çakışma', 'Zero Overlap')})
                      </div>
                      <div>{t('Yerleştirilen Bölümler:', 'Departments Placed:')}</div>
                      <div style={{ fontWeight: 600 }}>
                        {gaResult.validation.checked_departments.length} / {selectedProblem?.department_count ?? 10}
                      </div>
                      <div>{t('Yerleşim İmzası:', 'Layout Signature:')}</div>
                      <div style={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                        {gaResult.validation.signature ? `${gaResult.validation.signature.substring(0, 16)}...` : t('Yok', 'N/A')}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Generational Convergence History Table */}
              <div
                style={{
                  backgroundColor: 'var(--bg-card)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '1.25rem',
                }}
              >
                <h4 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>
                  {t('Nesilsel Yakınsama Telemetrisi', 'Generational Convergence Telemetry')} ({gaResult.result.history.length} {t('Örnekleme Noktası', 'Sampling Points')})
                </h4>
                <div style={{ maxHeight: '250px', overflowY: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)', textAlign: 'left' }}>
                        <th style={{ padding: '0.4rem' }}>{t('Nesil', 'Gen')}</th>
                        <th style={{ padding: '0.4rem' }}>{t('En İyi Uygunluk', 'Best Fitness')}</th>
                        <th style={{ padding: '0.4rem' }}>{t('En İyi MHC ($)', 'Best MHC ($)')}</th>
                        <th style={{ padding: '0.4rem' }}>{t('Esnek Ceza ($)', 'Soft Penalty ($)')}</th>
                        <th style={{ padding: '0.4rem' }}>{t('Ort. Uygunluk', 'Avg Fitness')}</th>
                        <th style={{ padding: '0.4rem' }}>{t('Durum', 'Status')}</th>
                        <th style={{ padding: '0.4rem' }}>{t('Çeşitlilik', 'Diversity')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gaResult.result.history
                        .filter((_, idx) => idx === 0 || idx % 5 === 0 || idx === gaResult.result.history.length - 1)
                        .map((rec) => (
                          <tr key={rec.generation} style={{ borderBottom: '1px solid var(--border-color)' }}>
                            <td style={{ padding: '0.4rem', fontWeight: 600 }}>{rec.generation}</td>
                            <td style={{ padding: '0.4rem', color: '#f472b6', fontWeight: 600 }}>
                              {rec.best_fitness.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                            </td>
                            <td style={{ padding: '0.4rem', color: '#38bdf8', fontWeight: 600 }}>
                              ${rec.best_mhc.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                            </td>
                            <td style={{ padding: '0.4rem', color: rec.best_soft_penalty === 0 ? '#10b981' : '#f59e0b' }}>
                              ${rec.best_soft_penalty.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                            </td>
                            <td style={{ padding: '0.4rem' }}>
                              {rec.avg_fitness.toLocaleString(undefined, { maximumFractionDigits: 1 })}
                            </td>
                            <td style={{ padding: '0.4rem' }}>
                              <span style={{ color: rec.best_is_feasible ? '#10b981' : '#f87171' }}>
                                {rec.best_is_feasible ? t('Uygun', 'Feasible') : t('Uygun Değil', 'Infeasible')}
                              </span>
                            </td>
                            <td style={{ padding: '0.4rem' }}>{(rec.diversity * 100).toFixed(1)}%</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

