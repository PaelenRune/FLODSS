import { departments } from './data';
export function DepartmentDistributionChart({ selected, onSelect }: { selected: string | null; onSelect: (id: string) => void }) {
  let offset = 0;
  return <section className="cockpit-panel distribution"><div className="panel-heading"><h2>Department distribution</h2><span>Area share</span></div>
    <div className="distribution-body"><svg viewBox="0 0 180 180" role="img" aria-label="Department area distribution donut chart"><circle cx="90" cy="90" r="64" fill="none" stroke="#263047" strokeWidth="17" />{[...departments, { id: 'OT', name: 'Other', color: '#475569', share: 4 }].map(d => { const start = offset; offset += d.share; return <circle key={d.id} cx="90" cy="90" r="64" fill="none" stroke={d.color} strokeWidth={selected === d.id ? 22 : 17} pathLength="100" strokeDasharray={`${d.share - 1} ${101 - d.share}`} strokeDashoffset={-start} transform="rotate(-90 90 90)" />; })}<text x="90" y="88" textAnchor="middle" className="donut-total">100%</text><text x="90" y="108" textAnchor="middle" className="donut-caption">Total area</text></svg>
    <div className="distribution-legend">{departments.map(d => <button key={d.id} onClick={() => onSelect(d.id)} aria-pressed={selected === d.id}><i style={{ background: d.color }} /><span>{d.name}</span><b>{d.share}%</b></button>)}<div><i style={{ background: '#475569' }} /><span>Other</span><b>4%</b></div></div></div>
  </section>;
}
