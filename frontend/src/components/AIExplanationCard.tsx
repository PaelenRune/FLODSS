import React, { useState, useEffect } from 'react';
import {
  AIExplanationResult,
  AIStatusResponse,
  DataTransferPreview,
  ExplanationMode,
  PresetQuestionType,
} from '../types/api';
import {
  fetchAIStatus,
  previewAIPayload,
  grantAIConsent,
  explainLocal,
  explainGemini,
} from '../services/api';
import { useLanguage } from '../context/LanguageContext';

const BENCHMARK_PROBLEMS = [
  { id: 'FLP_INDUSTRIAL_10', name: 'FLP_INDUSTRIAL_10 (10 Depts, 91.7% Util, Strict Bounds)' },
  { id: 'HIGH_DENSITY_15', name: 'HIGH_DENSITY_15 (15 Depts, 90.0% Util, Realistic Dense Flows)' },
  { id: 'HIGH_DENSITY_20', name: 'HIGH_DENSITY_20 (20 Depts, 95.8% Util, Heterogeneous Dense Plant)' },
  { id: 'CONSTRAINED_FACTORY_12', name: 'CONSTRAINED_FACTORY_12 (12 Depts, 81.3% Util, Fixed Dock & Reserved Spine)' },
  { id: 'LOGISTICS_FACTORY_15', name: 'LOGISTICS_FACTORY_15 (15 Depts, 85.0% Util, Asymmetric Tote Logistics)' },
  { id: 'FLP_ACADEMIC_4', name: 'FLP_ACADEMIC_4 (4 Depts, Small Unconstrained Flow)' },
  { id: 'FLP_MEDIUM_6', name: 'FLP_MEDIUM_6 (6 Depts, Medium Plant)' },
  { id: 'FLP_EXPANSION_8', name: 'FLP_EXPANSION_8 (8 Depts, Reserved Spine Aisle)' },
  { id: 'FLP_LOGISTICS_5', name: 'FLP_LOGISTICS_5 (5 Depts, Linear Flow Hub)' },
];

const PRESET_QUESTIONS: { type: PresetQuestionType; labelTr: string; labelEn: string; textTr: string; textEn: string }[] = [
  {
    type: 'why_strategy_selected',
    labelTr: 'Algoritma Seçimi',
    labelEn: 'Algorithm Selection',
    textTr: 'FLODSS neden bu algoritmayı seçti?',
    textEn: 'Why did FLODSS select this algorithm?',
  },
  {
    type: 'why_feasible',
    labelTr: 'Feasibility Gerekçesi',
    labelEn: 'Feasibility Rationale',
    textTr: 'Bu fabrika yerleşimi neden Feasible?',
    textEn: 'Why is this factory layout feasible?',
  },
  {
    type: 'pareto_comparison',
    labelTr: 'Pareto Trade-Off Analizi',
    labelEn: 'Pareto Trade-Offs',
    textTr: 'İki Pareto Frontier alternatifi arasındaki fark nedir?',
    textEn: 'What is the difference between these two Pareto alternatives?',
  },
  {
    type: 'soft_penalty_explanation',
    labelTr: 'Soft Penalty Etkisi',
    labelEn: 'Soft Penalty Impact',
    textTr: 'Soft Constraint Penalty değeri ne anlama geliyor?',
    textEn: 'What does the soft constraint penalty mean?',
  },
  {
    type: 'fallback_reason',
    labelTr: 'Fallback Mekanizması',
    labelEn: 'Fallback Mechanism',
    textTr: 'Yedek (Fallback) algoritma neden çalıştı?',
    textEn: 'Why did the fallback algorithm run?',
  },
  {
    type: 'global_optimality_query',
    labelTr: 'Global Optimality Sınırları',
    labelEn: 'Optimality Boundaries',
    textTr: 'Bu sonucun Global Optimal olduğu garanti edilir mi?',
    textEn: 'Is this result guaranteed to be globally optimal?',
  },
];

