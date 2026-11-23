import React, { useEffect, useState } from 'react';
import {
  FacilityLayoutProblem,
  ContinuousLayout,
  LayoutValidationResult,
  EvaluationReport,
} from '../types/api';
import {
  solveAdaptiveStrategy,
  solveGeneticAlgorithm,
  solveFeasibleGenerator,
  solveCRAFT,
  solveCORELAP,
  solveALDEP,
} from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import { formatCost } from '../utils/formatters';
import { calculateFlowMetrics, localizeBenchmarkText } from './cockpit/CockpitDataContext';
import { summarizeLayoutInfeasibility, summarizeSolverError } from '../utils/explainInfeasibility';

interface OptimizationWorkspaceCardProps {
  problem: FacilityLayoutProblem | null;
  currentLayout: ContinuousLayout | null;
  onSolutionGenerated: (
    layout: ContinuousLayout,
    validation?: LayoutValidationResult | null,
    evaluation?: EvaluationReport | null,
    metadata?: Record<string, any> | null
  ) => void;
  onNavigateToViewer: () => void;
  onPreviewOnCockpit?: () => void;
  onNavigateToPareto: () => void;
}

type AlgorithmType = 'adaptive' | 'ga' | 'craft' | 'feasible_generator' | 'corelap' | 'aldep';

type BatchStatus = 'idle' | 'waiting' | 'running' | 'done' | 'error';

interface BatchSolverRow {
  algoId: AlgorithmType;
  labelTr: string;
  labelEn: string;
  status: BatchStatus;
  placedCount: number;
  totalCount: number;
  missingFlows: number;
  isFeasible: boolean | null;
  isComparable: boolean;
  flowDistance: number | null;
  handlingCost: number | null;
  durationMs: number | null;
  layout: ContinuousLayout | null;
  validation: LayoutValidationResult | null;
  evaluation: EvaluationReport | null;
  startPlanLabel?: string;
  costDeltaPct?: number | null;
  plainReason?: string;
  misleadingNote?: string;
  errorDetails?: string;
}

const BATCH_ORDER: Array<{ algoId: AlgorithmType; labelTr: string; labelEn: string }> = [
  { algoId: 'feasible_generator', labelTr: 'Uygun Yerleşim Üretici', labelEn: 'Feasible Generator' },
  { algoId: 'ga', labelTr: 'Genetik Algoritma (GA)', labelEn: 'Genetic Algorithm (GA)' },
  { algoId: 'corelap', labelTr: 'CORELAP', labelEn: 'CORELAP' },
  { algoId: 'aldep', labelTr: 'ALDEP', labelEn: 'ALDEP' },
  { algoId: 'adaptive', labelTr: 'Adaptive Strategy Engine', labelEn: 'Adaptive Strategy Engine' },
  { algoId: 'craft', labelTr: 'CRAFT', labelEn: 'CRAFT' },
];

interface SeedCandidate {
  algoId: AlgorithmType;
  layout: ContinuousLayout;
  label: string;
  mhc: number;
  validation: LayoutValidationResult | null;
  evaluation: EvaluationReport | null;
  durationMs: number | null;
}

function pickBetterSeed(
  current: SeedCandidate | null,
  label: string,
  patch: Partial<BatchSolverRow>
): SeedCandidate | null {
  if (patch.isComparable && patch.layout && patch.handlingCost !== null && patch.handlingCost !== undefined && patch.algoId) {
    if (!current || patch.handlingCost < current.mhc) {
      return {
        algoId: patch.algoId,
        layout: patch.layout,
        label,
        mhc: patch.handlingCost,
        validation: patch.validation ?? null,
        evaluation: patch.evaluation ?? null,
        durationMs: patch.durationMs ?? null,
      };
    }
  }
  return current;
}

function extractViolationSummary(
  validation?: LayoutValidationResult | null,
  evaluation?: EvaluationReport | null
): string | undefined {
  const lines: string[] = [];
  if (validation?.errors && validation.errors.length > 0) {
    lines.push(...validation.errors.slice(0, 6));
  }
  if (evaluation?.hard_constraint_violations && evaluation.hard_constraint_violations.length > 0) {
    lines.push(...evaluation.hard_constraint_violations.slice(0, 4));
  } else if (evaluation?.constraint_violations && evaluation.constraint_violations.length > 0) {
    lines.push(...evaluation.constraint_violations.slice(0, 4).map((v) => v.description));
  }
  return lines.length > 0 ? Array.from(new Set(lines)).join('\n') : undefined;
}

interface AlgorithmInfo {
  name: string;
  categoryTr: string;
  categoryEn: string;
  descriptionTr: string;
  descriptionEn: string;
  supportedConditionsTr: string[];
  supportedConditionsEn: string[];
  assumptionsAndLimitationsTr: string[];
  assumptionsAndLimitationsEn: string[];
}

