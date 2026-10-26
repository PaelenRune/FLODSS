import { Download, Check } from 'lucide-react';
import { scenarios } from './data';
import { useCockpitData } from './CockpitDataContext';
export function LayoutVersionsTable({ selected, onSelect }: { selected: number; onSelect: (id: number) => void }) {
  const { live, layout, evaluation } = useCockpitData();
  if (live) {
    const exportLayout = () => {
      if (!layout) return;
      const url = URL.createObjectURL(new Blob([JSON.stringify(layout, null, 2)], { type: 'application/json' }));
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = 'flodss-active-layout.json'; anchor.click(); URL.revokeObjectURL(url);
    };
    return <section className="cockpit-panel versions-panel"><div className="panel-heading"><h2>Current workspace layout</h2><button className="icon-button" aria-label="Export active solver layout" disabled={!layout} onClick={exportLayout}><Download size={15}/></button></div><div className="panel-foot">{layout ? (layout.name || layout.id || 'Current solver / imported layout') : 'Run a solver or import a layout to begin.'}</div><div className="panel-foot">{evaluation ? `${evaluation.algorithm_name} · ${evaluation.is_feasible ? 'Feasible' : 'Infeasible'}` : 'Evaluation pending'}</div><div className="panel-foot">Saved runs and comparisons are available in the research workspace.</div></section>;
  }
  const download = () => { const blob = new Blob([JSON.stringify({ source: 'FLODSS reference scenario — not a live solver result', ...scenarios[selected] }, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'flodss-reference-scenario.json'; a.click(); URL.revokeObjectURL(url); };
  return <section className="cockpit-panel versions-panel"><div className="panel-heading"><h2>Layout scenarios comparison</h2><button className="icon-button" aria-label="Export selected reference scenario" onClick={download}><Download size={15} /></button></div><div className="scenario-columns"><span>Scenario</span><span>Score</span><span>Distance / cost</span></div>{scenarios.map((s, i) => <button className={`scenario-row ${selected === i ? 'selected' : ''}`} key={s.name} onClick={() => onSelect(i)} aria-pressed={selected === i}><span><b>{s.name}</b><small>{i === 1 ? 'Recommended' : i === 0 ? 'Original configuration' : 'Balanced alternative'} {selected === i && <Check size={12} />}</small></span><strong>{s.score}<small>/100</small></strong><span>{s.distance} m<small>${s.cost}/mo</small></span></button>)}<div className="panel-foot">Reference scenarios · click a row to compare</div></section>;
}
