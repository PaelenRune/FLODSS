import { Download, Check } from 'lucide-react';
import { scenarios } from './data';
import { calculateFlowMetrics, percentageDelta, useCockpitData } from './CockpitDataContext';
export function LayoutVersionsTable({ selected, onSelect }: { selected: number; onSelect: (id: number) => void }) {
  const { live, layout, problem, scenarios: liveScenarios = [], selectedScenario, selectScenario, baselineMetrics, metricConfig } = useCockpitData();
  if (live) {
    const exportLayout = () => {
      if (!layout) return;
      const url = URL.createObjectURL(new Blob([JSON.stringify(layout, null, 2)], { type: 'application/json' }));
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = 'flodss-active-layout.json'; anchor.click(); URL.revokeObjectURL(url);
    };
    return <section className="cockpit-panel versions-panel"><div className="panel-heading"><h2>Layout scenarios comparison</h2><button className="icon-button" aria-label="Export active cockpit layout" disabled={!layout} onClick={exportLayout}><Download size={15}/></button></div><div className="scenario-columns"><span>Scenario</span><span>Cost delta</span><span>Distance / cost</span></div>{problem && liveScenarios.map(s => {
      const metrics = calculateFlowMetrics(problem, s.layout, metricConfig);
      return <button className={`scenario-row ${selectedScenario === s.id ? 'selected' : ''}`} key={s.id} onClick={() => selectScenario?.(s.id)} aria-pressed={selectedScenario === s.id}><span><b>{s.name}</b><small>{s.id === 0 ? 'First loaded layout' : 'Click to apply'} {selectedScenario === s.id && <Check size={12}/>}</small></span><strong>{percentageDelta(metrics.handlingCost, baselineMetrics?.handlingCost ?? 0)}</strong><span>{metrics.flowDistance.toLocaleString(undefined, { maximumFractionDigits: 1 })}<small>{metrics.handlingCost.toLocaleString(undefined, { maximumFractionDigits: 1 })} cost units{metrics.missingFlows > 0 && ' · partial'}</small></span></button>;
    })}<div className="panel-foot">{liveScenarios.length ? 'Session history · centroid estimates · lower is better' : 'Run a solver or import a layout to begin.'}</div></section>;
  }
  const download = () => { const blob = new Blob([JSON.stringify({ source: 'FLODSS reference scenario — not a live solver result', ...scenarios[selected] }, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'flodss-reference-scenario.json'; a.click(); URL.revokeObjectURL(url); };
  return <section className="cockpit-panel versions-panel"><div className="panel-heading"><h2>Layout scenarios comparison</h2><button className="icon-button" aria-label="Export selected reference scenario" onClick={download}><Download size={15} /></button></div><div className="scenario-columns"><span>Scenario</span><span>Score</span><span>Distance / cost</span></div>{scenarios.map((s, i) => <button className={`scenario-row ${selected === i ? 'selected' : ''}`} key={s.name} onClick={() => onSelect(i)} aria-pressed={selected === i}><span><b>{s.name}</b><small>{i === 1 ? 'Recommended' : i === 0 ? 'Original configuration' : 'Balanced alternative'} {selected === i && <Check size={12} />}</small></span><strong>{s.score}<small>/100</small></strong><span>{s.distance} m<small>${s.cost}/mo</small></span></button>)}<div className="panel-foot">Reference scenarios · click a row to compare</div></section>;
}
