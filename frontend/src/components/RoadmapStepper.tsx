import React from 'react';

const STAGES = [
  { id: 'problem', name: 'Problem Modeling', desc: 'Facility, Departments, Flows, SLP Relations, Ingestion', phase: 'Phase 2', status: 'completed' },
  { id: 'geometry', name: 'Geometry & Layouts', desc: 'Continuous/Grid representation, overlap checks, signatures', phase: 'Phase 3', status: 'completed' },
  { id: 'constraints', name: 'Evaluation & Constraints', desc: 'Flow-Distance, MHC, Muther SLP, hard/soft constraints, multi-layout ranking', phase: 'Phase 4', status: 'completed' },
  { id: 'optimization', name: 'Optimization Solvers', desc: 'Construction (CORELAP v1.0), explainability trace, deterministic placement', phase: 'Phase 5', status: 'active' },
  { id: 'improvement', name: 'Improvement Heuristics', desc: 'CRAFT pairwise exchange, steepest descent improvement', phase: 'Phase 6', status: 'upcoming' },
  { id: 'metaheuristics', name: 'Metaheuristics & GA', desc: 'Genetic Algorithms, Simulated Annealing, NSGA-II', phase: 'Phase 7', status: 'upcoming' },
  { id: 'simulation', name: 'Dynamic Simulation', desc: 'Discrete event, aisle congestion, material flow validation', phase: 'Phase 8', status: 'upcoming' },
];

export const RoadmapStepper: React.FC = () => {
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
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>System Pipeline & Workflow Progression</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Modular architecture designed for multi-stage layout exploration and decision support
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
          Phase 5: CORELAP Construction Solver Active
        </span>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))',
        gap: '0.75rem',
      }}>
        {STAGES.map((stage, idx) => {
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
                  {stage.status}
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
