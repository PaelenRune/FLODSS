import React, { useState, useEffect } from 'react';
import { BenchmarkResult, BenchmarkComparisonRow, ALDEPProblemSummary } from '../types/api';
import { runBenchmark, getLatestBenchmark } from '../services/api';
import { useLanguage } from '../context/LanguageContext';

export const AlgorithmComparisonCard: React.FC = () => {
  const { t } = useLanguage();
  const [benchmarkResult, setBenchmarkResult] = useState<BenchmarkResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load latest benchmark on mount
  useEffect(() => {
    loadLatest();
  }, []);

  const loadLatest = async () => {
    try {
      setError(null);
      const data = await getLatestBenchmark();
      setBenchmarkResult(data);
    } catch {
      // If no persisted benchmark exists yet, that's fine
    }
  };

  const handleRunBenchmark = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await runBenchmark();
      setBenchmarkResult(data);
    } catch (err: any) {
      setError(err.message || t('Benchmark çalıştırılamadı', 'Failed to execute benchmark'));
    } finally {
      setLoading(false);
    }
  };

  const getAlgorithmBadge = (algo: string) => {
    if (algo.startsWith('CORELAP')) {
      return <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#3b82f620', color: '#3b82f6' }}>CORELAP (Constructive)</span>;
    }
    if (algo.startsWith('ALDEP')) {
      return <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#8b5cf620', color: '#8b5cf6' }}>ALDEP (Stochastic)</span>;
    }
    if (algo.startsWith('CRAFT')) {
      return <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#10b98120', color: '#10b981' }}>CRAFT (Improvement)</span>;
    }
    return <span style={{ padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600, backgroundColor: '#64748b20', color: '#64748b' }}>Manual Baseline</span>;
  };

  return (
    <div style={{
      backgroundColor: 'var(--bg-card, #ffffff)',
      border: '1px solid var(--border-color, #e2e8f0)',
      borderRadius: '8px',
      padding: '1.5rem',
      marginBottom: '2rem',
      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>📊</span> {t('Algoritma Benchmark & Karşılaştırma Matrisi (CORELAP / ALDEP / CRAFT)', 'Algorithm Benchmark & Comparison (Phase 7.1)')}
          </h2>
          <p style={{ margin: '0.25rem 0 0', fontSize: '0.85rem', color: 'var(--text-secondary, #64748b)' }}>
            {t(
              'Standart fabrika Benchmark problemleri üzerinde CORELAP, ALDEP ve CRAFT sezgisellerinin ampirik performans değerlendirmesi.',
              'Empirical evaluation across CORELAP, ALDEP, and CRAFT on standardized factory benchmarks.'
            )}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={loadLatest}
            disabled={loading}
            style={{
              padding: '0.5rem 0.85rem',
              backgroundColor: 'var(--bg-secondary, #f1f5f9)',
              color: 'var(--text-primary, #0f172a)',
              border: '1px solid var(--border-color, #cbd5e1)',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {t('↻ Son Sonucu Yükle', '↻ Reload Latest')}
          </button>
          <button
            onClick={handleRunBenchmark}
            disabled={loading}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            {loading ? t('Benchmark Matrisi Çalıştırılıyor...', 'Running Benchmark Matrix...') : t('▶ Tüm Benchmark Paketini Çalıştır', '▶ Run Full Benchmark Suite')}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          backgroundColor: '#fef2f2',
          border: '1px solid #f87171',
          color: '#991b1b',
          borderRadius: '6px',
          padding: '0.75rem 1rem',
          fontSize: '0.85rem',
          marginBottom: '1rem',
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Scientific Integrity Advisory Note */}
      <div style={{
        backgroundColor: '#eff6ff',
        border: '1px solid #bfdbfe',
        borderRadius: '6px',
        padding: '0.85rem 1rem',
        marginBottom: '1.25rem',
        fontSize: '0.825rem',
        color: '#1e40af',
        lineHeight: 1.5,
      }}>
        <strong>⚖️ {t('Bilimsel Bütünlük & Benchmark Adilliği:', 'Scientific Integrity & Benchmark Fairness:')}</strong>
        <div style={{ marginTop: '0.25rem' }}>
          {t(
            'Eksik yerleşimler (örn. FLP_INDUSTRIAL_10 üzerinde CORELAP) ve geometrik Hard Constraint ihlali içeren yerleşimler (örn. ALDEP Strip Sweep kaynaklı Pairwise Overlap) geçersiz karşılaştırmaları önlemek için MHC sıralamasından hariç tutulur (Excluded). CRAFT bir Improvement Heuristic olup yalnızca tam ve Feasible başlangıç yerleşimleri üzerinde çalışır.',
            'Incomplete layouts (e.g. CORELAP on FLP_INDUSTRIAL_10) and layouts with geometric constraint violations (e.g. continuous bounding box overlaps from ALDEP strip sweep) are strictly excluded from objective ranking to avoid invalid comparisons. CRAFT is an improvement heuristic and operates exclusively on complete, feasible initial baselines.'
          )}
        </div>
      </div>

      {benchmarkResult ? (
        <div>
          {/* Metadata bar */}
          <div style={{
            display: 'flex',
            gap: '1.5rem',
            flexWrap: 'wrap',
            padding: '0.75rem 1rem',
            backgroundColor: 'var(--bg-secondary, #f8fafc)',
            borderRadius: '6px',
            marginBottom: '1.25rem',
            fontSize: '0.8rem',
            color: 'var(--text-secondary, #475569)',
          }}>
            <div><strong>Run ID:</strong> <code>{benchmarkResult.run_id}</code></div>
            <div><strong>{t('Zaman Damgası:', 'Timestamp:')}</strong> {new Date(benchmarkResult.timestamp).toLocaleString()}</div>
            <div><strong>{t('Değerlendirilen Problemler:', 'Problems Evaluated:')}</strong> {benchmarkResult.config.problem_ids?.join(', ')}</div>
            <div><strong>ALDEP Seeds:</strong> {benchmarkResult.config.aldep_seeds?.length} seeds ({benchmarkResult.config.aldep_candidates_per_seed} candidates/seed)</div>
          </div>

          {/* Primary Cross-Algorithm Comparison Table */}
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            {t('Algoritmalar Arası Performans Matrisi (Cross-Algorithm Matrix)', 'Cross-Algorithm Performance Matrix')}
          </h3>
          <div style={{ overflowX: 'auto', marginBottom: '1.5rem' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '0.825rem',
              textAlign: 'left',
            }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-secondary, #f1f5f9)', borderBottom: '2px solid var(--border-color, #cbd5e1)' }}>
                  <th style={{ padding: '0.6rem 0.75rem' }}>{t('Algoritma', 'Algorithm')}</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Problem</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Run / Baseline</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>Complete</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>Feasible</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>Best MHC</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>Runtime (s)</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>{t('Durum & Tanı (Diagnostics)', 'Status & Diagnostics')}</th>
                </tr>
              </thead>
              <tbody>
                {benchmarkResult.comparison_table.map((row: BenchmarkComparisonRow, idx: number) => {
                  const isExcluded = !row.complete || !row.feasible;
                  return (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: '1px solid var(--border-color, #e2e8f0)',
                        backgroundColor: isExcluded ? '#fffbeb' : 'transparent',
                      }}
                    >
                      <td style={{ padding: '0.6rem 0.75rem', fontWeight: 500 }}>
                        {getAlgorithmBadge(row.algorithm)}
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem' }}>
                        <code>{row.problem_id}</code>
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', color: 'var(--text-secondary, #64748b)' }}>
                        {row.run_or_seed}
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
                        {row.complete ? (
                          <span style={{ color: '#16a34a', fontWeight: 600 }}>✓ Yes</span>
                        ) : (
                          <span style={{ color: '#dc2626', fontWeight: 600 }}>✗ Partial</span>
                        )}
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
                        {row.feasible ? (
                          <span style={{ color: '#16a34a', fontWeight: 600 }}>✓ Feasible</span>
                        ) : (
                          <span style={{ color: '#d97706', fontWeight: 600 }}>⚠ Excluded</span>
                        )}
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', textAlign: 'right', fontWeight: 600 }}>
                        {row.mhc !== null && row.mhc !== undefined ? (
                          row.mhc.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 2 })
                        ) : (
                          <span style={{ color: '#94a3b8', fontStyle: 'italic' }}>N/A (Excluded)</span>
                        )}
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', textAlign: 'right', color: 'var(--text-secondary, #64748b)' }}>
                        {row.runtime_seconds ? row.runtime_seconds.toFixed(4) : '0.0000'}
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', fontSize: '0.75rem', color: isExcluded ? '#b45309' : 'var(--text-secondary, #64748b)' }}>
                        {row.notes || '-'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* ALDEP Stochastic Portfolio Summary Breakdown */}
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            {t('ALDEP Stokastik Çoklu Aday İstatistikleri (Problem Başına 100 Deneme)', 'ALDEP Stochastic Multi-Candidate Statistics (100 Trials per Problem)')}
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: '0.825rem',
              textAlign: 'left',
            }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-secondary, #f1f5f9)', borderBottom: '2px solid var(--border-color, #cbd5e1)' }}>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Problem</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>Trials</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>Completion Rate</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>Feasibility Rate</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>Unique / Duplicates</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>Best MHC</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>Median MHC</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>Worst MHC</th>
                  <th style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>Std Dev</th>
                  <th style={{ padding: '0.6rem 0.75rem' }}>Sample Scope</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(benchmarkResult.aldep_summaries).map(([pid, summary]: [string, ALDEPProblemSummary]) => (
                  <tr key={pid} style={{ borderBottom: '1px solid var(--border-color, #e2e8f0)' }}>
                    <td style={{ padding: '0.6rem 0.75rem', fontWeight: 600 }}><code>{pid}</code></td>
                    <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>{summary.total_trials}</td>
                    <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
                      <span style={{ fontWeight: 600, color: summary.completion_rate === 1 ? '#16a34a' : '#d97706' }}>
                        {(summary.completion_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
                      <span style={{ fontWeight: 600, color: summary.feasibility_rate > 0 ? '#16a34a' : '#dc2626' }}>
                        {(summary.feasibility_rate * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
                      {summary.unique_layout_count} unique ({summary.duplicate_count} dups)
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', textAlign: 'right', fontWeight: 600 }}>
                      {summary.best_mhc ? summary.best_mhc.toFixed(1) : '-'}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>
                      {summary.median_mhc ? summary.median_mhc.toFixed(1) : '-'}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>
                      {summary.worst_mhc ? summary.worst_mhc.toFixed(1) : '-'}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', textAlign: 'right' }}>
                      {summary.std_mhc ? summary.std_mhc.toFixed(2) : '-'}
                    </td>
                    <td style={{ padding: '0.6rem 0.75rem', fontSize: '0.75rem', color: 'var(--text-secondary, #64748b)' }}>
                      {summary.sample_description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div style={{
          textAlign: 'center',
          padding: '2.5rem 1rem',
          backgroundColor: 'var(--bg-secondary, #f8fafc)',
          borderRadius: '6px',
          color: 'var(--text-secondary, #64748b)',
        }}>
          <p style={{ margin: 0, fontSize: '0.9rem' }}>
            {t(
              'Henüz Benchmark çalıştırması yüklenmedi. CORELAP, ALDEP ve CRAFT algoritmalarını karşılaştırmak için yukarıdaki "Tüm Benchmark Paketini Çalıştır" butonuna tıklayın.',
              'No benchmark run has been loaded yet. Click Run Full Benchmark Suite above to evaluate CORELAP, ALDEP, and CRAFT.'
            )}
          </p>
        </div>
      )}
    </div>
  );
};
