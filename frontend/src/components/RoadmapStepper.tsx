import React from 'react';
import { useLanguage } from '../context/LanguageContext';

export const RoadmapStepper: React.FC = () => {
  const { t } = useLanguage();

  const stages = [
    {
      id: 'problem',
      name: t('Problem Modelleme', 'Problem Modeling'),
      desc: t('Tesis, Bölümler, Akışlar, SLP İlişkileri, Veri Girişi', 'Facility, Departments, Flows, SLP Relations, Ingestion'),
      phase: t('Faz 2', 'Phase 2'),
      status: 'completed' as const,
    },
    {
      id: 'geometry',
      name: t('Geometri ve Yerleşimler', 'Geometry & Layouts'),
      desc: t('Sürekli/Izgara gösterimi, çakışma denetimi, imzalar', 'Continuous/Grid representation, overlap checks, signatures'),
      phase: t('Faz 3', 'Phase 3'),
      status: 'completed' as const,
    },
    {
      id: 'constraints',
      name: t('Değerlendirme ve Kısıtlar', 'Evaluation & Constraints'),
      desc: t('Akış-Mesafe, MHC, Muther SLP, kesin/esnek kısıtlar, çoklu yerleşim sıralama', 'Flow-Distance, MHC, Muther SLP, hard/soft constraints, multi-layout ranking'),
      phase: t('Faz 4', 'Phase 4'),
      status: 'completed' as const,
    },
    {
      id: 'optimization',
      name: t('Optimizasyon Çözücüleri', 'Optimization Solvers'),
      desc: t('Kurucu algoritma (CORELAP v1.0), açıklanabilirlik izi, deterministik yerleşim', 'Construction (CORELAP v1.0), explainability trace, deterministic placement'),
      phase: t('Faz 5', 'Phase 5'),
      status: 'active' as const,
    },
    {
      id: 'improvement',
      name: t('İyileştirme Sezgisel Algoritmaları', 'Improvement Heuristics'),
      desc: t('CRAFT ikili değişim, en dik iniş (steepest descent) iyileştirme', 'CRAFT pairwise exchange, steepest descent improvement'),
      phase: t('Faz 6', 'Phase 6'),
      status: 'upcoming' as const,
    },
    {
      id: 'metaheuristics',
      name: t('Metasezgiseller ve GA', 'Metaheuristics & GA'),
      desc: t('Genetik Algoritmalar, Tavlama Benzetimi, NSGA-II', 'Genetic Algorithms, Simulated Annealing, NSGA-II'),
      phase: t('Faz 7', 'Phase 7'),
      status: 'upcoming' as const,
    },
    {
      id: 'simulation',
      name: t('Dinamik Simülasyon', 'Dynamic Simulation'),
      desc: t('Ayrık olay simülasyonu, koridor yoğunluğu, malzeme akış doğrulaması', 'Discrete event, aisle congestion, material flow validation'),
      phase: t('Faz 8', 'Phase 8'),
      status: 'upcoming' as const,
    },
  ];

  const statusLabel = (status: 'completed' | 'active' | 'upcoming') => {
    if (status === 'completed') return t('Tamamlandı', 'completed');
    if (status === 'active') return t('Aktif', 'active');
    return t('Planlanan', 'upcoming');
  };

  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '12px',
      padding: '1.5rem',
      marginBottom: '2rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
            {t('Sistem Hattı ve İş Akışı İlerlemesi', 'System Pipeline & Workflow Progression')}
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {t(
              'Çok aşamalı yerleşim keşfi ve karar destek için tasarlanmış modüler mimari',
              'Modular architecture designed for multi-stage layout exploration and decision support'
            )}
          </p>
        </div>
        <span style={{
          fontSize: '0.75rem',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          padding: '0.25rem 0.6rem',
          borderRadius: '4px',
          backgroundColor: 'rgba(59, 130, 246, 0.15)',
          color: '#60a5fa',
          border: '1px solid rgba(59, 130, 246, 0.3)',
          fontWeight: 600,
        }}>
          {t('Faz 5: CORELAP Kurucu Çözücü Aktif', 'Phase 5: CORELAP Construction Solver Active')}
        </span>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))',
        gap: '0.75rem',
      }}>
        {stages.map((stage, idx) => {
          const isActive = stage.status === 'active';
          const isCompleted = stage.status === 'completed';
          const borderColor = isActive ? 'var(--accent-color)' : isCompleted ? '#10b981' : 'var(--border-color)';
          const bgBadge = isActive ? 'rgba(59, 130, 246, 0.2)' : isCompleted ? 'rgba(16, 185, 129, 0.2)' : 'rgba(107, 114, 128, 0.2)';
          const textBadge = isActive ? '#93c5fd' : isCompleted ? '#34d399' : '#9ca3af';

          return (
            <div
              key={stage.id}
              style={{
                backgroundColor: isActive ? 'rgba(59, 130, 246, 0.08)' : isCompleted ? 'rgba(16, 185, 129, 0.05)' : 'var(--bg-card)',
                border: `1px solid ${borderColor}`,
                borderRadius: '8px',
                padding: '0.9rem',
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.35rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: isActive ? 'var(--accent-color)' : isCompleted ? '#10b981' : 'var(--text-muted)',
                }}>
                  0{idx + 1}
                </span>
                <span style={{
                  fontSize: '0.65rem',
                  padding: '0.15rem 0.4rem',
                  borderRadius: '4px',
                  backgroundColor: bgBadge,
                  color: textBadge,
                  fontWeight: 600,
                  textTransform: 'capitalize',
                }}>
                  {statusLabel(stage.status)}
                </span>
              </div>
              <div style={{
                fontWeight: 600,
                fontSize: '0.85rem',
                color: isActive ? '#93c5fd' : isCompleted ? '#6ee7b7' : 'var(--text-primary)',
              }}>
                {stage.name}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', lineHeight: 1.3 }}>
                {stage.desc}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
