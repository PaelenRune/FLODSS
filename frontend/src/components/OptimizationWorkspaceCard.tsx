import React, { useState } from 'react';
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
  onNavigateToPareto: () => void;
}

type AlgorithmType = 'adaptive' | 'ga' | 'craft' | 'feasible_generator' | 'corelap' | 'aldep';

interface AlgorithmInfo {
  name: string;
  category: string;
  description: string;
  supportedConditions: string[];
  assumptionsAndLimitations: string[];
}

const ALGORITHM_DETAILS: Record<AlgorithmType, AlgorithmInfo> = {
  adaptive: {
    name: 'Adaptive Strategy Engine v1',
    category: 'Autonomous Multi-Method Pipeline',
    description: 'Analyzes structural problem fingerprint (density, aspect ratios, constraints) and executes tailored primary and fallback pipelines.',
    supportedConditions: [
      'Handles all facility density regimes (low, moderate, high >=80%).',
      'Supports fixed departments, reserved spine corridors, and tight aspect bounds.',
      'Automatic fallback to metaheuristic when constructive search encounters dead-ends.',
    ],
    assumptionsAndLimitations: [
      'Executes multiple algorithm evaluations within time budget.',
      'Constructs candidate portfolio and computes multi-objective Pareto dominance.',
    ],
  },
  ga: {
    name: 'Genetic Algorithm v1 (Slicing Tree)',
    category: 'Stochastic Population-Based Metaheuristic',
    description: 'Slicing-tree chromosome representation with area-preserving bay decoding, order crossover, and multi-operator mutation.',
    supportedConditions: [
      'Continuous 2D rectangular layout representation.',
      'Guarantees zero pairwise overlap and exact area conservation.',
      'Minimizes Material Handling Cost (MHC) with soft penalty guidance.',
    ],
    assumptionsAndLimitations: [
      'Does not guarantee global mathematical optimality (Facility Layout is strongly NP-hard).',
      'Evaluation budget scales linearly with population_size × generations.',
    ],
  },
  feasible_generator: {
    name: 'Feasible Rectangular Generator (Guillotine)',
    category: 'Deterministic Constructive Packing',
    description: 'Guillotine Row Packing constructive search establishing non-overlapping rectangular baselines from raw problem inputs.',
    supportedConditions: [
      'Blazingly fast (<150 ms) deterministic baseline construction.',
      'Works best on moderate-to-high density facilities with flexible aspect ratios.',
    ],
    assumptionsAndLimitations: [
      'Single-pass constructive search without recursive backtracking.',
      'Fails on extreme density (>=90%) or facilities bisected by reserved exclusion zones.',
    ],
  },
  craft: {
    name: 'CRAFT (Centroid Swapping Heuristic)',
    category: 'Steepest-Descent Improvement Heuristic',
    description: 'Pairwise department centroid exchange evaluating material handling cost deltas.',
    supportedConditions: [
      'Requires an existing feasible starting baseline layout.',
      'Evaluates pairwise coordinate exchanges to reduce flow-distance costs.',
    ],
    assumptionsAndLimitations: [
      'Susceptible to local optima entrapment.',
      'Swapping unequal department areas can produce non-rectangular shapes in discrete grids.',
    ],
  },
  corelap: {
    name: 'CORELAP (Total Closeness Rating)',
    category: 'Greedy Constructive Heuristic',
    description: 'Constructive algorithm placing departments sequentially based on Total Closeness Rating (TCR) computed from the REL matrix.',
    supportedConditions: [
      'Qualitative Systematic Layout Planning (SLP) driven.',
      'Places highest TCR department first at layout center.',
    ],
    assumptionsAndLimitations: [
      'Sensitive to placement tie-breaking order.',
      'Does not natively minimize quantitative flow-distance costs.',
    ],
  },
  aldep: {
    name: 'ALDEP (Automated Layout Design Program)',
    category: 'Stochastic Strip-Sweep Constructive Heuristic',
    description: 'Randomized department selection and continuous snake-like strip sweep placement based on relationship cutoff threshold.',
    supportedConditions: [
      'Generates diverse candidate alternatives via stochastic multi-trial sweep.',
    ],
    assumptionsAndLimitations: [
      'Fixed sweep width can produce elongated or irregular shapes in discrete grids.',
    ],
  },
};

