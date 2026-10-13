import React from 'react';
import { useAuth } from '../context/AuthContext';

interface HeaderProps {
  status: string | null;
  loading: boolean;
  error: string | null;
  onOpenUserManagement?: () => void;
  onOpenLogin?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  loading,
  error,
  onOpenUserManagement,
  onOpenLogin,
}) => {
  const { user, isAdmin, logout } = useAuth();

  return (
    <header style={{
      borderBottom: '1px solid var(--border-color, #334155)',
      backgroundColor: 'var(--bg-secondary, #0f172a)',
      padding: '1.1rem 2rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '1rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{
          width: '42px',
          height: '42px',
          borderRadius: '8px',
          background: 'linear-gradient(135deg, #2563eb, #06b6d4)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 700,
          fontSize: '1.25rem',
          color: '#ffffff',
          boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)',
        }}>
          FL
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.025em', margin: 0, color: '#f8fafc' }}>
              Facility Layout Optimization System (FLODSS)
            </h1>
            <span style={{
              fontSize: '0.725rem',
              padding: '0.15rem 0.5rem',
              borderRadius: '9999px',
              backgroundColor: '#10b98120',
              color: '#34d399',
              border: '1px solid #10b98140',
              fontWeight: 600,
            }}>
              v1.0.0-rc.1
            </span>
            <span style={{
              fontSize: '0.725rem',
              padding: '0.15rem 0.5rem',
              borderRadius: '9999px',
              backgroundColor: '#6366f120',
              color: '#818cf8',
              border: '1px solid #6366f140',
              fontWeight: 600,
            }}>
              Controlled Research Access
            </span>
          </div>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0.2rem 0 0 0' }}>
            Decision Support & Modular Operations Research Platform &bull; Multi-Tenant Local-First
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        {/* Backend health status badge */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.35rem 0.75rem',
          borderRadius: '9999px',
          fontSize: '0.8rem',
          fontWeight: 500,
          backgroundColor: error ? 'rgba(239, 68, 68, 0.15)' : status ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
          color: error ? '#f87171' : status ? '#34d399' : '#fbbf24',
          border: `1px solid ${error ? 'rgba(239, 68, 68, 0.3)' : status ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
        }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            backgroundColor: error ? '#ef4444' : status ? '#10b981' : '#f59e0b',
            display: 'inline-block',
            boxShadow: `0 0 8px ${error ? '#ef4444' : status ? '#10b981' : '#f59e0b'}`,
          }} />
          {loading ? 'Checking...' : error ? 'Offline' : 'Online'}
        </div>

        {/* User Profile & Auth Controls */}
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem', backgroundColor: '#1e293b', padding: '0.35rem 0.75rem', borderRadius: '10px', border: '1px solid #334155' }}>
            <div style={{
              width: '28px',
              height: '28px',
              borderRadius: '50%',
              backgroundColor: user.role === 'ADMIN' ? '#dc2626' : '#2563eb',
              color: '#fff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '0.75rem',
              fontWeight: 700,
            }}>
              {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f8fafc', lineHeight: 1.1 }}>
                {user.full_name}
              </span>
              <span style={{ fontSize: '0.675rem', color: '#94a3b8' }}>
                {user.email}
              </span>
            </div>

            <span style={{
              fontSize: '0.7rem',
              fontWeight: 700,
              padding: '0.15rem 0.45rem',
              borderRadius: '6px',
              backgroundColor: user.role === 'ADMIN' ? 'rgba(239, 68, 68, 0.2)' : user.role === 'RESEARCHER' ? 'rgba(37, 99, 235, 0.2)' : 'rgba(148, 163, 184, 0.2)',
              color: user.role === 'ADMIN' ? '#f87171' : user.role === 'RESEARCHER' ? '#60a5fa' : '#cbd5e1',
            }}>
              {user.role}
            </span>

            {isAdmin && onOpenUserManagement && (
              <button
                onClick={onOpenUserManagement}
                title="Manage Research Users & Invitations"
                style={{
                  padding: '0.3rem 0.6rem',
                  borderRadius: '6px',
                  backgroundColor: '#374151',
                  color: '#e5e7eb',
                  border: '1px solid #4b5563',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  marginLeft: '0.3rem',
                }}
              >
                👥 Users
              </button>
            )}

            <button
              onClick={() => logout()}
              title="Sign Out"
              style={{
                padding: '0.3rem 0.6rem',
                borderRadius: '6px',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                color: '#fca5a5',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Logout
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenLogin}
            style={{
              padding: '0.45rem 1rem',
              borderRadius: '8px',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              fontSize: '0.825rem',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)',
            }}
          >
            Sign In
          </button>
        )}
      </div>
    </header>
  );
};