const ALGORITHM_DETAILS: Record<AlgorithmType, AlgorithmInfo> = {
  adaptive: {
    name: 'Adaptive Strategy Engine v1',
    categoryTr: 'Otonom Çoklu Yöntem Hattı',
    categoryEn: 'Autonomous Multi-Method Pipeline',
    descriptionTr: 'Problem parmak izini (Alan Kullanımı, En-Boy Oranı, Kesin/Esnek Kısıtlar) analiz ederek en uygun birincil ve yedek çözücü hattını çalıştırır.',
    descriptionEn: 'Analyzes structural problem fingerprint (density, aspect ratios, constraints) and executes tailored primary and fallback pipelines.',
    supportedConditionsTr: [
      'Tüm tesis doluluk rejimlerini destekler (düşük, orta, yüksek >=%80 kullanım).',
      'Sabit Konum, Ayrılmış Yasaklı Bölge ve sıkı En-Boy Oranı sınırlarını destekler.',
      'Kurucu arama tıkanıklık yaşadığında otomatik olarak Metasezgisel (GA) moduna geçer.',
    ],
    supportedConditionsEn: [
      'Handles all facility density regimes (low, moderate, high >=80%).',
      'Supports fixed departments, reserved spine corridors, and tight aspect bounds.',
      'Automatic fallback to metaheuristic when constructive search encounters dead-ends.',
    ],
    assumptionsAndLimitationsTr: [
      'Zaman bütçesi dahilinde birden fazla algoritma çalıştırır.',
      'Aday portföyü oluşturur ve çok amaçlı Pareto Baskınlık (Non-Dominated) sıralaması hesaplar.',
    ],
    assumptionsAndLimitationsEn: [
      'Executes multiple algorithm evaluations within time budget.',
      'Constructs candidate portfolio and computes multi-objective Pareto dominance.',
    ],
  },
  ga: {
    name: 'Genetic Algorithm v1 (Slicing Tree)',
    categoryTr: 'Stokastik Popülasyon Tabanlı Metasezgisel',
    categoryEn: 'Stochastic Population-Based Metaheuristic',
    descriptionTr: 'Dilimleme Ağacı (Slicing Tree) kromozom temsili, alan koruyucu Hol Çözümleme, Sıra Çaprazlama (OX) ve çoklu mutasyon operatörleri.',
    descriptionEn: 'Slicing-tree chromosome representation with area-preserving bay decoding, order crossover, and multi-operator mutation.',
    supportedConditionsTr: [
      'Sürekli 2D dikdörtgensel yerleşim temsili.',
      'Sıfır ikili çakışma ve tam alan korunumu garantisi.',
      'Esnek Kısıt Cezası rehberliği ile Malzeme Taşıma Maliyeti (MHC) minimizasyonu.',
    ],
    supportedConditionsEn: [
      'Continuous 2D rectangular layout representation.',
      'Guarantees zero pairwise overlap and exact area conservation.',
      'Minimizes Material Handling Cost (MHC) with soft penalty guidance.',
    ],
    assumptionsAndLimitationsTr: [
      'Küresel matematiksel optimalliği garanti etmez (Tesis Yerleşimi Problemi güçlü NP-Zor sınıfındadır).',
      'Değerlendirme bütçesi Popülasyon Boyutu × Nesil Sayısı ile doğrusal ölçeklenir.',
    ],
    assumptionsAndLimitationsEn: [
      'Does not guarantee global mathematical optimality (Facility Layout is strongly NP-hard).',
      'Evaluation budget scales linearly with population_size × generations.',
    ],
  },
  feasible_generator: {
    name: 'Feasible Rectangular Generator (Guillotine)',
    categoryTr: 'Deterministik Kurucu Paketleme',
    categoryEn: 'Deterministic Constructive Packing',
    descriptionTr: 'Giyotin Sıra Paketleme ve MaxRects yaklaşımlarıyla ham problem girdilerinden çakışmasız (uygun) dikdörtgen başlangıç yerleşimi üretir.',
    descriptionEn: 'Guillotine Row Packing constructive search establishing non-overlapping rectangular baselines from raw problem inputs.',
    supportedConditionsTr: [
      'Çok hızlı (<150 ms) deterministik uygun başlangıç yerleşimi üretimi.',
      'Esnek En-Boy Oranı sınırlarına sahip orta-yüksek yoğunluklu tesislerde idealdir.',
    ],
    supportedConditionsEn: [
      'Blazingly fast (<150 ms) deterministic baseline construction.',
      'Works best on moderate-to-high density facilities with flexible aspect ratios.',
    ],
    assumptionsAndLimitationsTr: [
      'Tek geçişli kurucu paketleme; geri izleme içermez.',
      'Aşırı yüksek dolulukta (>=%90) veya ayrılmış yasaklı bölgelerle bölünmüş tesislerde başarısız olabilir.',
    ],
    assumptionsAndLimitationsEn: [
      'Single-pass constructive search without recursive backtracking.',
      'Fails on extreme density (>=90%) or facilities bisected by reserved exclusion zones.',
    ],
  },
  craft: {
    name: 'CRAFT (Centroid Swapping Heuristic)',
    categoryTr: 'En Dik İniş İyileştirme Sezgisel Algoritması',
    categoryEn: 'Steepest-Descent Improvement Heuristic',
    descriptionTr: 'Bölüm ağırlık merkezlerinin ikili değişimi ile Malzeme Taşıma Maliyeti (MHC) düşüşünü değerlendirir.',
    descriptionEn: 'Pairwise department centroid exchange evaluating material handling cost deltas.',
    supportedConditionsTr: [
      'Mevcut ve uygun bir başlangıç yerleşimi gerektirir.',
      'Akış-Mesafe maliyetini azaltmak için ikili koordinat takaslarını değerlendirir.',
    ],
    supportedConditionsEn: [
      'Requires an existing feasible starting baseline layout.',
      'Evaluates pairwise coordinate exchanges to reduce flow-distance costs.',
    ],
    assumptionsAndLimitationsTr: [
      'Yerel optimumlara takılmaya açıktır.',
      'Farklı alana sahip bölümlerin takası kesikli ızgaralarda düzensiz şekiller üretebilir.',
    ],
    assumptionsAndLimitationsEn: [
      'Susceptible to local optima entrapment.',
      'Swapping unequal department areas can produce non-rectangular shapes in discrete grids.',
    ],
  },
  corelap: {
    name: 'CORELAP (Total Closeness Rating)',
    categoryTr: 'Açgözlü Kurucu Sezgisel',
    categoryEn: 'Greedy Constructive Heuristic',
    descriptionTr: 'SLP REL Matrisi üzerinden hesaplanan Toplam Yakınlık Puanlarına (TCR) göre bölümleri sırayla yerleştiren kurucu sezgisel.',
    descriptionEn: 'Constructive algorithm placing departments sequentially based on Total Closeness Rating (TCR) computed from the REL matrix.',
    supportedConditionsTr: [
      'Niteliksel Sistematik Yerleşim Planlaması (SLP — A, E, I, O, U, X) odaklıdır.',
      'En yüksek TCR puanına sahip bölümü tesis merkezine ilk olarak yerleştirir.',
    ],
    supportedConditionsEn: [
      'Qualitative Systematic Layout Planning (SLP) driven.',
      'Places highest TCR department first at layout center.',
    ],
    assumptionsAndLimitationsTr: [
      'Eşitlik bozma sırasına duyarlıdır.',
      'Doğrudan niceliksel Akış-Mesafe (MHC) maliyetini en küçüklemez.',
    ],
    assumptionsAndLimitationsEn: [
      'Sensitive to placement tie-breaking order.',
      'Does not natively minimize quantitative flow-distance costs.',
    ],
  },
  aldep: {
    name: 'ALDEP (Automated Layout Design Program)',
    categoryTr: 'Stokastik Şerit Tarama Kurucu Sezgiseli',
    categoryEn: 'Stochastic Strip-Sweep Constructive Heuristic',
    descriptionTr: 'Yakınlık eşik değerine göre rastgele bölüm seçimi ve dikey şerit tarama (yılankavi şerit) yerleşimi.',
    descriptionEn: 'Randomized department selection and continuous snake-like strip sweep placement based on relationship cutoff threshold.',
    supportedConditionsTr: [
      'Stokastik çoklu deneme ile çeşitli alternatif yerleşimler üretir.',
    ],
    supportedConditionsEn: [
      'Generates diverse candidate alternatives via stochastic multi-trial sweep.',
    ],
    assumptionsAndLimitationsTr: [
      'Sabit şerit genişliği kesikli ızgaralarda ince uzun veya düzensiz şekiller oluşturabilir.',
    ],
    assumptionsAndLimitationsEn: [
      'Fixed sweep width can produce elongated or irregular shapes in discrete grids.',
    ],
  },
};

