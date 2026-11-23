import { useState } from 'react';
import { Factory, LayoutDashboard, PanelsTopLeft, Grid2X2, Workflow, Play, BarChart3, FileText, Settings, PanelLeftClose, PanelLeftOpen, Sliders, ShieldCheck, Sparkles, LogIn, Globe } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

export function CockpitSidebar({ active, onNavigate, onLogin, online }: { active: string; onNavigate: (id: string) => void; onLogin: () => void; online: boolean }) {
  const [collapsed, setCollapsed] = useState(false);
  const { lang, toggleLang, t } = useLanguage();
  const items = [
    { id: 'cockpit', label: t('Kontrol Paneli', 'Dashboard'), icon: LayoutDashboard },
    { id: 'layout', label: t('Yerleşim Düzenleyici', 'Layout editor'), icon: PanelsTopLeft },
    { id: 'matrices', label: t('Akış Matrisi', 'Flow matrix'), icon: Grid2X2 },
    { id: 'solvers', label: t('Optimizasyon', 'Optimization'), icon: Workflow },
    { id: 'decision', label: t('Simülasyon ve Karar Destek', 'Simulation & guidance'), icon: Play },
    { id: 'pareto', label: t('Analitik / Pareto', 'Analytics / Pareto'), icon: BarChart3 },
    { id: 'export', label: t('Raporlar ve Dışa Aktarım', 'Reports & export'), icon: FileText },
  ];
  const secondaryItems = [
    { id: 'problem', label: t('Problem Tanımı', 'Problem definition'), icon: Sliders },
    { id: 'constraints', label: t('Kısıtlar', 'Constraints'), icon: ShieldCheck },
    { id: 'overview', label: t('Sistem Ayarları', 'System settings'), icon: Settings },
  ];
  return <aside className={`cockpit-sidebar ${collapsed ? 'collapsed' : ''}`}>
    <a className="cockpit-logo" href="#" onClick={e => { e.preventDefault(); onNavigate('cockpit'); }} aria-label={t('FLODSS kontrol paneli', 'FLODSS dashboard')}>
      <span><Factory size={23}/></span>
      {!collapsed && <div>FLODSS<small>{t('Tesis Yerleşimi', 'Industrial intelligence')}</small></div>}
    </a>
    <button className="sidebar-collapse" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? t('Kenar çubuğunu genişlet', 'Expand sidebar') : t('Kenar çubuğunu daralt', 'Collapse sidebar')}>
      {collapsed ? <PanelLeftOpen size={16}/> : <PanelLeftClose size={16}/>}
    </button>
    <nav aria-label={t('Ana gezinme', 'Main navigation')}>
      {items.map(({ id, label, icon: Icon }) => (
        <button key={id} title={label} aria-current={active === id ? 'page' : undefined} onClick={() => onNavigate(id)}>
          <Icon size={18}/>{!collapsed && <span>{label}</span>}{active === id && <i/>}
        </button>
      ))}
      <div className="sidebar-divider"/>
      {secondaryItems.map(({ id, label, icon: Icon }) => (
        <button key={id} title={label} aria-current={active === id ? 'page' : undefined} onClick={() => onNavigate(id)}>
          <Icon size={18}/>{!collapsed && <span>{label}</span>}
        </button>
      ))}
    </nav>
    <div className="sidebar-bottom">
      {!collapsed && (
        <div className="sidebar-note">
          <Sparkles size={16}/>
          <strong>{t('Tek ekrandan yönetin.', 'Better flow. Better decisions.')}</strong>
          <p>{t('Problem, akış, kısıt ve optimizasyonu 3B planı kaybetmeden yönetin.', 'Explore the possibilities of your production floor.')}</p>
        </div>
      )}
      <button
        type="button"
        className="sidebar-lang"
        onClick={toggleLang}
        title={t('İngilizceye geç (EN)', 'Switch to Turkish (TR)')}
        aria-label={t('Arayüz dilini değiştir', 'Toggle interface language')}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'space-between',
          gap: '8px',
          width: '100%',
          marginTop: '12px',
          padding: '8px 10px',
          borderRadius: '6px',
          border: '1px solid #1d2737',
          background: '#111a28',
          color: '#9cacc0',
          fontSize: '11px',
          cursor: 'pointer',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Globe size={15}/>
          {!collapsed && <span>{t('Dil', 'Language')}</span>}
        </span>
        {!collapsed && (
          <strong style={{ color: '#34e4f0', fontSize: '10px', letterSpacing: '0.5px' }}>
            {lang === 'tr' ? 'TR 🇹🇷' : 'EN 🇬🇧'}
          </strong>
        )}
      </button>
      <button className="sidebar-account" onClick={onLogin} title={t('Hesap ve oturum açma', 'Account and sign in')}>
        <LogIn size={17}/>
        {!collapsed && (
          <span>
            {t('Araştırma çalışma alanı', 'Research workspace')}
            <small><i className={online ? 'online' : ''}/>{online ? t('API bağlı', 'API connected') : t('Referans modu', 'Reference mode')}</small>
          </span>
        )}
      </button>
      {!collapsed && <small className="sidebar-version">{t('FLODSS v1.0 · Yerel Öncelikli', 'FLODSS v1.0 · Local-first')}</small>}
    </div>
  </aside>;
}
