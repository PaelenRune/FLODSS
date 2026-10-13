import React, { useState, useEffect, useMemo } from 'react';
import {
  ParetoAnalysisResult,
  ContinuousLayout,
  ContinuousPlacement,
} from '../types/api';
import { fetchParetoAnalysis } from '../services/api';
import { LayoutCanvas } from './LayoutCanvas';
import { useLanguage } from '../context/LanguageContext';

export const ParetoAnalysisCard: React.FC = () => {
  const { t } = useLanguage();
  const [analysisResult, setAnalysisResult] = useState<ParetoAnalysisResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [activeProfile, setActiveProfile] = useState<string>('balanced');

  useEffect(() => {
    loadAnalysis();
  }, []);

  const loadAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchParetoAnalysis({
        problem_id: 'FLP_INDUSTRIAL_10',
        include_saved_baselines: true,
      });
      setAnalysisResult(data);
      // Default to first frontier candidate
      if (data.frontier_candidate_ids.length > 0) {
        setSelectedCandidateId(data.frontier_candidate_ids[0]);
      } else if (data.candidates.length > 0) {
        setSelectedCandidateId(data.candidates[0].candidate_id);
      }
    } catch (err: any) {
      setError(err.message || t('Pareto analizi yüklenemedi', 'Failed to load Pareto analysis'));
    } finally {
      setLoading(false);
    }
  };

  const selectedCandidate = useMemo(() => {
    if (!analysisResult || !selectedCandidateId) return null;
    return analysisResult.candidates.find((c) => c.candidate_id === selectedCandidateId) || null;
  }, [analysisResult, selectedCandidateId]);

  // Construct continuous layout for LayoutCanvas preview
  const previewLayout = useMemo<ContinuousLayout | null>(() => {
    if (!selectedCandidate || !selectedCandidate.placements) return null;

    const placementsMap: Record<string, ContinuousPlacement> = {};
    for (const [did, p] of Object.entries(selectedCandidate.placements)) {
      placementsMap[did] = {
        department_id: did,
        x: p.x ?? p.origin?.x ?? 0,
        y: p.y ?? p.origin?.y ?? 0,
        width: p.width ?? p.dimensions?.width ?? 10,
        height: p.height ?? p.dimensions?.height ?? 10,
        orientation_degrees: p.orientation_degrees ?? 0,
      };
    }

    return {
      problem_id: selectedCandidate.problem_id || 'FLP_INDUSTRIAL_10',
      representation_type: 'continuous',
      facility_width: 150.0,
      facility_height: 80.0,
      placements: placementsMap,
    };
  }, [selectedCandidate]);

  // Scatter chart coordinate mapping
  const chartData = useMemo(() => {
    if (!analysisResult || analysisResult.candidates.length === 0) return null;

    const candidates = analysisResult.candidates;
    const mhcValues = candidates.map((c) => c.objective_values.material_handling_cost ?? 0);
    const relValues = candidates.map((c) => c.objective_values.relationship_satisfaction ?? 0);

    const minMhc = Math.min(...mhcValues) * 0.95;
    const maxMhc = Math.max(...mhcValues) * 1.05;
    const minRel = Math.min(40, Math.min(...relValues) * 0.95);
    const maxRel = Math.max(70, Math.max(...relValues) * 1.05);

    const width = 640;
    const height = 320;
    const padX = 70;
    const padY = 40;

    const scaleX = (mhc: number) => padX + ((mhc - minMhc) / (maxMhc - minMhc || 1)) * (width - 2 * padX);
    const scaleY = (rel: number) => height - padY - ((rel - minRel) / (maxRel - minRel || 1)) * (height - 2 * padY);

    return {
      minMhc,
      maxMhc,
      minRel,
      maxRel,
      width,
      height,
      padX,
      padY,
      scaleX,
      scaleY,
      points: candidates.map((c) => ({
        candidate: c,
        x: scaleX(c.objective_values.material_handling_cost ?? 0),
        y: scaleY(c.objective_values.relationship_satisfaction ?? 0),
        isFrontier: c.pareto_rank === 1,
        mhc: c.objective_values.material_handling_cost ?? 0,
        rel: c.objective_values.relationship_satisfaction ?? 0,
        soft: c.objective_values.soft_penalty ?? 0,
      })),
    };
  }, [analysisResult]);

  const activeRecommendation = analysisResult?.recommendations[activeProfile];

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-card, #ffffff)',
        border: '1px solid var(--border-color, #e2e8f0)',
        borderRadius: '10px',
        padding: '1.75rem',
        marginBottom: '2rem',
        boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.25rem',
        }}
      >
        <div>
          <h2
            style={{
              fontSize: '1.35rem',
              fontWeight: 700,
              margin: 0,
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              color: 'var(--text-primary, #0f172a)',
            }}
          >
            <span>🎯</span> {t('Çok Amaçlı Pareto Frontier & Karar Destek Sistemi', 'Multi-Objective Pareto Frontier & Decision Support (Phase 10)')}
          </h2>
          <p style={{ margin: '0.35rem 0 0', fontSize: '0.875rem', color: 'var(--text-secondary, #64748b)' }}>
            {t(
              'Material Handling Cost (MHC $), Muther REL Satisfaction (%) ve Soft Constraint Penalty ($) eksenlerinde Non-Dominated Sorting ve ödünleşim (Trade-Off) analizi.',
              'Rigorous non-dominated sorting and trade-off analysis across Material Handling Cost ($), Muther Relationship Satisfaction (%), and Soft Penalties ($).'
            )}
          </p>
        </div>
        <div>
          <button
            onClick={loadAnalysis}
            disabled={loading}
            style={{
              padding: '0.55rem 1.1rem',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {loading ? t('Frontier Hesaplanıyor...', 'Evaluating Frontier...') : t('↻ Pareto Portföyünü Yeniden Değerlendir', '↻ Re-evaluate Pareto Portfolio')}
          </button>
        </div>
      </div>

      {error && (
        <div
          style={{
            backgroundColor: '#fef2f2',
            border: '1px solid #f87171',
            color: '#991b1b',
            borderRadius: '6px',
            padding: '0.75rem 1rem',
            fontSize: '0.85rem',
            marginBottom: '1rem',
          }}
        >
          ⚠️ {error}
        </div>
      )}

      {/* Summary KPI Badges */}
      {analysisResult && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
            marginBottom: '1.5rem',
          }}
        >
          <div style={{ backgroundColor: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '8px', padding: '0.85rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#166534', textTransform: 'uppercase' }}>Pareto Frontier (Rank 1)</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#15803d' }}>
              {analysisResult.frontier_count} {t('Çözüm', 'Solutions')}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#166534' }}>{t('Kesin Non-Dominated optimal alternatifler', 'Strictly non-dominated optimal choices')}</div>
          </div>
          <div style={{ backgroundColor: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '8px', padding: '0.85rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#1e40af', textTransform: 'uppercase' }}>{t('Geçerli Adaylar (Valid)', 'Valid Candidates')}</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1d4ed8' }}>
              {analysisResult.valid_candidates_count} {t('Yerleşim', 'Layouts')}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#1e40af' }}>{t('%100 tam ve Feasible geometriler', '100% complete & feasible geometries')}</div>
          </div>
          <div style={{ backgroundColor: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '0.85rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', textTransform: 'uppercase' }}>Pareto Layers</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#334155' }}>
              {Object.keys(analysisResult.ranks).length} Ranks
            </div>
            <div style={{ fontSize: '0.75rem', color: '#475569' }}>{t('Hiyerarşik Non-Dominated katmanlama', 'Hierarchical non-dominated peeling')}</div>
          </div>
          <div style={{ backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '8px', padding: '0.85rem' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#991b1b', textTransform: 'uppercase' }}>{t('Hariç Tutulanlar (Excluded)', 'Excluded Layouts')}</div>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#b91c1c' }}>
              {analysisResult.excluded_candidates_count}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#991b1b' }}>{t('Kopya, çakışmalı veya eksik yerleşimler', 'Duplicates, overlaps or incomplete')}</div>
          </div>
        </div>
      )}

      {/* Main Analysis View: 2-Column Grid */}
      {analysisResult && chartData && (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1.2fr) minmax(320px, 1fr)', gap: '1.5rem', marginBottom: '1.5rem' }}>
          {/* Column 1: Pareto Scatter Chart */}
          <div
            style={{
              border: '1px solid var(--border-color, #e2e8f0)',
              borderRadius: '8px',
              padding: '1.25rem',
              backgroundColor: '#fafbfc',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#0f172a' }}>
                📈 {t('Çok Amaçlı Pareto Frontier Grafiği (MHC vs. REL Satisfaction)', 'Multi-Objective Frontier Chart (MHC vs. Relationship)')}
              </div>
              <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                {t('İdeal: Sol-Üst (Düşük MHC, Yüksek REL)', 'Ideal: Top-Left (Low Cost, High Rel)')}
              </div>
            </div>

            {/* SVG Scatter Chart */}
            <div style={{ position: 'relative', width: '100%', overflowX: 'auto' }}>
              <svg viewBox={`0 0 ${chartData.width} ${chartData.height}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
                {/* Axes and Grid Lines */}
                <line
                  x1={chartData.padX}
                  y1={chartData.height - chartData.padY}
                  x2={chartData.width - chartData.padX + 20}
                  y2={chartData.height - chartData.padY}
                  stroke="#cbd5e1"
                  strokeWidth="1.5"
                />
                <line
                  x1={chartData.padX}
                  y1={chartData.padY - 10}
                  x2={chartData.padX}
                  y2={chartData.height - chartData.padY}
                  stroke="#cbd5e1"
                  strokeWidth="1.5"
                />

                {/* Axis Labels */}
                <text
                  x={chartData.width / 2}
                  y={chartData.height - 8}
                  textAnchor="middle"
                  fontSize="11"
                  fill="#475569"
                  fontWeight="600"
                >
                  {t('Material Handling Cost (MHC $) ➔ [Düşük Daha İyi / Minimize]', 'Material Handling Cost (MHC in $) ➔ [Lower is Better]')}
                </text>
                <text
                  x={16}
                  y={chartData.height / 2}
                  textAnchor="middle"
                  fontSize="11"
                  fill="#475569"
                  fontWeight="600"
                  transform={`rotate(-90 16 ${chartData.height / 2})`}
                >
                  {t('REL Satisfaction (%) ➔ [Yüksek Daha İyi / Maximize]', 'Relationship Satisfaction (%) ➔ [Higher is Better]')}
                </text>

                {/* X Axis Ticks */}
                <text x={chartData.padX} y={chartData.height - chartData.padY + 16} fontSize="9" fill="#64748b" textAnchor="middle">
                  ${Math.round(chartData.minMhc / 1000)}k
                </text>
                <text x={chartData.width - chartData.padX} y={chartData.height - chartData.padY + 16} fontSize="9" fill="#64748b" textAnchor="middle">
                  ${Math.round(chartData.maxMhc / 1000)}k
                </text>

                {/* Y Axis Ticks */}
                <text x={chartData.padX - 8} y={chartData.height - chartData.padY} fontSize="9" fill="#64748b" textAnchor="end">
                  {Math.round(chartData.minRel)}%
                </text>
                <text x={chartData.padX - 8} y={chartData.padY} fontSize="9" fill="#64748b" textAnchor="end">
                  {Math.round(chartData.maxRel)}%
                </text>

                {/* Connecting Frontier Line if >1 frontier points */}
                {(() => {
                  const frontierPoints = chartData.points
                    .filter((p) => p.isFrontier)
                    .sort((a, b) => a.mhc - b.mhc);
                  if (frontierPoints.length >= 2) {
                    const pathD = frontierPoints.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`).join(' ');
                    return <path d={pathD} fill="none" stroke="#10b981" strokeWidth="2" strokeDasharray="4 3" />;
                  }
                  return null;
                })()}

                {/* Scatter Points */}
                {chartData.points.map((pt, i) => {
                  const isSelected = selectedCandidateId === pt.candidate.candidate_id;
                  const circleFill = pt.isFrontier ? '#10b981' : pt.candidate.pareto_rank === 2 ? '#6366f1' : '#94a3b8';
                  const strokeCol = isSelected ? '#ea580c' : pt.isFrontier ? '#047857' : '#475569';
                  const radius = pt.isFrontier ? (isSelected ? 9 : 7) : isSelected ? 8 : 6;

                  return (
                    <g
                      key={i}
                      style={{ cursor: 'pointer' }}
                      onClick={() => setSelectedCandidateId(pt.candidate.candidate_id)}
                    >
                      {/* Highlight aura for selected or frontier */}
                      {isSelected && (
                        <circle cx={pt.x} cy={pt.y} r={radius + 5} fill="#ea580c" opacity="0.25" />
                      )}
                      {pt.isFrontier && !isSelected && (
                        <circle cx={pt.x} cy={pt.y} r={radius + 3} fill="#10b981" opacity="0.25" />
                      )}

                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r={radius}
                        fill={circleFill}
                        stroke={strokeCol}
                        strokeWidth={isSelected ? 3 : 1.5}
                      />

                      {/* Rank / Label Tag */}
                      <text
                        x={pt.x}
                        y={pt.y - radius - 4}
                        fontSize="9"
                        fontWeight={pt.isFrontier ? '700' : '500'}
                        fill={pt.isFrontier ? '#047857' : '#334155'}
                        textAnchor="middle"
                      >
                        {pt.candidate.candidate_id.replace('GA_SEED_', 'S-').slice(0, 10)}
                        {pt.isFrontier && ' ★'}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Legend */}
            <div style={{ display: 'flex', gap: '1.25rem', marginTop: '0.75rem', fontSize: '0.785rem', color: '#475569', justifyContent: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#10b981', display: 'inline-block' }} />
                <strong>Pareto Frontier (Rank 1)</strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#6366f1', display: 'inline-block' }} />
                <span>Rank 2 Sub-Optimal</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#94a3b8', display: 'inline-block' }} />
                <span>Dominated (Rank 3+)</span>
              </div>
            </div>
          </div>

          {/* Column 2: Selected Candidate Floor Plan & Metrics */}
          <div
            style={{
              border: '1px solid var(--border-color, #e2e8f0)',
              borderRadius: '8px',
              padding: '1.25rem',
              backgroundColor: '#ffffff',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
              <div>
                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                  {t('Aday Yerleşim Planı Önizlemesi', 'Candidate Floor Plan Preview')}
                </div>
                <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a' }}>
                  {selectedCandidate?.candidate_id || t('Seçilmedi', 'None Selected')}
                </div>
              </div>
              {selectedCandidate && (
                <span
                  style={{
                    padding: '3px 10px',
                    borderRadius: '9999px',
                    fontSize: '0.75rem',
                    fontWeight: 700,
                    backgroundColor: selectedCandidate.is_non_dominated ? '#dcfce7' : '#f1f5f9',
                    color: selectedCandidate.is_non_dominated ? '#15803d' : '#475569',
                    border: `1px solid ${selectedCandidate.is_non_dominated ? '#86efac' : '#cbd5e1'}`,
                  }}
                >
                  {selectedCandidate.is_non_dominated ? '★ Pareto Frontier' : `Rank ${selectedCandidate.pareto_rank} Dominated`}
                </span>
              )}
            </div>

            {/* Objective Score Cards */}
            {selectedCandidate && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', marginBottom: '0.85rem' }}>
                <div style={{ padding: '0.5rem', backgroundColor: '#f8fafc', borderRadius: '6px', textAlign: 'center', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.7rem', color: '#64748b' }}>MHC Cost</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                    ${selectedCandidate.objective_values.material_handling_cost?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                </div>
                <div style={{ padding: '0.5rem', backgroundColor: '#f8fafc', borderRadius: '6px', textAlign: 'center', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.7rem', color: '#64748b' }}>REL Satisfaction</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#16a34a' }}>
                    {selectedCandidate.objective_values.relationship_satisfaction?.toFixed(2)}%
                  </div>
                </div>
                <div style={{ padding: '0.5rem', backgroundColor: '#f8fafc', borderRadius: '6px', textAlign: 'center', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.7rem', color: '#64748b' }}>Soft Penalty</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: selectedCandidate.objective_values.soft_penalty ? '#dc2626' : '#15803d' }}>
                    ${selectedCandidate.objective_values.soft_penalty?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </div>
                </div>
              </div>
            )}

            {/* Canvas Preview */}
            <div style={{ minHeight: '180px' }}>
              <LayoutCanvas layout={previewLayout} />
            </div>

            {/* Dominated Details */}
            {selectedCandidate && selectedCandidate.dominated_by.length > 0 && (
              <div style={{ marginTop: '0.75rem', padding: '0.5rem 0.75rem', backgroundColor: '#fffbeb', border: '1px solid #fef3c7', borderRadius: '6px', fontSize: '0.75rem', color: '#92400e' }}>
                ⚠️ <strong>Dominated by:</strong> {selectedCandidate.dominated_by.join(', ')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Decision Support & Weighted Recommendation Section */}
      {analysisResult && (
        <div
          style={{
            border: '1px solid var(--border-color, #e2e8f0)',
            borderRadius: '8px',
            padding: '1.25rem',
            backgroundColor: '#f8fafc',
            marginBottom: '1.5rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '1rem' }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#0f172a' }}>
                🧭 {t('Karar Destek: Çok Kriterli Tercih Profilleri (Multi-Criteria Profiles)', 'Decision Support: Multi-Criteria Preference Profiles')}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#64748b' }}>
                {t(
                  'Ödünleşim faydasını değerlendirmek ve önerilen yerleşimi görmek için bir işletme öncelik profili seçin.',
                  'Select a business priority profile to evaluate trade-off utility and receive a recommended layout.'
                )}
              </div>
            </div>

            {/* Profile Selection Buttons */}
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {[
                { id: 'cost_priority', label: t('💰 Maliyet Öncelikli (70% MHC)', '💰 Cost Priority (70% MHC)') },
                { id: 'relationship_priority', label: t('🤝 Yakınlık Öncelikli (70% REL)', '🤝 Rel Priority (70% Rel)') },
                { id: 'soft_constraint_priority', label: t('🛡️ Ceza Kaçınımlı (70% Soft)', '🛡️ Penalty Aversion (70% Soft)') },
                { id: 'balanced', label: t('⚖️ Dengeli (Eşit Ağırlık)', '⚖️ Balanced (Equal Weights)') },
              ].map((prof) => (
                <button
                  key={prof.id}
                  onClick={() => setActiveProfile(prof.id)}
                  style={{
                    padding: '0.4rem 0.8rem',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: activeProfile === prof.id ? 700 : 500,
                    backgroundColor: activeProfile === prof.id ? '#2563eb' : '#ffffff',
                    color: activeProfile === prof.id ? '#ffffff' : '#334155',
                    border: '1px solid #cbd5e1',
                    cursor: 'pointer',
                  }}
                >
                  {prof.label}
                </button>
              ))}
            </div>
          </div>

          {/* Active Profile Recommendation Card */}
          {activeRecommendation && (
            <div
              style={{
                backgroundColor: '#ffffff',
                border: '1px solid #bfdbfe',
                borderRadius: '6px',
                padding: '0.85rem 1.15rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                flexWrap: 'wrap',
                gap: '1rem',
              }}
            >
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <span style={{ fontSize: '1.25rem' }}>🏆</span>
                  <span style={{ fontWeight: 700, color: '#1e3a8a', fontSize: '0.95rem' }}>
                    {t('Önerilen Aday:', 'Recommended:')} {activeRecommendation.recommended_candidate_id}
                  </span>
                  <span
                    style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      backgroundColor: activeRecommendation.is_on_pareto_frontier ? '#dcfce7' : '#fee2e2',
                      color: activeRecommendation.is_on_pareto_frontier ? '#15803d' : '#991b1b',
                    }}
                  >
                    {activeRecommendation.is_on_pareto_frontier ? 'Pareto Optimal' : 'Non-Pareto Dominated'}
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#475569', marginTop: '0.25rem', maxWidth: '750px' }}>
                  {activeRecommendation.rationale}
                </div>
              </div>

              <button
                onClick={() => setSelectedCandidateId(activeRecommendation.recommended_candidate_id)}
                style={{
                  padding: '0.45rem 0.9rem',
                  backgroundColor: '#1d4ed8',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {t('Yerleşimi İncele ➔', 'Inspect Layout ➔')}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Candidate Ranking Table */}
      {analysisResult && (
        <div style={{ overflowX: 'auto', marginBottom: '1.5rem' }}>
          <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#0f172a', marginBottom: '0.6rem' }}>
            📋 {t('Değerlendirilen Aday Portföy Sıralaması (Portfolio Ranking)', 'Evaluated Candidates Portfolio Ranking')}
          </div>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '0.825rem',
              textAlign: 'left',
            }}
          >
            <thead>
              <tr style={{ backgroundColor: '#f1f5f9', borderBottom: '2px solid #cbd5e1' }}>
                <th style={{ padding: '0.6rem 0.8rem' }}>Rank</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>{t('Aday ID', 'Candidate ID')}</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>{t('Kaynak Algoritma', 'Algorithm Source')}</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>MHC Cost ($)</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>REL Satisfaction (%)</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>Soft Penalty ($)</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>Flow-Distance</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>{t('Durum', 'Status')}</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>{t('İşlem', 'Action')}</th>
              </tr>
            </thead>
            <tbody>
              {analysisResult.candidates.map((cand) => {
                const isSelected = selectedCandidateId === cand.candidate_id;
                const isRank1 = cand.pareto_rank === 1;

                return (
                  <tr
                    key={cand.candidate_id}
                    onClick={() => setSelectedCandidateId(cand.candidate_id)}
                    style={{
                      borderBottom: '1px solid #e2e8f0',
                      backgroundColor: isSelected
                        ? '#eff6ff'
                        : isRank1
                        ? '#f0fdf4'
                        : '#ffffff',
                      cursor: 'pointer',
                    }}
                  >
                    <td style={{ padding: '0.6rem 0.8rem', fontWeight: 700 }}>
                      {isRank1 ? (
                        <span style={{ color: '#16a34a', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          ★ 1 (Frontier)
                        </span>
                      ) : (
                        `Rank ${cand.pareto_rank}`
                      )}
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', fontWeight: isSelected ? 700 : 500 }}>
                      {cand.candidate_id}
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', color: '#475569' }}>
                      {cand.algorithm_source}
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>
                      ${cand.objective_values.material_handling_cost?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', color: '#16a34a', fontWeight: 600 }}>
                      {cand.objective_values.relationship_satisfaction?.toFixed(2)}%
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', color: cand.objective_values.soft_penalty ? '#dc2626' : '#15803d', fontWeight: 600 }}>
                      ${cand.objective_values.soft_penalty?.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', color: '#64748b' }}>
                      {cand.auxiliary_metrics.flow_distance?.toLocaleString('en-US', { minimumFractionDigits: 2 })} m
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem' }}>
                      <span
                        style={{
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '0.7rem',
                          fontWeight: 600,
                          backgroundColor: cand.is_feasible ? '#dcfce7' : '#fee2e2',
                          color: cand.is_feasible ? '#15803d' : '#991b1b',
                        }}
                      >
                        {cand.is_feasible ? 'Feasible' : 'Infeasible'}
                      </span>
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedCandidateId(cand.candidate_id);
                        }}
                        style={{
                          padding: '0.25rem 0.6rem',
                          fontSize: '0.75rem',
                          backgroundColor: isSelected ? '#1d4ed8' : '#f1f5f9',
                          color: isSelected ? '#ffffff' : '#334155',
                          border: '1px solid #cbd5e1',
                          borderRadius: '4px',
                          cursor: 'pointer',
                        }}
                      >
                        {isSelected ? t('İnceleniyor', 'Viewing') : t('Seç', 'Select')}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Excluded Candidates Section if any */}
      {analysisResult && analysisResult.excluded.length > 0 && (
        <div style={{ marginTop: '1rem', padding: '0.85rem 1rem', backgroundColor: '#fef2f2', border: '1px solid #fecaca', borderRadius: '6px' }}>
          <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#991b1b', marginBottom: '0.4rem' }}>
            🚫 {t('Hariç Tutulan Adaylar (Excluded Candidates)', 'Excluded Candidates')} ({analysisResult.excluded.length})
          </div>
          <ul style={{ margin: 0, paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#7f1d1d' }}>
            {analysisResult.excluded.map((exc, idx) => (
              <li key={idx} style={{ marginBottom: '0.2rem' }}>
                <strong>{exc.candidate_id}</strong> ({exc.algorithm_source}): {exc.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