export const OptimizationWorkspaceCard: React.FC<OptimizationWorkspaceCardProps> = ({
  problem,
  currentLayout,
  onSolutionGenerated,
  onNavigateToViewer,
  onNavigateToPareto,
}) => {
  const [selectedAlgo, setSelectedAlgo] = useState<AlgorithmType>('adaptive');
  const [randomSeed, setRandomSeed] = useState<number>(42);
  const [timeBudget, setTimeBudget] = useState<number>(10.0);
  const [populationSize, setPopulationSize] = useState<number>(20);
  const [maxGenerations, setMaxGenerations] = useState<number>(20);

  const [solving, setSolving] = useState<boolean>(false);
  const [elapsedMs, setElapsedMs] = useState<number | null>(null);
  const [executionStatus, setExecutionStatus] = useState<string>('Ready');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [failureNotice, setFailureNotice] = useState<{ reason: string; partial: boolean; fallback: string } | null>(null);
  const [lastResultMetrics, setLastResultMetrics] = useState<any | null>(null);

  if (!problem) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
        <p style={{ color: 'var(--text-muted)' }}>Load or create a problem to access the Optimization Workspace.</p>
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
    setExecutionStatus(`Running ${currentAlgoInfo.name}...`);
    const t0 = performance.now();

    try {
      if (selectedAlgo === 'adaptive') {
        const res = await solveAdaptiveStrategy({
          problem_id: problem.id,
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

        if (!res.feasible_status || !bestLayout) {
          setFailureNotice({
            reason: res.termination_reason || 'Adaptive strategy could not find a feasible layout.',
            partial: totalCandidates > 0,
            fallback: 'Try increasing the time budget or relaxing aspect ratio bounds in Problem Editor.',
          });
          setExecutionStatus('Algorithm Completed (Infeasible)');
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
          onSolutionGenerated(bestLayout, null, null, {
            algorithm: res.selected_strategy?.name,
            seed: randomSeed,
            duration_ms: t1 - t0,
            termination_reason: res.termination_reason,
          });
          setExecutionStatus('Success: Feasible Solution Found');
        }
      } else if (selectedAlgo === 'ga') {
        const res = await solveGeneticAlgorithm({
          problem_id: problem.id,
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
            reason: 'Genetic search terminated without finding a fully feasible chromosome.',
            partial: res.continuous_layout !== null,
            fallback: 'Increase population size or generations to expand slicing-tree exploration.',
          });
          setExecutionStatus('Algorithm Completed (Infeasible)');
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
          setExecutionStatus('Success: Feasible Solution Found');
        }
      } else if (selectedAlgo === 'feasible_generator') {
        const res = await solveFeasibleGenerator({
          problem_id: problem.id,
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
            reason: res.result?.termination_reason || 'Guillotine Row Packing could not fit all departments within aspect bounds.',
            partial: false,
            fallback: 'Switch to Genetic Algorithm or Adaptive Mode which use recursive slicing.',
          });
          setExecutionStatus('Constructive Search Failed');
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
          setExecutionStatus('Success: Feasible Layout Generated');
        }
      } else if (selectedAlgo === 'craft') {
        const res = await solveCRAFT({
          problem_id: problem.id,
          initial_layout: currentLayout ? { placements: currentLayout.placements, facility_width: currentLayout.facility_width, facility_height: currentLayout.facility_height } : undefined,
          config: {
            max_iterations: maxGenerations,
          },
        });
        const t1 = performance.now();
        setElapsedMs(Math.round(t1 - t0));

        const mhcVal = res.final_evaluation?.material_handling_cost ?? res.final_evaluation?.objective_values?.material_handling_cost;
        const relVal = res.final_evaluation?.relationship_satisfaction_percentage ?? res.final_evaluation?.objective_values?.relationship_satisfaction;
        const softVal = res.final_evaluation?.soft_penalty ?? res.final_evaluation?.soft_constraint_penalty ?? res.final_evaluation?.total_constraint_penalty;

        setLastResultMetrics({
          is_feasible: res.solution?.feasibility_status,
          mhc: mhcVal,
          rel: relVal,
          soft_penalty: softVal,
          algorithm: 'CRAFT Improvement',
          evaluations: res.trace?.total_iterations || 1,
        });
        onSolutionGenerated(res.continuous_layout, null, res.final_evaluation, {
          algorithm: 'CRAFT',
          duration_ms: t1 - t0,
        });
        setExecutionStatus('Success: CRAFT Optimization Finished');
      } else if (selectedAlgo === 'corelap') {
        const res = await solveCORELAP({
          problem_id: problem.id,
        });
        const t1 = performance.now();
        setElapsedMs(Math.round(t1 - t0));

        const isFeas = res.validation?.is_valid && res.trace?.execution_success;
        if (!isFeas) {
          setFailureNotice({
            reason: res.trace?.failure_reason || 'CORELAP heuristic produced overlapping or incomplete placements.',
            partial: res.trace?.placed_count > 0,
            fallback: 'Use Feasible Generator, Genetic Algorithm, or Adaptive Mode for guaranteed feasibility.',
          });
          setExecutionStatus('CORELAP Infeasible Baseline');
        } else {
          setExecutionStatus('Success: CORELAP Placed');
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
        });
        const t1 = performance.now();
        setElapsedMs(Math.round(t1 - t0));

        const isFeas = res.validation?.is_valid;
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
        setExecutionStatus(isFeas ? 'Success: ALDEP Completed' : 'ALDEP Completed (Infeasible)');
      }
    } catch (err: any) {
      const t1 = performance.now();
      setElapsedMs(Math.round(t1 - t0));
      setErrorMsg(err.message || 'Optimization execution failed.');
      setExecutionStatus('Execution Error');
    } finally {
      setSolving(false);
    }
  };

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
          Optimization Execution Workspace
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>
          Select and run industrial layout optimization heuristics, metaheuristics, or the autonomous Adaptive Strategy Engine.
        </p>
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
            {currentAlgoInfo.category}
          </span>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
          {currentAlgoInfo.description}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', fontSize: '0.8rem' }}>
          <div>
            <div style={{ fontWeight: 600, color: '#34d399', marginBottom: '0.25rem' }}>
              ✓ Supported Operating Conditions:
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {currentAlgoInfo.supportedConditions.map((cond, i) => (
                <li key={i}>{cond}</li>
              ))}
            </ul>
          </div>
          <div>
            <div style={{ fontWeight: 600, color: '#fbbf24', marginBottom: '0.25rem' }}>
              ℹ Method Boundaries & Assumptions:
            </div>
            <ul style={{ margin: 0, paddingLeft: '1.2rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {currentAlgoInfo.assumptionsAndLimitations.map((lim, i) => (
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
            Random Seed:
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
            Time Budget (sec):
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
                Population Size:
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
                Generations:
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
          {solving ? '⏳ Solving Problem...' : `⚡ Run ${currentAlgoInfo.name.split(' (')[0]}`}
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', fontSize: '0.85rem' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Status: </span>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{executionStatus}</span>
          </div>
          {elapsedMs !== null && (
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Wall-clock: </span>
              <span style={{ fontWeight: 600, color: '#34d399' }}>{elapsedMs.toLocaleString()} ms</span>
            </div>
          )}
        </div>
      </div>

      {/* Error & Failure Notice Display */}
      {errorMsg && (
        <div style={{ padding: '1rem', borderRadius: '8px', backgroundColor: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#f87171', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
          <strong>Error:</strong> {errorMsg}
        </div>
      )}

      {failureNotice && (
        <div style={{ padding: '1rem', borderRadius: '8px', backgroundColor: 'rgba(245, 158, 11, 0.15)', border: '1px solid #f59e0b', color: '#fbbf24', fontSize: '0.85rem', marginBottom: '1.25rem' }}>
          <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>⚠ Algorithm Termination Notice (Infeasible):</div>
          <div><strong>Reason:</strong> {failureNotice.reason}</div>
          <div style={{ marginTop: '0.25rem' }}><strong>Suggested Fallback:</strong> {failureNotice.fallback}</div>
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
              SOLVER OUTCOME: {lastResultMetrics.algorithm}
            </div>
            <div style={{ display: 'flex', gap: '1.25rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
              <div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>MHC: </span>
                <strong style={{ fontSize: '0.95rem' }}>
                  {lastResultMetrics.mhc ? `$${Number(lastResultMetrics.mhc).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'N/A'}
                </strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>REL Satisfaction: </span>
                <strong style={{ fontSize: '0.95rem', color: '#10b981' }}>
                  {lastResultMetrics.rel ? `${Number(lastResultMetrics.rel).toFixed(2)}%` : 'N/A'}
                </strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>Soft Penalty: </span>
                <strong style={{ fontSize: '0.95rem' }}>
                  {lastResultMetrics.soft_penalty !== undefined ? `$${Number(lastResultMetrics.soft_penalty).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '$0.00'}
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
              📐 View 2D Floor Plan
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
              📊 Compare on Pareto Frontier
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
