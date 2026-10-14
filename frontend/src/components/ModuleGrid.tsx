import React from 'react';
import { SystemStatus } from '../types/api';
import { useLanguage } from '../context/LanguageContext';

interface ModuleGridProps {
  status: SystemStatus | null;
}

const ARCHITECTURAL_MODULES = [
  {
    key: 'models',
    name: 'Core Data Models',
    desc: 'Pydantic schemas: Facility, Department, Material Flow, SLP Relationship, and Constraints.',
    category: 'Domain Layer',
  },
  {
    key: 'algorithms',
    name: 'Algorithm Registry & Base Interface',
    desc: 'Extensible ABC contract enabling CORELAP, CRAFT, Metaheuristics, and MILP plug-ins.',
    category: 'Optimization Core',
  },
  {
    key: 'evaluation',
    name: 'Decoupled Evaluation Engine',
    desc: 'Independent evaluation of material handling cost, flow distance, closeness satisfaction, compactness.',
    category: 'Performance Analytics',
  },
  {
    key: 'constraints',
    name: 'Constraint Validation Engine',
    desc: 'Hard & soft feasibility checks: non-overlapping boundaries, clearances, and forbidden zones.',
    category: 'Rule Engine',
  },
  {
    key: 'optimization',
    name: 'Multi-Objective & Pareto Solvers',
    desc: 'Foundation for NSGA-II, Pareto front ranking, and trade-off exploration.',
    category: 'Metaheuristics & Exact',
  },
  {
    key: 'simulation',
    name: 'Dynamic Simulation Engine',
    desc: 'Discrete event flow validation, aisle congestion analysis, and stochastic material handling.',
    category: 'Verification & Dynamics',
  },
  {
    key: 'ai',
    name: 'AI Advisor & Decision Support',
    desc: 'Industrial layout diagnosis and reasoning engine (prepared for Gemini API integration).',
    category: 'Cognitive Layer',
  },
  {
    key: 'visualization',
    name: 'Spatial Rendering Subsystem',
    desc: 'Normalized coordinate transformers for 2D plant blueprints and future 3D factory view.',
    category: 'Visualization',
  },
];

export const ModuleGrid: React.FC<ModuleGridProps> = ({ status }) => {
  const { t } = useLanguage();
  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '12px',
      padding: '1.5rem',
    }}>
      <div style={{ marginBottom: '1.25rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
          {t('Modüler Alt Sistemler & Bağımsız Mimari (Decoupled Subsystems)', 'Modular Subsystems & Decoupled Architecture')}
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          {t(
            'Her alt sistem sıkı arayüz sözleşmeleriyle bağımsız çalışır, monolitik bağımlılıkları engeller.',
            'Each subsystem operates independently with strict interface contracts, preventing monolithic coupling.'
          )}
        </p>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '1rem',
      }}>
        {ARCHITECTURAL_MODULES.map((mod) => {
          const modStatus = status?.modules[mod.key] || 'ready';
          const isActive = modStatus === 'active';

          return (
            <div
              key={mod.key}
              style={{
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '1.1rem',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                transition: 'border-color 0.2s, background-color 0.2s',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{
                    fontSize: '0.7rem',
                    color: 'var(--accent-blue)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    fontWeight: 600,
                  }}>
                    {mod.category}
                  </span>
                  <span style={{
                    fontSize: '0.65rem',
                    padding: '0.15rem 0.5rem',
                    borderRadius: '9999px',
                    backgroundColor: isActive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                    color: isActive ? '#34d399' : '#60a5fa',
                    border: `1px solid ${isActive ? 'rgba(16, 185, 129, 0.3)' : 'rgba(59, 130, 246, 0.3)'}`,
                    fontWeight: 600,
                    textTransform: 'uppercase',
                  }}>
                    {modStatus}
                  </span>
                </div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                  {mod.name}
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {mod.desc}
                </p>
              </div>

              <div style={{ marginTop: '0.85rem', paddingTop: '0.65rem', borderTop: '1px solid rgba(255, 255, 255, 0.05)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                <code>app.{mod.key}</code>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
