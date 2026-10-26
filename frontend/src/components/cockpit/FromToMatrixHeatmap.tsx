import { useCockpitData } from './CockpitDataContext';

export function FromToMatrixHeatmap() {
  const { departments, flows, live } = useCockpitData();
  const maxFlow = Math.max(1, ...flows.flat());
  return <section className="cockpit-panel"><div className="panel-heading"><h2>From–to flow matrix</h2><span>fᵢⱼ</span></div>
    <div className="flow-table" style={{ overflow: 'auto', maxHeight: 290 }}><table><caption className="sr-only">{live ? 'Problem-defined directional material flow quantities' : 'Daily material transfers between departments'}</caption><thead><tr><th>From / To</th>{departments.map(d => <th key={d.id}>{d.id}</th>)}</tr></thead><tbody>{flows.map((row, i) => <tr key={departments[i].id}><th>{departments[i].id}</th>{row.map((v, j) => <td key={departments[j].id}><span tabIndex={0} title={`${departments[i].name} → ${departments[j].name}: ${v}`} style={{ background: v ? `rgba(0, 190, 224, ${0.08 + v / maxFlow * .7})` : '#151c2a', color: v > maxFlow * .6 ? '#bdfaff' : '#72849b' }}>{v || (i === j ? '—' : 0)}</span></td>)}</tr>)}</tbody></table></div>
    <div className="heatmap-key"><span>Low intensity</span><i/><span>High intensity</span></div></section>;
}
