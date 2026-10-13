import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getInvitationByTokenApi } from '../services/api';
import { InvitationResponse } from '../types/api';

interface InvitationAcceptModalProps {
  onClose: () => void;
  onOpenLogin: () => void;
}

export const InvitationAcceptModal: React.FC<InvitationAcceptModalProps> = ({
  onClose,
  onOpenLogin,
}) => {
  const { acceptInvitation, isLoading } = useAuth();
  const [tokenInput, setTokenInput] = useState('');
  const [invitation, setInvitation] = useState<InvitationResponse | null>(null);
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [verifyingToken, setVerifyingToken] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleVerifyToken = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    setVerifyingToken(true);
    setErrorMsg(null);
    try {
      const inv = await getInvitationByTokenApi(tokenInput.trim());
      setInvitation(inv);
    } catch (err: any) {
      setErrorMsg(err.message || 'Invitation token is invalid, expired, or already used.');
      setInvitation(null);
    } finally {
      setVerifyingToken(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!invitation) return;
    if (!fullName.trim()) {
      setErrorMsg('Please enter your full name.');
      return;
    }
    if (password.length < 8) {
      setErrorMsg('Password must be at least 8 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setErrorMsg('Passwords do not match.');
      return;
    }

    setErrorMsg(null);
    try {
      await acceptInvitation(invitation.token, fullName.trim(), password);
      setSuccessMsg('Account created successfully! Entering research workspace...');
      setTimeout(() => {
        onClose();
      }, 1000);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to complete registration.');
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        backgroundColor: 'rgba(10, 15, 29, 0.88)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1.5rem',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '480px',
          backgroundColor: '#111827',
          border: '1px solid #374151',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.65)',
          padding: '2.25rem',
          color: '#f9fafb',
          maxHeight: '90vh',
          overflowY: 'auto',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 700, margin: '0 0 0.35rem 0' }}>
            Activate Research Invitation
          </h2>
          <p style={{ fontSize: '0.85rem', color: '#9ca3af', margin: 0 }}>
            Enter your token issued by the lead research administrator.
          </p>
        </div>

        {errorMsg && (
          <div
            style={{
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.35)',
              color: '#fca5a5',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              fontSize: '0.85rem',
              marginBottom: '1.25rem',
            }}
          >
            ⚠️ {errorMsg}
          </div>
        )}

        {successMsg && (
          <div
            style={{
              backgroundColor: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              color: '#6ee7b7',
              padding: '0.75rem 1rem',
              borderRadius: '8px',
              fontSize: '0.85rem',
              marginBottom: '1.25rem',
            }}
          >
            ✅ {successMsg}
          </div>
        )}

        {!invitation ? (
          <form onSubmit={handleVerifyToken} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#d1d5db', marginBottom: '0.35rem' }}>
                Invitation Token
              </label>
              <input
                type="text"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                placeholder="Paste your 40+ character token here"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#ffffff',
                  fontSize: '0.85rem',
                  fontFamily: 'monospace',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <button
              type="submit"
              disabled={verifyingToken}
              style={{
                padding: '0.8rem 1rem',
                borderRadius: '8px',
                backgroundColor: '#0284c7',
                color: '#ffffff',
                fontWeight: 600,
                fontSize: '0.9rem',
                border: 'none',
                cursor: verifyingToken ? 'not-allowed' : 'pointer',
              }}
            >
              {verifyingToken ? 'Verifying Token...' : 'Verify Token & Proceed'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ backgroundColor: '#1e293b', padding: '0.85rem', borderRadius: '8px', fontSize: '0.825rem' }}>
              <div><strong>Email:</strong> {invitation.email}</div>
              <div style={{ marginTop: '0.25rem' }}><strong>Assigned Role:</strong> <span style={{ color: '#38bdf8', fontWeight: 600 }}>{invitation.role}</span></div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#d1d5db', marginBottom: '0.35rem' }}>
                Your Full Name & Academic Title
              </label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g., Dr. Jane Doe"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#ffffff',
                  fontSize: '0.9rem',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#d1d5db', marginBottom: '0.35rem' }}>
                Set Password (min 8 chars)
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Choose a password (min 8 chars)"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#ffffff',
                  fontSize: '0.9rem',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#d1d5db', marginBottom: '0.35rem' }}>
                Confirm Password
              </label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password (min 8 chars)"
                required
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  backgroundColor: '#1f2937',
                  border: '1px solid #374151',
                  borderRadius: '8px',
                  color: '#ffffff',
                  fontSize: '0.9rem',
                  outline: 'none',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              style={{
                marginTop: '0.5rem',
                padding: '0.8rem 1rem',
                borderRadius: '8px',
                backgroundColor: '#10b981',
                color: '#ffffff',
                fontWeight: 600,
                fontSize: '0.925rem',
                border: 'none',
                cursor: isLoading ? 'not-allowed' : 'pointer',
              }}
            >
              {isLoading ? 'Creating Account...' : 'Complete Activation & Enter Workspace'}
            </button>
          </form>
        )}

        <div style={{ marginTop: '1.5rem', textAlign: 'center', borderTop: '1px solid #374151', paddingTop: '1rem', display: 'flex', justifyContent: 'space-between' }}>
          <button
            type="button"
            onClick={onOpenLogin}
            style={{
              background: 'none',
              border: 'none',
              color: '#38bdf8',
              fontSize: '0.825rem',
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            Back to Sign In
          </button>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#9ca3af',
              fontSize: '0.825rem',
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};
