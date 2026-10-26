import { useState } from 'react';
import { ArrowUpRight, CircleHelp } from 'lucide-react';
import { IsometricFactoryCanvas } from './IsometricFactoryCanvas';
import { KpiMetricsCard } from './KpiMetricsCard';
import { DepartmentDistributionChart } from './DepartmentDistributionChart';
import { DepartmentSpaceTreemap } from './DepartmentSpaceTreemap';
import { FromToMatrixHeatmap } from './FromToMatrixHeatmap';
import { LayoutVersionsTable } from './LayoutVersionsTable';
import './cockpit.css';

export function CockpitOverview({ onOpenWorkspace }: { onOpenWorkspace: () => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [scenario, setScenario] = useState(1);
  const select = (id: string) => setSelected(s => s === id ? null : id);
  return <div className="cockpit-overview"><header className="cockpit-page-heading"><div><div className="cockpit-breadcrumb">Workspace / <span>Industrial decision support</span></div><h1>Factory intelligence. <span>In perspective.</span></h1><p>FLODSS: Tesis Yerleşimi Optimizasyonu ve Karar Destek Arayüzü</p></div><button className="workspace-button" onClick={onOpenWorkspace}>Open layout editor <ArrowUpRight size={15}/></button></header>
    <div className="cockpit-context"><span><i/> Reference scenario</span><span>Plant 04 <b>/</b> 3,000 m² <b>/</b> 5 departments</span><span className="context-note"><CircleHelp size={13}/> Illustrative portfolio dataset, not live solver output</span></div>
    <div className="cockpit-primary"><IsometricFactoryCanvas selected={selected} onSelect={select} scenario={scenario}/><aside className="cockpit-analytics"><KpiMetricsCard scenario={scenario}/><DepartmentDistributionChart selected={selected} onSelect={select}/></aside></div>
    <div className="cockpit-secondary"><DepartmentSpaceTreemap selected={selected} onSelect={select}/><FromToMatrixHeatmap/><LayoutVersionsTable selected={scenario} onSelect={setScenario}/></div>
    <footer className="cockpit-disclaimer"><span><i/> Decision support cockpit <b>·</b> Reference configuration</span><span>*Savings figure follows the supplied mock-up; scenario cost delta is $922/mo.</span></footer>
  </div>;
}
