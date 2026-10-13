import React, { useState, useEffect, useMemo } from 'react';
import {
  AdaptiveConfig,
  AdaptiveStrategyResult,
  ContinuousLayout,
  ContinuousPlacement,
  StrategyAnalyzeResponse,
} from '../types/api';
import { analyzeStrategy, solveAdaptiveStrategy } from '../services/api';
import { LayoutCanvas } from './LayoutCanvas';

const BENCHMARK_PROBLEMS = [
  { id: 'FLP_INDUSTRIAL_10', name: 'FLP_INDUSTRIAL_10 (10 Depts, 91.7% Util, Strict Bounds)' },
  { id: 'HIGH_DENSITY_15', name: 'HIGH_DENSITY_15 (15 Depts, 90.0% Util, Realistic Dense Flows)' },
  { id: 'HIGH_DENSITY_20', name: 'HIGH_DENSITY_20 (20 Depts, 95.8% Util, Heterogeneous Dense Plant)' },
  { id: 'CONSTRAINED_FACTORY_12', name: 'CONSTRAINED_FACTORY_12 (12 Depts, 81.3% Util, Fixed Dock & Reserved Spine)' },
  { id: 'LOGISTICS_FACTORY_15', name: 'LOGISTICS_FACTORY_15 (15 Depts, 85.0% Util, Asymmetric Tote Logistics)' },
  { id: 'FLP_ACADEMIC_4', name: 'FLP_ACADEMIC_4 (4 Depts, Small Unconstrained Flow)' },
  { id: 'FLP_MEDIUM_6', name: 'FLP_MEDIUM_6 (6 Depts, Medium Plant)' },
  { id: 'FLP_EXPANSION_8', name: 'FLP_EXPANSION_8 (8 Depts, Reserved Spine Aisle)' },
  { id: 'FLP_LOGISTICS_5', name: 'FLP_LOGISTICS_5 (5 Depts, Linear Flow Hub)' },
];

