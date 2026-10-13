import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';

interface LoginModalProps {
  onOpenInvite: () => void;
}

export const LoginModal: React.FC<LoginModalProps> = ({ onOpenInvite }) => {
  const { login, demoLogin, isLoading } = useAuth();
  const { lang, setLang, t } = useLanguage();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setErrorMsg(t('Lütfen e-posta ve parola alanlarını doldurun.', 'Please enter both email and password.'));
      return;
    }
    setErrorMsg(null);
    try {
      await login(email.trim(), password);
    } catch (err: any) {
      setErrorMsg(err.message || t('Giriş başarısız. Bilgilerinizi kontrol edin.', 'Login failed. Please check your credentials.'));
    }
  };

  const handleDemoLogin = async () => {
    setErrorMsg(null);
    try {
      await demoLogin();
    } catch (err: any) {
      setErrorMsg(err.message || t('Demo girişi başarısız oldu.', 'Demo login failed.'));
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
          maxWidth: '440px',
          backgroundColor: '#111827',
          border: '1px solid #374151',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.65)',
          padding: '2rem',
          color: '#f9fafb',
          position: 'relative',
        }}
      >
        {/* Top-Right Language Switcher */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            marginBottom: '0.5rem',
          }}
        >
          <div
            style={{
              display: 'inline-flex',
              backgroundColor: '#1f2937',
              border: '1px solid #374151',
              borderRadius: '8px',
              padding: '0.15rem',
              gap: '0.15rem',
            }}
          >
            <button
              type="button"
              onClick={() => setLang('tr')}
              style={{
                padding: '0.2rem 0.55rem',
                borderRadius: '6px',
                border: 'none',
                fontSize: '0.72rem',
                fontWeight: 700,
                cursor: 'pointer',
                backgroundColor: lang === 'tr' ? '#2563eb' : 'transparent',
                color: lang === 'tr' ? '#ffffff' : '#9ca3af',
              }}
            >
              🇹🇷 TR
            </button>
            <button
              type="button"
              onClick={() => setLang('en')}
              style={{
                padding: '0.2rem 0.55rem',
                borderRadius: '6px',
                border: 'none',
                fontSize: '0.72rem',
                fontWeight: 700,
                cursor: 'pointer',
                backgroundColor: lang === 'en' ? '#2563eb' : 'transparent',
                color: lang === 'en' ? '#ffffff' : '#9ca3af',
              }}
            >
              🇬🇧 EN
            </button>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
          <div
            style={{
              width: '54px',
              height: '54px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #2563eb, #06b6d4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 800,
              fontSize: '1.5rem',
              color: '#ffffff',
              margin: '0 auto 1rem auto',
              boxShadow: '0 8px 20px rgba(37, 99, 235, 0.4)',
            }}
          >
            FL
          </div>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 700, margin: '0 0 0.4rem 0' }}>
            FLODSS Research Portal
          </h2>
          <p style={{ fontSize: '0.85rem', color: '#9ca3af', margin: 0 }}>
            {t(
              'Tesis Yerleşim Optimizasyon & Karar Destek Sistemi • v1.0.0-rc.1',
              'Controlled Research & Thesis Pilot Environment • v1.0.0-rc.1'
            )}
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
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <span>⚠️</span>
            <span>{errorMsg}</span>
          </div>
        )}

        <div style={{ marginBottom: '1.25rem' }}>
          <button
            type="button"
            onClick={handleDemoLogin}
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.9rem 1rem',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #10b981, #059669)',
              color: '#ffffff',
              fontWeight: 700,
              fontSize: '0.95rem',
              border: 'none',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.7 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              boxShadow: '0 6px 16px rgba(16, 185, 129, 0.35)',
              transition: 'all 0.2s',
            }}
          >
            <span>🚀</span>
            <span>
              {isLoading
                ? t('Giriş Yapılıyor...', 'Entering Workspace...')
                : t('Demo / Misafir Olarak Başla (Şifresiz)', 'Start as Guest Researcher (No Password)')}
            </span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', margin: '1.25rem 0 0.25rem 0' }}>
            <div style={{ flex: 1, height: '1px', backgroundColor: '#374151' }} />
            <span style={{ padding: '0 0.75rem', fontSize: '0.72rem', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {t('veya kayıtlı hesapla giriş', 'or sign in with account')}
            </span>
            <div style={{ flex: 1, height: '1px', backgroundColor: '#374151' }} />
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.825rem', fontWeight: 600, color: '#d1d5db', marginBottom: '0.35rem' }}>
              {t('Kurumsal / Araştırmacı E-posta', 'Institutional / Researcher Email')}
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="researcher@university.edu"
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
              {t('Parola', 'Password')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
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
              backgroundColor: '#2563eb',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: '0.925rem',
              border: 'none',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              opacity: isLoading ? 0.7 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              boxShadow: '0 4px 12px rgba(37, 99, 235, 0.35)',
              transition: 'background-color 0.2s',
            }}
          >
            {isLoading ? t('Doğrulanıyor...', 'Authenticating...') : t('Çalışma Alanına Giriş Yap', 'Sign In to Workspace')}
          </button>
        </form>

        <div style={{ marginTop: '1.5rem', textAlign: 'center', borderTop: '1px solid #374151', paddingTop: '1.25rem' }}>
          <button
            type="button"
            onClick={onOpenInvite}
            style={{
              background: 'none',
              border: 'none',
              color: '#38bdf8',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              textDecoration: 'underline',
            }}
          >
            {t('Davet anahtarınız (Invitation Token) var mı? Hesabınızı etkinleştirin', 'Have an invitation token? Activate your account')}
          </button>
        </div>

        <div style={{ marginTop: '1.25rem', padding: '0.75rem', backgroundColor: '#1e293b', borderRadius: '8px', fontSize: '0.75rem', color: '#94a3b8' }}>
          <strong>🔒 {t('Erişim & Denetim Bilgilendirmesi:', 'Access Governance Notice:')}</strong>{' '}
          {t(
            'Bu platform tez danışmanları, hakemler ve araştırmacılar için tasarlanmıştır. Tüm optimizasyon deneyleri izole çalışma alanında yürütülür.',
            'Access is restricted strictly to authorized researchers, thesis advisors, and evaluation panelists. Actions are recorded in audit logs.'
          )}
        </div>
      </div>
    </div>
  );
};
