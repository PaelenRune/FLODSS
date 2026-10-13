import React, { useState, useEffect } from 'react';
import {
  ProblemSummary,
  LayoutExampleSummary,
  ContinuousLayout,
  EvaluationReport,
  ComparisonReport,
} from '../types/api';
import {
  fetchExampleProblems,
  fetchExampleLayouts,
  fetchExampleLayout,
  evaluateLayout,
  compareLayouts,
} from '../services/api';

export const LayoutEvaluationCard: React.FC = () => {
  const [problems, setProblems] = useState<ProblemSummary[]>([]);
  const [selectedProblemId, setSelectedProblemId] = useState<string>('');
  const [layouts, setLayouts] = useState<LayoutExampleSummary[]>([]);
  const [selectedLayoutId, setSelectedLayoutId] = useState<string>('');
  
  // Config
  const [distanceMetric, setDistanceMetric] = useState<'manhattan' | 'euclidean'>('manhattan');
  const [defaultUnitCost, setDefaultUnitCost] = useState<number>(1.0);
  
  // Results
  const [activeTab, setActiveTab] = useState<'single' | 'compare'>('single');
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [comparisonReport, setComparisonReport] = useState<ComparisonReport | null>(null);
  
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setError(null);
        const [probData, layoutData] = await Promise.all([
          fetchExampleProblems(),
          fetchExampleLayouts(),
        ]);
        setProblems(probData);
        if (probData.length > 0) {
          setSelectedProblemId(probData[0].id);
        }
        setLayouts(layoutData);
        if (layoutData.length > 0) {
          setSelectedLayoutId(layoutData[0].id);
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to initialize evaluation resources.');
      }
    }
    loadData();
  }, []);

  const handleEvaluate = async () => {
    if (!selectedProblemId || !selectedLayoutId) return;
    try {
      setLoading(true);
      setError(null);
      const layoutObj = await fetchExampleLayout(selectedLayoutId);
      const config = {
        distance_metric: distanceMetric,
        default_cost_per_unit_distance: defaultUnitCost,
      };
      const rep = await evaluateLayout(selectedProblemId, layoutObj, config);
      setReport(rep);
    } catch (err: any) {
      setError(err?.message || 'Failed to evaluate layout.');
    } finally {
      setLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!selectedProblemId || layouts.length === 0) return;
    try {
      setLoading(true);
      setError(null);
      // Fetch all layouts in catalog
      const loadedLayouts: ContinuousLayout[] = [];
      for (const item of layouts) {
        try {
          const l = await fetchExampleLayout(item.id);
          loadedLayouts.push(l);
        } catch {
          // ignore
        }
      }
      const config = {
        distance_metric: distanceMetric,
        default_cost_per_unit_distance: defaultUnitCost,
      };
      const comp = await compareLayouts(selectedProblemId, loadedLayouts, config);
      setComparisonReport(comp);
      setActiveTab('compare');
    } catch (err: any) {
      setError(err?.message || 'Failed to compare layouts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedProblemId && selectedLayoutId) {
      handleEvaluate();
    }
  }, [selectedProblemId, selectedLayoutId, distanceMetric, defaultUnitCost]);

  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '12px',
      padding: '1.5rem',
      marginBottom: '2rem',
    }}>
      {/* Title & Action Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Multi-Criteria Layout Evaluation</h2>
            <span style={{
              fontSize: '0.75rem',
              padding: '0.2rem 0.5rem',
              borderRadius: '9999px',
              backgroundColor: 'rgba(59, 130, 246, 0.15)',
              color: '#60a5fa',
              fontWeight: 600,
            }}>
              Phase 4 Engine
            </span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Decoupled industrial evaluation: Flow-Distance, MHC, Muther SLP closeness, area utilization, and hard/soft constraints.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setActiveTab('single')}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 500,
              cursor: 'pointer',
              backgroundColor: activeTab === 'single' ? 'var(--accent-color)' : 'var(--bg-card)',
              color: activeTab === 'single' ? '#ffffff' : 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
            }}
          >
            Single Evaluation
          </button>
          <button
            onClick={handleCompare}
            disabled={loading}
            style={{
              padding: '0.4rem 0.8rem',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 500,
              cursor: 'pointer',
              backgroundColor: activeTab === 'compare' ? 'var(--accent-color)' : 'var(--bg-card)',
              color: activeTab === 'compare' ? '#ffffff' : 'var(--text-secondary)',
              border: '1px solid var(--border-color)',
            }}
          >
            {loading && activeTab === 'compare' ? 'Comparing...' : 'Compare Catalog'}
          </button>
        </div>
      </div>

      {/* Control Filters */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        padding: '1rem',
        backgroundColor: 'var(--bg-card)',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        marginBottom: '1.5rem',
      }}>
        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
            Problem Case
          </label>
          <select
            value={selectedProblemId}
            onChange={(e) => setSelectedProblemId(e.target.value)}
            style={{
              width: '100%',
              padding: '0.45rem',
              borderRadius: '6px',
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              fontSize: '0.85rem',
            }}
          >
            {problems.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.department_count} depts)
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
            Candidate Layout
          </label>
          <select
            value={selectedLayoutId}
            onChange={(e) => setSelectedLayoutId(e.target.value)}
            style={{
              width: '100%',
              padding: '0.45rem',
              borderRadius: '6px',
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              fontSize: '0.85rem',
            }}
          >
            {layouts.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name} ({l.representation_type})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
            Distance Metric
          </label>
          <select
            value={distanceMetric}
            onChange={(e) => setDistanceMetric(e.target.value as any)}
            style={{
              width: '100%',
              padding: '0.45rem',
              borderRadius: '6px',
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              fontSize: '0.85rem',
            }}
          >
            <option value="manhattan">Manhattan (Rectilinear / Aisle)</option>
            <option value="euclidean">Euclidean (Straight Line / Crane)</option>
          </select>
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>
            Default Unit Cost ($/m)
          </label>
          <input
            type="number"
            min="0.1"
            step="0.5"
            value={defaultUnitCost}
            onChange={(e) => setDefaultUnitCost(parseFloat(e.target.value) || 1.0)}
            style={{
              width: '100%',
              padding: '0.45rem',
              borderRadius: '6px',
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              fontSize: '0.85rem',
            }}
          />
        </div>
      </div>

      {error && (
        <div style={{
          padding: '0.75rem 1rem',
          borderRadius: '8px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          color: '#f87171',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          marginBottom: '1rem',
          fontSize: '0.85rem',
        }}>
          {error}
        </div>
      )}

      {loading && !report && (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          Computing layout evaluations and matrix cross-products...
        </div>
      )}

      {/* SINGLE EVALUATION VIEW */}
      {activeTab === 'single' && report && (
        <div>
          {/* Feasibility & Signature Status Banner */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '0.85rem 1.25rem',
            borderRadius: '8px',
            marginBottom: '1.25rem',
            backgroundColor: report.is_feasible ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${report.is_feasible ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <span style={{
                fontSize: '0.85rem',
                fontWeight: 700,
                padding: '0.25rem 0.6rem',
                borderRadius: '6px',
                backgroundColor: report.is_feasible ? '#10b981' : '#ef4444',
                color: '#ffffff',
              }}>
                {report.is_feasible ? 'FEASIBLE LAYOUT' : 'INFEASIBLE LAYOUT'}
              </span>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {report.is_feasible
                  ? 'All hard spatial, boundary, and non-overlapping constraints satisfied.'
                  : `${report.hard_violation_count} hard constraint violation(s) detected.`}
              </span>
            </div>
            <div style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
              Signature: {report.layout_signature.slice(0, 16)}...
            </div>
          </div>

          {/* Metric KPI Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
            marginBottom: '1.5rem',
          }}>
            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1rem',
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Material Handling Cost
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#38bdf8', marginTop: '0.25rem' }}>
                ${(report.objective_values.material_handling_cost ?? 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Cost per flow cycle
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1rem',
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Total Flow Distance
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#818cf8', marginTop: '0.25rem' }}>
                {(report.objective_values.flow_distance ?? 0).toLocaleString()} <span style={{ fontSize: '0.85rem', fontWeight: 400 }}>m-moves</span>
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Directed sum Σ Fij × Dij
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1rem',
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Relationship Score
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#a78bfa', marginTop: '0.25rem' }}>
                {report.objective_values.relationship_score ?? 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Muther SLP satisfaction
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1rem',
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Area Utilization
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#34d399', marginTop: '0.25rem' }}>
                {report.objective_values.area_utilization ?? 0}%
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                Floor space occupied
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '1rem',
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Constraint Penalty
              </div>
              <div style={{
                fontSize: '1.4rem',
                fontWeight: 700,
                color: (report.objective_values.constraint_penalty ?? 0) > 0 ? '#f87171' : '#34d399',
                marginTop: '0.25rem',
              }}>
                ${(report.objective_values.constraint_penalty ?? 0).toLocaleString()}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                {report.soft_violation_count} soft penalty item(s)
              </div>
            </div>
          </div>

          {/* Top Flow Contributors Table */}
          {report.top_contributors && report.top_contributors.material_handling_cost && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                Top Material Handling Flow Contributors
              </h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '0.8rem',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: '6px',
                  overflow: 'hidden',
                }}>
                  <thead>
                    <tr style={{ backgroundColor: 'rgba(255, 255, 255, 0.03)', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Source Department</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Target Department</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Flow (moves)</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Distance ({distanceMetric})</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Cost ($)</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>% of Total MHC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.top_contributors.material_handling_cost.map((item: any, idx: number) => (
                      <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '0.5rem 0.75rem', fontWeight: 500 }}>{item.source}</td>
                        <td style={{ padding: '0.5rem 0.75rem', fontWeight: 500 }}>{item.target}</td>
                        <td style={{ padding: '0.5rem 0.75rem' }}>{item.flow}</td>
                        <td style={{ padding: '0.5rem 0.75rem' }}>{item.distance}m</td>
                        <td style={{ padding: '0.5rem 0.75rem', fontWeight: 600, color: '#38bdf8' }}>${item.cost}</td>
                        <td style={{ padding: '0.5rem 0.75rem' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <div style={{
                              flex: 1,
                              backgroundColor: 'rgba(56, 189, 248, 0.1)',
                              height: '6px',
                              borderRadius: '3px',
                              maxWidth: '60px',
                            }}>
                              <div style={{
                                width: `${Math.min(100, item.percentage || 0)}%`,
                                backgroundColor: '#38bdf8',
                                height: '100%',
                                borderRadius: '3px',
                              }} />
                            </div>
                            <span>{item.percentage}%</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Constraint Violations Table */}
          {report.constraint_violations && report.constraint_violations.length > 0 && (
            <div>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.5rem', color: '#f87171' }}>
                Detected Constraint Violations ({report.constraint_violations.length})
              </h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  fontSize: '0.8rem',
                  backgroundColor: 'var(--bg-card)',
                  borderRadius: '6px',
                  overflow: 'hidden',
                }}>
                  <thead>
                    <tr style={{ backgroundColor: 'rgba(255, 255, 255, 0.03)', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>
                      <th style={{ padding: '0.5rem 0.75rem' }}>ID</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Classification</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Type</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Departments</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Magnitude</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Penalty ($)</th>
                      <th style={{ padding: '0.5rem 0.75rem' }}>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.constraint_violations.map((v, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                        <td style={{ padding: '0.5rem 0.75rem', fontFamily: 'monospace' }}>{v.constraint_id}</td>
                        <td style={{ padding: '0.5rem 0.75rem' }}>
                          <span style={{
                            padding: '0.15rem 0.4rem',
                            borderRadius: '4px',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            backgroundColor: v.classification === 'hard' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                            color: v.classification === 'hard' ? '#f87171' : '#fbbf24',
                          }}>
                            {v.classification.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: '0.5rem 0.75rem' }}>{v.constraint_type}</td>
                        <td style={{ padding: '0.5rem 0.75rem' }}>{v.involved_departments.join(', ')}</td>
                        <td style={{ padding: '0.5rem 0.75rem' }}>{v.magnitude.toFixed(2)}</td>
                        <td style={{ padding: '0.5rem 0.75rem', fontWeight: 600 }}>${v.penalty_cost}</td>
                        <td style={{ padding: '0.5rem 0.75rem', color: 'var(--text-secondary)' }}>{v.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* MULTI-LAYOUT COMPARISON VIEW */}
      {activeTab === 'compare' && comparisonReport && (
        <div>
          <div style={{ marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 600 }}>
              Multi-Layout Benchmark Ranking ({comparisonReport.solution_count} solutions)
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Feasibility-first lexicographical ranking with multi-criteria min-max normalization.
            </p>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '0.8rem',
              backgroundColor: 'var(--bg-card)',
              borderRadius: '8px',
              overflow: 'hidden',
            }}>
              <thead>
                <tr style={{ backgroundColor: 'rgba(255, 255, 255, 0.03)', textAlign: 'left', borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Rank</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Layout / Algorithm</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Status</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Composite Score</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Material Handling Cost</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Flow Distance</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Relationship Score</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Utilization</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Penalty</th>
                </tr>
              </thead>
              <tbody>
                {comparisonReport.reports.map((r, idx) => (
                  <tr
                    key={idx}
                    style={{
                      borderBottom: '1px solid var(--border-color)',
                      backgroundColor: idx === 0 && r.is_feasible ? 'rgba(16, 185, 129, 0.05)' : 'transparent',
                    }}
                  >
                    <td style={{ padding: '0.6rem 0.75rem', fontWeight: 700 }}>
                      <span style={{
                        display: 'inline-block',
                        width: '24px',
                        height: '24px',
                        lineHeight: '24px',
                        textAlign: 'center',
                        borderRadius: '50%',
                        backgroundColor: idx === 0 ? 'var(--accent-color)' : 'rgba(255, 255, 255, 0.05)',
                        color: '#ffffff',
                      }}>
                        {r.rank ?? idx + 1}
                      </span>
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', fontWeight: 600 }}>{r.algorithm_name}</td>
                    <td style={{ padding: '0.6rem 0.75rem' }}>
                      <span style={{
                        padding: '0.15rem 0.45rem',
                        borderRadius: '4px',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        backgroundColor: r.is_feasible ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: r.is_feasible ? '#34d399' : '#f87171',
                      }}>
                        {r.is_feasible ? 'FEASIBLE' : 'INFEASIBLE'}
                      </span>
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', fontWeight: 700, color: 'var(--accent-color)' }}>
                      {r.composite_score !== undefined ? (r.composite_score * 100).toFixed(1) + '%' : '—'}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem' }}>
                      ${(r.objective_values.material_handling_cost ?? 0).toLocaleString()}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem' }}>
                      {(r.objective_values.flow_distance ?? 0).toLocaleString()}m
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem' }}>
                      {r.objective_values.relationship_score ?? 0}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem' }}>
                      {r.objective_values.area_utilization ?? 0}%
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', color: (r.objective_values.constraint_penalty ?? 0) > 0 ? '#f87171' : 'inherit' }}>
                      ${r.objective_values.constraint_penalty ?? 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
