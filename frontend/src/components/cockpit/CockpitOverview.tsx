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
import './cockpit.css';

interface Props {
  onOpenWorkspace: () => void;
  problem: FacilityLayoutProblem | null;
  layout: ContinuousLayout | null;
  evaluation: EvaluationReport | null;
  liveScenarios?: CockpitScenarios;
}

export function CockpitOverview({ onOpenWorkspace, problem, layout, evaluation, liveScenarios }: Props) {
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
    <header className="cockpit-page-heading"><div><div className="cockpit-breadcrumb">Workspace / <span>Industrial decision support</span></div><h1>Factory intelligence. <span>In perspective.</span></h1><p>FLODSS: Tesis Yerleşimi Optimizasyonu ve Karar Destek Arayüzü</p></div><button className="workspace-button" onClick={onOpenWorkspace}>Open layout editor <ArrowUpRight size={15}/></button></header>
    <div className="cockpit-context"><span><i/> {data.live ? 'Active workspace' : 'Reference scenario'}</span><span>{problem ? `${problem.name} / ${problem.facility.width * problem.facility.height} m² / ${problem.departments.length} departments` : 'Plant 04 / 3,000 m² / 5 departments'}</span><span className="context-note"><CircleHelp size={13}/>{data.live ? (data.layout ? 'Live problem and current layout' : 'No layout yet — run a solver') : 'Illustrative portfolio dataset, not live solver output'}</span></div>
    <div className="cockpit-primary"><IsometricFactoryCanvas selected={activeSelection} onSelect={select} scenario={scenario}/><aside className="cockpit-analytics"><KpiMetricsCard scenario={scenario}/><DepartmentDistributionChart selected={activeSelection} onSelect={select}/></aside></div>
    <div className="cockpit-secondary"><DepartmentSpaceTreemap selected={activeSelection} onSelect={select}/><FromToMatrixHeatmap/><LayoutVersionsTable selected={scenario} onSelect={setScenario}/></div>
    <footer className="cockpit-disclaimer"><span><i/> Decision support cockpit <b>·</b> {data.live ? 'Active problem configuration' : 'Reference configuration'}</span><span>{data.live ? 'Instant centroid estimates · What-If layouts require backend feasibility validation.' : '*Savings figure follows the supplied mock-up; scenario cost delta is $922/mo.'}</span></footer>
  </div></CockpitDataContext.Provider>;
}
