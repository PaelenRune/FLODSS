import React, { useState, useEffect, useMemo } from 'react';
import {
  ParetoAnalysisResult,
  ContinuousLayout,
  ContinuousPlacement,
  FacilityLayoutProblem,
  ParetoCandidate,
  LayoutValidationResult,
} from '../types/api';
import { fetchParetoAnalysis } from '../services/api';
import { LayoutCanvas } from './LayoutCanvas';
import { DecisionGuidanceBox } from './DecisionGuidanceBox';
import { useLanguage } from '../context/LanguageContext';
import { formatCost } from '../utils/formatters';
import { Scale, CheckCircle2, ArrowRightLeft, Target, AlertTriangle } from 'lucide-react';

export interface ParetoAnalysisCardProps {
  problem?: FacilityLayoutProblem | null;
  activeLayout?: ContinuousLayout | null;
  onSelectCandidate?: (candidate: ParetoCandidate) => void;
}

function candidateToContinuousLayout(
  cand: ParetoCandidate | null,
  problem: FacilityLayoutProblem | null | undefined
): ContinuousLayout | null {
  if (!cand || !cand.placements) return null;
  const placementsMap: Record<string, ContinuousPlacement> = {};
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
  const facWidth = problem?.facility?.width ?? (problem as any)?.facility_width ?? 150.0;
  const facHeight = problem?.facility?.height ?? (problem as any)?.facility_height ?? 80.0;

  return {
    problem_id: cand.problem_id || problem?.id || 'FLP_INDUSTRIAL_10',
    representation_type: 'continuous',
    facility_width: facWidth,
    facility_height: facHeight,
    placements: placementsMap,
    layout_signature: cand.layout_signature,
  };
}

function candidateToValidation(cand: ParetoCandidate | null): LayoutValidationResult | null {
  if (!cand) return null;
  return {
    is_valid: cand.is_feasible,
    errors: cand.is_feasible ? [] : ['Candidate marked infeasible in Pareto portfolio'],
    warnings: [],
    total_overlap_area: 0,
    checked_departments: Object.keys(cand.placements || {}),
    metrics: {
      occupied_area: 0,
      free_area: 0,
      utilization_ratio: 0,
      total_overlap_area: 0,
      bounding_envelope_area: 0,
      compactness: 0,
    },
    signature: cand.layout_signature,
  };
}

