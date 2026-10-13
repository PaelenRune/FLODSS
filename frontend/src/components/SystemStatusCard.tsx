import React from 'react';
import { SystemStatus } from '../types/api';

interface SystemStatusCardProps {
  status: SystemStatus | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({
  status,
  loading,
  error,
  onRefresh,
}) => {
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
          <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>Backend Core & Runtime Diagnostics</h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Real-time status reported by FastAPI health endpoint (<code>GET /api/health</code>)
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            color: 'var(--text-primary)',
            padding: '0.45rem 0.9rem',
            borderRadius: '6px',
            fontSize: '0.8rem',
            fontWeight: 500,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            transition: 'all 0.2s',
          }}
        >
          {loading ? 'Probing...' : 'Refresh Status'}
        </button>
      </div>

      {error ? (
        <div style={{
          padding: '1rem',
          borderRadius: '8px',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          color: '#f87171',
          fontSize: '0.875rem',
        }}>
          <strong>Connection Alert:</strong> {error}. Ensure FastAPI backend is running on <code>http://127.0.0.1:8000</code>.
        </div>
      ) : status ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
        }}>
          <div style={{
            backgroundColor: 'var(--bg-card)',
            padding: '1rem',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>API Status</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#34d399', marginTop: '0.25rem' }}>
              {status.status.toUpperCase()}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              System Version {status.version}
            </div>
          </div>

          <div style={{
            backgroundColor: 'var(--bg-card)',
            padding: '1rem',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Python Runtime</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: 'var(--accent-blue)', marginTop: '0.25rem' }}>
              v{status.python_version}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              {status.platform.substring(0, 22)}...
            </div>
          </div>

          <div style={{
            backgroundColor: 'var(--bg-card)',
            padding: '1rem',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Algorithm Registry</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#a78bfa', marginTop: '0.25rem' }}>
              {status.registered_algorithms} Registered
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              Plug-and-play architecture active
            </div>
          </div>

          <div style={{
            backgroundColor: 'var(--bg-card)',
            padding: '1rem',
            borderRadius: '8px',
            border: '1px solid var(--border-color)',
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Last Sync Timestamp</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginTop: '0.5rem', fontFamily: 'var(--font-mono)' }}>
              {new Date(status.timestamp).toLocaleTimeString()}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              UTC Timestamp verified
            </div>
          </div>
        </div>
      ) : (
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Initial probe in progress...</div>
      )}
    </div>
  );
};