export const AdaptiveStrategyCard: React.FC = () => {
  const [selectedProblemId, setSelectedProblemId] = useState<string>('FLP_INDUSTRIAL_10');
  const [budgetSeconds, setBudgetSeconds] = useState<number>(15.0);
  const [maxCalls, setMaxCalls] = useState<number>(5);
  const [fallbackEnabled, setFallbackEnabled] = useState<boolean>(true);
  const [randomSeed, setRandomSeed] = useState<number>(42);

  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [solving, setSolving] = useState<boolean>(false);
  const [analysis, setAnalysis] = useState<StrategyAnalyzeResponse | null>(null);
  const [result, setResult] = useState<AdaptiveStrategyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [selectedCandidateSig, setSelectedCandidateSig] = useState<string | null>(null);

  // Auto-analyze on problem switch
  useEffect(() => {
    handleAnalyze();
  }, [selectedProblemId]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    try {
      const data = await analyzeStrategy({ problem_id: selectedProblemId });
      setAnalysis(data);
    } catch (err: any) {
      setError(err.message || 'Failed to analyze problem');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSolve = async () => {
    setSolving(true);
    setError(null);
    try {
      const config: AdaptiveConfig = {
        max_total_runtime_seconds: budgetSeconds,
        max_algorithm_calls: maxCalls,
        fallback_enabled: fallbackEnabled,
        random_seed: randomSeed,
        ga_population_size: 25,
        ga_generations: 20,
      };
      const res = await solveAdaptiveStrategy({
        problem_id: selectedProblemId,
        config,
      });
      setResult(res);
      if (res.final_recommendation && res.final_recommendation.layout_signature) {
        setSelectedCandidateSig(res.final_recommendation.layout_signature);
      } else if (res.candidate_portfolio.items.length > 0) {
        setSelectedCandidateSig(res.candidate_portfolio.items[0].output_layout_signature);
      }
    } catch (err: any) {
      setError(err.message || 'Adaptive execution failed');
    } finally {
      setSolving(false);
    }
  };

  // Convert selected layout candidate to ContinuousLayout for canvas visualization
  const activeLayout = useMemo<ContinuousLayout | null>(() => {
    if (!result || !selectedCandidateSig) return null;
    const item = result.candidate_portfolio.items.find(
      (it) => it.output_layout_signature === selectedCandidateSig
    );
    if (!item || !item.solution || !item.solution.placements) return null;

    const fp = result.fingerprint;
    const placementsMap: Record<string, ContinuousPlacement> = {};
    for (const [did, p] of Object.entries(item.solution.placements)) {
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

    return {
      representation_type: 'continuous',
      facility_width: fp.facility_width || 150,
      facility_height: fp.facility_height || 80,
      placements: placementsMap,
    };
  }, [result, selectedCandidateSig]);

  return (
    <div className="card" style={{ marginBottom: '2rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, padding: '0.2rem 0.5rem', borderRadius: '4px', backgroundColor: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Phase 11
            </span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
              Adaptive Strategy Engine v1
            </h2>
          </div>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: 0 }}>
            Automated fingerprint extraction, rule-based algorithm selection, fallback resilience, and shared candidate portfolio.
          </p>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button
            className="btn btn-secondary"
            onClick={handleAnalyze}
            disabled={analyzing || solving}
            style={{ fontSize: '0.85rem' }}
          >
            {analyzing ? 'Analyzing...' : 'Re-Analyze Fingerprint'}
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSolve}
            disabled={solving}
            style={{ fontSize: '0.85rem', fontWeight: 600, backgroundColor: '#3b82f6', borderColor: '#3b82f6' }}
          >
            {solving ? 'Solving Adaptively...' : 'Launch Adaptive Optimization'}
          </button>
        </div>
      </div>

      {/* Control Configuration Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', backgroundColor: 'var(--bg-secondary)', padding: '1rem', borderRadius: '8px', marginBottom: '1.5rem', border: '1px solid var(--border-color)' }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            PROBLEM INSTANCE
          </label>
          <select
            value={selectedProblemId}
            onChange={(e) => setSelectedProblemId(e.target.value)}
            disabled={solving}
            style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
          >
            {BENCHMARK_PROBLEMS.map((bp) => (
              <option key={bp.id} value={bp.id}>
                {bp.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            TIME BUDGET (SECONDS)
          </label>
          <input
            type="number"
            min="1.0"
            max="120.0"
            step="1.0"
            value={budgetSeconds}
            onChange={(e) => setBudgetSeconds(parseFloat(e.target.value) || 15.0)}
            disabled={solving}
            style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            MAX ALGORITHM CALLS
          </label>
          <input
            type="number"
            min="1"
            max="15"
            value={maxCalls}
            onChange={(e) => setMaxCalls(parseInt(e.target.value) || 5)}
            disabled={solving}
            style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            RANDOM SEED
          </label>
          <input
            type="number"
            value={randomSeed}
            onChange={(e) => setRandomSeed(parseInt(e.target.value) || 42)}
            disabled={solving}
            style={{ width: '100%', padding: '0.45rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={fallbackEnabled}
              onChange={(e) => setFallbackEnabled(e.target.checked)}
              disabled={solving}
            />
            <span style={{ fontWeight: 600 }}>Enable Adaptive Fallback</span>
          </label>
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
            Auto-switch to secondary solver if primary heuristic fails
          </span>
        </div>
      </div>

      {error && (
        <div style={{ padding: '0.75rem 1rem', borderRadius: '6px', backgroundColor: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#ef4444', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Section 1: Structural Problem Fingerprint & Strategy Recommendation */}
      {analysis && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          {/* Fingerprint Card */}
          <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem', backgroundColor: 'var(--bg-secondary)' }}>
            <h4 style={{ fontSize: '0.85rem', fontWeight: 700, margin: '0 0 0.75rem 0', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>
              Deterministic Problem Fingerprint
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.8rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Departments:</span> <strong>{analysis.fingerprint.department_count}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Utilization:</span> <strong>{(analysis.fingerprint.area_utilization * 100).toFixed(1)}%</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Plant Footprint:</span> <strong>{analysis.fingerprint.facility_width} × {analysis.fingerprint.facility_height} m</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Area Variation:</span> <strong>{analysis.fingerprint.area_variation}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Flow Density:</span> <strong>{(analysis.fingerprint.flow_density * 100).toFixed(1)}%</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>REL Density:</span> <strong>{(analysis.fingerprint.rel_density ? (analysis.fingerprint.rel_density * 100).toFixed(1) : 0)}%</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Aspect Bounds:</span> <strong>{analysis.fingerprint.has_aspect_ratio_constraints ? `${analysis.fingerprint.aspect_ratio_constrained_count} Depts` : 'None'}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Reserved Zones:</span> <strong>{analysis.fingerprint.reserved_zone_count ? `${analysis.fingerprint.reserved_zone_count} (${(analysis.fingerprint.reserved_zone_ratio! * 100).toFixed(1)}%)` : 'None'}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Hard Constraints:</span> <strong>{analysis.fingerprint.hard_constraints_count}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Soft Constraints:</span> <strong>{analysis.fingerprint.soft_constraints_count}</strong>
              </div>
            </div>
            {analysis.fingerprint.unavailable_features && analysis.fingerprint.unavailable_features.length > 0 && (
              <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-color)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                <em>Unavailable features (not modeled):</em> {analysis.fingerprint.unavailable_features.join(', ')}
              </div>
            )}
          </div>

          {/* Strategy Recommendation Card */}
          <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem', backgroundColor: 'var(--bg-secondary)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <h4 style={{ fontSize: '0.85rem', fontWeight: 700, margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>
                Recommended Strategy Pipeline
              </h4>
              <span style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem', borderRadius: '4px', backgroundColor: 'rgba(16, 185, 129, 0.15)', color: '#10b981', fontWeight: 600 }}>
                {analysis.selected_strategy.rule_id}
              </span>
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#3b82f6', marginBottom: '0.4rem' }}>
              {analysis.selected_strategy.name}
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4, margin: '0 0 0.5rem 0' }}>
              {analysis.selected_strategy.rationale}
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', fontSize: '0.75rem', marginTop: '0.5rem' }}>
              <span style={{ padding: '0.2rem 0.5rem', backgroundColor: 'var(--bg-primary)', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                <strong>Primary:</strong> {analysis.selected_strategy.primary_algorithm}
              </span>
              <span style={{ padding: '0.2rem 0.5rem', backgroundColor: 'var(--bg-primary)', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
                <strong>Improvement:</strong> {analysis.selected_strategy.improvement_algorithms.join(', ') || 'None'}
              </span>
              {analysis.selected_strategy.fallback_algorithm && (
                <span style={{ padding: '0.2rem 0.5rem', backgroundColor: 'var(--bg-primary)', borderRadius: '4px', border: '1px solid var(--border-color)', color: '#f59e0b' }}>
                  <strong>Fallback:</strong> {analysis.selected_strategy.fallback_algorithm}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Section 2: Results & Explainable Execution Trace */}
      {result && (
        <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
          {/* Executive Metrics Bar */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
            <div style={{ padding: '0.75rem', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>FEASIBILITY STATUS</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: result.feasible_status ? '#10b981' : '#ef4444' }}>
                {result.feasible_status ? 'Complete & Feasible' : 'Infeasible / Failed'}
              </div>
            </div>

            <div style={{ padding: '0.75rem', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>BEST FEASIBLE MHC</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#3b82f6' }}>
                {result.final_recommendation?.material_handling_cost ? `$${result.final_recommendation.material_handling_cost.toLocaleString()}` : 'N/A'}
              </div>
            </div>

            <div style={{ padding: '0.75rem', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PORTFOLIO CANDIDATES</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                {result.candidate_portfolio.feasible_candidates_count} Feasible / {result.candidate_portfolio.total_candidates_generated} Total
              </div>
            </div>

            <div style={{ padding: '0.75rem', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PARETO FRONTIER</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#8b5cf6' }}>
                {result.pareto_frontier.frontier_count} Non-Dominated
              </div>
            </div>

            <div style={{ padding: '0.75rem', borderRadius: '6px', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)' }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>TOTAL EXECUTION TIME</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700 }}>
                {result.total_runtime_seconds.toFixed(2)}s ({result.total_algorithm_calls} calls)
              </div>
            </div>
          </div>

          {/* Explainable Decision Trace Table */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginBottom: '0.5rem' }}>
              Explainable Decision & Execution Trace (Honest Audit Record)
            </h4>
            <div style={{ overflowX: 'auto', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ backgroundColor: 'var(--bg-secondary)', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>
                    <th style={{ padding: '0.5rem' }}>Step</th>
                    <th style={{ padding: '0.5rem' }}>Action / Algorithm</th>
                    <th style={{ padding: '0.5rem' }}>Category</th>
                    <th style={{ padding: '0.5rem' }}>Result Status</th>
                    <th style={{ padding: '0.5rem' }}>MHC ($)</th>
                    <th style={{ padding: '0.5rem' }}>Runtime</th>
                    <th style={{ padding: '0.5rem' }}>Audit Reason & Next Action</th>
                  </tr>
                </thead>
                <tbody>
                  {result.execution_trace.map((step) => (
                    <tr key={step.step_index} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '0.5rem', fontWeight: 600 }}>{step.step_index}</td>
                      <td style={{ padding: '0.5rem' }}>
                        <code>{step.selected_algorithm}</code> {step.was_fallback && <span style={{ color: '#f59e0b', fontSize: '0.7rem' }}>[FALLBACK]</span>}
                      </td>
                      <td style={{ padding: '0.5rem', textTransform: 'capitalize' }}>{step.algorithm_category}</td>
                      <td style={{ padding: '0.5rem' }}>
                        {step.success ? (
                          <span style={{ color: '#10b981', fontWeight: 600 }}>Feasible</span>
                        ) : (
                          <span style={{ color: '#ef4444', fontWeight: 600 }}>
                            Infeasible {step.failure_reason && `(${step.failure_reason})`}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: '0.5rem' }}>
                        {step.objective_values.material_handling_cost ? `$${step.objective_values.material_handling_cost.toLocaleString()}` : '-'}
                      </td>
                      <td style={{ padding: '0.5rem' }}>{step.execution_time_seconds.toFixed(3)}s</td>
                      <td style={{ padding: '0.5rem', color: 'var(--text-secondary)' }}>
                        {step.next_action_rationale}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Layout Visualization & Portfolio Alternatives */}
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 350px', gap: '1.25rem', alignItems: 'start' }}>
            {/* Visual Canvas */}
            <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem', backgroundColor: 'var(--bg-secondary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <h4 style={{ fontSize: '0.9rem', fontWeight: 700, margin: 0 }}>
                  Layout Preview: {selectedCandidateSig ? `Sig ${selectedCandidateSig.substring(0, 8)}...` : 'None'}
                </h4>
                {result.final_recommendation?.layout_signature === selectedCandidateSig && (
                  <span style={{ fontSize: '0.7rem', fontWeight: 700, padding: '0.15rem 0.5rem', borderRadius: '4px', backgroundColor: 'rgba(59, 130, 246, 0.2)', color: '#3b82f6' }}>
                    RECOMMENDED BEST
                  </span>
                )}
              </div>

              {activeLayout ? (
                <div style={{ height: '380px', backgroundColor: 'var(--bg-primary)', borderRadius: '6px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
                  <LayoutCanvas layout={activeLayout} />
                </div>
              ) : (
                <div style={{ height: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                  No visual placement available for this candidate.
                </div>
              )}
            </div>

            {/* Candidate Portfolio Selection List */}
            <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1rem', backgroundColor: 'var(--bg-secondary)' }}>
              <h4 style={{ fontSize: '0.9rem', fontWeight: 700, margin: '0 0 0.5rem 0' }}>
                Candidate Portfolio ({result.candidate_portfolio.unique_candidates_count} Unique)
              </h4>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0 0 0.75rem 0' }}>
                Deduplicated signatures with preserved algorithm provenance. Click candidate to view layout.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '360px', overflowY: 'auto' }}>
                {result.candidate_portfolio.items.map((cand) => {
                  const isSelected = cand.output_layout_signature === selectedCandidateSig;
                  return (
                    <div
                      key={cand.candidate_id}
                      onClick={() => setSelectedCandidateSig(cand.output_layout_signature)}
                      style={{
                        padding: '0.6rem',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        border: isSelected ? '2px solid #3b82f6' : '1px solid var(--border-color)',
                        backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-primary)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.2rem' }}>
                        <span style={{ fontWeight: 700, fontSize: '0.8rem' }}>{cand.candidate_id} ({cand.source_algorithm})</span>
                        <span style={{ fontSize: '0.7rem', fontWeight: 600, color: cand.feasibility ? '#10b981' : '#ef4444' }}>
                          {cand.feasibility ? 'Feasible' : 'Infeasible'}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        MHC: <strong>{cand.material_handling_cost ? `$${cand.material_handling_cost.toLocaleString()}` : 'N/A'}</strong> | Rel Sat: {cand.relationship_satisfaction ? `${cand.relationship_satisfaction.toFixed(1)}%` : 'N/A'}
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                        Provenance: {cand.provenance_sources.map((p) => p.algorithm_name).join(', ')}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
