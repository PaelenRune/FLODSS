import React, { useState } from 'react';
import { FacilityLayoutProblem, Department, ProblemValidationReport } from '../types/api';
import { validateProblemPayload } from '../services/api';
import { useLanguage } from '../context/LanguageContext';

interface ProblemEditorCardProps {
  problem: FacilityLayoutProblem | null;
  onUpdateProblem: (updated: FacilityLayoutProblem) => void;
  onLoadExample: (problemId: string) => void;
  availableExamples: Array<{ id: string; name: string }>;
}

export const ProblemEditorCard: React.FC<ProblemEditorCardProps> = ({
  problem,
  onUpdateProblem,
  onLoadExample,
  availableExamples,
}) => {
  const { t } = useLanguage();
  const [validating, setValidating] = useState(false);
  const [validationReport, setValidationReport] = useState<ProblemValidationReport | null>(null);
  const [editingDeptId, setEditingDeptId] = useState<string | null>(null);

  // New department template form
  const [newDeptId, setNewDeptId] = useState('');
  const [newDeptName, setNewDeptName] = useState('');
  const [newDeptArea, setNewDeptArea] = useState<number>(1000);
  const [newDeptMinAspect, setNewDeptMinAspect] = useState<number>(1.0);
  const [newDeptMaxAspect, setNewDeptMaxAspect] = useState<number>(3.0);
  const [newDeptIsFixed, setNewDeptIsFixed] = useState(false);
  const [newDeptFixedX, setNewDeptFixedX] = useState<number>(0);
  const [newDeptFixedY, setNewDeptFixedY] = useState<number>(0);

  if (!problem) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
        <p style={{ color: 'var(--text-muted)' }}>
          {t('Yüklü problem bulunmuyor. Bir benchmark seçin veya yeni problem oluşturun.', 'No problem loaded. Select a benchmark or create a new problem.')}
        </p>
      </div>
    );
  }

  // Facility dimensions updates
  const handleFacilityDimChange = (field: 'width' | 'height', val: number) => {
    if (val <= 0) return;
    const updated: FacilityLayoutProblem = {
      ...problem,
      facility: {
        ...problem.facility,
        [field]: val,
        area: field === 'width' ? val * problem.facility.height : problem.facility.width * val,
      },
    };
    onUpdateProblem(updated);
  };

  // Add department
  const handleAddDepartment = () => {
    const cleanId = newDeptId.trim().toUpperCase() || `DEP_${(problem.departments.length + 1).toString().padStart(2, '0')}`;
    if (problem.departments.some(d => d.id === cleanId)) {
      alert(t(`'${cleanId}' ID'li bölüm zaten mevcut.`, `Department with ID '${cleanId}' already exists.`));
      return;
    }
    const newDept: Department = {
      id: cleanId,
      name: newDeptName.trim() || `Department ${cleanId}`,
      required_area: Number(newDeptArea) || 1000,
      min_aspect_ratio: Number(newDeptMinAspect) || 1.0,
      max_aspect_ratio: Number(newDeptMaxAspect) || 3.0,
      fixed_position: newDeptIsFixed ? { x: Number(newDeptFixedX) || 0, y: Number(newDeptFixedY) || 0 } : undefined,
    };
    const updated: FacilityLayoutProblem = {
      ...problem,
      departments: [...problem.departments, newDept],
    };
    onUpdateProblem(updated);
    // Reset form
    setNewDeptId('');
    setNewDeptName('');
    setNewDeptArea(1000);
    setNewDeptIsFixed(false);
  };

  // Remove department
  const handleRemoveDepartment = (deptId: string) => {
    const updated: FacilityLayoutProblem = {
      ...problem,
      departments: problem.departments.filter(d => d.id !== deptId),
      flows: problem.flows.filter(f => f.source_department !== deptId && f.target_department !== deptId),
      relationships: problem.relationships.filter(r => r.department_a !== deptId && r.department_b !== deptId),
    };
    onUpdateProblem(updated);
  };

  // Department field edit
  const handleDeptChange = (deptId: string, field: keyof Department, val: any) => {
    const updated: FacilityLayoutProblem = {
      ...problem,
      departments: problem.departments.map(d => {
        if (d.id === deptId) {
          return { ...d, [field]: val };
        }
        return d;
      }),
    };
    onUpdateProblem(updated);
  };

  // Validate problem against backend schema
  const handleValidate = async () => {
    setValidating(true);
    setValidationReport(null);
    try {
      const report = await validateProblemPayload(problem);
      setValidationReport(report);
    } catch (e: any) {
      setValidationReport({
        is_valid: false,
        errors: [e.message || 'Validation request failed'],
        warnings: [],
        stats: {},
      });
    } finally {
      setValidating(false);
    }
  };

  const totalReqArea = problem.departments.reduce((acc, d) => acc + (d.required_area || 0), 0);
  const facArea = (problem.facility.width || 1) * (problem.facility.height || 1);
  const utilPct = (totalReqArea / facArea) * 100;

  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      borderRadius: '12px',
      border: '1px solid var(--border-color)',
      padding: '1.75rem',
      marginBottom: '2rem',
    }}>
      {/* Synthetic Benchmark & Confidential Data Notice Banner */}
      <div style={{
        backgroundColor: 'rgba(234, 88, 12, 0.1)',
        border: '1px solid rgba(234, 88, 12, 0.35)',
        borderRadius: '8px',
        padding: '0.85rem 1.15rem',
        marginBottom: '1.25rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
      }}>
        <span style={{ fontSize: '1.25rem' }}>⚠️</span>
        <div style={{ fontSize: '0.825rem', color: '#ea580c', lineHeight: 1.45 }}>
          <strong>{t('Gizlilik & Akademik Veri Notu:', 'Confidential Research Pilot Notice:')}</strong>{' '}
          {t(
            'Bu web pilotu sentetik benchmark ve akademik test örnekleri (Simple 4, Industrial 10, Warehouse 12 vb.) için yapılandırılmıştır. Lütfen gerçek fabrika gizli verilerini veya ticari sır içeren üretim matrislerini yüklemeyiniz.',
            'This web pilot is restricted to synthetic benchmarks and academic test instances (e.g., Simple 4, Industrial 10, Warehouse 12). Do not enter, paste, or upload real-world proprietary factory layouts, sensitive customer bill-of-materials, or confidential production flow matrices.'
          )}
        </div>
      </div>

      {/* Top Header & Fast Benchmark Loader */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            {t('Tesis Yerleşim Problemi Tanımlama (FLP Problem Editor)', 'Factory Problem Editor')}
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>
            {t(
              'Tesis sınırlarını, üretim/lojistik bölümlerini, Aspect Ratio kısıtlarını ve Fixed Position koordinatlarını yapılandırın.',
              'Configure plant boundaries, production departments, aspect ratio constraints, and fixed locations without editing raw JSON.'
            )}
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
            {t('Benchmark Şablonu:', 'Load Template:')}
          </label>
          <select
            value={problem.id}
            onChange={(e) => onLoadExample(e.target.value)}
            style={{
              padding: '0.45rem 0.85rem',
              backgroundColor: 'var(--bg-card)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            {availableExamples.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.name}
              </option>
            ))}
          </select>

          <button
            onClick={handleValidate}
            disabled={validating}
            style={{
              padding: '0.45rem 1rem',
              backgroundColor: 'var(--accent-blue)',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            {validating ? t('Doğrulanıyor...', 'Validating...') : t('✓ Problemi Doğrula', '✓ Validate Problem')}
          </button>
        </div>
      </div>

      {/* Validation Banner */}
      {validationReport && (
        <div style={{
          padding: '1rem',
          borderRadius: '8px',
          marginBottom: '1.5rem',
          backgroundColor: validationReport.is_valid ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
          border: `1px solid ${validationReport.is_valid ? '#10b981' : '#ef4444'}`,
        }}>
          <div style={{ fontWeight: 700, color: validationReport.is_valid ? '#34d399' : '#f87171', fontSize: '0.9rem' }}>
            {validationReport.is_valid
              ? t('✓ Problem Tanımı Geçerli & Çözücüye (Solver) Hazır', '✓ Problem Definition Valid & Solver Ready')
              : t('⚠ Doğrulama Sorunları Tespit Edildi', '⚠ Validation Issues Detected')}
          </div>
          {validationReport.errors && validationReport.errors.length > 0 && (
            <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem', color: '#f87171', fontSize: '0.8rem' }}>
              {validationReport.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          )}
          {validationReport.warnings && validationReport.warnings.length > 0 && (
            <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem', color: '#fbbf24', fontSize: '0.8rem' }}>
              {validationReport.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Facility Boundary & Quick Stats Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem',
        padding: '1.25rem',
        backgroundColor: 'var(--bg-card)',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
      }}>
        <div>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
            {t('Tesis Genişliği (Width X - metre):', 'Facility Width (X-axis meters):')}
          </label>
          <input
            type="number"
            min="10"
            max="1000"
            value={problem.facility.width}
            onChange={(e) => handleFacilityDimChange('width', parseFloat(e.target.value) || 1)}
            style={{
              width: '100%',
              padding: '0.45rem 0.65rem',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
              fontSize: '0.9rem',
              fontWeight: 600,
            }}
          />
        </div>

        <div>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
            {t('Tesis Yüksekliği (Height Y - metre):', 'Facility Height (Y-axis meters):')}
          </label>
          <input
            type="number"
            min="10"
            max="1000"
            value={problem.facility.height}
            onChange={(e) => handleFacilityDimChange('height', parseFloat(e.target.value) || 1)}
            style={{
              width: '100%',
              padding: '0.45rem 0.65rem',
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
              fontSize: '0.9rem',
              fontWeight: 600,
            }}
          />
        </div>

        <div>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
            {t('Toplam Tesis Alanı (Footprint):', 'Facility Footprint:')}
          </label>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '0.2rem' }}>
            {facArea.toLocaleString()} m²
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {t('Kullanılabilir Brüt Zemin Alanı', 'Available Gross Boundary Area')}
          </span>
        </div>

        <div>
          <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
            {t('Alan Kullanım Oranı (Utilization):', 'Department Utilization:')}
          </label>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: utilPct > 95 ? '#ef4444' : utilPct >= 80 ? '#10b981' : '#f59e0b', marginTop: '0.2rem' }}>
            {utilPct.toFixed(1)}% ({totalReqArea.toLocaleString()} m²)
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {problem.departments.length} {t('Fonksiyonel Bölüm (Activity Center)', 'Functional Activity Centers')}
          </span>
        </div>
      </div>

      {/* Departments Table */}
      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            {t(`Üretim & Lojistik Bölümleri (${problem.departments.length})`, `Production & Logistics Departments (${problem.departments.length})`)}
          </h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {t('Toplam bölüm alanı ≤ brüt tesis alanı olmalıdır', 'All areas must sum ≤ facility gross area')}
          </span>
        </div>

        <div style={{ overflowX: 'auto', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-secondary)' }}>
                <th style={{ padding: '0.65rem 0.85rem' }}>ID</th>
                <th style={{ padding: '0.65rem 0.85rem' }}>{t('Bölüm Adı (Department)', 'Department Name')}</th>
                <th style={{ padding: '0.65rem 0.85rem' }}>{t('Gerekli Alan (m²)', 'Req Area (m²)')}</th>
                <th style={{ padding: '0.65rem 0.85rem' }}>Min Aspect Ratio</th>
                <th style={{ padding: '0.65rem 0.85rem' }}>Max Aspect Ratio</th>
                <th style={{ padding: '0.65rem 0.85rem' }}>Fixed Position</th>
                <th style={{ padding: '0.65rem 0.85rem', textAlign: 'right' }}>{t('İşlemler', 'Actions')}</th>
              </tr>
            </thead>
            <tbody>
              {problem.departments.map((dept) => {
                const isEditing = editingDeptId === dept.id;
                return (
                  <tr key={dept.id} style={{ borderBottom: '1px solid var(--border-color)', backgroundColor: isEditing ? 'rgba(59, 130, 246, 0.08)' : 'transparent' }}>
                    <td style={{ padding: '0.65rem 0.85rem', fontWeight: 700, color: 'var(--accent-blue)' }}>
                      {dept.id}
                    </td>
                    <td style={{ padding: '0.65rem 0.85rem' }}>
                      {isEditing ? (
                        <input
                          type="text"
                          value={dept.name}
                          onChange={(e) => handleDeptChange(dept.id, 'name', e.target.value)}
                          style={{ padding: '0.2rem 0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', width: '100%' }}
                        />
                      ) : (
                        dept.name
                      )}
                    </td>
                    <td style={{ padding: '0.65rem 0.85rem' }}>
                      {isEditing ? (
                        <input
                          type="number"
                          value={dept.required_area}
                          onChange={(e) => handleDeptChange(dept.id, 'required_area', parseFloat(e.target.value) || 100)}
                          style={{ padding: '0.2rem 0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', width: '90px' }}
                        />
                      ) : (
                        `${dept.required_area.toLocaleString()} m²`
                      )}
                    </td>
                    <td style={{ padding: '0.65rem 0.85rem' }}>
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.1"
                          value={dept.min_aspect_ratio || 1.0}
                          onChange={(e) => handleDeptChange(dept.id, 'min_aspect_ratio', parseFloat(e.target.value) || 1.0)}
                          style={{ padding: '0.2rem 0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', width: '65px' }}
                        />
                      ) : (
                        (dept.min_aspect_ratio || 1.0).toFixed(1)
                      )}
                    </td>
                    <td style={{ padding: '0.65rem 0.85rem' }}>
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.1"
                          value={dept.max_aspect_ratio || 3.0}
                          onChange={(e) => handleDeptChange(dept.id, 'max_aspect_ratio', parseFloat(e.target.value) || 3.0)}
                          style={{ padding: '0.2rem 0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', width: '65px' }}
                        />
                      ) : (
                        (dept.max_aspect_ratio || 3.0).toFixed(1)
                      )}
                    </td>
                    <td style={{ padding: '0.65rem 0.85rem' }}>
                      {dept.fixed_position ? (
                        <span style={{ color: '#fbbf24', fontWeight: 600 }}>
                          📌 ({dept.fixed_position.x}, {dept.fixed_position.y})
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)' }}>Floating</span>
                      )}
                    </td>
                    <td style={{ padding: '0.65rem 0.85rem', textAlign: 'right' }}>
                      <button
                        onClick={() => setEditingDeptId(isEditing ? null : dept.id)}
                        style={{
                          marginRight: '0.5rem',
                          padding: '0.25rem 0.5rem',
                          fontSize: '0.75rem',
                          borderRadius: '4px',
                          border: '1px solid var(--border-color)',
                          backgroundColor: 'var(--bg-card)',
                          color: 'var(--text-primary)',
                        }}
                      >
                        {isEditing ? t('Tamam', 'Done') : t('Düzenle', 'Edit')}
                      </button>
                      <button
                        onClick={() => handleRemoveDepartment(dept.id)}
                        style={{
                          padding: '0.25rem 0.5rem',
                          fontSize: '0.75rem',
                          borderRadius: '4px',
                          border: '1px solid rgba(239, 68, 68, 0.4)',
                          backgroundColor: 'rgba(239, 68, 68, 0.1)',
                          color: '#f87171',
                        }}
                      >
                        {t('Sil', 'Delete')}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Department Inline Form */}
      <div style={{
        padding: '1.25rem',
        backgroundColor: 'var(--bg-card)',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
      }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, margin: '0 0 0.85rem', color: 'var(--text-primary)' }}>
          {t('+ Yeni Bölüm (Department) Ekle', '+ Add New Department')}
        </h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem', alignItems: 'end' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>ID:</label>
            <input
              type="text"
              placeholder="e.g. DEP_11"
              value={newDeptId}
              onChange={(e) => setNewDeptId(e.target.value)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
              {t('Bölüm Adı:', 'Name:')}
            </label>
            <input
              type="text"
              placeholder={t('Örn: Paketleme Birimi', 'Packaging Unit')}
              value={newDeptName}
              onChange={(e) => setNewDeptName(e.target.value)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>
              {t('Alan (m²):', 'Area (m²):')}
            </label>
            <input
              type="number"
              value={newDeptArea}
              onChange={(e) => setNewDeptArea(parseFloat(e.target.value) || 500)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Min Aspect Ratio:</label>
            <input
              type="number"
              step="0.1"
              value={newDeptMinAspect}
              onChange={(e) => setNewDeptMinAspect(parseFloat(e.target.value) || 1.0)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Max Aspect Ratio:</label>
            <input
              type="number"
              step="0.1"
              value={newDeptMaxAspect}
              onChange={(e) => setNewDeptMaxAspect(parseFloat(e.target.value) || 3.0)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-secondary)', cursor: 'pointer', marginBottom: '0.45rem' }}>
              <input
                type="checkbox"
                checked={newDeptIsFixed}
                onChange={(e) => setNewDeptIsFixed(e.target.checked)}
              />
              Fixed Position?
            </label>
            {newDeptIsFixed && (
              <div style={{ display: 'flex', gap: '0.25rem' }}>
                <input
                  type="number"
                  placeholder="X"
                  value={newDeptFixedX}
                  onChange={(e) => setNewDeptFixedX(parseFloat(e.target.value) || 0)}
                  style={{ width: '50%', padding: '0.3rem', fontSize: '0.75rem', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', borderRadius: '4px' }}
                />
                <input
                  type="number"
                  placeholder="Y"
                  value={newDeptFixedY}
                  onChange={(e) => setNewDeptFixedY(parseFloat(e.target.value) || 0)}
                  style={{ width: '50%', padding: '0.3rem', fontSize: '0.75rem', backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-color)', color: 'var(--text-primary)', borderRadius: '4px' }}
                />
              </div>
            )}
          </div>
          <div>
            <button
              onClick={handleAddDepartment}
              style={{
                width: '100%',
                padding: '0.45rem',
                backgroundColor: 'var(--accent-blue)',
                color: '#fff',
                border: 'none',
                borderRadius: '6px',
                fontWeight: 600,
                fontSize: '0.85rem',
                cursor: 'pointer',
              }}
            >
              {t('Bölüm Ekle', 'Add Department')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
