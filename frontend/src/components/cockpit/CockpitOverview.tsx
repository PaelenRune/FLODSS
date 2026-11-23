import React, { useState } from 'react';
import { ArrowUpRight, CircleHelp, Play, Layers, Minimize2, Maximize2, X } from 'lucide-react';
import { IsometricFactoryCanvas } from './IsometricFactoryCanvas';
import { KpiMetricsCard } from './KpiMetricsCard';
import { DepartmentDistributionChart } from './DepartmentDistributionChart';
import { DepartmentSpaceTreemap } from './DepartmentSpaceTreemap';
import { FromToMatrixHeatmap } from './FromToMatrixHeatmap';
import { LayoutVersionsTable } from './LayoutVersionsTable';
import type { ContinuousLayout, EvaluationReport, FacilityLayoutProblem, ProblemSummary } from '../../types/api';
import { buildCockpitData, calculateFlowMetrics, CockpitDataContext, localizeBenchmarkText } from './CockpitDataContext';
import { useCockpitScenarios, type CockpitScenarios } from './liveScenarios';
import { useLanguage } from '../../context/LanguageContext';
import './cockpit.css';

export type QuickSolverId = 'craft' | 'corelap' | 'aldep' | 'feasible_generator' | 'ga';

interface Props {
  onOpenWorkspace: () => void;
  problem: FacilityLayoutProblem | null;
  layout: ContinuousLayout | null;
  evaluation: EvaluationReport | null;
  liveScenarios?: CockpitScenarios;
  availableProblems?: ProblemSummary[];
  onLoadExample?: (problemId: string) => void;
  onQuickSolve?: (algorithm: QuickSolverId) => void;
  quickSolving?: boolean;
  quickStatus?: string | null;
  activePanel?: string;
  onSelectPanel?: (panelId: string) => void;
  workbench?: React.ReactNode;
  workbenchTitle?: string;
}

export function CockpitOverview({
  onOpenWorkspace,
  problem,
  layout,
  evaluation,
  liveScenarios,
  availableProblems,
  onLoadExample,
  onQuickSolve,
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
  const localScenarios = useCockpitScenarios(problem, layout, evaluation);
  const history = liveScenarios ?? localScenarios;
  const active = history.scenarios.find(s => s.id === history.selected);
  const data = buildCockpitData(problem, active?.layout ?? layout, active?.evaluation ?? null);
  data.scenarios = history.scenarios;
  data.selectedScenario = history.selected;
  data.selectScenario = history.select;
  data.swap = history.swap;
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

  const quickPills = [
    { id: 'cockpit', label: t('Özet', 'Overview') },
    { id: 'problem', label: t('Problem', 'Problem') },
    { id: 'matrices', label: t('Akış / REL', 'Flow / REL') },
    { id: 'constraints', label: t('Kısıtlar', 'Constraints') },
    { id: 'solvers', label: t('Optimizasyon', 'Optimization') },
    { id: 'layout', label: t('2B Plan', '2D Plan') },
    { id: 'pareto', label: t('Pareto', 'Pareto') },
    { id: 'decision', label: t('Karar Destek', 'Decision') },
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
      <button className="workspace-button" onClick={onOpenWorkspace}>
        {t('Klasik Görünüme Geç', 'Open layout editor')} <ArrowUpRight size={15}/>
      </button>
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
            <label className="commandbar-group">
              <span>{t('Problem', 'Problem')}</span>
              <select
                className="cockpit-select"
                value={problem?.id ?? ''}
                onChange={e => e.target.value && onLoadExample(e.target.value)}
              >
                {availableProblems.map(p => (
                  <option key={p.id} value={p.id}>
                    {p.id} · {localizeBenchmarkText(p.name, t)}
                  </option>
                ))}
              </select>
            </label>
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
                {quickSolving ? t('Çalıştırılıyor...', 'Running...') : t('Optimize Et', 'Optimize')}
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
