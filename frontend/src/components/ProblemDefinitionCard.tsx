import React, { useState, useEffect } from 'react';
import { ProblemSummary, FacilityLayoutProblem } from '../types/api';
import { fetchExampleProblems, fetchExampleProblem } from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import { localizeBenchmarkText, localizeDepartmentName } from '../utils/localizeDomain';

export const ProblemDefinitionCard: React.FC = () => {
  const { t } = useLanguage();
  const [examples, setExamples] = useState<ProblemSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [problem, setProblem] = useState<FacilityLayoutProblem | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [problemLoading, setProblemLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'departments' | 'flows' | 'constraints'>('overview');

  useEffect(() => {
    async function loadExamples() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchExampleProblems();
        setExamples(data);
        if (data.length > 0) {
          setSelectedId(data[0].id);
        }
      } catch (err: any) {
        setError(err?.message || t('Örnek problemler alınamadı', 'Failed to fetch example problems'));
      } finally {
        setLoading(false);
      }
    }
    loadExamples();
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    async function loadDetail() {
      try {
        setProblemLoading(true);
        const data = await fetchExampleProblem(selectedId);
        setProblem(data);
      } catch (err: any) {
        setError(err?.message || t(`${selectedId} problemi yüklenemedi`, `Failed to load problem ${selectedId}`));
      } finally {
        setProblemLoading(false);
      }
    }
    loadDetail();
  }, [selectedId]);

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
        marginBottom: '1.25rem',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              color: 'var(--accent-blue)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
            }}>
              {t('Faz 2 Aktif', 'Phase 2 Active')}
            </span>
            <span style={{
              fontSize: '0.7rem',
              padding: '0.15rem 0.45rem',
              borderRadius: '4px',
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              color: '#34d399',
              fontWeight: 600,
            }}>
              {t('Veri Girişi Hazır', 'Data Ingestion Ready')}
            </span>
          </div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 600, marginTop: '0.2rem' }}>
            {t('Tesis Yerleşimi Problem Tanımı', 'Facility Layout Problem Specification')}
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {t(
              'Doğrulanmış tesis sınırlarını, bölüm alanlarını, malzeme akışlarını ve kısıtları inceleyin.',
              'Inspect validated plant boundary, department footprints, material flows, and constraints.'
            )}
          </p>
        </div>

        {/* Example Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label htmlFor="example-select" style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {t('Aktif Vaka:', 'Active Case:')}
          </label>
          <select
            id="example-select"
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            disabled={loading}
            style={{
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              padding: '0.45rem 0.85rem',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 500,
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            {examples.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {localizeBenchmarkText(ex.name, t)} ({ex.department_count} {t('bölüm', 'depts')})
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div style={{
          padding: '0.85rem',
          borderRadius: '8px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#f87171',
          fontSize: '0.85rem',
          marginBottom: '1rem',
        }}>
          {error}
        </div>
      )}

      {problemLoading || !problem ? (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          {t('Problem parametreleri yükleniyor...', 'Loading problem parameters...')}
        </div>
      ) : (
        <div>
          {/* Key Metrics Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
            marginBottom: '1.5rem',
          }}>
            <div style={{
              backgroundColor: 'var(--bg-card)',
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
            }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{t('Tesis Sınırı', 'Facility Boundary')}</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
                {problem.facility.width}m × {problem.facility.height}m
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {problem.facility.area?.toLocaleString()} m² {t('toplam alan', 'total area')}
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
            }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{t('Bölümler', 'Departments')}</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--accent-blue)', marginTop: '0.2rem' }}>
                {problem.departments.length} {t('İş Hücresi', 'Work Cells')}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {problem.departments.reduce((acc, d) => acc + d.required_area, 0).toLocaleString()} m² {t('gerekli', 'required')}
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
            }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{t('Alan Kullanımı', 'Area Utilization')}</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#34d399', marginTop: '0.2rem' }}>
                {((problem.departments.reduce((acc, d) => acc + d.required_area, 0) / (problem.facility.area || 1)) * 100).toFixed(1)}%
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {t('Koridorlar ve tamponlar için boşluk', 'Clearance for aisles & buffers')}
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
            }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{t('Malzeme Akışı', 'Material Flow')}</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f59e0b', marginTop: '0.2rem' }}>
                {problem.flows.length} {t('Bağlantı', 'Connections')}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {problem.flows.reduce((acc, f) => acc + f.quantity, 0).toLocaleString()} {t('yük/gün', 'loads/day')}
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
            }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{t('REL İlişkileri', 'REL Relationships')}</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#a78bfa', marginTop: '0.2rem' }}>
                {problem.relationships.length} {t('Derece', 'Ratings')}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {t('Muther SLP yakınlık çizelgesi', 'Muther SLP closeness chart')}
              </div>
            </div>

            <div style={{
              backgroundColor: 'var(--bg-card)',
              padding: '1rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
            }}>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>{t('Kısıtlar', 'Constraints')}</div>
              <div style={{ fontSize: '1.15rem', fontWeight: 700, color: '#f43f5e', marginTop: '0.2rem' }}>
                {problem.constraints.length} {t('Kural', 'Rules')}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                {problem.constraints.filter(c => c.classification === 'hard').length} {t('Kesin', 'Hard')} &bull; {problem.constraints.filter(c => c.classification === 'soft').length} {t('Esnek', 'Soft')}
              </div>
            </div>
          </div>

          {/* Subtabs for Inspection */}
          <div style={{
            display: 'flex',
            gap: '0.5rem',
            borderBottom: '1px solid var(--border-color)',
            marginBottom: '1rem',
            paddingBottom: '0.5rem',
          }}>
            <button
              onClick={() => setActiveTab('overview')}
              style={{
                background: 'none',
                border: 'none',
                color: activeTab === 'overview' ? 'var(--accent-blue)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'overview' ? 600 : 400,
                fontSize: '0.85rem',
                padding: '0.35rem 0.75rem',
                borderRadius: '4px',
                backgroundColor: activeTab === 'overview' ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
              }}
            >
              {t('Genel Bakış ve Amaçlar', 'Overview & Objectives')}
            </button>
            <button
              onClick={() => setActiveTab('departments')}
              style={{
                background: 'none',
                border: 'none',
                color: activeTab === 'departments' ? 'var(--accent-blue)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'departments' ? 600 : 400,
                fontSize: '0.85rem',
                padding: '0.35rem 0.75rem',
                borderRadius: '4px',
                backgroundColor: activeTab === 'departments' ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
              }}
            >
              {t('Bölümler', 'Departments')} ({problem.departments.length})
            </button>
            <button
              onClick={() => setActiveTab('flows')}
              style={{
                background: 'none',
                border: 'none',
                color: activeTab === 'flows' ? 'var(--accent-blue)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'flows' ? 600 : 400,
                fontSize: '0.85rem',
                padding: '0.35rem 0.75rem',
                borderRadius: '4px',
                backgroundColor: activeTab === 'flows' ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
              }}
            >
              {t('Akışlar', 'Flows')} ({problem.flows.length})
            </button>
            <button
              onClick={() => setActiveTab('constraints')}
              style={{
                background: 'none',
                border: 'none',
                color: activeTab === 'constraints' ? 'var(--accent-blue)' : 'var(--text-secondary)',
                fontWeight: activeTab === 'constraints' ? 600 : 400,
                fontSize: '0.85rem',
                padding: '0.35rem 0.75rem',
                borderRadius: '4px',
                backgroundColor: activeTab === 'constraints' ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
              }}
            >
              {t('Kısıtlar ve Kurallar', 'Constraints & Rules')} ({problem.constraints.length})
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'overview' && (
            <div style={{
              backgroundColor: 'var(--bg-card)',
              padding: '1.25rem',
              borderRadius: '8px',
              border: '1px solid var(--border-color)',
            }}>
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                {t('Optimizasyon Amaçları Yapılandırması', 'Optimization Objectives Configuration')}
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                {t('Problem tanımından okunan ağırlıklar ve optimizasyon yönleri:', 'Weights and optimization directions parsed from problem specification:')}
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.75rem' }}>
                {problem.objective_config?.objectives && Object.entries(problem.objective_config.objectives).map(([k, v]: [string, any]) => (
                  <div key={k} style={{
                    padding: '0.75rem',
                    borderRadius: '6px',
                    backgroundColor: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid rgba(255, 255, 255, 0.06)',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{k.replace(/_/g, ' ')}</span>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '0.1rem 0.4rem',
                        borderRadius: '3px',
                        backgroundColor: v.direction === 'minimize' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                        color: v.direction === 'minimize' ? '#60a5fa' : '#34d399',
                        textTransform: 'uppercase',
                        fontWeight: 600,
                      }}>
                        {v.direction === 'minimize' ? t('EN KÜÇÜKLE', 'minimize') : t('EN BÜYÜKLE', 'maximize')}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                      {t('Ağırlık faktörü:', 'Weight factor:')} <strong>{v.weight}</strong> &bull; {v.enabled ? t('Etkin', 'Enabled') : t('Devre Dışı', 'Disabled')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'departments' && (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', textAlign: 'left' }}>
                    <th style={{ padding: '0.6rem' }}>{t('Kod', 'ID')}</th>
                    <th style={{ padding: '0.6rem' }}>{t('Bölüm Adı', 'Department Name')}</th>
                    <th style={{ padding: '0.6rem' }}>{t('Gerekli Alan', 'Required Area')}</th>
                    <th style={{ padding: '0.6rem' }}>{t('Genişlik Sınırları', 'Width Bounds')}</th>
                    <th style={{ padding: '0.6rem' }}>{t('Rampa / Özellikler', 'Dock / Attributes')}</th>
                  </tr>
                </thead>
                <tbody>
                  {problem.departments.map((d) => (
                    <tr key={d.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                      <td style={{ padding: '0.6rem', fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>{d.id}</td>
                      <td style={{ padding: '0.6rem', fontWeight: 500 }}>{localizeDepartmentName(d.name, t)}</td>
                      <td style={{ padding: '0.6rem' }}>{d.required_area} m²</td>
                      <td style={{ padding: '0.6rem', color: 'var(--text-muted)' }}>
                        {d.min_width ? `${d.min_width}m – ${d.max_width}m` : t('Sınırsız', 'Unconstrained')}
                      </td>
                      <td style={{ padding: '0.6rem', color: 'var(--text-muted)' }}>
                        {d.metadata?.requires_dock ? t('Rampa Gerekli', 'Dock Required') : d.metadata?.hazard ? d.metadata.hazard : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'flows' && (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)', textAlign: 'left' }}>
                    <th style={{ padding: '0.6rem' }}>{t('Kaynak', 'Source')}</th>
                    <th style={{ padding: '0.6rem' }}>{t('Hedef', 'Target')}</th>
                    <th style={{ padding: '0.6rem' }}>{t('Miktar', 'Quantity')}</th>
                    <th style={{ padding: '0.6rem' }}>{t('Ürün / Malzeme', 'Product / Material')}</th>
                    <th style={{ padding: '0.6rem' }}>{t('Birim Taşıma Maliyeti', 'Handling Unit Cost')}</th>
                  </tr>
                </thead>
                <tbody>
                  {problem.flows.map((f, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                      <td style={{ padding: '0.6rem', fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>{f.source_department}</td>
                      <td style={{ padding: '0.6rem', fontFamily: 'var(--font-mono)', color: '#818cf8' }}>{f.target_department}</td>
                      <td style={{ padding: '0.6rem', fontWeight: 600 }}>{f.quantity} {f.unit}</td>
                      <td style={{ padding: '0.6rem', color: 'var(--text-secondary)' }}>{f.product_or_process_id || t('Genel Malzeme', 'General Material')}</td>
                      <td style={{ padding: '0.6rem', color: 'var(--text-muted)' }}>{f.cost_per_unit_distance || 1.0} $/m</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === 'constraints' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {problem.constraints.map((c) => (
                <div key={c.id} style={{
                  backgroundColor: 'var(--bg-card)',
                  padding: '0.9rem',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '0.85rem' }}>{c.id}</span>
                      <span style={{
                        fontSize: '0.65rem',
                        padding: '0.1rem 0.4rem',
                        borderRadius: '3px',
                        backgroundColor: c.classification === 'hard' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                        color: c.classification === 'hard' ? '#f87171' : '#fbbf24',
                        textTransform: 'uppercase',
                        fontWeight: 700,
                      }}>
                        {c.classification === 'hard' ? t('KESİN', 'hard') : t('ESNEK', 'soft')}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {t('Tür:', 'Type:')} {c.type}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                      {t('İlgili bölümler:', 'Involved:')} {c.involved_departments.length > 0 ? c.involved_departments.join(', ') : t('Tüm bölümler', 'All departments')}
                      {c.parameters?.distance && ` | ${t('Mesafe parametresi:', 'Distance parameter:')} ≥ ${c.parameters.distance}m`}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {t('Ceza:', 'Penalty:')} {c.penalty}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
