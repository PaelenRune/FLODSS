import { useState } from 'react';
import { ArrowUpRight, CircleHelp } from 'lucide-react';
import { IsometricFactoryCanvas } from './IsometricFactoryCanvas';
import { KpiMetricsCard } from './KpiMetricsCard';
import { DepartmentDistributionChart } from './DepartmentDistributionChart';
import { DepartmentSpaceTreemap } from './DepartmentSpaceTreemap';
import { FromToMatrixHeatmap } from './FromToMatrixHeatmap';
import { LayoutVersionsTable } from './LayoutVersionsTable';
import type { ContinuousLayout, EvaluationReport, FacilityLayoutProblem } from '../../types/api';
import { buildCockpitData, calculateFlowMetrics, CockpitDataContext } from './CockpitDataContext';
import { useCockpitScenarios, type CockpitScenarios } from './liveScenarios';
import { useLanguage } from '../../context/LanguageContext';
import './cockpit.css';

interface Props {
  onOpenWorkspace: () => void;
  problem: FacilityLayoutProblem | null;
  layout: ContinuousLayout | null;
  evaluation: EvaluationReport | null;
  liveScenarios?: CockpitScenarios;
}

export function CockpitOverview({ onOpenWorkspace, problem, layout, evaluation, liveScenarios }: Props) {
  const { t } = useLanguage();
  const [selected, setSelected] = useState<string | null>(null);
  const [scenario, setScenario] = useState(1);
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
  return <CockpitDataContext.Provider value={data}><div className="cockpit-overview">
    <header className="cockpit-page-heading">
      <div>
        <div className="cockpit-breadcrumb">
          {t('Çalışma Alanı', 'Workspace')} / <span>{t('Endüstriyel karar destek', 'Industrial decision support')}</span>
        </div>
        <h1>{t('Fabrika zekâsı.', 'Factory intelligence.')} <span>{t('Perspektiften.', 'In perspective.')}</span></h1>
        <p>{t('FLODSS: Tesis Yerleşimi Optimizasyonu ve Karar Destek Arayüzü', 'FLODSS: Facility Layout Optimization & Decision Support Interface')}</p>
      </div>
      <button className="workspace-button" onClick={onOpenWorkspace}>
        {t('Yerleşim düzenleyiciyi aç', 'Open layout editor')} <ArrowUpRight size={15}/>
      </button>
    </header>
    <div className="cockpit-context">
      <span><i/> {data.live ? t('Aktif çalışma alanı', 'Active workspace') : t('Referans senaryo', 'Reference scenario')}</span>
      <span>
        {problem
          ? `${problem.name} / ${problem.facility.width * problem.facility.height} m² / ${problem.departments.length} ${t('bölüm', 'departments')}`
          : t('Tesis 04 / 3.000 m² / 5 bölüm', 'Plant 04 / 3,000 m² / 5 departments')}
      </span>
      <span className="context-note">
        <CircleHelp size={13}/>
        {data.live
          ? (data.layout ? t('Canlı problem ve güncel yerleşim', 'Live problem and current layout') : t('Henüz yerleşim yok — bir çözücü çalıştırın', 'No layout yet — run a solver'))
          : t('Örnek portföy veri seti, canlı çözücü çıktısı değildir', 'Illustrative portfolio dataset, not live solver output')}
      </span>
    </div>
    <div className="cockpit-primary"><IsometricFactoryCanvas selected={activeSelection} onSelect={select} scenario={scenario}/><aside className="cockpit-analytics"><KpiMetricsCard scenario={scenario}/><DepartmentDistributionChart selected={activeSelection} onSelect={select}/></aside></div>
    <div className="cockpit-secondary"><DepartmentSpaceTreemap selected={activeSelection} onSelect={select}/><FromToMatrixHeatmap/><LayoutVersionsTable selected={scenario} onSelect={setScenario}/></div>
    <footer className="cockpit-disclaimer">
      <span><i/> {t('Karar destek kokpiti', 'Decision support cockpit')} <b>·</b> {data.live ? t('Aktif problem yapılandırması', 'Active problem configuration') : t('Referans yapılandırması', 'Reference configuration')}</span>
      <span>{data.live ? t('Anlık ağırlık merkezi tahminleri · Senaryo denemesi yerleşimleri sunucu uygunluk doğrulaması gerektirir.', 'Instant centroid estimates · What-If layouts require backend feasibility validation.') : t('*Tasarruf tutarı örnek taslağa göredir; senaryo maliyet farkı aylık $922 değerindedir.', '*Savings figure follows the supplied mock-up; scenario cost delta is $922/mo.')}</span>
    </footer>
  </div></CockpitDataContext.Provider>;
}
