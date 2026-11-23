import React, { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, CircleHelp, Download, FileSpreadsheet, Play, Plus, Layers, Minimize2, Maximize2, X } from 'lucide-react';
import { IsometricFactoryCanvas } from './IsometricFactoryCanvas';
import { KpiMetricsCard } from './KpiMetricsCard';
import { DepartmentDistributionChart } from './DepartmentDistributionChart';
import { DepartmentSpaceTreemap } from './DepartmentSpaceTreemap';
import { FromToMatrixHeatmap } from './FromToMatrixHeatmap';
import { LayoutVersionsTable } from './LayoutVersionsTable';
import type { ContinuousLayout, EvaluationReport, FacilityLayoutProblem, LayoutValidationResult, ProblemSummary } from '../../types/api';
import { buildCockpitData, calculateFlowMetrics, CockpitDataContext, getShortDepartmentLabel, localizeBenchmarkText, percentageDelta } from './CockpitDataContext';
import { useCockpitScenarios, type CockpitScenarios } from './liveScenarios';
import { useLanguage } from '../../context/LanguageContext';
import './cockpit.css';

export type QuickSolverId = 'craft' | 'corelap' | 'aldep' | 'feasible_generator' | 'ga';

interface Props {
  onOpenWorkspace: () => void;
  problem: FacilityLayoutProblem | null;
  layout: ContinuousLayout | null;
  evaluation: EvaluationReport | null;
  validation?: LayoutValidationResult | null;
  liveScenarios?: CockpitScenarios;
  availableProblems?: ProblemSummary[];
  onLoadExample?: (problemId: string) => void;
  onQuickSolve?: (algorithm: QuickSolverId) => void;
  onCreateSampleLayout?: () => void;
  onOpenNewProject?: () => void;
  onEditPlan?: (scenarioId: number) => void;
  quickSolving?: boolean;
  quickStatus?: string | null;
  activePanel?: string;
  onSelectPanel?: (panelId: string) => void;
  workbench?: React.ReactNode;
  workbenchTitle?: string;
}