export const AIExplanationCard: React.FC = () => {
  const { lang, t } = useLanguage();
  const [mode, setMode] = useState<ExplanationMode>('local');
  const [selectedProblemId, setSelectedProblemId] = useState<string>('FLP_INDUSTRIAL_10');
  const [selectedQuestionType, setSelectedQuestionType] = useState<PresetQuestionType>('why_strategy_selected');
  const [customQuestion, setCustomQuestion] = useState<string>('');

  const [aiStatus, setAiStatus] = useState<AIStatusResponse | null>(null);
  const [preview, setPreview] = useState<DataTransferPreview | null>(null);
  const [consentChecked, setConsentChecked] = useState<boolean>(false);
  const [showPreviewModal, setShowPreviewModal] = useState<boolean>(false);

  // Security & Minimization states
  const [clientSessionId] = useState<string>(() => 'sess_' + Math.random().toString(36).substring(2, 12));
  const [optInDimensions, setOptInDimensions] = useState<boolean>(false);
  const [optInAreas, setOptInAreas] = useState<boolean>(false);
  const [optInFinancial, setOptInFinancial] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AIExplanationResult | null>(null);

  // Load AI configuration status
  useEffect(() => {
    fetchAIStatus()
      .then(setAiStatus)
      .catch((err) => console.warn('Could not fetch AI status:', err));
  }, []);

  const handleExplainLocal = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await explainLocal({
        problem_id: selectedProblemId,
        question_type: selectedQuestionType,
        custom_question: selectedQuestionType === 'custom' ? customQuestion : undefined,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || t('Yerel açıklama üretilemedi', 'Local explanation generation failed'));
    } finally {
      setLoading(false);
    }
  };

  const handleOpenPreview = async () => {
    setLoading(true);
    setError(null);
    setConsentChecked(false);
    try {
      const p = await previewAIPayload({
        problem_id: selectedProblemId,
        question_type: selectedQuestionType,
        custom_question: selectedQuestionType === 'custom' ? customQuestion : undefined,
        client_session_id: clientSessionId,
      });
      setPreview(p);
      setShowPreviewModal(true);
    } catch (err: any) {
      setError(err.message || t('Önizleme veri paketi oluşturulamadı', 'Failed to generate preview data packet'));
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmGeminiConsent = async () => {
    if (!preview || !consentChecked) return;
    setShowPreviewModal(false);
    setLoading(true);
    setError(null);
    try {
      // 1. Explicitly grant server-side consent and obtain single-use token
      const consentRes = await grantAIConsent({
        payload_hash: preview.payload_hash,
        client_session_id: clientSessionId,
        consent_acknowledged: consentChecked,
        opt_in_exact_dimensions: optInDimensions,
        opt_in_exact_areas: optInAreas,
        opt_in_financial_costs: optInFinancial,
      });

      // 2. Invoke Gemini with single-use session-bound token
      const res = await explainGemini({
        problem_id: selectedProblemId,
        question_type: selectedQuestionType,
        custom_question: selectedQuestionType === 'custom' ? customQuestion : undefined,
        payload_hash: preview.payload_hash,
        consent_token: consentRes.consent_token,
        client_session_id: clientSessionId,
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || t('Gemini açıklaması başarısız oldu', 'Gemini explanation failed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      backgroundColor: 'var(--bg-secondary)',
      borderRadius: '12px',
      border: '1px solid var(--border-color)',
      padding: '1.75rem',
      marginBottom: '2rem',
      boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.25rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              {t('Gemini AI Karar Açıklama & Mühendislik Denetimi (XAI)', 'Phase 12: Gemini AI Decision Explanation & Engineering Audit')}
            </h2>
            <span style={{
              fontSize: '0.75rem',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: '999px',
              backgroundColor: '#e0e7ff',
              color: '#3730a3',
            }}>
              {t('GİZLİLİK GARANTİLİ', 'CONFIDENTIALITY GUARANTEED')}
            </span>
          </div>
          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-secondary)', maxWidth: '850px' }}>
            {t(
              'Algoritma seçimleri, geometrik kısıtlar (Hard/Soft Constraints) ve çok amaçlı Pareto Frontier ödünleşimleri için kanıta dayalı açıklamalar sunar. Gemini yalnızca yorumlayıcı asistandır; asla koordinat değiştirmez veya hesaplanan metrikleri ezmez.',
              'Provides grounded, explainable rationales for algorithm choices, geometric constraints, and multi-objective Pareto trade-offs. Gemini acts strictly as an interpretation assistant—it never optimizes, moves coordinates, or overrides computed metrics.'
            )}
          </p>
        </div>

        {/* Confidentiality Privacy Tag */}
        <div style={{
          backgroundColor: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          padding: '0.5rem 0.85rem',
          fontSize: '0.75rem',
          color: '#475569',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          gap: '2px',
        }}>
          <div><strong>{t('Aktarım Politikası:', 'Transmission Policy:')}</strong> Whitelist Only</div>
          <div>{t('Hariç Tutulan: Koordinatlar, Akış Matrisi, Kaynak Kod, İsimler', 'Excluded: Coordinates, Raw Flows, Source Code, Names')}</div>
        </div>
      </div>

      {/* Mode Switcher */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '0.75rem',
        backgroundColor: 'var(--bg-primary)',
        borderRadius: '8px',
        border: '1px solid var(--border-color)',
        marginBottom: '1.25rem',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
          {t('Açıklama Motoru:', 'Explanation Engine:')}
        </span>
        <button
          onClick={() => { setMode('local'); setError(null); }}
          style={{
            padding: '0.4rem 0.85rem',
            borderRadius: '6px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            border: 'none',
            backgroundColor: mode === 'local' ? 'var(--accent-color, #2563eb)' : 'transparent',
            color: mode === 'local' ? '#ffffff' : 'var(--text-primary)',
            transition: 'all 0.15s ease',
          }}
        >
          {t('Yerel Açıklama (Çevrimdışı & Deterministik)', 'Explain Locally (Offline & Deterministic)')}
        </button>
        <button
          onClick={() => { setMode('gemini'); setError(null); }}
          style={{
            padding: '0.4rem 0.85rem',
            borderRadius: '6px',
            fontSize: '0.85rem',
            fontWeight: 600,
            cursor: 'pointer',
            border: 'none',
            backgroundColor: mode === 'gemini' ? '#7c3aed' : 'transparent',
            color: mode === 'gemini' ? '#ffffff' : 'var(--text-primary)',
            transition: 'all 0.15s ease',
          }}
        >
          {t('Gemini AI ile Açıkla (Onaylı & Gizli)', 'Explain with Gemini AI (Confidential Opt-in)')}
        </button>

        <span style={{ marginLeft: 'auto', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {mode === 'local'
            ? t('✓ %100 çevrimdışı kural tabanlı şablonlar', '✓ 100% offline rule-based templates')
            : aiStatus?.ai_enabled
              ? `✓ Model: ${aiStatus.gemini_model}`
              : t('⚠ AI varsayılan olarak kapalı (yerel moda döner)', '⚠ AI disabled by default (falls back to local)')}
        </span>
      </div>

      {/* Inputs Section */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
        {/* Problem selector */}
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem', color: 'var(--text-secondary)' }}>
            {t('Hedef Problem', 'Target Problem')}
          </label>
          <select
            value={selectedProblemId}
            onChange={(e) => setSelectedProblemId(e.target.value)}
            style={{
              width: '100%',
              padding: '0.5rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
            }}
          >
            {BENCHMARK_PROBLEMS.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Question Type */}
        <div>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem', color: 'var(--text-secondary)' }}>
            {t('Denetim Soru Kategorisi', 'Audit Question Category')}
          </label>
          <select
            value={selectedQuestionType}
            onChange={(e) => setSelectedQuestionType(e.target.value as PresetQuestionType)}
            style={{
              width: '100%',
              padding: '0.5rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
            }}
          >
            {PRESET_QUESTIONS.map((q) => (
              <option key={q.type} value={q.type}>
                {lang === 'tr' ? `${q.labelTr}: "${q.textTr}"` : `${q.labelEn}: "${q.textEn}"`}
              </option>
            ))}
            <option value="custom">{t('Özel Mühendislik Sorusu...', 'Custom Engineering Question...')}</option>
          </select>
        </div>
      </div>

      {/* Custom question text input */}
      {selectedQuestionType === 'custom' && (
        <div style={{ marginBottom: '1.25rem' }}>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '0.35rem', color: 'var(--text-secondary)' }}>
            {t('Mühendislik Sorusu Girin (Temizlenmiş, Maks 300 Karakter)', 'Enter Engineering Question (Strictly Sanitized, Max 300 Characters)')}
          </label>
          <textarea
            value={customQuestion}
            onChange={(e) => setCustomQuestion(e.target.value.slice(0, 300))}
            placeholder={t('Örn: Area Utilization yoğunluğu koridor açıklıklarını nasıl etkiler?', 'e.g. How does the area density affect layout stability and aisle clearances?')}
            rows={2}
            style={{
              width: '100%',
              padding: '0.6rem',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              backgroundColor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              fontSize: '0.85rem',
              resize: 'none',
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
            <span>{t('HTML etiketleri ve Prompt Injection işaretleri otomatik temizlenir.', 'HTML tags and prompt injection markers will be redacted.')}</span>
            <span>{customQuestion.length}/300</span>
          </div>
        </div>
      )}

      {/* Preset Question Quick Buttons */}
      <div style={{ marginBottom: '1.25rem' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
          {t('Hızlı Arketip Sorular:', 'Quick Archetype Questions:')}
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {PRESET_QUESTIONS.map((q) => (
            <button
              key={q.type}
              onClick={() => setSelectedQuestionType(q.type)}
              style={{
                fontSize: '0.75rem',
                padding: '0.35rem 0.65rem',
                borderRadius: '6px',
                border: selectedQuestionType === q.type ? '1px solid #6366f1' : '1px solid var(--border-color)',
                backgroundColor: selectedQuestionType === q.type ? '#eef2ff' : 'var(--bg-primary)',
                color: selectedQuestionType === q.type ? '#4338ca' : 'var(--text-secondary)',
                cursor: 'pointer',
              }}
            >
              {lang === 'tr' ? q.labelTr : q.labelEn}
            </button>
          ))}
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
        {mode === 'local' ? (
          <button
            onClick={handleExplainLocal}
            disabled={loading}
            style={{
              padding: '0.6rem 1.4rem',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? t('Açıklama Üretiliyor...', 'Generating Explanation...') : t('Yerel Açıklama Üret', 'Generate Local Explanation')}
          </button>
        ) : (
          <button
            onClick={handleOpenPreview}
            disabled={loading}
            style={{
              padding: '0.6rem 1.4rem',
              backgroundColor: '#7c3aed',
              color: '#ffffff',
              border: 'none',
              borderRadius: '6px',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? t('Veri Önizlemesi Hazırlanıyor...', 'Preparing Data Preview...') : t('Veri Paketini Önizle & Onayla', 'Preview Data Packet & Review Consent')}
          </button>
        )}

        {error && (
          <div style={{ color: '#dc2626', fontSize: '0.85rem', fontWeight: 500 }}>
            {t('Hata:', 'Error:')} {error}
          </div>
        )}
      </div>

      {/* Preview Modal for Explicit Consent */}
      {showPreviewModal && preview && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '1.5rem',
        }}>
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '12px',
            maxWidth: '750px',
            width: '100%',
            maxHeight: '90vh',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
            overflow: 'hidden',
          }}>
            <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#1e293b' }}>
                  {t('Gizli Veri Aktarım Önizlemesi & Açık Rıza', 'Confidential Data Transfer Preview & Consent')}
                </h3>
                <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                  {t('Hedef Sağlayıcı:', 'Target Provider:')} {preview.provider} &bull; Model: {preview.target_model}
                </span>
              </div>
              <button
                onClick={() => setShowPreviewModal(false)}
                style={{ background: 'none', border: 'none', fontSize: '1.25rem', cursor: 'pointer', color: '#64748b' }}
              >
                &times;
              </button>
            </div>

            <div style={{ padding: '1.25rem 1.5rem', overflowY: 'auto', fontSize: '0.85rem', lineHeight: 1.5 }}>
              <div style={{ backgroundColor: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: '6px', padding: '0.75rem', marginBottom: '1rem', color: '#1e3a8a' }}>
                <strong>{t('Gizlilik Politikası:', 'Confidentiality Policy:')}</strong> {preview.privacy_impact}
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '0.25rem' }}>
                  {t('Gönderilecek İzinli (Whitelisted) Alanlar:', 'Whitelisted Fields To Be Transmitted:')}
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.25rem', color: '#334155' }}>
                  {preview.whitelisted_fields.slice(0, 8).map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                  <li>{t('...ve kanonik metrikler ile anonimleştirilmiş departman alanları.', '...plus canonical metrics and anonymized department areas.')}</li>
                </ul>
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontWeight: 600, color: '#991b1b', marginBottom: '0.25rem' }}>
                  {t('Kesinlikle Hariç Tutulan Hassas Alanlar (Sıfır Aktarım):', 'Explicitly Excluded Sensitive Fields (Zero Transmission):')}
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.25rem', color: '#991b1b' }}>
                  {preview.excluded_sensitive_fields.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '0.25rem' }}>
                  Exact JSON Payload:
                </div>
                <pre style={{
                  backgroundColor: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  padding: '0.75rem',
                  fontSize: '0.75rem',
                  maxHeight: '160px',
                  overflowY: 'auto',
                  fontFamily: 'monospace',
                }}>
                  {JSON.stringify(preview.payload, null, 2)}
                </pre>
                <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '4px', fontFamily: 'monospace' }}>
                  SHA-256 Payload Hash: {preview.payload_hash}
                </div>
              </div>

              <div style={{
                backgroundColor: '#f8fafc',
                border: '1px solid #cbd5e1',
                borderRadius: '6px',
                padding: '0.75rem',
                marginTop: '1rem',
              }}>
                <div style={{ marginBottom: '0.75rem', paddingBottom: '0.75rem', borderBottom: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#334155', marginBottom: '0.4rem' }}>
                    {t('Veri Minimizasyonu & İsteğe Bağlı Alanlar:', 'Granular Field Minimization & Opt-in Flags:')}
                  </div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', fontSize: '0.75rem', color: '#475569', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={optInDimensions}
                      onChange={(e) => setOptInDimensions(e.target.checked)}
                    />
                    {t('Tam tesis dış sınır boyutlarını dahil et (metre cinsinden genişlik & derinlik)', 'Include exact facility boundary dimensions (width & height in meters)')}
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', fontSize: '0.75rem', color: '#475569', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={optInAreas}
                      onChange={(e) => setOptInAreas(e.target.checked)}
                    />
                    {t('Tam departman hedef alan değerlerini dahil et (m²)', 'Include exact department target area values (m²)')}
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: '#475569', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={optInFinancial}
                      onChange={(e) => setOptInFinancial(e.target.checked)}
                    />
                    {t('Tam Material Handling Cost (MHC $) tutarlarını dahil et', 'Include exact material handling cost dollar figures ($)')}
                  </label>
                </div>

                <label style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={consentChecked}
                    onChange={(e) => setConsentChecked(e.target.checked)}
                    style={{ marginTop: '3px' }}
                  />
                  <span style={{ fontSize: '0.8rem', color: '#1e293b' }}>
                    {t(
                      'Yukarıdaki izinli özetin Google Gemini API servisine gönderilmesine açıkça onay veriyorum. Koordinatların, akışların ve gizli isimlerin hariç tutulduğunu ve Global Optimality garantisi verilmediğini kabul ediyorum.',
                      'I explicitly consent to sending the whitelisted summary above to Google Gemini API. I acknowledge that coordinates, flows, and confidential names are excluded, and that no guarantees of global optimality apply.'
                    )}
                  </span>
                </label>

                <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.6rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <span style={{ color: '#059669', fontWeight: 700 }}>&#x1F512; Single-Use Replay Protection:</span>
                  {t(
                    `Yetkilendirme 15 dakika geçerlidir, ${clientSessionId.substring(0, 10)}... oturumuna bağlıdır ve ilk kullanımda geçersiz kılınır.`,
                    `Authorization is valid for 15 minutes, bound to session ${clientSessionId.substring(0, 10)}..., and invalidated immediately upon first execution.`
                  )}
                </div>
              </div>
            </div>

            <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid #e2e8f0', display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
              <button
                onClick={() => setShowPreviewModal(false)}
                style={{
                  padding: '0.5rem 1rem',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  backgroundColor: '#ffffff',
                  color: '#475569',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                }}
              >
                {t('İptal', 'Cancel')}
              </button>
              <button
                onClick={handleConfirmGeminiConsent}
                disabled={!consentChecked}
                style={{
                  padding: '0.5rem 1.25rem',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: consentChecked ? '#7c3aed' : '#cbd5e1',
                  color: '#ffffff',
                  cursor: consentChecked ? 'pointer' : 'not-allowed',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                }}
              >
                {t('Yetkilendir & Gemini\'ye Gönder', 'Authorize & Send to Gemini')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Explanation Results View */}
      {result && (
        <div style={{
          backgroundColor: 'var(--bg-primary)',
          borderRadius: '8px',
          border: '1px solid var(--border-color)',
          padding: '1.5rem',
          marginTop: '1rem',
        }}>
          {/* Provenance Banner */}
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '0.5rem',
            marginBottom: '1rem',
            paddingBottom: '0.75rem',
            borderBottom: '1px solid var(--border-color)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '4px',
                backgroundColor: result.mode === 'gemini' ? '#7c3aed' : '#2563eb',
                color: '#ffffff',
                textTransform: 'uppercase',
              }}>
                {result.mode === 'gemini' ? 'Google Gemini 3.8 Flash' : 'Local Deterministic Explainer'}
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {t('Soru:', 'Question:')} "{result.question}"
              </span>
            </div>

            {result.fallback_to_local_used && (
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 600,
                color: '#b45309',
                backgroundColor: '#fef3c7',
                padding: '2px 8px',
                borderRadius: '4px',
              }}>
                Fallback Active: {result.fallback_reason || 'AI offline'}
              </span>
            )}
          </div>

          {/* Executive Summary */}
          <div style={{
            fontSize: '0.95rem',
            lineHeight: 1.6,
            fontWeight: 500,
            color: 'var(--text-primary)',
            backgroundColor: 'var(--bg-secondary)',
            padding: '1rem',
            borderRadius: '6px',
            borderLeft: '4px solid #4f46e5',
            marginBottom: '1.25rem',
          }}>
            <strong>{t('Özet:', 'Summary:')}</strong> {result.explanation.summary}
          </div>

          {/* Grounded Canonical Metrics Box */}
          {result.verified_canonical_metrics && Object.keys(result.verified_canonical_metrics).length > 0 && (
            <div style={{
              display: 'flex',
              gap: '1rem',
              flexWrap: 'wrap',
              marginBottom: '1.25rem',
              padding: '0.75rem 1rem',
              backgroundColor: 'var(--bg-secondary)',
              borderRadius: '6px',
            }}>
              <div style={{ fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Material Handling Cost (MHC): </span>
                <strong>${Number(result.verified_canonical_metrics.material_handling_cost || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
              </div>
              <div style={{ fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>REL Satisfaction: </span>
                <strong>{Number(result.verified_canonical_metrics.relationship_satisfaction || 0).toFixed(2)}%</strong>
              </div>
              <div style={{ fontSize: '0.8rem' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Soft Constraint Penalty: </span>
                <strong>${Number(result.verified_canonical_metrics.soft_penalty || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong>
              </div>
            </div>
          )}

          {/* Rationales, Strengths, Risks Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginBottom: '1.25rem' }}>
            {/* Main Reasons */}
            {result.explanation.main_reasons.length > 0 && (
              <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '0.85rem', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#1e3a8a', marginBottom: '0.4rem' }}>
                  {t('Temel Mühendislik Gerekçeleri', 'Primary Engineering Reasons')}
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                  {result.explanation.main_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Strengths */}
            {result.explanation.strengths.length > 0 && (
              <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '0.85rem', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#065f46', marginBottom: '0.4rem' }}>
                  {t('Yerleşim & Algoritma Güçlü Yönleri', 'Layout & Algorithmic Strengths')}
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                  {result.explanation.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Operational Risks */}
            {result.explanation.risks.length > 0 && (
              <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '0.85rem', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#92400e', marginBottom: '0.4rem' }}>
                  {t('Olası Operasyonel Riskler', 'Potential Operational Risks')}
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                  {result.explanation.risks.map((rk, i) => (
                    <li key={i}>{rk}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Trade-offs & Compromises */}
            {result.explanation.trade_offs.length > 0 && (
              <div style={{ backgroundColor: 'var(--bg-secondary)', padding: '0.85rem', borderRadius: '6px' }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#4338ca', marginBottom: '0.4rem' }}>
                  {t('Çok Amaçlı Ödünleşimler (Multi-Objective Trade-Offs)', 'Multi-Objective Trade-Offs')}
                </div>
                <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.8rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
                  {result.explanation.trade_offs.map((tItem, i) => (
                    <li key={i}>{tItem}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Evidence references chips */}
          {result.explanation.evidence_references.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                {t('Atıf Yapılan Kanonik Metrikler:', 'Cited Canonical Metrics:')}
              </span>
              {result.explanation.evidence_references.map((ev, i) => (
                <span
                  key={i}
                  style={{
                    fontSize: '0.7rem',
                    fontFamily: 'monospace',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: '#e2e8f0',
                    color: '#334155',
                  }}
                >
                  {ev}
                </span>
              ))}
            </div>
          )}

          {/* Mandatory Global Optimality Disclaimer */}
          <div style={{
            fontSize: '0.75rem',
            lineHeight: 1.5,
            color: '#64748b',
            backgroundColor: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '6px',
            padding: '0.75rem',
            fontStyle: 'italic',
          }}>
            <strong>{t('Mühendislik Sorumluluk Notu:', 'Engineering Disclaimer:')}</strong> {result.explanation.global_optimality_disclaimer}
          </div>
        </div>
      )}
    </div>
  );
};