export const OptimizationWorkspaceCard: React.FC<OptimizationWorkspaceCardProps> = ({
  problem,
  currentLayout,
  onSolutionGenerated,
  onNavigateToViewer,
  onPreviewOnCockpit,
  onNavigateToPareto,
}) => {
  const { lang, t } = useLanguage();
  const [selectedAlgo, setSelectedAlgo] = useState<AlgorithmType>('adaptive');
  const [randomSeed, setRandomSeed] = useState<number>(42);
  const [timeBudget, setTimeBudget] = useState<number>(10.0);
  const [populationSize, setPopulationSize] = useState<number>(30);
  const [maxGenerations, setMaxGenerations] = useState<number>(25);

  const [solving, setSolving] = useState<boolean>(false);
  const [batchRunning, setBatchRunning] = useState<boolean>(false);
  const [shownAlgoId, setShownAlgoId] = useState<AlgorithmType | null>(null);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [executionStatus, setExecutionStatus] = useState<string>(() => t('Hazır', 'Ready'));
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [failureNotice, setFailureNotice] = useState<{ reason: string; partial: boolean; fallback: string } | null>(null);
  const [lastResultMetrics, setLastResultMetrics] = useState<any | null>(null);

  const buildInitialRows = (totalDepts: number): BatchSolverRow[] =>
    BATCH_ORDER.map((item) => ({
      algoId: item.algoId,
      labelTr: item.labelTr,
      labelEn: item.labelEn,
      status: 'idle',
      placedCount: 0,
      totalCount: totalDepts,
      missingFlows: 0,
      isFeasible: null,
      isComparable: false,
      flowDistance: null,
      handlingCost: null,
      durationMs: null,
      layout: null,
      validation: null,
      evaluation: null,
    }));

  const [batchRows, setBatchRows] = useState<BatchSolverRow[]>(() =>
    buildInitialRows(problem?.departments?.length ?? 0)
  );

  useEffect(() => {
    setBatchRows(buildInitialRows(problem?.departments?.length ?? 0));
    setShownAlgoId(null);
    setErrorMsg(null);
    setFailureNotice(null);
    setLastResultMetrics(null);
  }, [problem?.id]);

  if (!problem) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
        <p style={{ color: 'var(--text-muted)' }}>
          {t('Optimizasyon Çalışma Alanına erişmek için bir problem yükleyin veya oluşturun.', 'Load or create a problem to access the Optimization Workspace.')}
        </p>
      </div>
    );
  }

  const currentAlgoInfo = ALGORITHM_DETAILS[selectedAlgo];

  // Execute the selected algorithm
  const handleRunOptimization = async () => {
    setSolving(true);
    setErrorMsg(null);
    setFailureNotice(null);
    setLastResultMetrics(null);
    setExecutionStatus(t(`${currentAlgoInfo.name} çalıştırılıyor...`, `Running ${currentAlgoInfo.name}...`));
    const t0 = performance.now();

    try {
      if (selectedAlgo === 'adaptive') {
        const res = await solveAdaptiveStrategy({
          problem_id: problem.id,
          problem: problem,
          config: {
            random_seed: randomSeed,
            max_total_runtime_seconds: timeBudget,
            ga_population_size: populationSize,
            ga_generations: maxGenerations,
          },
        });
        const t1 = performance.now();
        setElapsedMs(Math.round(t1 - t0));

        const bestLayout = res.best_continuous_layout || (res.candidate_portfolio?.items?.find((it: any) => it.feasibility)?.solution as any)?.continuous_layout || null;
        const totalCandidates = res.candidate_portfolio?.total_candidates_generated ?? res.candidate_portfolio?.items?.length ?? 0;
        const isFeas = res.is_feasible ?? res.feasible_status;
        const execStatus = res.execution_status || 'COMPLETED';
        const valStatus = res.validation_status || (isFeas ? 'FEASIBLE' : 'INFEASIBLE');

        if (!isFeas || !bestLayout) {
          setFailureNotice({
            reason: res.failure_reason || res.termination_reason || t('Adaptive Strategy geçerli (Feasible) bir yerleşim bulamadı.', 'Adaptive strategy could not find a feasible layout.'),
            partial: totalCandidates > 0,
            fallback: t('Zaman bütçesini artırmayı veya Problem Editöründe Aspect Ratio sınırlarını esnetmeyi deneyin.', 'Try increasing the time budget or relaxing aspect ratio bounds in Problem Editor.'),
          });
          setExecutionStatus(`${execStatus} (${valStatus})`);
        } else {
          const rec = res.final_recommendation || {};
          setLastResultMetrics({
            is_feasible: true,
            mhc: rec.material_handling_cost,
            rel: rec.relationship_satisfaction,
            soft_penalty: rec.soft_penalty,
            algorithm: res.selected_strategy?.name || 'Adaptive Pipeline',
            evaluations: res.total_algorithm_calls,
          });
          onSolutionGenerated(bestLayout, res.best_validation || null, res.best_evaluation || null, {
            algorithm: res.selected_strategy?.name,
            seed: randomSeed,
            duration_ms: t1 - t0,
            termination_reason: res.termination_reason,
            execution_status: execStatus,
            validation_status: valStatus,
          });
          setExecutionStatus(t('Başarılı: Feasible Çözüm Bulundu', 'Success: Feasible Solution Found'));
        }
      } else if (selectedAlgo === 'ga') {
        const res = await solveGeneticAlgorithm({
          problem_id: problem.id,
          problem: problem,
          config: {
            population_size: populationSize,
            generations: maxGenerations,
            random_seed: randomSeed,
            max_runtime_seconds: timeBudget,
          },
        });
        const t1 = performance.now();
        setElapsedMs(Math.round(t1 - t0));

        if (!res.validation?.is_valid || !res.continuous_layout) {
          setFailureNotice({
            reason: t('Genetic Algorithm tam Feasible bir kromozom bulamadan sonlandı.', 'Genetic search terminated without finding a fully feasible chromosome.'),
            partial: res.continuous_layout !== null,
            fallback: t('Slicing Tree arama uzayını genişletmek için Population Size veya Generations değerini artırın.', 'Increase population size or generations to expand slicing-tree exploration.'),
          });
          setExecutionStatus(t('Tamamlandı (Infeasible)', 'Algorithm Completed (Infeasible)'));
        } else {
          const mhcVal = res.evaluation?.material_handling_cost ?? res.evaluation?.objective_values?.material_handling_cost;
          const relVal = res.evaluation?.relationship_satisfaction_percentage ?? res.evaluation?.objective_values?.relationship_satisfaction;
          const softVal = res.evaluation?.soft_penalty ?? res.evaluation?.soft_constraint_penalty ?? res.evaluation?.total_constraint_penalty;

          setLastResultMetrics({
            is_feasible: true,
            mhc: mhcVal,
            rel: relVal,
            soft_penalty: softVal,
            algorithm: 'Genetic Algorithm v1',
            evaluations: (res.result?.generation_count || 1) * populationSize,
          });
          onSolutionGenerated(res.continuous_layout, res.validation, res.evaluation, {
            algorithm: 'Genetic Algorithm v1',
            seed: randomSeed,
            duration_ms: t1 - t0,
          });
          setExecutionStatus(t('Başarılı: Feasible Çözüm Bulundu', 'Success: Feasible Solution Found'));
        }
      } else if (selectedAlgo === 'feasible_generator') {
        const res = await solveFeasibleGenerator({
          problem_id: problem.id,
          problem: problem,
          config: {
            random_seed: randomSeed,
            max_runtime_seconds: timeBudget,
          },
        });
        const t1 = performance.now();
        setElapsedMs(Math.round(t1 - t0));

        const layoutObj = res.result?.layout || res.continuous_layout;
        if (!res.result?.feasible || !layoutObj) {
          setFailureNotice({
            reason: res.result?.termination_reason || t('Guillotine Row Packing tüm departmanları Aspect Ratio sınırları içinde sığdıramadı.', 'Guillotine Row Packing could not fit all departments within aspect bounds.'),
            partial: false,
            fallback: t('Recursive Slicing kullanan Genetic Algorithm veya Adaptive Strategy moduna geçin.', 'Switch to Genetic Algorithm or Adaptive Mode which use recursive slicing.'),
          });
          setExecutionStatus(t('Constructive Arama Başarısız', 'Constructive Search Failed'));
        } else {
          const mhcVal = res.evaluation?.material_handling_cost ?? res.evaluation?.objective_values?.material_handling_cost;
          const relVal = res.evaluation?.relationship_satisfaction_percentage ?? res.evaluation?.objective_values?.relationship_satisfaction;
          const softVal = res.evaluation?.soft_penalty ?? res.evaluation?.soft_constraint_penalty ?? res.evaluation?.total_constraint_penalty;

          setLastResultMetrics({
            is_feasible: true,
            mhc: mhcVal,
            rel: relVal,
            soft_penalty: softVal,
            algorithm: 'Feasible Rectangular Generator (Guillotine)',
            evaluations: 1,
          });
          onSolutionGenerated(layoutObj, res.validation, res.evaluation, {
            algorithm: 'Feasible Rectangular Generator (Guillotine)',
            seed: randomSeed,
            duration_ms: t1 - t0,
          });
          setExecutionStatus(t('Başarılı: Feasible Yerleşim Üretildi', 'Success: Feasible Layout Generated'));
        }
      } else if (selectedAlgo === 'craft') {
        const res = await solveCRAFT({
          problem_id: problem.id,
          problem: problem,
          initial_layout: currentLayout ? { placements: currentLayout.placements, facility_width: currentLayout.facility_width, facility_height: currentLayout.facility_height } : undefined,
          config: {
            max_iterations: maxGenerations,
          },
        });
        const t1 = performance.now();
        setElapsedMs(Math.round(t1 - t0));

        const mhcVal = res.final_evaluation?.material_handling_cost ?? res.final_evaluation?.objective_values?.material_handling_cost;
        const initMhcVal = res.initial_evaluation?.material_handling_cost ?? res.initial_evaluation?.objective_values?.material_handling_cost;
        const relVal = res.final_evaluation?.relationship_satisfaction_percentage ?? res.final_evaluation?.objective_values?.relationship_satisfaction;
        const softVal = res.final_evaluation?.soft_penalty ?? res.final_evaluation?.soft_constraint_penalty ?? res.final_evaluation?.total_constraint_penalty;
        const deltaPct = initMhcVal && initMhcVal > 0 && Number.isFinite(mhcVal)
          ? ((Number(mhcVal) - Number(initMhcVal)) / Number(initMhcVal)) * 100
          : null;

        setLastResultMetrics({
          is_feasible: res.solution?.feasibility_status ?? res.final_evaluation?.is_feasible,
          mhc: mhcVal,
          rel: relVal,
          soft_penalty: softVal,
          algorithm: t(
            `CRAFT · Başlangıç: ${currentLayout?.name || 'Aktif Plan'}${deltaPct !== null ? ` · Maliyet farkı: %${deltaPct.toFixed(1)}` : ''}`,
            `CRAFT · Seed: ${currentLayout?.name || 'Active Plan'}${deltaPct !== null ? ` · Cost delta: ${deltaPct.toFixed(1)}%` : ''}`
          ),
          evaluations: res.trace?.total_iterations || 1,
        });
        onSolutionGenerated(res.continuous_layout, null, res.final_evaluation, {
          algorithm: 'CRAFT',
          duration_ms: t1 - t0,
        });
        setExecutionStatus(t('Başarılı: CRAFT Optimizasyonu Tamamlandı', 'Success: CRAFT Optimization Finished'));
      } else if (selectedAlgo === 'corelap') {
        const res = await solveCORELAP({
          problem_id: problem.id,
          problem: problem,
        });
        const t1 = performance.now();
        setElapsedMs(Math.round(t1 - t0));

        const isFeas = res.validation?.is_valid && res.trace?.execution_success;
        if (!isFeas) {
          setFailureNotice({
            reason: res.trace?.failure_reason || t('CORELAP sezgisel algoritması çakışmalı veya eksik yerleşim üretti.', 'CORELAP heuristic produced overlapping or incomplete placements.'),
            partial: res.trace?.placed_count > 0,
            fallback: t('Garantili Feasible yerleşim için Feasible Generator, Genetic Algorithm veya Adaptive Mode kullanın.', 'Use Feasible Generator, Genetic Algorithm, or Adaptive Mode for guaranteed feasibility.'),
          });
          setExecutionStatus(t('CORELAP: Uygun Olmayan Temel Yerleşim', 'CORELAP Infeasible Baseline'));
        } else {
          setExecutionStatus(t('Başarılı: CORELAP Yerleştirildi', 'Success: CORELAP Placed'));
        }

        const mhcVal = res.evaluation?.material_handling_cost ?? res.evaluation?.objective_values?.material_handling_cost;
        const relVal = res.evaluation?.relationship_satisfaction_percentage ?? res.evaluation?.objective_values?.relationship_satisfaction;
        const softVal = res.evaluation?.soft_penalty ?? res.evaluation?.soft_constraint_penalty ?? res.evaluation?.total_constraint_penalty;

        setLastResultMetrics({
          is_feasible: isFeas,
          mhc: mhcVal,
          rel: relVal,
          soft_penalty: softVal,
          algorithm: 'CORELAP',
        });
        onSolutionGenerated(res.continuous_layout, res.validation, res.evaluation, {
          algorithm: 'CORELAP',
          duration_ms: t1 - t0,
        });
      } else if (selectedAlgo === 'aldep') {
        const res = await solveALDEP({
          problem_id: problem.id,
          problem: problem,
        });
        const t1 = performance.now();
        setElapsedMs(Math.round(t1 - t0));

        const isFeas = Boolean(res.validation?.is_valid);
        const localResMetrics = res.continuous_layout ? calculateFlowMetrics(problem, res.continuous_layout, problem.objective_config) : null;
        const infSummary = !isFeas
          ? summarizeLayoutInfeasibility(problem, res.continuous_layout || null, res.validation, res.evaluation, localResMetrics?.missingFlows ?? 0, t)
          : null;
        if (!isFeas && infSummary && infSummary.status !== 'feasible') {
          setFailureNotice({
            reason: `${infSummary.headline}: ${infSummary.reasons.join(' ')} ${infSummary.misleadingCostNote}`,
            partial: (res.continuous_layout ? Object.keys(res.continuous_layout.placements).length : 0) < problem.departments.length,
            fallback: t('Gerçekçi ve kısıtlara uygun bir yerleşim için Genetik Algoritma veya Adaptive Strategy kullanın.', 'Use Genetic Algorithm or Adaptive Strategy for a valid buildable layout.'),
          });
        }
        const mhcVal = res.evaluation?.material_handling_cost ?? res.evaluation?.objective_values?.material_handling_cost;
        const relVal = res.evaluation?.relationship_satisfaction_percentage ?? res.evaluation?.objective_values?.relationship_satisfaction;
        const softVal = res.evaluation?.soft_penalty ?? res.evaluation?.soft_constraint_penalty ?? res.evaluation?.total_constraint_penalty;

        setLastResultMetrics({
          is_feasible: isFeas,
          mhc: mhcVal,
          rel: relVal,
          soft_penalty: softVal,
          algorithm: 'ALDEP',
        });
        onSolutionGenerated(res.continuous_layout, res.validation, res.evaluation, {
          algorithm: 'ALDEP',
          duration_ms: t1 - t0,
        });
        setExecutionStatus(isFeas ? t('Başarılı: ALDEP Tamamlandı', 'Success: ALDEP Completed') : t('ALDEP Tamamlandı (Uygun Değil)', 'ALDEP Completed (Infeasible)'));
      }
    } catch (err: any) {
      const t1 = performance.now();
      setElapsedMs(Math.round(t1 - t0));
      setErrorMsg(err.message || t('Optimizasyon çalıştırılamadı.', 'Optimization execution failed.'));
      setExecutionStatus(t('Çalıştırma Hatası', 'Execution Error'));
    } finally {
      setSolving(false);
    }
  };

  const computeRowPatch = (
    algoId: AlgorithmType,
    layoutObj: ContinuousLayout | null,
    validationObj: LayoutValidationResult | null,
    evaluationObj: EvaluationReport | null,
    durationMs: number,
    explicitFeasible?: boolean | null,
    extraNote?: string
  ): Partial<BatchSolverRow> => {
    const totalCount = problem.departments.length;
    const placedCount = layoutObj ? Object.keys(layoutObj.placements).length : 0;
    const localMetrics = layoutObj ? calculateFlowMetrics(problem, layoutObj, problem.objective_config) : null;
    const missingFlows = localMetrics?.missingFlows ?? problem.flows.length;

    const evalMhc =
      evaluationObj?.material_handling_cost ??
      evaluationObj?.objective_values?.material_handling_cost ??
      evaluationObj?.diagnostic_partial_values?.partial_material_handling_cost;
    const evalDist =
      evaluationObj?.flow_distance ??
      evaluationObj?.objective_values?.flow_distance ??
      evaluationObj?.diagnostic_partial_values?.partial_flow_distance;

    const handlingCost = Number.isFinite(evalMhc)
      ? Number(evalMhc)
      : (localMetrics ? localMetrics.handlingCost : null);
    const flowDistance = Number.isFinite(evalDist)
      ? Number(evalDist)
      : (localMetrics ? localMetrics.flowDistance : null);

    const isComplete = placedCount >= totalCount && missingFlows === 0;
    const rawFeasible =
      explicitFeasible !== undefined && explicitFeasible !== null
        ? explicitFeasible
        : (validationObj?.is_valid ?? evaluationObj?.is_feasible ?? false);
    const isFeasible = Boolean(isComplete && rawFeasible);
    const isComparable = Boolean(isComplete && isFeasible && handlingCost !== null);

    const inf = layoutObj
      ? summarizeLayoutInfeasibility(problem, layoutObj, validationObj, evaluationObj, missingFlows, t)
      : null;

    const plainReason = !layoutObj
      ? summarizeSolverError(extraNote || '', t)
      : !isComparable && inf && inf.status !== 'feasible'
        ? inf.reasons[0]
        : undefined;

    const misleadingNote = !isComparable && layoutObj && inf && inf.status !== 'feasible'
      ? inf.misleadingCostNote
      : undefined;

    const errorDetails = [extraNote, extractViolationSummary(validationObj, evaluationObj)]
      .filter(Boolean)
      .join('\n') || undefined;

    return {
      status: 'done',
      placedCount,
      totalCount,
      missingFlows,
      isFeasible,
      isComparable,
      flowDistance,
      handlingCost,
      durationMs,
      layout: layoutObj,
      validation: validationObj,
      evaluation: evaluationObj,
      plainReason,
      misleadingNote,
      errorDetails,
      algoId,
    };
  };

  const handleRunAllMethods = async () => {
    if (!problem || batchRunning || solving) return;
    const runProblem = problem;
    setBatchRunning(true);
    setErrorMsg(null);
    setFailureNotice(null);
    setBatchRows(
      BATCH_ORDER.map((item) => ({
        algoId: item.algoId,
        labelTr: item.labelTr,
        labelEn: item.labelEn,
        status: 'waiting',
        placedCount: 0,
        totalCount: runProblem.departments.length,
        missingFlows: 0,
        isFeasible: null,
        isComparable: false,
        flowDistance: null,
        handlingCost: null,
        durationMs: null,
        layout: null,
        validation: null,
        evaluation: null,
      }))
    );

    const updateRow = (algoId: AlgorithmType, patch: Partial<BatchSolverRow>) => {
      setBatchRows((prev) => prev.map((r) => (r.algoId === algoId ? { ...r, ...patch } : r)));
    };

    let bestSeed: SeedCandidate | null = null;

    for (const item of BATCH_ORDER) {
      updateRow(item.algoId, { status: 'running' });
      const t0 = performance.now();
      try {
        if (item.algoId === 'feasible_generator') {
          const res = await solveFeasibleGenerator({
            problem_id: runProblem.id,
            problem: runProblem,
            config: { random_seed: randomSeed, max_runtime_seconds: timeBudget },
          });
          const layoutObj = res.result?.layout || res.continuous_layout || null;
          const patch = computeRowPatch(
            item.algoId,
            layoutObj,
            res.validation || null,
            res.evaluation || null,
            Math.round(performance.now() - t0),
            res.result?.feasible && res.validation?.is_valid !== false,
            res.result?.termination_reason
          );
          bestSeed = pickBetterSeed(bestSeed, t(item.labelTr, item.labelEn), patch);
          updateRow(item.algoId, patch);
        } else if (item.algoId === 'ga') {
          const res = await solveGeneticAlgorithm({
            problem_id: runProblem.id,
            problem: runProblem,
            config: {
              population_size: populationSize,
              generations: maxGenerations,
              random_seed: randomSeed,
              max_runtime_seconds: timeBudget,
            },
          });
          const patch = computeRowPatch(
            item.algoId,
            res.continuous_layout || null,
            res.validation || null,
            res.evaluation || null,
            Math.round(performance.now() - t0),
            Boolean(res.validation?.is_valid && res.evaluation?.is_feasible !== false)
          );
          bestSeed = pickBetterSeed(bestSeed, t(item.labelTr, item.labelEn), patch);
          updateRow(item.algoId, patch);
        } else if (item.algoId === 'corelap') {
          const res = await solveCORELAP({ problem_id: runProblem.id, problem: runProblem });
          const patch = computeRowPatch(
            item.algoId,
            res.continuous_layout || null,
            res.validation || null,
            res.evaluation || null,
            Math.round(performance.now() - t0),
            Boolean(res.validation?.is_valid && res.trace?.execution_success),
            res.trace?.failure_reason || undefined
          );
          bestSeed = pickBetterSeed(bestSeed, t(item.labelTr, item.labelEn), patch);
          updateRow(item.algoId, patch);
        } else if (item.algoId === 'aldep') {
          const res = await solveALDEP({ problem_id: runProblem.id, problem: runProblem });
          const patch = computeRowPatch(
            item.algoId,
            res.continuous_layout || null,
            res.validation || null,
            res.evaluation || null,
            Math.round(performance.now() - t0),
            Boolean(res.validation?.is_valid && res.evaluation?.is_feasible !== false)
          );
          bestSeed = pickBetterSeed(bestSeed, t(item.labelTr, item.labelEn), patch);
          updateRow(item.algoId, patch);
        } else if (item.algoId === 'adaptive') {
          const res = await solveAdaptiveStrategy({
            problem_id: runProblem.id,
            problem: runProblem,
            config: {
              random_seed: randomSeed,
              max_total_runtime_seconds: timeBudget,
              ga_population_size: populationSize,
              ga_generations: maxGenerations,
            },
          });
          const bestLayout =
            res.best_continuous_layout ||
            (res.candidate_portfolio?.items?.find((it: any) => it.feasibility)?.solution as any)?.continuous_layout ||
            null;
          const patch = computeRowPatch(
            item.algoId,
            bestLayout,
            res.best_validation || null,
            res.best_evaluation || null,
            Math.round(performance.now() - t0),
            Boolean(res.is_feasible ?? res.feasible_status),
            res.failure_reason || undefined
          );
          bestSeed = pickBetterSeed(bestSeed, t(item.labelTr, item.labelEn), patch);
          updateRow(item.algoId, patch);
        } else if (item.algoId === 'craft') {
          const seedForCraft = bestSeed;
          const chosenSeed = seedForCraft?.layout ?? (currentLayout?.problem_id === runProblem.id ? currentLayout : null);
          const seedLabel = seedForCraft
            ? seedForCraft.label
            : chosenSeed
              ? t('Aktif kokpit planı', 'Active cockpit plan')
              : t('Otomatik başlangıç', 'Auto initial');
          const seedBaselineMhc = seedForCraft
            ? seedForCraft.mhc
            : chosenSeed
              ? calculateFlowMetrics(runProblem, chosenSeed, runProblem.objective_config).handlingCost
              : null;

          const res = await solveCRAFT({
            problem_id: runProblem.id,
            problem: runProblem,
            initial_layout: chosenSeed
              ? {
                  placements: chosenSeed.placements,
                  facility_width: chosenSeed.facility_width,
                  facility_height: chosenSeed.facility_height,
                }
              : undefined,
            config: { max_iterations: maxGenerations },
          });
          const patch = computeRowPatch(
            item.algoId,
            res.continuous_layout || null,
            null,
            res.final_evaluation || null,
            Math.round(performance.now() - t0),
            Boolean(res.final_evaluation?.is_feasible ?? res.solution?.feasibility_status)
          );
          const finalCost = patch.handlingCost;
          const costDeltaPct =
            seedBaselineMhc && seedBaselineMhc > 0 && finalCost !== null && finalCost !== undefined
              ? ((finalCost - seedBaselineMhc) / seedBaselineMhc) * 100
              : null;
          bestSeed = pickBetterSeed(bestSeed, t(item.labelTr, item.labelEn), patch);
          updateRow(item.algoId, {
            ...patch,
            startPlanLabel: seedLabel,
            costDeltaPct,
          });
        }
      } catch (err: any) {
        const rawMsg = err?.message || '';
        updateRow(item.algoId, {
          status: 'error',
          durationMs: Math.round(performance.now() - t0),
          isFeasible: false,
          isComparable: false,
          plainReason: summarizeSolverError(rawMsg, t),
          errorDetails: rawMsg || t('Çözücü çalıştırılamadı', 'Solver execution failed'),
        });
      }
    }
    if (bestSeed) {
      setShownAlgoId(bestSeed.algoId);
      onSolutionGenerated(bestSeed.layout, bestSeed.validation, bestSeed.evaluation, {
        algorithm: bestSeed.label,
        seed: randomSeed,
        duration_ms: bestSeed.durationMs ?? undefined,
      });
    }
    setBatchRunning(false);
  };

  const minComparableMhc = React.useMemo(() => {
    const vals = batchRows
      .filter((r) => r.status === 'done' && r.isComparable && r.handlingCost !== null)
      .map((r) => r.handlingCost as number);
    return vals.length > 0 ? Math.min(...vals) : null;
  }, [batchRows]);

  const supportedConditions = lang === 'tr' ? currentAlgoInfo.supportedConditionsTr : currentAlgoInfo.supportedConditionsEn;
  const assumptions = lang === 'tr' ? currentAlgoInfo.assumptionsAndLimitationsTr : currentAlgoInfo.assumptionsAndLimitationsEn;

  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      borderRadius: '12px',
      border: '1px solid var(--border-color)',
      padding: '1.75rem',
      marginBottom: '2rem',
    }}>
      <div style={{ marginBottom: '1.25rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
          {t('Optimizasyon Çalıştırma Alanı (Heuristics & Metaheuristics)', 'Optimization Execution Workspace')}
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>
          {t(
            '5 Kayıtlı Temel Çözücü (CORELAP, ALDEP, CRAFT, Feasible Generator, Genetic Algorithm) + 1 Otonom Orkestrasyon Hattı (Adaptive Strategy Engine).',
            '5 Registered Base Solvers (CORELAP, ALDEP, CRAFT, Feasible Generator, Genetic Algorithm) + 1 Autonomous Orchestration Pipeline (Adaptive Strategy Engine).'
          )}
        </p>
        <div className="problem-context-banner">
          <strong>{problem.departments.length} {t('bölüm', 'depts')}</strong>
          <span>·</span>
          <strong>{(problem.facility.width * problem.facility.height).toLocaleString()} m²</strong>
          <span>·</span>
          <span>{localizeBenchmarkText(problem.name, t)} ({problem.id})</span>
        </div>
      </div>

      {/* Batch Multi-Solver Comparison Card */}
      <div style={{
        backgroundColor: 'var(--bg-card)',
        borderRadius: '10px',
        border: '1px solid var(--border-color)',
        padding: '1.15rem',
        marginBottom: '1.5rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.9rem' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {t('Tüm Yöntemleri Tek Ekranda Karşılaştır', 'Compare All Solvers in One Table')}
            </h3>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              {t(
                '6 yöntemi seçili problemde sırayla çalıştırır; ilk sütunda uygunluğu doğrular ve kısmi/uygun olmayan sonuçları açıkça ayırır.',
                'Runs 6 solvers sequentially on the active problem, putting feasibility first and flagging partial/infeasible outputs.'
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={handleRunAllMethods}
            disabled={batchRunning || solving}
            style={{
              padding: '0.55rem 1.25rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: batchRunning ? '#475569' : '#0891b2',
              color: '#ffffff',
              fontSize: '0.85rem',
              fontWeight: 700,
              cursor: batchRunning || solving ? 'not-allowed' : 'pointer',
              whiteSpace: 'nowrap',
            }}
          >
            {batchRunning ? t('Tüm Yöntemler Çalışıyor...', 'Running All Methods...') : t('Tüm yöntemleri çalıştır', 'Run all methods')}
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="batch-table">
            <thead>
              <tr>
                <th>{t('Uygunluk', 'Feasibility')}</th>
                <th>{t('Yöntem', 'Method')}</th>
                <th>{t('Yerleşen', 'Placed')}</th>
                <th className="num">{t('Akış Mesafesi', 'Flow Distance')}</th>
                <th className="num">{t('Taşıma Maliyeti', 'Handling Cost')}</th>
                <th>{t('Süre ve İşlem', 'Runtime & Action')}</th>
              </tr>
            </thead>
            <tbody>
              {batchRows.map((row) => {
                const isBest =
                  minComparableMhc !== null &&
                  row.isComparable &&
                  row.handlingCost !== null &&
                  Math.abs(row.handlingCost - minComparableMhc) < 0.01;
                const isPartial = row.status === 'done' && (row.placedCount < row.totalCount || row.missingFlows > 0);
                const statusBadge =
                  row.status === 'idle' ? (
                    <span className="feas-badge neutral">{t('Hazır', 'Ready')}</span>
                  ) : row.status === 'waiting' ? (
                    <span className="feas-badge neutral">{t('Bekliyor', 'Waiting')}</span>
                  ) : row.status === 'running' ? (
                    <span className="feas-badge running">{t('Çalışıyor...', 'Running...')}</span>
                  ) : row.status === 'error' ? (
                    <span className="feas-badge fail">{t('Hata', 'Error')}</span>
                  ) : row.isComparable ? (
                    <span className="feas-badge ok">{t('Uygun', 'Feasible')}</span>
                  ) : isPartial ? (
                    <span className="feas-badge partial">{t(`Kısmi (${row.placedCount}/${row.totalCount})`, `Partial (${row.placedCount}/${row.totalCount})`)}</span>
                  ) : (
                    <span className="feas-badge fail">{t('Uygun değil', 'Infeasible')}</span>
                  );

                return (
                  <tr key={row.algoId} className={isBest ? 'best-row' : ''}>
                    <td>{statusBadge}</td>
                    <td>
                      <strong style={{ color: 'var(--text-primary)' }}>{t(row.labelTr, row.labelEn)}</strong>
                      {row.algoId === 'craft' && (
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                          {row.status === 'done' && row.startPlanLabel && row.costDeltaPct !== null && row.costDeltaPct !== undefined
                            ? Math.abs(row.costDeltaPct) < 0.05
                              ? t(`${row.startPlanLabel} ile eşit · %0 iyileşme`, `Equal to ${row.startPlanLabel} · 0% improvement`)
                              : `${t('Başlangıç:', 'Seed:')} ${row.startPlanLabel} · ${t('Maliyet farkı:', 'Delta:')} ${row.costDeltaPct > 0 ? '+' : ''}${row.costDeltaPct.toFixed(1)}%`
                            : t('Başlangıç: En iyi uygun plan', 'Seed: Best feasible layout')}
                        </div>
                      )}
                      {row.plainReason && !row.isComparable && (
                        <div className="batch-plain-reason">{row.plainReason}</div>
                      )}
                    </td>
                    <td>
                      {row.status === 'done' ? `${row.placedCount}/${row.totalCount}` : '—'}
                    </td>
                    <td className="num">
                      {row.status === 'done' && row.flowDistance !== null
                        ? row.flowDistance.toLocaleString(undefined, { maximumFractionDigits: 2 })
                        : '—'}
                    </td>
                    <td className="num">
                      {row.status === 'done' && row.handlingCost !== null ? (
                        <div>
                          <strong>{row.handlingCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
                          {isBest && (
                            <div>
                              <span className="best-feasible-tag">
                                {batchRunning
                                  ? t('Şu ana kadarki en düşük', 'Lowest so far')
                                  : t('En düşük uygun maliyet', 'Lowest feasible cost')}
                              </span>
                            </div>
                          )}
                          {!row.isComparable && (
                            <div className="misleading-cost-tag">
                              {isPartial
                                ? t('Yanıltıcı maliyet · Eksik yerleşim', 'Misleading cost · Partial layout')
                                : t('Yanıltıcı maliyet · Gerçek çözüm değil', 'Misleading cost · Not buildable')}
                            </div>
                          )}
                          {isPartial && (
                            <div style={{ fontSize: '0.72rem', color: '#fbbf24', marginTop: '2px' }}>
                              {t(`${row.placedCount}/${row.totalCount} bölüm · ${row.missingFlows} akış hesap dışı`, `${row.placedCount}/${row.totalCount} depts · ${row.missingFlows} flows excluded`)}
                            </div>
                          )}
                        </div>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', alignItems: 'flex-start' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                          {row.durationMs !== null && (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              {row.durationMs.toLocaleString()} ms
                            </span>
                          )}
                          {row.layout && (
                            <button
                              type="button"
                              className={`batch-show-btn ${shownAlgoId === row.algoId ? 'active' : ''}`}
                              onClick={() => {
                                setShownAlgoId(row.algoId);
                                onSolutionGenerated(row.layout!, row.validation, row.evaluation, {
                                  algorithm: t(row.labelTr, row.labelEn),
                                  duration_ms: row.durationMs ?? undefined,
                                });
                                if (onPreviewOnCockpit) {
                                  onPreviewOnCockpit();
                                } else {
                                  onNavigateToViewer();
                                }
                              }}
                            >
                              {shownAlgoId === row.algoId ? t('Planda açık', 'Shown on plan') : t('Planda göster', 'Show on plan')}
                            </button>
                          )}
                        </div>
                        {row.errorDetails && (
                          <details style={{ fontSize: '0.72rem', color: '#fca5a5', maxWidth: '280px' }}>
                            <summary style={{ cursor: 'pointer' }}>{t('İhlal / Hata ayrıntısı', 'Violation / Error details')}</summary>
                            <pre style={{ whiteSpace: 'pre-wrap', margin: '4px 0 0', fontSize: '0.7rem', color: '#fecaca' }}>{row.errorDetails}</pre>
                          </details>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Algorithm Selector Tabs */}
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        flexWrap: 'wrap',
        marginBottom: '1.25rem',
        borderBottom: '1px solid var(--border-color)',
        paddingBottom: '0.75rem',
      }}>
        {(Object.keys(ALGORITHM_DETAILS) as AlgorithmType[]).map((algoKey) => {
          const isSelected = selectedAlgo === algoKey;
          return (
            <button
              key={algoKey}
              onClick={() => setSelectedAlgo(algoKey)}
              style={{
                padding: '0.5rem 0.85rem',
                fontSize: '0.825rem',
                borderRadius: '6px',
                border: isSelected ? '1px solid var(--accent-blue)' : '1px solid var(--border-color)',
                backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-card)',
                color: isSelected ? '#60a5fa' : 'var(--text-secondary)',
                fontWeight: isSelected ? 700 : 500,
                cursor: 'pointer',
              }}
            >
              {ALGORITHM_DETAILS[algoKey].name.split(' (')[0]}
            </button>
          );
        })}
      </div>

      {/* Algorithm Characteristics & Conditions Card */}
      <div style={{
        backgroundColor: 'var(--bg-card)',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        padding: '1.25rem',
        marginBottom: '1.5rem',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {currentAlgoInfo.name}
          </h3>
          <span style={{ fontSize: '0.75rem', padding: '0.15rem 0.5rem', borderRadius: '9999px', backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', fontWeight: 600 }}>
            {lang === 'tr' ? currentAlgoInfo.categoryTr : currentAlgoInfo.categoryEn}
          </span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
          {lang === 'tr' ? currentAlgoInfo.descriptionTr : currentAlgoInfo.descriptionEn}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', fontSize: '0.8rem' }}>
          <div>
            <div style={{ fontWeight: 600, color: '#34d399', marginBottom: '0.25rem' }}>
              ✓ {t('Desteklenen Çalışma Koşulları:', 'Supported Operating Conditions:')}
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {supportedConditions.map((cond, i) => (
                <li key={i}>{cond}</li>
              ))}
            </ul>
          </div>
          <div>
            <div style={{ fontWeight: 600, color: '#fbbf24', marginBottom: '0.25rem' }}>
              ℹ {t('Yöntem Sınırları & Varsayımlar:', 'Method Boundaries & Assumptions:')}
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {assumptions.map((lim, i) => (
                <li key={i}>{lim}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Execution Parameter Inputs */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: '1rem',
        padding: '1.25rem',
        backgroundColor: 'var(--bg-card)',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        marginBottom: '1.5rem',
      }}>
        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
            {t('Rastgelelik Tohumu (Seed):', 'Random Seed:')}
          </label>
          <input
            type="number"
            value={randomSeed}
            onChange={(e) => setRandomSeed(parseInt(e.target.value) || 42)}
            style={{ width: '100%', padding: '0.4rem 0.6rem', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
          />
        </div>

        <div>
          <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
            {t('Zaman Bütçesi / Time Budget (sn):', 'Time Budget (sec):')}
          </label>
          <input
            type="number"
            min="1"
            max="60"
            value={timeBudget}
            onChange={(e) => setTimeBudget(parseFloat(e.target.value) || 10.0)}
            style={{ width: '100%', padding: '0.4rem 0.6rem', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
          />
        </div>

        {(selectedAlgo === 'ga' || selectedAlgo === 'adaptive') && (
          <>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
                {t('Popülasyon Boyutu:', 'Population Size:')}
              </label>
              <input
                type="number"
                min="10"
                max="100"
                value={populationSize}
                onChange={(e) => setPopulationSize(parseInt(e.target.value) || 20)}
                style={{ width: '100%', padding: '0.4rem 0.6rem', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
                {t('Nesil Sayısı:', 'Generations:')}
              </label>
              <input
                type="number"
                min="5"
                max="100"
                value={maxGenerations}
                onChange={(e) => setMaxGenerations(parseInt(e.target.value) || 20)}
                style={{ width: '100%', padding: '0.4rem 0.6rem', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)', fontSize: '0.85rem' }}
              />
            </div>
          </>
        )}
      </div>

      {/* Execution Trigger Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
        <button
          onClick={handleRunOptimization}
          disabled={solving}
          style={{
            padding: '0.65rem 1.75rem',
            backgroundColor: solving ? 'var(--text-muted)' : 'var(--accent-blue)',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            fontSize: '0.95rem',
            fontWeight: 700,
            cursor: solving ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)',
          }}
        >
          {solving ? t('⏳ Problem Çözülüyor...', '⏳ Solving Problem...') : `⚡ ${t('Çalıştır:', 'Run')} ${currentAlgoInfo.name.split(' (')[0]}`}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.85rem' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>{t('Durum: ', 'Status: ')}</span>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{executionStatus}</span>
          </div>
          {elapsedMs !== null && (
            <div>
              <span style={{ color: 'var(--text-muted)' }}>{t('Çalışma Süresi: ', 'Wall-clock: ')}</span>
              <span style={{ fontWeight: 600, color: '#34d399' }}>{elapsedMs.toLocaleString()} ms</span>
            </div>
          )}
        </div>
      </div>

      {/* Error & Failure Notice Display */}
      {errorMsg && (
        <div style={{ padding: '1rem', borderRadius: '8px', backgroundColor: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#fca5a5', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span><strong>{t('Çözücü Durduruldu:', 'Solver Stopped:')}</strong> {summarizeSolverError(errorMsg, t)}</span>
            {currentLayout && (
              <button type="button" className="batch-show-btn" onClick={onNavigateToViewer}>
                {t('Planda göster', 'Show on plan')}
              </button>
            )}
          </div>
          {errorMsg.length > 80 && (
            <details style={{ marginTop: '0.5rem' }}>
              <summary style={{ cursor: 'pointer', fontSize: '0.78rem' }}>{t('Teknik hata ayrıntısını aç', 'View technical error details')}</summary>
              <pre style={{ whiteSpace: 'pre-wrap', margin: '0.4rem 0 0', fontSize: '0.75rem', color: '#fecaca' }}>{errorMsg}</pre>
            </details>
          )}
        </div>
      )}

      {failureNotice && (
        <div style={{ padding: '1rem', borderRadius: '8px', backgroundColor: 'rgba(245, 158, 11, 0.15)', border: '1px solid #f59e0b', color: '#fbbf24', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
          <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>⚠ {t('Geçersiz / Uygulanamaz Sonuç — Gerçek Çözüm Değildir:', 'Invalid / Not Buildable Result — Misleading Cost Warning:')}</div>
          <div><strong>{t('Neden:', 'Reason:')}</strong> {summarizeSolverError(failureNotice.reason, t)}</div>
          <div style={{ marginTop: '0.25rem' }}><strong>{t('Önerilen Çözüm:', 'Suggested Action:')}</strong> {failureNotice.fallback}</div>
          {failureNotice.reason.length > 140 && (
            <details style={{ marginTop: '0.4rem' }}>
              <summary style={{ cursor: 'pointer', fontSize: '0.78rem' }}>{t('Teknik ihlal ayrıntıları', 'Technical violation details')}</summary>
              <pre style={{ whiteSpace: 'pre-wrap', margin: '0.35rem 0 0', fontSize: '0.75rem' }}>{failureNotice.reason}</pre>
            </details>
          )}
        </div>
      )}

      {/* Execution Results Summary Box */}
      {lastResultMetrics && (
        <div style={{
          padding: '1.25rem',
          borderRadius: '8px',
          backgroundColor: lastResultMetrics.is_feasible ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          border: `1px solid ${lastResultMetrics.is_feasible ? '#10b981' : '#ef4444'}`,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
        }}>
          <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
              {t('ÇÖZÜCÜ SONUCU:', 'SOLVER OUTCOME:')} {lastResultMetrics.algorithm}
            </div>
            {!lastResultMetrics.is_feasible && (
              <div className="misleading-cost-tag" style={{ marginTop: '4px' }}>
                ⚠ {t('Geçersiz / Uygulanamaz Çözüm — Gösterilen maliyet yanıltıcıdır', 'Invalid / Not Buildable — Displayed cost is misleading')}
              </div>
            )}
            <div style={{ display: 'flex', gap: '1.25rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
              <div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>MHC: </span>
                <strong style={{ fontSize: '0.95rem' }}>
                  {lastResultMetrics.mhc ? formatCost(Number(lastResultMetrics.mhc), problem?.metadata?.currency) : 'N/A'}
                </strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{t('REL Memnuniyeti: ', 'REL Satisfaction: ')}</span>
                <strong style={{ fontSize: '0.95rem', color: '#10b981' }}>
                  {lastResultMetrics.rel ? `${Number(lastResultMetrics.rel).toFixed(2)}%` : 'N/A'}
                </strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>{t('Esnek Ceza Puanı: ', 'Soft Penalty: ')}</span>
                <strong style={{ fontSize: '0.95rem' }}>
                  {lastResultMetrics.soft_penalty !== undefined ? formatCost(Number(lastResultMetrics.soft_penalty), problem?.metadata?.currency) : formatCost(0, problem?.metadata?.currency)}
                </strong>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={onNavigateToViewer}
              style={{
                padding: '0.45rem 0.85rem',
                backgroundColor: 'var(--accent-blue)',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              📐 {t('2D Yerleşim Planını Gör', 'View 2D Floor Plan')}
            </button>
            <button
              onClick={onNavigateToPareto}
              style={{
                padding: '0.45rem 0.85rem',
                backgroundColor: 'var(--bg-card)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              📊 {t('Pareto Frontier Üzerinde Karşılaştır', 'Compare on Pareto Frontier')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