export const ParetoAnalysisCard: React.FC<ParetoAnalysisCardProps> = ({
  problem,
  onSelectCandidate,
}) => {
  const { t } = useLanguage();
  const [analysisResult, setAnalysisResult] = useState<ParetoAnalysisResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [activeProfile, setActiveProfile] = useState<string>('balanced');

  // Comparison mode states
  const [compareMode, setCompareMode] = useState<boolean>(false);
  const [compareCandidateId, setCompareCandidateId] = useState<string | null>(null);

  // Active solution notification feedback
  const [activeSetMessage, setActiveSetMessage] = useState<string | null>(null);

  useEffect(() => {
    loadAnalysis();
  }, [problem?.id]);

  const loadAnalysis = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchParetoAnalysis({
        problem_id: problem?.id || 'FLP_INDUSTRIAL_10',
        problem: problem ? (problem as any) : undefined,
        include_saved_baselines: true,
      });
      setAnalysisResult(data);
      // Default to first frontier candidate
      if (data.frontier_candidate_ids.length > 0) {
        setSelectedCandidateId(data.frontier_candidate_ids[0]);
        // Default candidate B to second candidate if available
        if (data.frontier_candidate_ids.length > 1) {
          setCompareCandidateId(data.frontier_candidate_ids[1]);
        } else if (data.candidates.length > 1) {
          setCompareCandidateId(data.candidates[1].candidate_id);
        }
      } else if (data.candidates.length > 0) {
        setSelectedCandidateId(data.candidates[0].candidate_id);
        if (data.candidates.length > 1) {
          setCompareCandidateId(data.candidates[1].candidate_id);
        }
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

  const compareCandidate = useMemo(() => {
    if (!analysisResult || !compareCandidateId) return null;
    return analysisResult.candidates.find((c) => c.candidate_id === compareCandidateId) || null;
  }, [analysisResult, compareCandidateId]);

  // Construct continuous layouts for LayoutCanvas preview
  const previewLayout = useMemo<ContinuousLayout | null>(() => {
    return candidateToContinuousLayout(selectedCandidate, problem);
  }, [selectedCandidate, problem]);

  const candidateValidation = useMemo<LayoutValidationResult | null>(() => {
    return candidateToValidation(selectedCandidate);
  }, [selectedCandidate]);

  const previewLayoutB = useMemo<ContinuousLayout | null>(() => {
    return candidateToContinuousLayout(compareCandidate, problem);
  }, [compareCandidate, problem]);

  const candidateValidationB = useMemo<LayoutValidationResult | null>(() => {
    return candidateToValidation(compareCandidate);
  }, [compareCandidate]);

  // Handle setting candidate as active solution
  const handleSetActiveSolution = (candidateToSet: ParetoCandidate | null) => {
    if (!candidateToSet) return;
    if (onSelectCandidate) {
      onSelectCandidate(candidateToSet);
    }
    setActiveSetMessage(candidateToSet.candidate_id);
    setTimeout(() => {
      setActiveSetMessage(null);
    }, 4500);
  };

  // Delta calculations for Candidate Comparison
  const comparisonDeltas = useMemo(() => {
    if (!selectedCandidate || !compareCandidate) return null;

    // Strict Scientific Compatibility Check: problem hashes must match
    const hasHashA = !!selectedCandidate.problem_composite_hash;
    const hasHashB = !!compareCandidate.problem_composite_hash;
    const isCompatible = !hasHashA || !hasHashB || selectedCandidate.problem_composite_hash === compareCandidate.problem_composite_hash;

    if (!isCompatible) {
      return {
        isCompatible: false,
        incompatibilityReason: t(
          'Farklı problem tanımları tespit edildi! Bilimsel doğruluk gereği farklı problem modelleri arasında matematiksel karşılaştırma yapılamaz.',
          'Incompatible problem models detected! Mathematically valid comparison requires identical problem composite hashes.'
        ),
        mhcA: selectedCandidate.objective_values.material_handling_cost ?? 0,
        mhcB: compareCandidate.objective_values.material_handling_cost ?? 0,
        deltaMhc: 0,
        pctDeltaMhc: 0,
        relA: selectedCandidate.objective_values.relationship_satisfaction ?? 0,
        relB: compareCandidate.objective_values.relationship_satisfaction ?? 0,
        deltaRel: 0,
        softA: selectedCandidate.objective_values.soft_penalty ?? 0,
        softB: compareCandidate.objective_values.soft_penalty ?? 0,
        deltaSoft: 0,
        aDominatesB: false,
        bDominatesA: false,
        isTradeOff: false,
        tradeOffSummary: t(
          'Karşılaştırma engellendi: Problem hash uyumsuzluğu.',
          'Comparison blocked: Problem hash mismatch.'
        ),
      };
    }

    const mhcA = selectedCandidate.objective_values.material_handling_cost ?? 0;
    const mhcB = compareCandidate.objective_values.material_handling_cost ?? 0;
    const deltaMhc = mhcB - mhcA;
    const pctDeltaMhc = mhcA > 0 ? (deltaMhc / mhcA) * 100 : 0;

    const relA = selectedCandidate.objective_values.relationship_satisfaction ?? 0;
    const relB = compareCandidate.objective_values.relationship_satisfaction ?? 0;
    const deltaRel = relB - relA; // percentage points (%p)

    const softA = selectedCandidate.objective_values.soft_penalty ?? 0;
    const softB = compareCandidate.objective_values.soft_penalty ?? 0;
    const deltaSoft = softB - softA;

    // Dominance check
    const aDominatesB =
      mhcA <= mhcB &&
      relA >= relB &&
      softA <= softB &&
      (mhcA < mhcB || relA > relB || softA < softB);

    const bDominatesA =
      mhcB <= mhcA &&
      relB >= relA &&
      softB <= softA &&
      (mhcB < mhcA || relB > relA || softB < softA);

    const currency = problem?.metadata?.currency;
    let tradeOffSummary = '';
    if (aDominatesB) {
      tradeOffSummary = t(
        `Aday A (${selectedCandidate.candidate_id}), Aday B'yi her iki kriterde de domine etmektedir. Kesinlikle Aday A tercih edilmelidir.`,
        `Candidate A strictly dominates Candidate B across all objectives. Candidate A is objectively superior.`
      );
    } else if (bDominatesA) {
      tradeOffSummary = t(
        `Aday B (${compareCandidate.candidate_id}), Aday A'yı her iki kriterde de domine etmektedir. Kesinlikle Aday B tercih edilmelidir.`,
        `Candidate B strictly dominates Candidate A across all objectives. Candidate B is objectively superior.`
      );
    } else {
      // Trade-off exists
      if (deltaMhc < 0 && deltaRel < 0) {
        tradeOffSummary = t(
          `Aday B, MHC maliyetinde ${formatCost(Math.abs(deltaMhc), currency)} (%${Math.abs(pctDeltaMhc).toFixed(1)}) tasarruf sağlar; ancak REL memnuniyeti ${Math.abs(deltaRel).toFixed(2)} puan (%p) daha düşüktür.`,
          `Candidate B saves ${formatCost(Math.abs(deltaMhc), currency)} (${Math.abs(pctDeltaMhc).toFixed(1)}%) in MHC cost, but sacrifices ${Math.abs(deltaRel).toFixed(2)} %p of REL satisfaction.`
        );
      } else if (deltaMhc > 0 && deltaRel > 0) {
        tradeOffSummary = t(
          `Aday B, REL memnuniyetini +${deltaRel.toFixed(2)} puan (%p) artırır; ancak MHC maliyeti ${formatCost(deltaMhc, currency)} (%${pctDeltaMhc.toFixed(1)}) daha yüksektir.`,
          `Candidate B improves REL satisfaction by +${deltaRel.toFixed(2)} %p, at the cost of +${formatCost(deltaMhc, currency)} (+${pctDeltaMhc.toFixed(1)}%) higher MHC.`
        );
      } else {
        tradeOffSummary = t(
          `İki aday Pareto ödünleşim sınırında farklı işletme önceliklerine hizmet etmektedir.`,
          `Both candidates offer distinct non-dominated trade-offs along the Pareto frontier.`
        );
      }
    }

    return {
      isCompatible: true,
      mhcA,
      mhcB,
      deltaMhc,
      pctDeltaMhc,
      relA,
      relB,
      deltaRel,
      softA,
      softB,
      deltaSoft,
      aDominatesB,
      bDominatesA,
      isTradeOff: !aDominatesB && !bDominatesA,
      tradeOffSummary,
    };
  }, [selectedCandidate, compareCandidate, problem, t]);

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

  // Candidates eligible for Candidate B comparison: strictly enforce matching problem composite hash
  const selectableCandidatesB = useMemo(() => {
    if (!analysisResult?.candidates) return [];
    if (!selectedCandidate?.problem_composite_hash) return analysisResult.candidates;
    return analysisResult.candidates.filter(
      (c) => !c.problem_composite_hash || c.problem_composite_hash === selectedCandidate.problem_composite_hash
    );
  }, [analysisResult, selectedCandidate]);

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
          marginBottom: '1rem',
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
            <span>🎯</span> {t('Çok Amaçlı Pareto Frontier & Karar Destek Sistemi', 'Multi-Objective Pareto Frontier & Decision Support (Phase 15.1)')}
          </h2>
          <p style={{ margin: '0.35rem 0 0', fontSize: '0.875rem', color: 'var(--text-secondary, #64748b)' }}>
            {t(
              'Material Handling Cost (MHC), Muther REL Satisfaction (%) ve Soft Constraint Penalty eksenlerinde Non-Dominated Sorting ve ödünleşim (Trade-Off) analizi.',
              'Rigorous non-dominated sorting and trade-off analysis across Material Handling Cost (MHC), Muther Relationship Satisfaction (%), and Soft Penalties.'
            )}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <button
            onClick={() => setCompareMode(!compareMode)}
            style={{
              padding: '0.55rem 1rem',
              backgroundColor: compareMode ? '#7c3aed' : '#ffffff',
              color: compareMode ? '#ffffff' : '#475569',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              fontSize: '0.875rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <ArrowRightLeft size={15} />
            {compareMode ? t('Karşılaştırma Modunu Kapat', 'Exit Compare Mode') : t('Aday Karşılaştırma Modu (A vs B)', 'Candidate Comparison Mode (A vs B)')}
          </button>
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

      {/* User Guidance Box */}
      <DecisionGuidanceBox mode="pareto" defaultOpen={false} />

      {/* Feedback Alert for Setting Active Solution */}
      {activeSetMessage && (
        <div
          style={{
            backgroundColor: '#f0fdf4',
            border: '1px solid #86efac',
            color: '#166534',
            borderRadius: '6px',
            padding: '0.75rem 1rem',
            fontSize: '0.875rem',
            fontWeight: 600,
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
          }}
        >
          <CheckCircle2 size={18} color="#16a34a" />
          <span>
            {t(
              `✓ Aday "${activeSetMessage}" platformun aktif çözümü olarak atandı! 2D Layout Görünümü ve Export Center güncellendi.`,
              `✓ Candidate "${activeSetMessage}" has been set as the platform's active solution! 2D Layout Viewer and Export Center updated.`
            )}
          </span>
        </div>
      )}

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
            <div style={{ fontSize: '0.75rem', color: '#166534' }}>{t('Kesin Non-Dominated (en iyi bulunan) alternatifler', 'Strictly non-dominated (best-found) candidates')}</div>
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

      {/* SIDE-BY-SIDE CANDIDATE COMPARISON MODE (A vs B) */}
      {compareMode && analysisResult && selectedCandidate && compareCandidate && comparisonDeltas && (
        <div
          style={{
            backgroundColor: '#faf5ff',
            border: '2px solid #c084fc',
            borderRadius: '10px',
            padding: '1.25rem',
            marginBottom: '1.75rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Scale size={20} color="#7c3aed" />
              <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#581c87' }}>
                {t('Yan Yana Aday Karşılaştırma Modu (Candidate A vs Candidate B)', 'Side-by-Side Candidate Comparison Mode (A vs B)')}
              </h3>
            </div>
            <div style={{ fontSize: '0.8rem', color: '#6b21a8', fontWeight: 600 }}>
              {t('Matematiksel Δ Farkları ve Dominance Analizi', 'Mathematical Δ Differences & Dominance Analysis')}
            </div>
          </div>

          {/* Selectors for A and B */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e9d5ff' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#2563eb', display: 'block', marginBottom: '0.25rem' }}>
                {t('Aday A (Referans):', 'Candidate A (Reference):')}
              </label>
              <select
                value={selectedCandidateId || ''}
                onChange={(e) => setSelectedCandidateId(e.target.value)}
                style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
              >
                {analysisResult.candidates.map((c) => (
                  <option key={c.candidate_id} value={c.candidate_id}>
                    {c.candidate_id} ({c.pareto_rank === 1 ? '★ Rank 1' : `Rank ${c.pareto_rank}`} • {formatCost(c.objective_values.material_handling_cost, problem?.metadata?.currency)})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e9d5ff' }}>
              <label style={{ fontSize: '0.75rem', fontWeight: 700, color: '#7c3aed', display: 'block', marginBottom: '0.25rem' }}>
                {t('Aday B (Kıyaslanan):', 'Candidate B (Comparison Target):')}
              </label>
              <select
                value={compareCandidateId || ''}
                onChange={(e) => setCompareCandidateId(e.target.value)}
                style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid #cbd5e1', fontSize: '0.85rem' }}
              >
                {selectableCandidatesB.map((c) => (
                  <option key={c.candidate_id} value={c.candidate_id}>
                    {c.candidate_id} ({c.pareto_rank === 1 ? '★ Rank 1' : `Rank ${c.pareto_rank}`} • {formatCost(c.objective_values.material_handling_cost, problem?.metadata?.currency)})
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Scientific Hash Compatibility Warning Banner */}
          {!comparisonDeltas.isCompatible && (
            <div
              style={{
                backgroundColor: '#fef2f2',
                border: '2px solid #ef4444',
                color: '#991b1b',
                borderRadius: '8px',
                padding: '0.85rem 1rem',
                marginBottom: '1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
              }}
            >
              <AlertTriangle size={24} color="#dc2626" />
              <div>
                <strong style={{ fontSize: '0.9rem' }}>
                  {t('Bilimsel Kıyaslama Engellendi: Problem Modeli Uyuşmazlığı', 'Scientific Comparison Blocked: Problem Model Mismatch')}
                </strong>
                <div style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                  {comparisonDeltas.incompatibilityReason}
                </div>
              </div>
            </div>
          )}

          {/* Mathematical Delta Comparison Table */}
          <div style={{ backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #e9d5ff', overflowX: 'auto', marginBottom: '1rem' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ backgroundColor: '#f3e8ff', borderBottom: '2px solid #d8b4fe' }}>
                  <th style={{ padding: '0.6rem 0.8rem' }}>{t('Kriter / Metrik', 'Criterion / Metric')}</th>
                  <th style={{ padding: '0.6rem 0.8rem', color: '#1d4ed8' }}>Aday A ({selectedCandidate.candidate_id})</th>
                  <th style={{ padding: '0.6rem 0.8rem', color: '#7c3aed' }}>Aday B ({compareCandidate.candidate_id})</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>{t('Fark (Δ = B - A)', 'Difference (Δ = B - A)')}</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>{t('Değerlendirme', 'Evaluation')}</th>
                </tr>
              </thead>
              <tbody>
                {/* MHC Row */}
                <tr style={{ borderBottom: '1px solid #f3e8ff' }}>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>Material Handling Cost (MHC)</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>{formatCost(comparisonDeltas.mhcA, problem?.metadata?.currency)}</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>{formatCost(comparisonDeltas.mhcB, problem?.metadata?.currency)}</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 700, color: comparisonDeltas.deltaMhc <= 0 ? '#16a34a' : '#dc2626' }}>
                    {comparisonDeltas.deltaMhc > 0 ? '+' : ''}{formatCost(comparisonDeltas.deltaMhc, problem?.metadata?.currency)}
                    {' '}({comparisonDeltas.pctDeltaMhc > 0 ? '+' : ''}{comparisonDeltas.pctDeltaMhc.toFixed(1)}%)
                  </td>
                  <td style={{ padding: '0.6rem 0.8rem', fontSize: '0.75rem', color: comparisonDeltas.deltaMhc <= 0 ? '#16a34a' : '#dc2626' }}>
                    {comparisonDeltas.deltaMhc < 0 ? t('B daha ucuz (MHC tasarrufu)', 'B is cheaper (MHC savings)') : comparisonDeltas.deltaMhc > 0 ? t('A daha ucuz (MHC tasarrufu)', 'A is cheaper (MHC savings)') : t('Eşit maliyet', 'Equal cost')}
                  </td>
                </tr>

                {/* REL Satisfaction Row */}
                <tr style={{ borderBottom: '1px solid #f3e8ff' }}>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>REL Satisfaction (%)</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>{comparisonDeltas.relA.toFixed(2)}%</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>{comparisonDeltas.relB.toFixed(2)}%</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 700, color: comparisonDeltas.deltaRel >= 0 ? '#16a34a' : '#dc2626' }}>
                    {comparisonDeltas.deltaRel > 0 ? '+' : ''}{comparisonDeltas.deltaRel.toFixed(2)} %p (yüzde puanı)
                  </td>
                  <td style={{ padding: '0.6rem 0.8rem', fontSize: '0.75rem', color: comparisonDeltas.deltaRel >= 0 ? '#16a34a' : '#dc2626' }}>
                    {comparisonDeltas.deltaRel > 0 ? t('B daha iyi yakınlık memnuniyeti', 'B has higher REL satisfaction') : comparisonDeltas.deltaRel < 0 ? t('A daha iyi yakınlık memnuniyeti', 'A has higher REL satisfaction') : t('Eşit memnuniyet', 'Equal satisfaction')}
                  </td>
                </tr>

                {/* Soft Penalty Row */}
                <tr style={{ borderBottom: '1px solid #f3e8ff' }}>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>Soft Penalty</td>
                  <td style={{ padding: '0.6rem 0.8rem' }}>{formatCost(comparisonDeltas.softA, problem?.metadata?.currency)}</td>
                  <td style={{ padding: '0.6rem 0.8rem' }}>{formatCost(comparisonDeltas.softB, problem?.metadata?.currency)}</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600, color: comparisonDeltas.deltaSoft <= 0 ? '#16a34a' : '#dc2626' }}>
                    {comparisonDeltas.deltaSoft > 0 ? '+' : ''}{formatCost(comparisonDeltas.deltaSoft, problem?.metadata?.currency)}
                  </td>
                  <td style={{ padding: '0.6rem 0.8rem', fontSize: '0.75rem' }}>
                    {comparisonDeltas.deltaSoft < 0 ? t('B daha düşük ceza', 'B has lower penalty') : comparisonDeltas.deltaSoft > 0 ? t('A daha düşük ceza', 'A has lower penalty') : t('Eşit ceza', 'Equal penalty')}
                  </td>
                </tr>

                {/* Feasibility Row */}
                <tr style={{ borderBottom: '1px solid #f3e8ff' }}>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>{t('Fiziksel Geçerlilik (Feasibility)', 'Feasibility')}</td>
                  <td style={{ padding: '0.6rem 0.8rem' }}>
                    <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600, backgroundColor: selectedCandidate.is_feasible ? '#dcfce7' : '#fee2e2', color: selectedCandidate.is_feasible ? '#15803d' : '#991b1b' }}>
                      {selectedCandidate.is_feasible ? 'Feasible' : 'Infeasible'}
                    </span>
                  </td>
                  <td style={{ padding: '0.6rem 0.8rem' }}>
                    <span style={{ padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600, backgroundColor: compareCandidate.is_feasible ? '#dcfce7' : '#fee2e2', color: compareCandidate.is_feasible ? '#15803d' : '#991b1b' }}>
                      {compareCandidate.is_feasible ? 'Feasible' : 'Infeasible'}
                    </span>
                  </td>
                  <td style={{ padding: '0.6rem 0.8rem' }} colSpan={2}>
                    {selectedCandidate.is_feasible && compareCandidate.is_feasible
                      ? t('Her iki aday da %100 çakışmasız ve geçerlidir.', 'Both layouts are 100% overlap-free and valid.')
                      : t('Adaylardan en az biri kısıt ihlali içermektedir.', 'At least one candidate contains constraint violations.')}
                  </td>
                </tr>

                {/* Pareto Rank Row */}
                <tr style={{ borderBottom: '1px solid #f3e8ff' }}>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>Pareto Rank</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 700, color: selectedCandidate.pareto_rank === 1 ? '#15803d' : '#475569' }}>
                    {selectedCandidate.pareto_rank === 1 ? '★ Rank 1 (Non-Dominated)' : `Rank ${selectedCandidate.pareto_rank}`}
                  </td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 700, color: compareCandidate.pareto_rank === 1 ? '#15803d' : '#475569' }}>
                    {compareCandidate.pareto_rank === 1 ? '★ Rank 1 (Non-Dominated)' : `Rank ${compareCandidate.pareto_rank}`}
                  </td>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }} colSpan={2}>
                    {comparisonDeltas.aDominatesB
                      ? t('Aday A, Aday B\'yi DOMINE EDER!', 'Candidate A DOMINATES Candidate B!')
                      : comparisonDeltas.bDominatesA
                      ? t('Aday B, Aday A\'yı DOMINE EDER!', 'Candidate B DOMINATES Candidate A!')
                      : t('Trade-Off: İkisi de birbirini domine etmez.', 'Trade-Off: Neither strictly dominates the other.')}
                  </td>
                </tr>

                {/* Layout Signature & Hash Row (Part 6.3) */}
                <tr>
                  <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>{t('Yerleşim İmzası (Signature)', 'Layout Signature')}</td>
                  <td style={{ padding: '0.6rem 0.8rem', fontFamily: 'monospace', fontSize: '0.72rem' }}>
                    {selectedCandidate.layout_signature ? selectedCandidate.layout_signature.slice(0, 14) + '…' : t('Mevcut değil', 'N/A')}
                  </td>
                  <td style={{ padding: '0.6rem 0.8rem', fontFamily: 'monospace', fontSize: '0.72rem' }}>
                    {compareCandidate.layout_signature ? compareCandidate.layout_signature.slice(0, 14) + '…' : t('Mevcut değil', 'N/A')}
                  </td>
                  <td style={{ padding: '0.6rem 0.8rem', fontSize: '0.75rem' }} colSpan={2}>
                    {selectedCandidate.problem_composite_hash === compareCandidate.problem_composite_hash
                      ? <span style={{ color: '#16a34a', fontWeight: 600 }}>✓ {t('Aynı problem hash uyumlu', 'Compatible problem hashes')}</span>
                      : <span style={{ color: '#dc2626', fontWeight: 700 }}>⚠ {t('Farklı problem tanımları! Kıyaslama geçersiz.', 'Incompatible problem hashes!')}</span>}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Trade-off Academic Interpretation Box */}
          <div data-testid="academic-tradeoff-box" style={{ backgroundColor: '#ffffff', padding: '0.85rem 1rem', borderRadius: '6px', border: '1px solid #d8b4fe', marginBottom: '1rem' }}>
            <div style={{ fontWeight: 700, color: '#581c87', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
              💡 {t('Akademik Ödünleşim Değerlendirmesi:', 'Academic Trade-off Interpretation:')}
            </div>
            <div style={{ fontSize: '0.825rem', color: '#334155' }}>
              {comparisonDeltas.tradeOffSummary}
            </div>
          </div>

          {/* Dual Side-by-Side Compact Previews */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div style={{ border: '1px solid #bfdbfe', borderRadius: '6px', padding: '0.75rem', backgroundColor: '#ffffff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 700, color: '#1d4ed8', fontSize: '0.85rem' }}>Aday A: {selectedCandidate.candidate_id}</span>
                <button
                  onClick={() => handleSetActiveSolution(selectedCandidate)}
                  style={{
                    padding: '0.25rem 0.5rem',
                    backgroundColor: '#1d4ed8',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '0.72rem',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  {t('Aday A\'yı Aktif Yap', 'Set A Active')}
                </button>
              </div>
              <LayoutCanvas layout={previewLayout} problem={problem} validation={candidateValidation} compact={true} />
            </div>

            <div style={{ border: '1px solid #d8b4fe', borderRadius: '6px', padding: '0.75rem', backgroundColor: '#ffffff' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 700, color: '#7c3aed', fontSize: '0.85rem' }}>Aday B: {compareCandidate.candidate_id}</span>
                <button
                  onClick={() => handleSetActiveSolution(compareCandidate)}
                  style={{
                    padding: '0.25rem 0.5rem',
                    backgroundColor: '#7c3aed',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '4px',
                    fontSize: '0.72rem',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  {t('Aday B\'yi Aktif Yap', 'Set B Active')}
                </button>
              </div>
              <LayoutCanvas layout={previewLayoutB} problem={problem} validation={candidateValidationB} compact={true} />
            </div>
          </div>
        </div>
      )}

      {/* Main Analysis View: 2-Column Grid (Scatter Chart & Selected Preview) */}
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
                  {t('Material Handling Cost (MHC) ➔ [Düşük Daha İyi / Minimize]', 'Material Handling Cost (MHC) ➔ [Lower is Better]')}
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
                  {Math.round(chartData.minMhc / 1000)}k
                </text>
                <text x={chartData.width - chartData.padX} y={chartData.height - chartData.padY + 16} fontSize="9" fill="#64748b" textAnchor="middle">
                  {Math.round(chartData.maxMhc / 1000)}k
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
                  const isCompareTarget = compareMode && compareCandidateId === pt.candidate.candidate_id;
                  const circleFill = pt.isFrontier ? '#10b981' : pt.candidate.pareto_rank === 2 ? '#6366f1' : '#94a3b8';
                  const strokeCol = isSelected ? '#ea580c' : isCompareTarget ? '#7c3aed' : pt.isFrontier ? '#047857' : '#475569';
                  const radius = pt.isFrontier ? (isSelected || isCompareTarget ? 9 : 7) : isSelected || isCompareTarget ? 8 : 6;

                  return (
                    <g
                      key={i}
                      style={{ cursor: 'pointer' }}
                      onClick={() => {
                        if (compareMode && selectedCandidateId && selectedCandidateId !== pt.candidate.candidate_id) {
                          setCompareCandidateId(pt.candidate.candidate_id);
                        } else {
                          setSelectedCandidateId(pt.candidate.candidate_id);
                        }
                      }}
                    >
                      {/* Highlight aura for selected or frontier */}
                      {isSelected && (
                        <circle cx={pt.x} cy={pt.y} r={radius + 5} fill="#ea580c" opacity="0.25" />
                      )}
                      {isCompareTarget && (
                        <circle cx={pt.x} cy={pt.y} r={radius + 5} fill="#7c3aed" opacity="0.25" />
                      )}
                      {pt.isFrontier && !isSelected && !isCompareTarget && (
                        <circle cx={pt.x} cy={pt.y} r={radius + 3} fill="#10b981" opacity="0.25" />
                      )}

                      <circle
                        cx={pt.x}
                        cy={pt.y}
                        r={radius}
                        fill={circleFill}
                        stroke={strokeCol}
                        strokeWidth={isSelected || isCompareTarget ? 3 : 1.5}
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
            <div style={{ display: 'flex', gap: '1.25rem', marginTop: '0.75rem', fontSize: '0.785rem', color: '#475569', justifyContent: 'center', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#10b981', display: 'inline-block' }} />
                <strong>Pareto Frontier (Rank 1)</strong>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#6366f1', display: 'inline-block' }} />
                <span>Rank 2 Dominated</span>
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
              display: 'flex',
              flexDirection: 'column',
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
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.15rem' }}>
                  {t('Kaynak Algoritma:', 'Algorithm:')} <strong>{selectedCandidate?.algorithm_source || 'Unknown'}</strong>
                </div>
              </div>
              {selectedCandidate && (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.4rem' }}>
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

                  {/* SET AS ACTIVE SOLUTION BUTTON */}
                  <button
                    onClick={() => handleSetActiveSolution(selectedCandidate)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.35rem',
                      padding: '0.35rem 0.75rem',
                      backgroundColor: '#16a34a',
                      color: '#ffffff',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                    }}
                    title={t(
                      'Bu adayı tüm sistem genelinde aktif layout olarak ayarlar ve Export Center ile senkronize eder.',
                      'Sets this candidate as the platform-wide active layout and synchronizes with Export Center.'
                    )}
                  >
                    <Target size={14} />
                    {t('Aktif Çözüm Yap', 'Set Active')}
                  </button>
                </div>
              )}
            </div>

            {/* Objective Score Cards */}
            {selectedCandidate && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem', marginBottom: '0.85rem' }}>
                <div style={{ padding: '0.5rem', backgroundColor: '#f8fafc', borderRadius: '6px', textAlign: 'center', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.7rem', color: '#64748b' }}>MHC Cost</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                    {formatCost(selectedCandidate.objective_values.material_handling_cost, problem?.metadata?.currency)}
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
                    {formatCost(selectedCandidate.objective_values.soft_penalty, problem?.metadata?.currency)}
                  </div>
                </div>
              </div>
            )}

            {/* Canvas Preview with compact={true} */}
            <div style={{ flex: 1, minHeight: '220px' }}>
              <LayoutCanvas
                layout={previewLayout}
                problem={problem}
                validation={candidateValidation}
                compact={true}
              />
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
                    {activeRecommendation.is_on_pareto_frontier ? 'Pareto Non-Dominated' : 'Dominated Candidate'}
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: '#475569', marginTop: '0.25rem', maxWidth: '750px' }}>
                  {activeRecommendation.rationale}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem' }}>
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
                <button
                  onClick={() => {
                    const recCand = analysisResult.candidates.find(c => c.candidate_id === activeRecommendation.recommended_candidate_id);
                    if (recCand) {
                      handleSetActiveSolution(recCand);
                    }
                  }}
                  style={{
                    padding: '0.45rem 0.9rem',
                    backgroundColor: '#16a34a',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {t('Aktif Çözüm Yap', 'Set Active')}
                </button>
              </div>
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
                <th style={{ padding: '0.6rem 0.8rem' }}>MHC Cost</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>REL Satisfaction (%)</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>Soft Penalty</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>Flow-Distance</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>{t('Durum', 'Status')}</th>
                <th style={{ padding: '0.6rem 0.8rem' }}>{t('İşlem', 'Action')}</th>
              </tr>
            </thead>
            <tbody>
              {analysisResult.candidates.map((cand) => {
                const isSelected = selectedCandidateId === cand.candidate_id;
                const isCompareTarget = compareMode && compareCandidateId === cand.candidate_id;
                const isRank1 = cand.pareto_rank === 1;

                return (
                  <tr
                    key={cand.candidate_id}
                    onClick={() => {
                      if (compareMode && selectedCandidateId && selectedCandidateId !== cand.candidate_id) {
                        setCompareCandidateId(cand.candidate_id);
                      } else {
                        setSelectedCandidateId(cand.candidate_id);
                      }
                    }}
                    style={{
                      borderBottom: '1px solid #e2e8f0',
                      backgroundColor: isSelected
                        ? '#eff6ff'
                        : isCompareTarget
                        ? '#faf5ff'
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
                    <td style={{ padding: '0.6rem 0.8rem', fontWeight: isSelected || isCompareTarget ? 700 : 500 }}>
                      {cand.candidate_id}
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', color: '#475569' }}>
                      <span style={{ padding: '2px 6px', borderRadius: '4px', backgroundColor: '#f1f5f9', border: '1px solid #e2e8f0', fontSize: '0.72rem' }}>
                        {cand.algorithm_source}
                      </span>
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600 }}>
                      {formatCost(cand.objective_values.material_handling_cost, problem?.metadata?.currency)}
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', color: '#16a34a', fontWeight: 600 }}>
                      {cand.objective_values.relationship_satisfaction?.toFixed(2)}%
                    </td>
                    <td style={{ padding: '0.6rem 0.8rem', color: cand.objective_values.soft_penalty ? '#dc2626' : '#15803d', fontWeight: 600 }}>
                      {formatCost(cand.objective_values.soft_penalty, problem?.metadata?.currency)}
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
                      <div style={{ display: 'flex', gap: '0.35rem' }}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedCandidateId(cand.candidate_id);
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.72rem',
                            backgroundColor: isSelected ? '#1d4ed8' : '#f1f5f9',
                            color: isSelected ? '#ffffff' : '#334155',
                            border: '1px solid #cbd5e1',
                            borderRadius: '4px',
                            cursor: 'pointer',
                          }}
                        >
                          {isSelected ? t('İnceleniyor', 'Viewing') : t('Seç', 'Select')}
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSetActiveSolution(cand);
                          }}
                          style={{
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.72rem',
                            backgroundColor: '#16a34a',
                            color: '#ffffff',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontWeight: 600,
                          }}
                          title={t('Bu adayı aktif platform çözümü yap', 'Set as active platform solution')}
                        >
                          {t('Aktif Yap', 'Set Active')}
                        </button>
                      </div>
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
