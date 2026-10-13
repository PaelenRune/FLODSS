import React, { useState, useEffect } from 'react';
import { LayoutExampleSummary, ContinuousLayout, LayoutValidationResult } from '../types/api';
import { fetchExampleLayouts, fetchExampleLayout, validateLayout } from '../services/api';
import { LayoutCanvas } from './LayoutCanvas';

export const LayoutViewerCard: React.FC = () => {
  const [exampleLayouts, setExampleLayouts] = useState<LayoutExampleSummary[]>([]);
  const [selectedLayoutId, setSelectedLayoutId] = useState<string>('');
  const [layout, setLayout] = useState<ContinuousLayout | null>(null);
  const [validation, setValidation] = useState<LayoutValidationResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [validating, setValidating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDeptId, setSelectedDeptId] = useState<string | null>(null);

  useEffect(() => {
    async function loadCatalog() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchExampleLayouts();
        setExampleLayouts(data);
        if (data.length > 0) {
          setSelectedLayoutId(data[0].id);
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to fetch layout examples catalog');
      } finally {
        setLoading(false);
      }
    }
    loadCatalog();
  }, []);

  useEffect(() => {
    if (!selectedLayoutId) return;

    async function loadAndValidate() {
      try {
        setValidating(true);
        setError(null);
        const layoutData = await fetchExampleLayout(selectedLayoutId);
        setLayout(layoutData);

        // Validate against problem
        const problemId = layoutData.problem_id || 'FLP_INDUSTRIAL_10';
        try {
          const valResult = await validateLayout(problemId, layoutData);
          setValidation(valResult);
        } catch (valErr: any) {
          console.warn('Validation error:', valErr);
        }
      } catch (err: any) {
        setError(err?.message || `Failed to load layout ${selectedLayoutId}`);
      } finally {
        setValidating(false);
      }
    }

    loadAndValidate();
  }, [selectedLayoutId]);

  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '12px',
      padding: '1.5rem',
      marginBottom: '2rem',
    }}>
      {/* Header and selector */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '1rem',
        marginBottom: '1.5rem',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '1.4rem' }}>📐</span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
              Phase 3 &bull; Layout Representation & Geometry Engine
            </h2>
            <span style={{
              fontSize: '0.75rem',
              padding: '0.2rem 0.6rem',
              borderRadius: '9999px',
              backgroundColor: '#3b82f620',
              color: '#60a5fa',
              border: '1px solid #3b82f640',
              fontWeight: 600,
            }}>
              2D Spatial Model
            </span>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', marginTop: '0.25rem', marginBottom: 0 }}>
            Continuous Cartesian space (origin bottom-left) &bull; Pairwise overlap verification &bull; Canonical SHA-256 signatures
          </p>
        </div>

        {/* Layout dropdown selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {validating && (
            <span style={{ fontSize: '0.75rem', color: '#60a5fa', fontWeight: 500 }}>
              Validating...
            </span>
          )}
          <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Select Layout:
          </label>
          <select
            value={selectedLayoutId}
            onChange={(e) => setSelectedLayoutId(e.target.value)}
            disabled={loading}
            style={{
              padding: '0.45rem 0.9rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-card)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              minWidth: '260px',
              cursor: 'pointer',
            }}
          >
            {exampleLayouts.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.name} ({ex.department_count} depts)
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '0.85rem 1.25rem',
          borderRadius: '8px',
          backgroundColor: '#ef444415',
          border: '1px solid #ef444440',
          color: '#f87171',
          fontSize: '0.85rem',
          marginBottom: '1rem',
        }}>
          {error}
        </div>
      )}

      {/* Interactive 2D Layout Canvas */}
      <LayoutCanvas
        layout={layout}
        validation={validation}
        selectedDeptId={selectedDeptId}
        onSelectDept={setSelectedDeptId}
      />

      {/* Spatial Placement Specifications Table */}
      {layout && (
        <div style={{ marginTop: '1rem' }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem' }}>
            Allocated Department Coordinates & Dimensions
          </h3>
          <div style={{
            overflowX: 'auto',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            backgroundColor: 'var(--bg-card)',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-color)', background: 'var(--bg-primary)', color: 'var(--text-secondary)' }}>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Department ID</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Origin (X, Y)</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Width × Height</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Area</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Centroid</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Aspect Ratio</th>
                  <th style={{ padding: '0.6rem 0.8rem' }}>Orientation</th>
                </tr>
              </thead>
              <tbody>
                {Object.values(layout.placements).map((p) => {
                  const isSelected = selectedDeptId === p.department_id;
                  const aspect = Math.max(p.width, p.height) / Math.min(p.width, p.height);
                  return (
                    <tr
                      key={p.department_id}
                      onClick={() => setSelectedDeptId(isSelected ? null : p.department_id)}
                      style={{
                        borderBottom: '1px solid var(--border-color)',
                        cursor: 'pointer',
                        backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                        transition: 'background-color 0.1s ease',
                      }}
                    >
                      <td style={{ padding: '0.6rem 0.8rem', fontWeight: 600, color: isSelected ? 'var(--accent-color)' : 'var(--text-primary)' }}>
                        {p.department_id}
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem', fontFamily: 'monospace' }}>
                        ({p.x.toFixed(1)}, {p.y.toFixed(1)})
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>
                        {p.width.toFixed(1)}m × {p.height.toFixed(1)}m
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem', fontWeight: 500 }}>
                        {(p.width * p.height).toLocaleString()} m²
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                        ({(p.x + p.width / 2).toFixed(1)}, {(p.y + p.height / 2).toFixed(1)})
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem' }}>
                        {aspect.toFixed(2)}
                      </td>
                      <td style={{ padding: '0.6rem 0.8rem', color: 'var(--text-secondary)' }}>
                        {p.orientation_degrees ?? 0.0}°
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
