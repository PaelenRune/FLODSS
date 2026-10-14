import React, { useState } from 'react';
import { useLanguage } from '../context/LanguageContext';
import { HelpCircle, ChevronDown, ChevronUp, CheckCircle, Info, DollarSign, Heart, ShieldCheck, ArrowRight } from 'lucide-react';

export interface DecisionGuidanceBoxProps {
  mode: 'layout' | 'pareto';
  defaultOpen?: boolean;
}

export const DecisionGuidanceBox: React.FC<DecisionGuidanceBoxProps> = ({ mode, defaultOpen = false }) => {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (mode === 'layout') {
    return (
      <div
        style={{
          border: '1px solid #bfdbfe',
          backgroundColor: '#f8fafc',
          borderRadius: '8px',
          marginBottom: '1rem',
          overflow: 'hidden',
        }}
      >
        <button
          onClick={() => setIsOpen(!isOpen)}
          style={{
            width: '100%',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            padding: '0.75rem 1rem',
            backgroundColor: '#eff6ff',
            border: 'none',
            cursor: 'pointer',
            textAlign: 'left',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, color: '#1e40af', fontSize: '0.875rem' }}>
            <HelpCircle size={16} />
            <span>{t('2D Layout İnceleme Rehberi & Akademik Karar Notları', '2D Layout Inspection Guide & Academic Decision Notes')}</span>
          </div>
          <div style={{ color: '#3b82f6', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}>
            <span>{isOpen ? t('Gizle', 'Hide') : t('Nasıl Okunur?', 'How to Read?')}</span>
            {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </div>
        </button>

        {isOpen && (
          <div style={{ padding: '1rem', fontSize: '0.825rem', color: '#334155', lineHeight: 1.5 }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
              <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <Info size={14} color="#2563eb" /> {t('1. Ne Görüyorum?', '1. What am I viewing?')}
                </div>
                <div>
                  {t(
                    'Tesis sınırları (facility envelope) içinde departmanların 1:1 sürekli Kartezyen yerleşimini ve centroid tabanlı malzeme akış çizgilerini görüyorsunuz.',
                    'You are viewing the 1:1 continuous Cartesian spatial placement of departments within facility boundaries along with centroid-based material flow lines.'
                  )}
                </div>
              </div>

              <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <CheckCircle size={14} color="#16a34a" /> {t('2. Neye Bakmalıyım?', '2. What should I look for?')}
                </div>
                <div>
                  {t(
                    'Kırmızı çakışma (overlap) alanı olmamalıdır. Departmanların en-boy oranı (aspect ratio) kısıt sınırında (ör. ≤ 3.0) kalmalı ve yoğun akışlı departmanlar birbirine yakın olmalıdır.',
                    'No red overlap areas should exist. Department aspect ratios must remain within constraints (e.g. ≤ 3.0), and high-traffic departments should be located close together.'
                  )}
                </div>
              </div>

              <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <DollarSign size={14} color="#d97706" /> {t('3. Akış Çizgileri & MHC Maliyeti', '3. Flow Lines & MHC Cost')}
                </div>
                <div>
                  {t(
                    'Yönlü oklar malzeme trafiğini gösterir. Turuncu oklar en yüksek taşıma maliyeti yaratan "İlk 5 Maliyet Sürücüsü"dür (Top 5 Cost Drivers). Bu departmanları yaklaştırmak MHC\'yi hızla düşürür.',
                    'Directed arrows indicate material volume. Orange arrows mark the Top 5 Cost Drivers. Placing these departments closer reduces MHC dramatically.'
                  )}
                </div>
              </div>

              <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
                <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <ShieldCheck size={14} color="#6366f1" /> {t('4. Feasible = Optimal midir?', '4. Is Feasible = Optimal?')}
                </div>
                <div>
                  {t(
                    'Hayır. Feasible olması yerleşimin fiziki kuralları ihlal etmediğini (çakışmasız, sınırlar içinde) kanıtlar; ancak en düşük maliyetli (optimal) çözüm olduğunu garanti etmez. Pareto sekmesinde ödünleşimleri kıyaslayın.',
                    'No. Feasible guarantees physical constraint satisfaction (no overlap, within boundary), but does not mean it is globally optimal. Compare trade-offs in the Pareto tab.'
                  )}
                </div>
              </div>
            </div>

            <div style={{ marginTop: '0.75rem', padding: '0.5rem 0.75rem', backgroundColor: '#f1f5f9', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ArrowRight size={14} color="#0284c7" />
              <span>
                <strong>{t('Sonraki Adım:', 'Next Step:')}</strong>{' '}
                {t(
                  'Bir departmana tıklayarak detaylı boyut/akış panelini açın veya üst menüden Pareto sekmesine geçerek alternatif adayları kıyaslayın.',
                  'Click any department to inspect exact dimensions and flow traffic, or navigate to Pareto tab to compare alternative candidates.'
                )}
              </span>
            </div>
          </div>
        )}
      </div>
    );
  }

  // mode === 'pareto'
  return (
    <div
      style={{
        border: '1px solid #bfdbfe',
        backgroundColor: '#f8fafc',
        borderRadius: '8px',
        marginBottom: '1.25rem',
        overflow: 'hidden',
      }}
    >
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: '100%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.75rem 1rem',
          backgroundColor: '#eff6ff',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 600, color: '#1e40af', fontSize: '0.875rem' }}>
          <HelpCircle size={16} />
          <span>{t('Pareto Karar Verme & Ödünleşim (Trade-Off) Rehberi', 'Pareto Decision Support & Trade-Off Guide')}</span>
        </div>
        <div style={{ color: '#3b82f6', display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: '0.75rem' }}>
          <span>{isOpen ? t('Gizle', 'Hide') : t('Rehberi Göster', 'Show Guide')}</span>
          {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {isOpen && (
        <div style={{ padding: '1rem', fontSize: '0.825rem', color: '#334155', lineHeight: 1.5 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
            <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
              <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Info size={14} color="#2563eb" /> {t('1. Ne Görüyorum?', '1. What am I viewing?')}
              </div>
              <div>
                {t(
                  'Farklı optimizasyon yöntemlerinden (GA, CORELAP vb.) elde edilen aday çözümlerin Malzeme Taşıma Maliyeti (MHC) ve Yakınlık Memnuniyeti (REL) eksenlerindeki dağılımını görüyorsunuz.',
                  'Distribution of candidate layout solutions from multiple solvers (GA, CORELAP, etc.) plotted across Material Handling Cost (MHC) and Relationship Satisfaction (REL).'
                )}
              </div>
            </div>

            <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
              <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <CheckCircle size={14} color="#16a34a" /> {t('2. Neye Bakmalıyım? (İdeal Nokta)', '2. What should I target?')}
              </div>
              <div>
                {t(
                  'Grafiğin sol-üst bölgesi (Sol = Düşük MHC, Üst = Yüksek REL) ideal yöndür. Yeşil yıldızlı (Rank 1) noktalar Pareto Sınırı üzerindedir ve hiçbir çözüm tarafından domine edilmemiştir.',
                  'Top-left region (Left = Low MHC, Top = High REL) is mathematically ideal. Green star (Rank 1) solutions lie on the Pareto Frontier and are strictly non-dominated.'
                )}
              </div>
            </div>

            <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
              <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <DollarSign size={14} color="#d97706" /> {t('3. Neden Düşük MHC?', '3. Why minimize MHC?')}
              </div>
              <div>
                {t(
                  'Düşük MHC, fabrikada malzeme taşıyan forklift, AGV veya personelin katettiği toplam ton-metre maliyetini doğrudan düşürür; operasyonel giderleri (OPEX) minimize eder.',
                  'Lower MHC directly slashes tone-distance traveled by forklifts, AGVs, or operators, minimizing recurring operational expenditure (OPEX).'
                )}
              </div>
            </div>

            <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
              <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Heart size={14} color="#dc2626" /> {t('4. Yüksek REL Ne Anlama Gelir?', '4. What does high REL mean?')}
              </div>
              <div>
                {t(
                  'Muther REL skoru, kritik departmanların (A-Kesinlikle Gerekli, E-Önemli) yakınlık memnuniyetini ölçer. Güvenlik, bilgi akışı, denetim ve ortak kaynak kullanımı kalitesini yansıtır.',
                  'Muther REL score measures satisfaction of qualitative adjacency preferences (A-Absolute, E-Essential). It reflects safety, supervisor oversight, and workflow coherence.'
                )}
              </div>
            </div>

            <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
              <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <ShieldCheck size={14} color="#7c3aed" /> {t('5. Non-Dominated vs Dominated', '5. Non-Dominated vs Dominated')}
              </div>
              <div>
                {t(
                  'Bir çözümün "Dominated" (Rank 2+) olması, başka bir adayın hem daha ucuz MHC hem de daha yüksek REL sağladığı anlamına gelir. Seçim yaparken mutlaka Rank 1 çözümleri tercih edin.',
                  'A solution is "Dominated" (Rank 2+) if another layout achieves both strictly lower MHC and higher REL. Always select from Rank 1 non-dominated candidates.'
                )}
              </div>
            </div>

            <div style={{ backgroundColor: '#ffffff', padding: '0.75rem', borderRadius: '6px', border: '1px solid #e2e8f0' }}>
              <div style={{ fontWeight: 700, color: '#0f172a', marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <ArrowRight size={14} color="#059669" /> {t('6. Sonraki Adım Nedir?', '6. What is the Next Step?')}
              </div>
              <div>
                {t(
                  'İşletme önceliğinize göre bir adayı seçin veya "Karşılaştırma Modu" ile iki adayı yan yana kıyaslayın. Ardından "Aktif Çözüm Yap" butonuna basarak çözümü platform geneline uygulayın.',
                  'Pick a candidate according to business priority or use "Comparison Mode" to compare two candidates side-by-side. Then click "Set as Active Platform Solution".'
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
