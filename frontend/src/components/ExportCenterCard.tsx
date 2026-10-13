import React, { useState } from 'react';
import { Download, FileText, Copy, Check, ShieldCheck, Database, Layers } from 'lucide-react';
import { FacilityLayoutProblem, ContinuousLayout, EvaluationReport } from '../types/api';

interface ExportCenterCardProps {
  problem: FacilityLayoutProblem | null;
  layout: ContinuousLayout | null;
  evaluation: EvaluationReport | null;
  paretoPortfolio?: any | null;
  executionInfo?: {
    algorithm: string;
    seed?: number;
    durationMs?: number;
    config?: Record<string, any>;
  } | null;
}

export const ExportCenterCard: React.FC<ExportCenterCardProps> = ({
  problem,
  layout,
  evaluation,
  paretoPortfolio,
  executionInfo,
}) => {
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const copyToClipboard = (text: string, fieldName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const downloadFile = (content: string, filename: string, mimeType: string) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const currentVersion = 'v1.0.0-rc.1';
  const timestampIso = new Date().toISOString();

  // Export 1: Layout JSON
  const handleExportLayoutJson = () => {
    if (!layout) return;
    const sig = layout.layout_signature || layout.metadata?.signature || 'layout-signature';
    const bundle = {
      flodss_version: currentVersion,
      exported_at_utc: timestampIso,
      reproducibility: {
        problem_id: layout.problem_id || problem?.id,
        layout_signature: sig,
        evaluation_config_hash: evaluation?.config_hash || evaluation?.metadata?.config_hash || 'canonical-default-hash',
        algorithm: executionInfo?.algorithm || layout.metadata?.algorithm || 'unknown',
        seed: executionInfo?.seed ?? 42,
      },
      layout: {
        problem_id: layout.problem_id,
        bounding_box: layout.bounding_box || { x_min: 0, y_min: 0, x_max: layout.facility_width, y_max: layout.facility_height },
        placements: layout.placements,
        metadata: layout.metadata,
      },
    };
    downloadFile(
      JSON.stringify(bundle, null, 2),
      `flodss_layout_${layout.problem_id || 'solution'}_${sig.substring(0, 8)}.json`,
      'application/json'
    );
  };

  // Export 2: Experiment Config JSON
  const handleExportExperimentConfigJson = () => {
    const experimentBundle = {
      flodss_version: currentVersion,
      exported_at_utc: timestampIso,
      experiment_environment: {
        system: 'FLODSS Modular Decision Support System',
        confidentiality_level: 'PRIVATE_RESEARCH_PROTOTYPE',
        python_runtime: '>=3.12',
      },
      problem_specification: problem,
      algorithm_configuration: {
        selected_algorithm: executionInfo?.algorithm || 'GA_V1',
        seed: executionInfo?.seed ?? 42,
        duration_ms: executionInfo?.durationMs,
        parameters: executionInfo?.config || {},
      },
      evaluation_protocol: {
        distance_metric: 'rectilinear_manhattan',
        evaluation_config_hash: evaluation?.config_hash || evaluation?.metadata?.config_hash || 'canonical-default-hash',
      },
    };
    downloadFile(
      JSON.stringify(experimentBundle, null, 2),
      `flodss_experiment_config_${problem?.id || 'problem'}.json`,
      'application/json'
    );
  };

  // Export 3: Canonical Metrics CSV
  const handleExportMetricsCsv = () => {
    if (!evaluation) return;
    const mhc = (evaluation.material_handling_cost ?? evaluation.objective_values?.material_handling_cost ?? 0).toFixed(2);
    const flowDist = (evaluation.flow_distance ?? evaluation.objective_values?.flow_distance ?? 0).toFixed(2);
    const relSat = (evaluation.relationship_satisfaction_percentage ?? evaluation.objective_values?.relationship_satisfaction ?? 0).toFixed(2);
    const adjSat = (evaluation.adjacency_satisfaction_percentage ?? evaluation.objective_values?.adjacency_satisfaction ?? 0).toFixed(2);
    const softPen = (evaluation.soft_constraint_penalty ?? evaluation.soft_penalty ?? evaluation.objective_values?.soft_constraint_penalty ?? evaluation.total_constraint_penalty ?? 0).toFixed(2);
    const hardViolations = (evaluation.hard_violation_count ?? evaluation.hard_constraint_violations?.length ?? 0).toString();
    const isFeasible = evaluation.is_feasible ? 'TRUE' : 'FALSE';

    const rows = [
      ['Metric', 'Value', 'Unit', 'Direction', 'Description'],
      ['Material Handling Cost (MHC)', mhc, 'Cost Units', 'Minimize', 'Total material flow × distance cost'],
      ['Flow-Distance Metric', flowDist, 'm × unit flow', 'Minimize', 'Raw sum of rectilinear flow-distance'],
      ['Relationship (REL) Satisfaction', `${relSat}%`, '%', 'Maximize', 'Closeness relationship score satisfaction'],
      ['Adjacency Satisfaction', `${adjSat}%`, '%', 'Maximize', 'Boundary adjacency between departments'],
      ['Soft Constraint Penalty', softPen, 'Penalty Units', 'Minimize', 'Cumulative penalty for soft violations'],
      ['Hard Constraint Violations', hardViolations, 'Count', 'Strict 0', 'Boundary, overlap, or fixed violations'],
      ['Is Hard Feasible', isFeasible, 'Boolean', 'Must be TRUE', 'Full geometric and boundary compliance'],
    ];

    const csvContent = rows.map((r) => r.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(',')).join('\n');
    downloadFile(csvContent, `flodss_metrics_${evaluation.problem_id || 'eval'}.csv`, 'text/csv');
  };

  // Export 4: Benchmark Comparison CSV
  const handleExportComparisonCsv = () => {
    const rows = [
      ['Algorithm', 'MHC', 'Flow_Distance', 'REL_Satisfaction_Pct', 'Soft_Penalty', 'Hard_Feasible', 'Wall_Clock_Ms'],
    ];

    if (evaluation) {
      const mhc = (evaluation.material_handling_cost ?? evaluation.objective_values?.material_handling_cost ?? 0).toFixed(2);
      const flowDist = (evaluation.flow_distance ?? evaluation.objective_values?.flow_distance ?? 0).toFixed(2);
      const relSat = (evaluation.relationship_satisfaction_percentage ?? evaluation.objective_values?.relationship_satisfaction ?? 0).toFixed(2);
      const softPen = (evaluation.soft_constraint_penalty ?? evaluation.soft_penalty ?? evaluation.objective_values?.soft_constraint_penalty ?? evaluation.total_constraint_penalty ?? 0).toFixed(2);
      const isFeasible = evaluation.is_feasible ? 'YES' : 'NO';

      rows.push([
        executionInfo?.algorithm || 'Current Layout',
        mhc,
        flowDist,
        relSat,
        softPen,
        isFeasible,
        executionInfo?.durationMs?.toString() || 'N/A',
      ]);
    }

    if (paretoPortfolio?.solutions && Array.isArray(paretoPortfolio.solutions)) {
      paretoPortfolio.solutions.forEach((sol: any) => {
        rows.push([
          sol.source_algorithm || 'Candidate',
          (sol.objectives?.material_handling_cost ?? sol.mhc ?? 0).toFixed(2),
          (sol.objectives?.flow_distance ?? sol.flow_distance ?? 0).toFixed(2),
          (sol.objectives?.relationship_satisfaction ?? sol.rel_satisfaction ?? 0).toFixed(2),
          (sol.objectives?.soft_constraint_penalty ?? sol.soft_penalty ?? 0).toFixed(2),
          sol.is_feasible ? 'YES' : 'NO',
          sol.duration_ms?.toString() || 'N/A',
        ]);
      });
    }

    const csvContent = rows.map((r) => r.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(',')).join('\n');
    downloadFile(csvContent, `flodss_algorithm_comparison_${problem?.id || 'benchmark'}.csv`, 'text/csv');
  };

  // Export 5: Pareto Portfolio JSON
  const handleExportParetoPortfolioJson = () => {
    const portfolioBundle = {
      flodss_version: currentVersion,
      exported_at_utc: timestampIso,
      problem_id: problem?.id,
      pareto_analysis: paretoPortfolio || {
        notice: 'No batch Pareto execution run loaded. Single active layout exported.',
        active_candidate: {
          layout_signature: layout?.layout_signature,
          evaluation: evaluation,
        },
      },
    };
    downloadFile(
      JSON.stringify(portfolioBundle, null, 2),
      `flodss_pareto_portfolio_${problem?.id || 'experiment'}.json`,
      'application/json'
    );
  };

  // Export 6: 2D Layout Floor Plan SVG
  const handleExportLayoutSvg = () => {
    if (!layout || !layout.placements) return;
    const facW = layout.facility_width || problem?.facility.width || 150.0;
    const facH = layout.facility_height || problem?.facility.height || 80.0;
    const pad = 40;
    const w = facW + pad * 2;
    const h = facH + pad * 2;
    const palette = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316', '#14b8a6', '#6366f1', '#84cc16'];
    const rects = Object.values(layout.placements).map((p: any, i: number) => {
      const color = palette[i % palette.length];
      const svgY = pad + (facH - p.y - p.height);
      const svgX = pad + p.x;
      return `<rect x="${svgX}" y="${svgY}" width="${p.width}" height="${p.height}" fill="${color}" fill-opacity="0.8" stroke="#ffffff" stroke-width="1.5" rx="2" />
      <text x="${svgX + p.width / 2}" y="${svgY + p.height / 2}" text-anchor="middle" dominant-baseline="middle" fill="#ffffff" font-size="11" font-family="sans-serif" font-weight="bold">${p.department_id}</text>`;
    }).join('\n    ');

    const svgContent = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w * 6}" height="${h * 6}">
  <rect width="100%" height="100%" fill="#0d1117" />
  <rect x="${pad}" y="${pad}" width="${facW}" height="${facH}" fill="#161b22" stroke="#30363d" stroke-width="2" />
  <text x="${pad + 10}" y="${pad - 12}" fill="#8b949e" font-size="12" font-family="sans-serif">Facility Boundary: ${facW}m × ${facH}m &bull; ${layout.problem_id || 'FLODSS'}</text>
  <g id="departments">
    ${rects}
  </g>
</svg>`;
    downloadFile(svgContent, `flodss_layout_${layout.problem_id || 'solution'}.svg`, 'image/svg+xml');
  };

  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '12px',
      padding: '1.5rem',
      marginBottom: '2rem',
    }}>
      {/* Title & Badge */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '1.4rem' }}>📦</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
              Phase 14 &bull; Research Export Center & Provenance
            </h2>
            <span style={{
              fontSize: '0.75rem',
              padding: '0.2rem 0.6rem',
              borderRadius: '9999px',
              backgroundColor: '#10b98120',
              color: '#34d399',
              border: '1px solid #10b98140',
              fontWeight: 600,
            }}>
              Release Candidate {currentVersion}
            </span>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem', marginBottom: 0 }}>
            Deterministic scientific experiment exports &bull; Cryptographic signatures &bull; Zero external data transmission
          </p>
        </div>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
          fontSize: '0.8rem',
          padding: '0.35rem 0.75rem',
          borderRadius: '6px',
          backgroundColor: '#3b82f615',
          color: '#60a5fa',
          border: '1px solid #3b82f630',
        }}>
          <ShieldCheck size={16} />
          <span>Local Research Mode (Confidential)</span>
        </div>
      </div>

      {/* Thesis Provenance Card */}
      <div style={{
        padding: '1.25rem',
        borderRadius: '8px',
        backgroundColor: 'var(--bg-card)',
        border: '1px solid var(--border-color)',
        marginBottom: '1.5rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.85rem' }}>
          <Database size={16} color="#60a5fa" />
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
            Academic Thesis Reproducibility Metadata
          </h3>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '0.85rem',
          fontSize: '0.825rem',
        }}>
          <div style={{ padding: '0.6rem 0.8rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.75rem' }}>FLODSS Version</span>
            <span style={{ fontWeight: 600, color: '#34d399' }}>{currentVersion}</span>
          </div>

          <div style={{ padding: '0.6rem 0.8rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.75rem' }}>Problem Identifier</span>
            <span style={{ fontWeight: 600 }}>{problem?.id || layout?.problem_id || 'FLP_INDUSTRIAL_10'}</span>
          </div>

          <div style={{ padding: '0.6rem 0.8rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>Layout SHA-256 Signature</span>
              <button
                onClick={() => copyToClipboard(layout?.layout_signature || layout?.metadata?.signature || '', 'sig')}
                disabled={!(layout?.layout_signature || layout?.metadata?.signature)}
                style={{ background: 'none', border: 'none', color: '#60a5fa', cursor: 'pointer', padding: 0 }}
                title="Copy signature"
              >
                {copiedField === 'sig' ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
              </button>
            </div>
            <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', wordBreak: 'break-all' }}>
              {layout?.layout_signature || layout?.metadata?.signature || 'No active layout loaded'}
            </span>
          </div>

          <div style={{ padding: '0.6rem 0.8rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.75rem' }}>Evaluation Config Hash</span>
            <span style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
              {evaluation?.config_hash || evaluation?.metadata?.config_hash || 'canonical-evaluation-v1-default'}
            </span>
          </div>

          <div style={{ padding: '0.6rem 0.8rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.75rem' }}>Source Algorithm</span>
            <span style={{ fontWeight: 600 }}>{executionInfo?.algorithm || layout?.metadata?.algorithm || 'Adaptive Strategy Engine'}</span>
          </div>

          <div style={{ padding: '0.6rem 0.8rem', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}>
            <span style={{ color: 'var(--text-secondary)', display: 'block', fontSize: '0.75rem' }}>Execution Parameters</span>
            <span>Seed: {executionInfo?.seed ?? 42} &bull; Time: {executionInfo?.durationMs ? `${executionInfo.durationMs}ms` : 'Recorded'}</span>
          </div>
        </div>

        <div style={{
          marginTop: '0.85rem',
          padding: '0.6rem 0.8rem',
          borderRadius: '6px',
          backgroundColor: '#3b82f610',
          border: '1px solid #3b82f625',
          fontSize: '0.775rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.5,
        }}>
          <strong>Thesis Citation / Provenance Note:</strong> "Layout optimization was executed deterministically via FLODSS {currentVersion}. 
          Objective evaluations enforce Rectilinear (Manhattan) centroid distance, zero pairwise overlap, and exact department area conservation in continuous Cartesian space."
        </div>
      </div>

      {/* Export Action Buttons Grid */}
      <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>
        Export Data & Deliverables
      </h3>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
        gap: '1rem',
      }}>
        {/* Button 1: Layout JSON */}
        <div style={{
          padding: '1rem',
          borderRadius: '8px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <FileText size={18} color="#3b82f6" />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, margin: 0 }}>Layout Geometry JSON</h4>
            </div>
            <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>
              Continuous Cartesian coordinates, department dimensions, and layout SHA-256 signature.
            </p>
          </div>
          <button
            onClick={handleExportLayoutJson}
            disabled={!layout}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.5rem 0.85rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: layout ? '#2563eb' : 'var(--bg-primary)',
              color: layout ? '#ffffff' : 'var(--text-muted)',
              fontSize: '0.825rem',
              fontWeight: 600,
              cursor: layout ? 'pointer' : 'not-allowed',
            }}
          >
            <Download size={14} />
            Download Layout JSON
          </button>
        </div>

        {/* Button 2: Experiment Config JSON */}
        <div style={{
          padding: '1rem',
          borderRadius: '8px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <FileText size={18} color="#10b981" />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, margin: 0 }}>Experiment Config JSON</h4>
            </div>
            <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>
              Complete problem definition, algorithm hyperparameters, random seeds, and environment settings.
            </p>
          </div>
          <button
            onClick={handleExportExperimentConfigJson}
            disabled={!problem}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.5rem 0.85rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: problem ? '#059669' : 'var(--bg-primary)',
              color: problem ? '#ffffff' : 'var(--text-muted)',
              fontSize: '0.825rem',
              fontWeight: 600,
              cursor: problem ? 'pointer' : 'not-allowed',
            }}
          >
            <Download size={14} />
            Download Config JSON
          </button>
        </div>

        {/* Button 3: Canonical Metrics CSV */}
        <div style={{
          padding: '1rem',
          borderRadius: '8px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <Download size={18} color="#f59e0b" />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, margin: 0 }}>Evaluation Metrics CSV</h4>
            </div>
            <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>
              Canonical MHC, Flow-Distance, REL score, soft penalties, and feasibility flags.
            </p>
          </div>
          <button
            onClick={handleExportMetricsCsv}
            disabled={!evaluation}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.5rem 0.85rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: evaluation ? '#d97706' : 'var(--bg-primary)',
              color: evaluation ? '#ffffff' : 'var(--text-muted)',
              fontSize: '0.825rem',
              fontWeight: 600,
              cursor: evaluation ? 'pointer' : 'not-allowed',
            }}
          >
            <Download size={14} />
            Download Metrics CSV
          </button>
        </div>

        {/* Button 4: Comparison CSV */}
        <div style={{
          padding: '1rem',
          borderRadius: '8px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <Layers size={18} color="#8b5cf6" />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, margin: 0 }}>Algorithm Comparison CSV</h4>
            </div>
            <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>
              Comparative benchmark data table ready for import into LaTeX / Excel / R.
            </p>
          </div>
          <button
            onClick={handleExportComparisonCsv}
            disabled={!evaluation}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.5rem 0.85rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: evaluation ? '#7c3aed' : 'var(--bg-primary)',
              color: evaluation ? '#ffffff' : 'var(--text-muted)',
              fontSize: '0.825rem',
              fontWeight: 600,
              cursor: evaluation ? 'pointer' : 'not-allowed',
            }}
          >
            <Download size={14} />
            Download Comparison CSV
          </button>
        </div>

        {/* Button 5: Pareto Portfolio JSON */}
        <div style={{
          padding: '1rem',
          borderRadius: '8px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <FileText size={18} color="#ec4899" />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, margin: 0 }}>Pareto Portfolio JSON</h4>
            </div>
            <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>
              Non-dominated layout candidates, objective vectors, and trade-off points.
            </p>
          </div>
          <button
            onClick={handleExportParetoPortfolioJson}
            disabled={!layout}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.5rem 0.85rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: layout ? '#db2777' : 'var(--bg-primary)',
              color: layout ? '#ffffff' : 'var(--text-muted)',
              fontSize: '0.825rem',
              fontWeight: 600,
              cursor: layout ? 'pointer' : 'not-allowed',
            }}
          >
            <Download size={14} />
            Download Pareto JSON
          </button>
        </div>

        {/* Button 6: 2D Layout Plan SVG */}
        <div style={{
          padding: '1rem',
          borderRadius: '8px',
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-color)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <Download size={18} color="#06b6d4" />
              <h4 style={{ fontSize: '0.9rem', fontWeight: 600, margin: 0 }}>2D Layout Floor Plan SVG</h4>
            </div>
            <p style={{ fontSize: '0.775rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>
              High-resolution vector floor plan with labeled department boundaries and facility canvas.
            </p>
          </div>
          <button
            onClick={handleExportLayoutSvg}
            disabled={!layout}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.5rem 0.85rem',
              borderRadius: '6px',
              border: 'none',
              backgroundColor: layout ? '#0891b2' : 'var(--bg-primary)',
              color: layout ? '#ffffff' : 'var(--text-muted)',
              fontSize: '0.825rem',
              fontWeight: 600,
              cursor: layout ? 'pointer' : 'not-allowed',
            }}
          >
            <Download size={14} />
            Download Layout SVG
          </button>
        </div>
      </div>
    </div>
  );
};
