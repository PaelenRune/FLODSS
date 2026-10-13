import React, { useState, useEffect, useCallback } from 'react';
import {
  UserProfile,
  InvitationResponse,
  UserRole,
} from '../types/api';
import {
  getUsersApi,
  updateUserStatusApi,
  createInvitationApi,
  getInvitationsApi,
} from '../services/api';

interface UserManagementModalProps {
  onClose: () => void;
}

export const UserManagementModal: React.FC<UserManagementModalProps> = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState<'users' | 'invitations' | 'create_invite'>('users');
  const [users, setUsers] = useState<UserProfile[]>([]);
  const [invitations, setInvitations] = useState<InvitationResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // New invitation form state
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<UserRole>('RESEARCHER');
  const [inviteName, setInviteName] = useState('');
  const [generatedInvite, setGeneratedInvite] = useState<InvitationResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [uList, iList] = await Promise.all([getUsersApi(), getInvitationsApi()]);
      setUsers(uList);
      setInvitations(iList);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to load user and invitation records.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleToggleActive = async (user: UserProfile) => {
    try {
      const updated = await updateUserStatusApi(user.id, { is_active: !user.is_active });
      setUsers((prev) => prev.map((u) => (u.id === user.id ? updated : u)));
      setSuccessMsg(`User ${user.email} is now ${updated.is_active ? 'ACTIVE' : 'DISABLED'}.`);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to update user status.');
    }
  };

  const handleToggleGemini = async (user: UserProfile) => {
    try {
      const updated = await updateUserStatusApi(user.id, { allow_gemini: !user.allow_gemini });
      setUsers((prev) => prev.map((u) => (u.id === user.id ? updated : u)));
      setSuccessMsg(`Gemini AI privilege for ${user.email} is now ${updated.allow_gemini ? 'ENABLED' : 'DISABLED'}.`);
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to update AI privilege.');
    }
  };

  const handleCreateInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const inv = await createInvitationApi({
        email: inviteEmail.trim(),
        role: inviteRole,
        full_name: inviteName.trim() || undefined,
      });
      setGeneratedInvite(inv);
      setSuccessMsg(`Invitation successfully generated for ${inv.email}.`);
      setInviteEmail('');
      setInviteName('');
      loadData();
    } catch (e: any) {
      setErrorMsg(e.message || 'Failed to generate invitation.');
    } finally {
      setIsSubmitting(false);
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
          maxWidth: '860px',
          backgroundColor: '#111827',
          border: '1px solid #374151',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.65)',
          padding: '2rem',
          color: '#f9fafb',
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <div>
            <h2 style={{ fontSize: '1.35rem', fontWeight: 700, margin: '0 0 0.25rem 0' }}>
              User & Access Governance
            </h2>
            <p style={{ fontSize: '0.8rem', color: '#9ca3af', margin: 0 }}>
              Lead Research Administrator Control Panel &bull; Role Authorization & Pilot Access
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: '#1f2937',
              border: '1px solid #374151',
              color: '#d1d5db',
              borderRadius: '8px',
              padding: '0.4rem 0.8rem',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            ✕ Close
          </button>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '1px solid #374151', paddingBottom: '0.75rem', marginBottom: '1.25rem' }}>
          <button
            onClick={() => setActiveTab('users')}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: activeTab === 'users' ? '#2563eb' : '#1f2937',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            Registered Users ({users.length})
          </button>
          <button
            onClick={() => setActiveTab('create_invite')}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: activeTab === 'create_invite' ? '#059669' : '#1f2937',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            + Issue New Invitation
          </button>
          <button
            onClick={() => setActiveTab('invitations')}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: activeTab === 'invitations' ? '#6366f1' : '#1f2937',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            Invitation Log ({invitations.length})
          </button>
        </div>

        {errorMsg && (
          <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', border: '1px solid rgba(239, 68, 68, 0.35)', color: '#fca5a5', padding: '0.65rem 0.9rem', borderRadius: '8px', fontSize: '0.825rem', marginBottom: '1rem' }}>
            ⚠️ {errorMsg}
          </div>
        )}

        {successMsg && (
          <div style={{ backgroundColor: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.35)', color: '#6ee7b7', padding: '0.65rem 0.9rem', borderRadius: '8px', fontSize: '0.825rem', marginBottom: '1rem' }}>
            ✅ {successMsg}
          </div>
        )}

        <div style={{ flex: 1, overflowY: 'auto' }}>
          {/* TAB 1: USERS LIST */}
          {activeTab === 'users' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {loading ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af' }}>Loading user profiles...</div>
              ) : (
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                  <thead>
                    <tr style={{ borderBottom: '1px solid #374151', color: '#9ca3af', textAlign: 'left' }}>
                      <th style={{ padding: '0.6rem' }}>User / Email</th>
                      <th style={{ padding: '0.6rem' }}>Role</th>
                      <th style={{ padding: '0.6rem' }}>Account Status</th>
                      <th style={{ padding: '0.6rem' }}>Gemini AI</th>
                      <th style={{ padding: '0.6rem', textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} style={{ borderBottom: '1px solid #1f2937' }}>
                        <td style={{ padding: '0.6rem' }}>
                          <div style={{ fontWeight: 600, color: '#f3f4f6' }}>{u.full_name}</div>
                          <div style={{ color: '#9ca3af', fontSize: '0.75rem' }}>{u.email}</div>
                        </td>
                        <td style={{ padding: '0.6rem' }}>
                          <span
                            style={{
                              padding: '0.2rem 0.5rem',
                              borderRadius: '9999px',
                              fontSize: '0.725rem',
                              fontWeight: 700,
                              backgroundColor: u.role === 'ADMIN' ? 'rgba(239, 68, 68, 0.2)' : u.role === 'RESEARCHER' ? 'rgba(37, 99, 235, 0.2)' : 'rgba(156, 163, 175, 0.2)',
                              color: u.role === 'ADMIN' ? '#f87171' : u.role === 'RESEARCHER' ? '#60a5fa' : '#d1d5db',
                            }}
                          >
                            {u.role}
                          </span>
                        </td>
                        <td style={{ padding: '0.6rem' }}>
                          <span style={{ color: u.is_active ? '#34d399' : '#f87171', fontWeight: 600 }}>
                            {u.is_active ? '● Active' : '○ Disabled'}
                          </span>
                        </td>
                        <td style={{ padding: '0.6rem' }}>
                          <span style={{ color: u.allow_gemini ? '#a78bfa' : '#6b7280', fontWeight: 600 }}>
                            {u.allow_gemini ? 'Allowed' : 'Off'}
                          </span>
                        </td>
                        <td style={{ padding: '0.6rem', textAlign: 'right' }}>
                          {u.role !== 'ADMIN' && (
                            <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                              <button
                                onClick={() => handleToggleActive(u)}
                                style={{
                                  padding: '0.25rem 0.55rem',
                                  borderRadius: '6px',
                                  fontSize: '0.725rem',
                                  fontWeight: 600,
                                  backgroundColor: u.is_active ? 'rgba(239, 68, 68, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                                  color: u.is_active ? '#fca5a5' : '#86efac',
                                  border: 'none',
                                  cursor: 'pointer',
                                }}
                              >
                                {u.is_active ? 'Disable' : 'Enable'}
                              </button>
                              <button
                                onClick={() => handleToggleGemini(u)}
                                style={{
                                  padding: '0.25rem 0.55rem',
                                  borderRadius: '6px',
                                  fontSize: '0.725rem',
                                  fontWeight: 600,
                                  backgroundColor: 'rgba(99, 102, 241, 0.2)',
                                  color: '#a5b4fc',
                                  border: 'none',
                                  cursor: 'pointer',
                                }}
                              >
                                {u.allow_gemini ? 'Revoke AI' : 'Grant AI'}
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* TAB 2: CREATE INVITATION */}
          {activeTab === 'create_invite' && (
            <div style={{ maxWidth: '520px', margin: '0 auto', padding: '1rem 0' }}>
              <form onSubmit={handleCreateInvite} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#d1d5db', marginBottom: '0.35rem' }}>
                    Candidate / Reviewer Email Address
                  </label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="advisor@university.edu"
                    required
                    style={{
                      width: '100%',
                      padding: '0.7rem 0.9rem',
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#ffffff',
                      fontSize: '0.875rem',
                      outline: 'none',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#d1d5db', marginBottom: '0.35rem' }}>
                    Assigned Authorization Role
                  </label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value as UserRole)}
                    style={{
                      width: '100%',
                      padding: '0.7rem 0.9rem',
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#ffffff',
                      fontSize: '0.875rem',
                      outline: 'none',
                      boxSizing: 'border-box',
                    }}
                  >
                    <option value="RESEARCHER">RESEARCHER — Can create problems, run optimizers & save experiments</option>
                    <option value="VIEWER">VIEWER — Read-only access to assigned projects and benchmark comparisons</option>
                  </select>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#d1d5db', marginBottom: '0.35rem' }}>
                    Candidate Full Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={inviteName}
                    onChange={(e) => setInviteName(e.target.value)}
                    placeholder="Prof. John Smith"
                    style={{
                      width: '100%',
                      padding: '0.7rem 0.9rem',
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#ffffff',
                      fontSize: '0.875rem',
                      outline: 'none',
                      boxSizing: 'border-box',
                    }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  style={{
                    padding: '0.75rem 1rem',
                    borderRadius: '8px',
                    backgroundColor: '#059669',
                    color: '#ffffff',
                    fontWeight: 600,
                    fontSize: '0.9rem',
                    border: 'none',
                    cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  }}
                >
                  {isSubmitting ? 'Issuing Token...' : 'Generate 48h Invitation Token'}
                </button>
              </form>

              {generatedInvite && (
                <div style={{ marginTop: '1.5rem', padding: '1rem', backgroundColor: '#1e293b', borderRadius: '10px', border: '1px solid #334155' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#38bdf8', marginBottom: '0.5rem' }}>
                    ✅ Single-Use Invitation Generated
                  </div>
                  <div style={{ fontSize: '0.775rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                    Share this secret token with the researcher. It expires in 48 hours.
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <input
                      type="text"
                      readOnly
                      value={generatedInvite.token}
                      style={{
                        flex: 1,
                        padding: '0.5rem',
                        backgroundColor: '#0f172a',
                        border: '1px solid #334155',
                        borderRadius: '6px',
                        color: '#f8fafc',
                        fontFamily: 'monospace',
                        fontSize: '0.8rem',
                      }}
                    />
                    <button
                      onClick={() => navigator.clipboard.writeText(generatedInvite.token)}
                      style={{
                        padding: '0.5rem 0.8rem',
                        backgroundColor: '#3b82f6',
                        color: '#fff',
                        borderRadius: '6px',
                        border: 'none',
                        cursor: 'pointer',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                      }}
                    >
                      Copy Token
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: INVITATIONS LOG */}
          {activeTab === 'invitations' && (
            <div>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.825rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid #374151', color: '#9ca3af', textAlign: 'left' }}>
                    <th style={{ padding: '0.6rem' }}>Invited Email</th>
                    <th style={{ padding: '0.6rem' }}>Role</th>
                    <th style={{ padding: '0.6rem' }}>Status</th>
                    <th style={{ padding: '0.6rem' }}>Expires</th>
                    <th style={{ padding: '0.6rem' }}>Token</th>
                  </tr>
                </thead>
                <tbody>
                  {invitations.map((inv) => {
                    const isUsed = !!inv.used_at;
                    const isExpired = new Date(inv.expires_at) < new Date();
                    const statusText = isUsed ? 'Used' : isExpired ? 'Expired' : 'Active';
                    const statusColor = isUsed ? '#9ca3af' : isExpired ? '#f87171' : '#34d399';

                    return (
                      <tr key={inv.id} style={{ borderBottom: '1px solid #1f2937' }}>
                        <td style={{ padding: '0.6rem', fontWeight: 600 }}>{inv.email}</td>
                        <td style={{ padding: '0.6rem' }}>{inv.role}</td>
                        <td style={{ padding: '0.6rem', color: statusColor, fontWeight: 600 }}>● {statusText}</td>
                        <td style={{ padding: '0.6rem', fontSize: '0.75rem', color: '#9ca3af' }}>{new Date(inv.expires_at).toLocaleDateString()}</td>
                        <td style={{ padding: '0.6rem' }}>
                          <span style={{ fontFamily: 'monospace', fontSize: '0.75rem', color: '#94a3b8' }}>
                            {inv.token.substring(0, 10)}...
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
