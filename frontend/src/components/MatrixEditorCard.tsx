import React, { useState, useMemo } from 'react';
import { FacilityLayoutProblem } from '../types/api';
import { useLanguage } from '../context/LanguageContext';

interface MatrixEditorCardProps {
  problem: FacilityLayoutProblem | null;
  onUpdateProblem: (updated: FacilityLayoutProblem) => void;
}

const REL_OPTIONS = [
  { code: 'A', score: 4, label: 'A - Absolutely Necessary', color: '#059669', bg: 'rgba(5, 150, 105, 0.2)' },
  { code: 'E', score: 3, label: 'E - Especially Important', color: '#10b981', bg: 'rgba(16, 185, 129, 0.2)' },
  { code: 'I', score: 2, label: 'I - Important', color: '#0284c7', bg: 'rgba(2, 132, 199, 0.2)' },
  { code: 'O', score: 1, label: 'O - Ordinary Closeness', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.2)' },
  { code: 'U', score: 0, label: 'U - Unimportant', color: '#6b7280', bg: 'rgba(107, 114, 128, 0.15)' },
  { code: 'X', score: -1, label: 'X - Undesirable', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.2)' },
];

export const MatrixEditorCard: React.FC<MatrixEditorCardProps> = ({ problem, onUpdateProblem }) => {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<'flows' | 'relationships'>('flows');

  if (!problem || !problem.departments || problem.departments.length === 0) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
        <p style={{ color: 'var(--text-muted)' }}>
          {t(
            'Flow ve REL matrislerini oluşturmak için Problem Tanımı sekmesinde en az iki bölüm tanımlayın.',
            'Define at least two departments in the Problem Editor to build flow and relationship matrices.'
          )}
        </p>
      </div>
    );
  }

  const deptIds = useMemo(() => problem.departments.map(d => d.id), [problem]);

  // Build 2D flow lookup: flowMap[source][target] = quantity
  const flowMap = useMemo(() => {
    const map: Record<string, Record<string, number>> = {};
    for (const d of deptIds) {
      map[d] = {};
      for (const t of deptIds) {
        map[d][t] = 0;
      }
    }
    for (const f of problem.flows) {
      if (map[f.source_department] && map[f.source_department][f.target_department] !== undefined) {
        map[f.source_department][f.target_department] = f.quantity;
      }
    }
    return map;
  }, [problem.flows, deptIds]);

  // Build 2D relationship lookup: relMap[a][b] = code
  const relMap = useMemo(() => {
    const map: Record<string, Record<string, string>> = {};
    for (const d of deptIds) {
      map[d] = {};
      for (const t of deptIds) {
        map[d][t] = 'U';
      }
    }
    for (const r of problem.relationships) {
      const code = r.relationship_type.toUpperCase();
      if (map[r.department_a] && map[r.department_a][r.department_b] !== undefined) {
        map[r.department_a][r.department_b] = code;
        map[r.department_b][r.department_a] = code;
      }
    }
    return map;
  }, [problem.relationships, deptIds]);

  // Update a single flow cell
  const handleFlowCellChange = (source: string, target: string, val: number) => {
    const safeVal = Math.max(0, val || 0);
    const existing = problem.flows.filter(f => !(f.source_department === source && f.target_department === target));
    if (safeVal > 0) {
      existing.push({
        source_department: source,
        target_department: target,
        quantity: safeVal,
        unit: 'pallets_per_day',
      });
    }
    onUpdateProblem({
      ...problem,
      flows: existing,
    });
  };

  // Update a relationship cell
  const handleRelCellChange = (deptA: string, deptB: string, code: string) => {
    const existing = problem.relationships.filter(
      r => !((r.department_a === deptA && r.department_b === deptB) || (r.department_a === deptB && r.department_b === deptA))
    );
    const opt = REL_OPTIONS.find(o => o.code === code) || { score: 0 };
    if (code !== 'U') {
      existing.push({
        department_a: deptA,
        department_b: deptB,
        relationship_type: code,
        score: opt.score,
      });
    }
    onUpdateProblem({
      ...problem,
      relationships: existing,
    });
  };

  // Export Flows as CSV
  const handleExportFlowCSV = () => {
    let csv = `Source/Target,${deptIds.join(',')}\n`;
    for (const s of deptIds) {
      const row = [s];
      for (const t of deptIds) {
        row.push((flowMap[s]?.[t] || 0).toString());
      }
      csv += row.join(',') + '\n';
    }
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${problem.id}_flows.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Export REL as CSV
  const handleExportRelCSV = () => {
    let csv = `Dept_A,Dept_B,Rating,Score\n`;
    for (let i = 0; i < deptIds.length; i++) {
      for (let j = i + 1; j < deptIds.length; j++) {
        const da = deptIds[i];
        const db = deptIds[j];
        const code = relMap[da]?.[db] || 'U';
        const score = REL_OPTIONS.find(o => o.code === code)?.score || 0;
        csv += `${da},${db},${code},${score}\n`;
      }
    }
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${problem.id}_relationships.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Totals calculations
  const totalFlowSum = problem.flows.reduce((acc, f) => acc + (f.quantity || 0), 0);
  const relCount = problem.relationships.length;

  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      borderRadius: '12px',
      border: '1px solid var(--border-color)',
      padding: '1.75rem',
      marginBottom: '2rem',
    }}>
      {/* Top Header & Tab Switcher */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            {t('Malzeme Akış & Yakınlık Matrisleri (Flow & REL Matrices)', 'Flow & Relationship Matrices')}
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>
            {t(
              'Bölümler arası malzeme taşıma miktarları (From-To Flow Matrix) ve Muther Systematic Layout Planning (SLP) yakınlık dereceleri (A, E, I, O, U, X).',
              'Interactive matrix table editors for From-To material transfers and Systematic Layout Planning (SLP) closeness ratings.'
            )}
          </p>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <div style={{ display: 'flex', border: '1px solid var(--border-color)', borderRadius: '6px', overflow: 'hidden' }}>
            <button
              onClick={() => setActiveTab('flows')}
              style={{
                padding: '0.45rem 0.85rem',
                fontSize: '0.825rem',
                fontWeight: 600,
                border: 'none',
                backgroundColor: activeTab === 'flows' ? 'var(--accent-blue)' : 'var(--bg-card)',
                color: activeTab === 'flows' ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              From-To Flow Matrix ({totalFlowSum.toLocaleString()} vol)
            </button>
            <button
              onClick={() => setActiveTab('relationships')}
              style={{
                padding: '0.45rem 0.85rem',
                fontSize: '0.825rem',
                fontWeight: 600,
                border: 'none',
                backgroundColor: activeTab === 'relationships' ? 'var(--accent-blue)' : 'var(--bg-card)',
                color: activeTab === 'relationships' ? '#fff' : 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              REL Closeness Matrix ({relCount} {t('çift', 'pairs')})
            </button>
          </div>

          <button
            onClick={activeTab === 'flows' ? handleExportFlowCSV : handleExportRelCSV}
            style={{
              padding: '0.45rem 0.75rem',
              fontSize: '0.825rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-primary)',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {t('CSV İndir', 'Export CSV')}
          </button>
        </div>
      </div>

      {/* From-To Flow Matrix View */}
      {activeTab === 'flows' && (
        <div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
            {t(
              'Satırlar kaynak bölümleri (From), sütunlar hedef bölümleri (To) temsil eder. Hücrelere birim akış hacmini girin.',
              'Rows represent source departments (From); Columns represent destination departments (To). Enter transfer volume per cell.'
            )}
          </div>
          <div style={{ overflowX: 'auto', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'center' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '0.5rem', textAlign: 'left', minWidth: '90px' }}>From \ To</th>
                  {deptIds.map(d => (
                    <th key={d} style={{ padding: '0.5rem', minWidth: '65px', color: 'var(--accent-blue)' }}>
                      {d.replace(/^DEP_/, '')}
                    </th>
                  ))}
                  <th style={{ padding: '0.5rem', backgroundColor: 'rgba(59, 130, 246, 0.1)', minWidth: '70px', fontWeight: 700 }}>
                    {t('Toplam Çıkış', 'Out Total')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {deptIds.map(source => {
                  let rowSum = 0;
                  return (
                    <tr key={source} style={{ borderBottom: '1px solid var(--border-color)' }}>
                      <td style={{ padding: '0.5rem', fontWeight: 700, textAlign: 'left', backgroundColor: 'var(--bg-card)' }}>
                        {source.replace(/^DEP_/, '')}
                      </td>
                      {deptIds.map(target => {
                        const isSelf = source === target;
                        const val = flowMap[source]?.[target] || 0;
                        rowSum += val;
                        return (
                          <td key={target} style={{ padding: '0.25rem', backgroundColor: isSelf ? 'rgba(0,0,0,0.3)' : undefined }}>
                            {isSelf ? (
                              <span style={{ color: 'var(--text-muted)' }}>&mdash;</span>
                            ) : (
                              <input
                                type="number"
                                min="0"
                                value={val || ''}
                                placeholder="0"
                                onChange={(e) => handleFlowCellChange(source, target, parseFloat(e.target.value) || 0)}
                                style={{
                                  width: '55px',
                                  padding: '0.2rem',
                                  fontSize: '0.8rem',
                                  textAlign: 'center',
                                  borderRadius: '4px',
                                  border: '1px solid var(--border-color)',
                                  backgroundColor: val > 0 ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-secondary)',
                                  color: val > 0 ? '#60a5fa' : 'var(--text-muted)',
                                  fontWeight: val > 0 ? 600 : 400,
                                }}
                              />
                            )}
                          </td>
                        );
                      })}
                      <td style={{ padding: '0.5rem', fontWeight: 700, backgroundColor: 'rgba(59, 130, 246, 0.08)', color: 'var(--text-primary)' }}>
                        {rowSum.toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Relationship (REL) Matrix View */}
      {activeTab === 'relationships' && (
        <div>
          {/* REL Code Legend */}
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem', padding: '0.75rem', backgroundColor: 'var(--bg-card)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            {REL_OPTIONS.map(opt => (
              <div key={opt.code} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem' }}>
                <span style={{ width: '16px', height: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '3px', backgroundColor: opt.color, color: '#fff', fontWeight: 700 }}>
                  {opt.code}
                </span>
                <span style={{ color: 'var(--text-secondary)' }}>{opt.label.split(' - ')[1]} ({opt.score})</span>
              </div>
            ))}
          </div>

          <div style={{ overflowX: 'auto', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', textAlign: 'center' }}>
              <thead>
                <tr style={{ backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)' }}>
                  <th style={{ padding: '0.5rem', textAlign: 'left', minWidth: '90px' }}>Dept A \ B</th>
                  {deptIds.map(d => (
                    <th key={d} style={{ padding: '0.5rem', minWidth: '60px', color: 'var(--accent-blue)' }}>
                      {d.replace(/^DEP_/, '')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {deptIds.map((deptA, idxA) => (
                  <tr key={deptA} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td style={{ padding: '0.5rem', fontWeight: 700, textAlign: 'left', backgroundColor: 'var(--bg-card)' }}>
                      {deptA.replace(/^DEP_/, '')}
                    </td>
                    {deptIds.map((deptB, idxB) => {
                      if (idxA === idxB) {
                        return (
                          <td key={deptB} style={{ padding: '0.25rem', backgroundColor: 'rgba(0,0,0,0.3)' }}>
                            <span style={{ color: 'var(--text-muted)' }}>&mdash;</span>
                          </td>
                        );
                      }
                      if (idxA > idxB) {
                        // Symmetric lower triangle: mirror top
                        const code = relMap[deptA]?.[deptB] || 'U';
                        const opt = REL_OPTIONS.find(o => o.code === code) || REL_OPTIONS[4];
                        return (
                          <td key={deptB} style={{ padding: '0.25rem', opacity: 0.5 }}>
                            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: opt.color }}>
                              {code}
                            </span>
                          </td>
                        );
                      }
                      // Upper active interactive triangle
                      const code = relMap[deptA]?.[deptB] || 'U';
                      const opt = REL_OPTIONS.find(o => o.code === code) || REL_OPTIONS[4];
                      return (
                        <td key={deptB} style={{ padding: '0.25rem' }}>
                          <select
                            value={code}
                            onChange={(e) => handleRelCellChange(deptA, deptB, e.target.value)}
                            style={{
                              padding: '0.2rem',
                              fontSize: '0.8rem',
                              borderRadius: '4px',
                              border: `1px solid ${opt.color}`,
                              backgroundColor: opt.bg,
                              color: opt.color,
                              fontWeight: 700,
                              cursor: 'pointer',
                              textAlign: 'center',
                            }}
                          >
                            {REL_OPTIONS.map(o => (
                              <option key={o.code} value={o.code} style={{ backgroundColor: '#1f2937', color: '#fff' }}>
                                {o.code}
                              </option>
                            ))}
                          </select>
                        </td>
                      );
                    })}
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
