import React, { useState } from 'react';
import { FacilityLayoutProblem, ReservedZone } from '../types/api';

interface ConstraintEditorCardProps {
  problem: FacilityLayoutProblem | null;
  onUpdateProblem: (updated: FacilityLayoutProblem) => void;
}

export const ConstraintEditorCard: React.FC<ConstraintEditorCardProps> = ({ problem, onUpdateProblem }) => {
  const [newZoneId, setNewZoneId] = useState('');
  const [newZoneType, setNewZoneType] = useState('aisle_corridor');
  const [newZoneXMin, setNewZoneXMin] = useState<number>(0);
  const [newZoneXMax, setNewZoneXMax] = useState<number>(10);
  const [newZoneYMin, setNewZoneYMin] = useState<number>(0);
  const [newZoneYMax, setNewZoneYMax] = useState<number>(50);
  const [newZoneStrict, setNewZoneStrict] = useState(true);

  if (!problem) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
        <p style={{ color: 'var(--text-muted)' }}>No problem loaded. Load a problem to configure spatial constraints.</p>
      </div>
    );
  }

  const reservedZones = problem.facility.reserved_zones || [];
  const fixedDepts = problem.departments.filter(d => d.fixed_position);

  // Add Reserved Zone
  const handleAddReservedZone = () => {
    const id = newZoneId.trim().toUpperCase() || `RZ_${(reservedZones.length + 1).toString().padStart(2, '0')}`;
    if (reservedZones.some(z => z.id === id)) {
      alert(`Reserved zone with ID '${id}' already exists.`);
      return;
    }
    const zone: ReservedZone = {
      id,
      type: newZoneType,
      bounding_box: {
        x_min: Number(newZoneXMin),
        x_max: Number(newZoneXMax),
        y_min: Number(newZoneYMin),
        y_max: Number(newZoneYMax),
      },
      strict: newZoneStrict,
    };
    onUpdateProblem({
      ...problem,
      facility: {
        ...problem.facility,
        reserved_zones: [...reservedZones, zone],
      },
    });
    setNewZoneId('');
  };

  // Remove Reserved Zone
  const handleRemoveReservedZone = (id: string) => {
    onUpdateProblem({
      ...problem,
      facility: {
        ...problem.facility,
        reserved_zones: reservedZones.filter(z => z.id !== id),
      },
    });
  };

  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      borderRadius: '12px',
      border: '1px solid var(--border-color)',
      padding: '1.75rem',
      marginBottom: '2rem',
    }}>
      <div style={{ marginBottom: '1.25rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
          Spatial & Geometric Constraints Editor
        </h2>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0' }}>
          Define reserved spine corridors, emergency thoroughfares, and unmovable fixed department anchors.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Fixed Placements Summary Card */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          borderRadius: '8px',
          border: '1px solid var(--border-color)',
          padding: '1.25rem',
        }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#fbbf24', marginTop: 0, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            📌 Fixed Department Placements ({fixedDepts.length})
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
            Fixed departments are anchored at exact $(x, y)$ coordinates (e.g. receiving docks, rail sidings).
          </p>
          {fixedDepts.length === 0 ? (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No departments are currently pinned. You can toggle fixed locations in the Problem Editor.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {fixedDepts.map(d => (
                <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.45rem 0.65rem', backgroundColor: 'var(--bg-secondary)', borderRadius: '6px', fontSize: '0.8rem', border: '1px solid var(--border-color)' }}>
                  <div>
                    <strong style={{ color: 'var(--accent-blue)' }}>{d.name}</strong> ({d.id})
                  </div>
                  <div style={{ color: '#fbbf24', fontWeight: 600 }}>
                    ({d.fixed_position?.x}m, {d.fixed_position?.y}m)
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Facility Reserved Exclusion Zones List */}
        <div style={{
          backgroundColor: 'var(--bg-card)',
          borderRadius: '8px',
          border: '1px solid var(--border-color)',
          padding: '1.25rem',
        }}>
          <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f59e0b', marginTop: 0, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            🚧 Facility Reserved Exclusion Zones ({reservedZones.length})
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
            Geometric areas strictly forbidden from department occupation (e.g. spine aisles, column grid).
          </p>
          {reservedZones.length === 0 ? (
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No exclusion zones defined. Add a zone using the form below.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {reservedZones.map(rz => (
                <div key={rz.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.45rem 0.65rem', backgroundColor: 'var(--bg-secondary)', borderRadius: '6px', fontSize: '0.8rem', border: '1px solid var(--border-color)' }}>
                  <div>
                    <strong style={{ color: '#f59e0b' }}>{rz.id}</strong> ({rz.type})
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      X: [{rz.bounding_box.x_min}, {rz.bounding_box.x_max}]m &bull; Y: [{rz.bounding_box.y_min}, {rz.bounding_box.y_max}]m
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemoveReservedZone(rz.id)}
                    style={{
                      padding: '0.2rem 0.5rem',
                      fontSize: '0.72rem',
                      backgroundColor: 'rgba(239, 68, 68, 0.1)',
                      color: '#f87171',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: '4px',
                      cursor: 'pointer',
                    }}
                  >
                    Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add Reserved Zone Form */}
      <div style={{
        padding: '1.25rem',
        backgroundColor: 'var(--bg-card)',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
      }}>
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, margin: '0 0 0.85rem', color: 'var(--text-primary)' }}>
          + Add New Reserved Exclusion Zone
        </h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', alignItems: 'end' }}>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Zone ID:</label>
            <input
              type="text"
              placeholder="RZ_SPINE"
              value={newZoneId}
              onChange={(e) => setNewZoneId(e.target.value)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Type:</label>
            <select
              value={newZoneType}
              onChange={(e) => setNewZoneType(e.target.value)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            >
              <option value="aisle_corridor">Aisle Corridor</option>
              <option value="building_column">Structural Column</option>
              <option value="emergency_exit">Emergency Exit</option>
              <option value="utility_chase">Utility Chase</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>X Min (m):</label>
            <input
              type="number"
              value={newZoneXMin}
              onChange={(e) => setNewZoneXMin(parseFloat(e.target.value) || 0)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>X Max (m):</label>
            <input
              type="number"
              value={newZoneXMax}
              onChange={(e) => setNewZoneXMax(parseFloat(e.target.value) || 0)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Y Min (m):</label>
            <input
              type="number"
              value={newZoneYMin}
              onChange={(e) => setNewZoneYMin(parseFloat(e.target.value) || 0)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div>
            <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>Y Max (m):</label>
            <input
              type="number"
              value={newZoneYMax}
              onChange={(e) => setNewZoneYMax(parseFloat(e.target.value) || 0)}
              style={{ width: '100%', padding: '0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)', backgroundColor: 'var(--bg-secondary)', color: 'var(--text-primary)', fontSize: '0.85rem' }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', paddingBottom: '0.4rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.75rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={newZoneStrict}
                onChange={(e) => setNewZoneStrict(e.target.checked)}
              />
              Strict Exclusion
            </label>
          </div>
          <div>
            <button
              onClick={handleAddReservedZone}
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
              Add Zone
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
