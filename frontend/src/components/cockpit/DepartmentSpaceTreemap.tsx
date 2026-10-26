import { departments } from './data';
export function DepartmentSpaceTreemap({ selected, onSelect }: { selected: string | null; onSelect: (id: string) => void }) {
  return <section className="cockpit-panel"><div className="panel-heading"><h2>Department space allocation</h2><span>m²</span></div><div className="space-treemap">{departments.map(d => <button key={d.id} onClick={() => onSelect(d.id)} aria-pressed={selected === d.id} style={{ background: `${d.dark}99`, borderColor: d.color, gridArea: d.id }}><span style={{ color: d.color }}>{d.name}</span><strong>{d.area} <small>m²</small></strong><span>Required {d.required} m²</span></button>)}</div><div className="panel-foot">Required vs allocated · select a zone to inspect</div></section>;
}
