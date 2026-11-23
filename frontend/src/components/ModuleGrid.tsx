import React from 'react';
import { SystemStatus } from '../types/api';
import { useLanguage } from '../context/LanguageContext';

interface ModuleGridProps {
  status: SystemStatus | null;
}

const ARCHITECTURAL_MODULES = [
  {
    key: 'models',
    nameTr: 'Çekirdek Veri Modelleri',
    nameEn: 'Core Data Models',
    descTr: 'Pydantic şemaları: Tesis, Bölüm, Malzeme Akışı, SLP İlişkileri ve Kısıtlar.',
    descEn: 'Pydantic schemas: Facility, Department, Material Flow, SLP Relationship, and Constraints.',
    categoryTr: 'Alan Katmanı',
    categoryEn: 'Domain Layer',
  },
  {
    key: 'algorithms',
    nameTr: 'Algoritma Kayıt Defteri ve Temel Arayüz',
    nameEn: 'Algorithm Registry & Base Interface',
    descTr: 'CORELAP, CRAFT, Metasezgiseller ve MILP eklentilerini destekleyen genişletilebilir soyut sözleşme.',
    descEn: 'Extensible ABC contract enabling CORELAP, CRAFT, Metaheuristics, and MILP plug-ins.',
    categoryTr: 'Optimizasyon Çekirdeği',
    categoryEn: 'Optimization Core',
  },
  {
    key: 'evaluation',
    nameTr: 'Bağımsız Değerlendirme Motoru',
    nameEn: 'Decoupled Evaluation Engine',
    descTr: 'Malzeme taşıma maliyeti, akış mesafesi, yakınlık memnuniyeti ve kompaktlık metriklerinin bağımsız değerlendirmesi.',
    descEn: 'Independent evaluation of material handling cost, flow distance, closeness satisfaction, compactness.',
    categoryTr: 'Performans Analitiği',
    categoryEn: 'Performance Analytics',
  },
  {
    key: 'constraints',
    nameTr: 'Kısıt Doğrulama Motoru',
    nameEn: 'Constraint Validation Engine',
    descTr: 'Kesin ve esnek uygunluk denetimleri: çakışmama sınırları, boşluklar ve yasaklı bölgeler.',
    descEn: 'Hard & soft feasibility checks: non-overlapping boundaries, clearances, and forbidden zones.',
    categoryTr: 'Kural Motoru',
    categoryEn: 'Rule Engine',
  },
  {
    key: 'optimization',
    nameTr: 'Çok Amaçlı ve Pareto Çözücüler',
    nameEn: 'Multi-Objective & Pareto Solvers',
    descTr: 'NSGA-II, Pareto sınırı sıralaması ve ödünleşim (trade-off) keşfi altyapısı.',
    descEn: 'Foundation for NSGA-II, Pareto front ranking, and trade-off exploration.',
    categoryTr: 'Metasezgiseller ve Kesin Yöntemler',
    categoryEn: 'Metaheuristics & Exact',
  },
  {
    key: 'simulation',
    nameTr: 'Dinamik Simülasyon Motoru',
    nameEn: 'Dynamic Simulation Engine',
    descTr: 'Ayrık olay akış doğrulaması, koridor yoğunluğu analizi ve stokastik malzeme taşıma.',
    descEn: 'Discrete event flow validation, aisle congestion analysis, and stochastic material handling.',
    categoryTr: 'Doğrulama ve Dinamikler',
    categoryEn: 'Verification & Dynamics',
  },
  {
    key: 'ai',
    nameTr: 'Yapay Zekâ Danışmanı ve Karar Destek',
    nameEn: 'AI Advisor & Decision Support',
    descTr: 'Endüstriyel yerleşim tanılaması ve gerekçelendirme motoru (Gemini API entegrasyonuna hazır).',
    descEn: 'Industrial layout diagnosis and reasoning engine (prepared for Gemini API integration).',
    categoryTr: 'Bilişsel Katman',
    categoryEn: 'Cognitive Layer',
  },
  {
    key: 'visualization',
    nameTr: 'Mekânsal Görselleştirme Alt Sistemi',
    nameEn: 'Spatial Rendering Subsystem',
    descTr: '2D tesis planları ve 3D fabrika görünümü için normalize edilmiş koordinat dönüştürücüler.',
    descEn: 'Normalized coordinate transformers for 2D plant blueprints and future 3D factory view.',
    categoryTr: 'Görselleştirme',
    categoryEn: 'Visualization',
  },
];

export const ModuleGrid: React.FC<ModuleGridProps> = ({ status }) => {
  const { lang, t } = useLanguage();
  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '12px',
      padding: '1.5rem',
    }}>
      <div style={{ marginBottom: '1.25rem' }}>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600 }}>
          {t('Modüler Alt Sistemler ve Bağımsız Mimari', 'Modular Subsystems & Decoupled Architecture')}
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
          const statusLabel =
            modStatus === 'active'
              ? t('AKTİF', 'ACTIVE')
              : modStatus === 'ready'
              ? t('HAZIR', 'READY')
              : modStatus.toUpperCase();

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
                    {lang === 'tr' ? mod.categoryTr : mod.categoryEn}
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
                    {statusLabel}
                  </span>
                </div>
                <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.35rem' }}>
                  {lang === 'tr' ? mod.nameTr : mod.nameEn}
                </h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {lang === 'tr' ? mod.descTr : mod.descEn}
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