export function buildQuickSvgDocument(
  problem: FacilityLayoutProblem | null | undefined,
  activeLayout: ContinuousLayout,
  departments: Array<{ id: string; name: string }>,
  t: (tr: string, en: string) => string
): string {
  const escapeXml = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const facW = activeLayout.facility_width || problem?.facility.width || 150;
  const facH = activeLayout.facility_height || problem?.facility.height || 80;
  const pad = 28;
  const palette = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#f97316', '#14b8a6', '#6366f1', '#84cc16'];
  const rects = Object.values(activeLayout.placements).map((pl, idx) => {
    const deptObj = departments.find(d => d.id === pl.department_id) ?? { id: pl.department_id, name: pl.department_id };
    const label = escapeXml(getShortDepartmentLabel(deptObj, t));
    const color = palette[idx % palette.length];
    const svgX = pad + pl.x;
    const svgY = pad + (facH - pl.y - pl.height);
    const areaTxt = `${Math.round(pl.width * pl.height)} m²`;
    return `<rect x="${svgX}" y="${svgY}" width="${pl.width}" height="${pl.height}" fill="${color}" fill-opacity="0.82" stroke="#f8fafc" stroke-width="0.9" rx="1"/>
  <text x="${svgX + pl.width / 2}" y="${svgY + pl.height / 2 - 2.2}" text-anchor="middle" dominant-baseline="middle" fill="#ffffff" font-size="4.6" font-family="sans-serif" font-weight="bold">${label}</text>
  <text x="${svgX + pl.width / 2}" y="${svgY + pl.height / 2 + 3.2}" text-anchor="middle" dominant-baseline="middle" fill="#e2e8f0" font-size="3.4" font-family="sans-serif">${areaTxt}</text>`;
  }).join('\n  ');
  const title = escapeXml(localizeBenchmarkText(problem?.name, t) || activeLayout.problem_id || 'FLODSS');
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${facW + pad * 2} ${facH + pad * 2}" width="${(facW + pad * 2) * 7}" height="${(facH + pad * 2) * 7}">
  <rect width="100%" height="100%" fill="#0b1220"/>
  <text x="${pad}" y="${pad - 9}" fill="#94a3b8" font-size="5" font-family="sans-serif">${title} · ${facW}×${facH} m</text>
  <rect x="${pad}" y="${pad}" width="${facW}" height="${facH}" fill="#111b2e" stroke="#38bdf8" stroke-width="1"/>
  ${rects}
</svg>`;
}

export function CockpitOverview({
  onOpenWorkspace,
  problem,
  layout,
  evaluation,
  validation = null,
  liveScenarios,
  availableProblems,
  onLoadExample,
  onQuickSolve,
  onCreateSampleLayout,
  onOpenNewProject,
  onEditPlan,
  quickSolving = false,
  quickStatus,
  activePanel = 'cockpit',
  onSelectPanel,
  workbench,
  workbenchTitle,
}: Props) {
  const { t } = useLanguage();
  const [selected, setSelected] = useState<string | null>(null);
  const [scenario, setScenario] = useState(1);
  const [quickAlgo, setQuickAlgo] = useState<QuickSolverId>('ga');
  const [compactCanvas, setCompactCanvas] = useState(false);
  const [downloadNotice, setDownloadNotice] = useState<string | null>(null);
  const downloadTimerRef = useRef<number | null>(null);
  useEffect(() => () => {
    if (downloadTimerRef.current !== null && typeof window !== 'undefined') {
      window.clearTimeout(downloadTimerRef.current);
    }
  }, []);

  const localScenarios = useCockpitScenarios(problem, layout, evaluation, undefined, validation);
  const history = liveScenarios ?? localScenarios;
  const active = history.scenarios.find(s => s.id === history.selected);
  const activeValidation = active?.validation ?? (active?.layout === layout ? validation : null);
  const data = buildCockpitData(problem, active?.layout ?? layout, active?.evaluation ?? null, activeValidation);
  data.scenarios = history.scenarios;
  data.selectedScenario = history.selected;
  data.selectScenario = history.select;
  data.swap = history.swap;
  data.onCreateSampleLayout = onCreateSampleLayout;
  data.onEditPlan = onEditPlan;

  const activePlanShortLabel = !active
    ? t('İlk yerleşim', 'Baseline')
    : active.name === 'Baseline Layout'
      ? t('İlk yerleşim', 'Baseline')
      : active.name.startsWith('Solver Layout · ')
        ? active.name.slice('Solver Layout · '.length).trim()
        : active.name.startsWith('What-If')
          ? t(`Senaryo #${active.id}`, `What-If #${active.id}`)
          : active.id === 0
            ? t('İlk yerleşim', 'Baseline')
            : t('Optimize edilmiş', 'Optimized');

  // Keep one metric/cost convention for every alternative, including unevaluated swaps.
  data.metricConfig = { ...problem?.objective_config, ...(evaluation?.problem_id === problem?.id ? evaluation?.evaluation_config : {}) };
  if (problem) {
    data.metrics = calculateFlowMetrics(problem, data.layout ?? null, data.metricConfig);
    if (history.scenarios[0]) data.baselineMetrics = calculateFlowMetrics(problem, history.scenarios[0].layout, data.metricConfig);
  }
  const activeSelection = data.departments.some(department => department.id === selected) ? selected : null;
  const select = (id: string) => setSelected(s => s === id ? null : id);
  const hasCommandBar = Boolean(onLoadExample || onQuickSolve || onSelectPanel);
  const hasWorkbench = Boolean(workbench && activePanel && activePanel !== 'cockpit');

  const triggerDownload = (content: string, filename: string, mime: string) => {
    const blob = new Blob([content], { type: mime });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1500);
    setDownloadNotice(t(`İndirildi: ${filename}`, `Downloaded: ${filename}`));
    if (downloadTimerRef.current !== null) {
      window.clearTimeout(downloadTimerRef.current);
    }
    downloadTimerRef.current = window.setTimeout(() => setDownloadNotice(null), 6000);
  };

  const handleDownloadQuickSvg = (scenarioId?: number) => {
    const targetScenario = scenarioId !== undefined
      ? history.scenarios.find(s => s.id === scenarioId)
      : active;
    const activeLayout = targetScenario?.layout ?? data.layout;
    if (!activeLayout?.placements) return;
    const planSlug = !targetScenario || targetScenario.id === 0
      ? t('ilk_yerlesim', 'baseline')
      : targetScenario.name.startsWith('What-If')
        ? t(`senaryo_${targetScenario.id}`, `what_if_${targetScenario.id}`)
        : t('optimize_edilmis', 'optimized');
    const svg = buildQuickSvgDocument(problem, activeLayout, data.departments, t);
    triggerDownload(svg, `flodss_2d_${planSlug}_${problem?.id || 'layout'}.svg`, 'image/svg+xml;charset=utf-8');
  };
  data.onDownloadPlanSvg = handleDownloadQuickSvg;

  const handleDownloadQuickCsv = () => {
    if (!problem || !data.layout) return;
    const header = [
      t('Senaryo', 'Scenario'),
      t('Alan Kullanımı (%)', 'Area Utilization (%)'),
      t('Akış Mesafesi', 'Flow Distance'),
      t('Taşıma Maliyeti (MHC)', 'Handling Cost (MHC)'),
      t('İlk Yerleşime Göre Fark', 'Delta vs Baseline'),
    ];
    const rows: string[][] = [header];
    const list = history.scenarios.length > 0 ? history.scenarios : [{ id: 0, name: 'Active Layout', layout: data.layout, evaluation }];
    const baseStats = list[0] ? calculateFlowMetrics(problem, list[0].layout, data.metricConfig) : null;
    const facArea = Math.max(1, problem.facility.width * problem.facility.height);
    for (const sc of list) {
      const st = calculateFlowMetrics(problem, sc.layout, data.metricConfig);
      const occ = Object.values(sc.layout.placements).reduce((s, p) => s + p.width * p.height, 0);
      const util = ((occ / facArea) * 100).toFixed(2);
      const scLabel = sc.id === 0 ? t('İlk yerleşim', 'Baseline Layout') : t(`Optimize edilmiş #${sc.id}`, `Optimized #${sc.id}`);
      const delta = sc.id === 0 || !baseStats ? '0%' : percentageDelta(st.handlingCost, baseStats.handlingCost);
      rows.push([scLabel, util, st.flowDistance.toFixed(2), st.handlingCost.toFixed(2), delta]);
    }
    const csv = '\uFEFF' + rows.map(r => r.map(cell => `"${cell.replace(/"/g, '""')}"`).join(',')).join('\n');
    triggerDownload(csv, `flodss_sonuclar_${problem.id}.csv`, 'text/csv;charset=utf-8');
  };

  const quickPills = [
    { id: 'cockpit', label: t('Özet', 'Overview') },
    { id: 'problem', label: t('Problem', 'Problem') },
    { id: 'matrices', label: t('Akış / REL', 'Flow / REL') },
    { id: 'constraints', label: t('Kısıtlar', 'Constraints') },
    { id: 'solvers', label: t('Optimizasyon', 'Optimization') },
    { id: 'layout', label: t('Yerleşimi Düzenle', 'Edit Layout') },
    { id: 'pareto', label: t('Pareto', 'Pareto') },
    { id: 'decision', label: t('Strateji / Kısıt', 'Strategy / Constraints') },
    { id: 'export', label: t('Dışa Aktar', 'Export') },
    { id: 'overview', label: t('Sistem', 'System') },
  ];

  return <CockpitDataContext.Provider value={data}><div className={`cockpit-overview ${compactCanvas ? 'canvas-compact' : ''}`}>
    <header className="cockpit-page-heading">
      <div>
        <div className="cockpit-breadcrumb">
          {t('FLODSS', 'Workspace')} / <span>{t('Tesis Yerleşimi ve Karar Destek', 'Industrial decision support')}</span>
        </div>
        <h1>{t('Tesis Yerleşim', 'Factory intelligence.')} <span>{t('Kokpiti', 'In perspective.')}</span></h1>
        <p>{t('3B canlı yerleşim, tek tıkla optimizasyon ve entegre karar destek merkezi', 'FLODSS: Facility Layout Optimization & Decision Support Interface')}</p>
      </div>
      <div className="heading-actions">
        {onOpenNewProject && (
          <button type="button" className="cockpit-btn-accent" onClick={onOpenNewProject}>
            <Plus size={15}/>
            {t('Yeni Proje Oluştur', 'New Project')}
          </button>
        )}
        <button className="workspace-button" onClick={onOpenWorkspace}>
          {t('Klasik Görünüme Geç', 'Open layout editor')} <ArrowUpRight size={15}/>
        </button>
      </div>
    </header>
    <div className="cockpit-context">
      <span><i/> {data.live ? t('Aktif çalışma alanı', 'Active workspace') : t('Referans senaryo', 'Reference scenario')}</span>
      <span>
        {problem
          ? `${localizeBenchmarkText(problem.name, t)} / ${(problem.facility.width * problem.facility.height).toLocaleString()} m² / ${problem.departments.length} ${t('bölüm', 'departments')}`
          : t('Tesis 04 / 3.000 m² / 5 bölüm', 'Plant 04 / 3,000 m² / 5 departments')}
      </span>
      <span className="context-note">
        <CircleHelp size={13}/>
        {data.live
          ? (data.layout ? t('Canlı problem ve güncel yerleşim', 'Live problem and current layout') : t('Henüz yerleşim yok — bir çözücü çalıştırın', 'No layout yet — run a solver'))
          : t('Örnek portföy veri seti, canlı çözücü çıktısı değildir', 'Illustrative portfolio dataset, not live solver output')}
      </span>
    </div>

    {hasCommandBar && (
      <section className="cockpit-commandbar" aria-label={t('Hızlı kontrol çubuğu', 'Quick command bar')}>
        <div className="commandbar-controls">
          {onLoadExample && availableProblems && availableProblems.length > 0 && (
            <div className="commandbar-group">
              <span>{t('Problem', 'Problem')}</span>
              <select
                className="cockpit-select"
                aria-label={t('Problem seçin', 'Select problem')}
                value={problem?.id ?? ''}
                onChange={e => e.target.value && onLoadExample(e.target.value)}
              >
                {availableProblems.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.id.startsWith('CUSTOM_') ? localizeBenchmarkText(p.name, t) : `${p.id} · ${localizeBenchmarkText(p.name, t)}`}
                  </option>
                ))}
              </select>
              {onOpenNewProject && (
                <button
                  type="button"
                  className="cockpit-btn-accent compact"
                  onClick={onOpenNewProject}
                  title={t('Kendi tesis boyutları, bölümler ve akışlarla yeni proje oluştur', 'Create a custom project with your own dimensions, departments, and flows')}
                >
                  <Plus size={13}/>
                  {t('Yeni Proje', 'New Project')}
                </button>
              )}
            </div>
          )}

          {onQuickSolve && (
            <div className="commandbar-group">
              <span>{t('Hızlı Çözücü', 'Quick Solver')}</span>
              <select
                className="cockpit-select"
                value={quickAlgo}
                disabled={quickSolving || !problem}
                onChange={e => setQuickAlgo(e.target.value as QuickSolverId)}
              >
                <option value="ga">{t('Genetik Algoritma (GA)', 'Genetic Algorithm (GA)')}</option>
                <option value="feasible_generator">{t('Uygun Yerleşim Üretici', 'Feasible Generator')}</option>
                <option value="craft">{t('CRAFT (Mevcut İyileştirme)', 'CRAFT Improvement')}</option>
                <option value="corelap">{t('CORELAP (İlişki Temelli)', 'CORELAP Construction')}</option>
                <option value="aldep">{t('ALDEP (Şerit Yerleşimi)', 'ALDEP Construction')}</option>
              </select>
              <button
                type="button"
                className="cockpit-btn-primary"
                disabled={quickSolving || !problem}
                onClick={() => onQuickSolve(quickAlgo)}
              >
                <Play size={13}/>
                {quickSolving ? t('Çalıştırılıyor...', 'Running...') : t('Yerleşimi iyileştir', 'Improve layout')}
              </button>
              {quickStatus && <span className="commandbar-status">{quickStatus}</span>}
            </div>
          )}

          <button
            type="button"
            className="cockpit-btn-ghost"
            onClick={() => setCompactCanvas(v => !v)}
          >
            {compactCanvas ? <Maximize2 size={13}/> : <Minimize2 size={13}/>}
            {compactCanvas ? t('3B Planı Genişlet', 'Expand 3D') : t('3B Planı Daralt', 'Compact 3D')}
          </button>
        </div>

        {onSelectPanel && (
          <div className="cockpit-quick-pills" role="tablist" aria-label={t('Hızlı işlem sekmeleri', 'Quick action tabs')}>
            {quickPills.map(pill => {
              const isSelected = activePanel === pill.id;
              return (
                <button
                  key={pill.id}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  className={isSelected ? 'active' : ''}
                  onClick={() => onSelectPanel(isSelected && pill.id !== 'cockpit' ? 'cockpit' : pill.id)}
                >
                  {pill.label}
                </button>
              );
            })}
          </div>
        )}

        {data.layout && (
          <div className="commandbar-exports">
            <span className="export-label">{t('Hızlı İndir:', 'Quick Export:')}</span>
            <button type="button" className="cockpit-btn-shortcut" onClick={() => handleDownloadQuickSvg()}>
              <Download size={13}/>
              {t(`2B planı indir (SVG · ${activePlanShortLabel})`, `Download 2D plan (SVG · ${activePlanShortLabel})`)}
            </button>
            <button type="button" className="cockpit-btn-shortcut" onClick={handleDownloadQuickCsv}>
              <FileSpreadsheet size={13}/>
              {t('Sonuç tablosunu indir (CSV)', 'Download results table (CSV)')}
            </button>
            {onSelectPanel && (
              <button type="button" className="cockpit-btn-shortcut secondary" onClick={() => onSelectPanel('export')}>
                {t('Tüm dışa aktarma seçenekleri', 'All export options')} →
              </button>
            )}
            {downloadNotice && (
              <span className="download-notice" role="status">{downloadNotice}</span>
            )}
          </div>
        )}
      </section>
    )}

    <div className="cockpit-primary"><IsometricFactoryCanvas selected={activeSelection} onSelect={select} scenario={scenario}/><aside className="cockpit-analytics"><KpiMetricsCard scenario={scenario}/><DepartmentDistributionChart selected={activeSelection} onSelect={select}/></aside></div>

    {hasWorkbench && (
      <section className="cockpit-workbench" aria-label={workbenchTitle || t('Entegre çalışma paneli', 'Integrated workbench')}>
        <div className="workbench-header">
          <div className="workbench-title">
            <Layers size={15}/>
            <h2>{workbenchTitle}</h2>
          </div>
          {onSelectPanel && (
            <button type="button" className="cockpit-btn-ghost" onClick={() => onSelectPanel('cockpit')}>
              <X size={13}/>
              {t('Özete Dön', 'Back to overview')}
            </button>
          )}
        </div>
        <div className="workbench-body">
          {workbench}
        </div>
      </section>
    )}

    <div className="cockpit-secondary"><DepartmentSpaceTreemap selected={activeSelection} onSelect={select}/><FromToMatrixHeatmap/><LayoutVersionsTable selected={scenario} onSelect={setScenario}/></div>
    <footer className="cockpit-disclaimer">
      <span><i/> {t('Karar destek kokpiti', 'Decision support cockpit')} <b>·</b> {data.live ? t('Aktif problem yapılandırması', 'Active problem configuration') : t('Referans yapılandırması', 'Reference configuration')}</span>
      <span>{data.live ? t('Anlık ağırlık merkezi tahminleri · Senaryo denemesi yerleşimleri sunucu uygunluk doğrulaması gerektirir.', 'Instant centroid estimates · What-If layouts require backend feasibility validation.') : t('*Tasarruf tutarı örnek taslağa göredir; senaryo maliyet farkı aylık $922 değerindedir.', '*Savings figure follows the supplied mock-up; scenario cost delta is $922/mo.')}</span>
    </footer>
  </div></CockpitDataContext.Provider>;
}
