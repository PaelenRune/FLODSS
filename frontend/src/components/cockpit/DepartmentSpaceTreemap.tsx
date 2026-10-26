import { useCockpitData } from './CockpitDataContext';

export function DepartmentSpaceTreemap({ selected, onSelect }: { selected: string | null; onSelect: (id: string) => void }) {
  const { departments, live } = useCockpitData();
  return <section className="cockpit-panel"><div className="panel-heading"><h2>Department space allocation</h2><span>m²</span></div>
    <div className="space-treemap" style={live ? { display: 'flex', flexWrap: 'wrap', overflow: 'auto' } : undefined}>
      {departments.map(d => <button key={d.id} onClick={() => onSelect(d.id)} aria-pressed={selected === d.id} style={{ background: `${d.dark}99`, borderColor: d.color, ...(live ? { flex: `${Math.max(d.area, d.required, 1)} 1 95px` } : { gridArea: d.id }) }}><span style={{ color: d.color }}>{d.name}</span><strong>{d.area.toLocaleString(undefined, { maximumFractionDigits: 1 })} <small>m²</small></strong><span>Required {d.required} m²</span></button>)}
    </div><div className="panel-foot">Required vs allocated · select a zone to inspect</div></section>;
}
