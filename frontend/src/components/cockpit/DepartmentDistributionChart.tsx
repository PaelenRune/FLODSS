import { useCockpitData } from './CockpitDataContext';

export function DepartmentDistributionChart({ selected, onSelect }: { selected: string | null; onSelect: (id: string) => void }) {
  const { departments } = useCockpitData();
  const occupied = departments.reduce((sum, d) => sum + d.share, 0);
  const free = Math.max(0, 100 - occupied);
  const denominator = Math.max(100, occupied);
  const segments = [...departments, { id: '__free', name: 'Unallocated', color: '#475569', share: free }];
  let offset = 0;
  return <section className="cockpit-panel distribution">
    <div className="panel-heading"><h2>Department distribution</h2><span>Area share</span></div>
    <div className="distribution-body"><svg viewBox="0 0 180 180" role="img" aria-label="Department area distribution donut chart">
      <circle cx="90" cy="90" r="64" fill="none" stroke="#263047" strokeWidth="17"/>
      {segments.map(d => {
        const share = d.share / denominator * 100, start = offset; offset += share;
        return <circle key={d.id} cx="90" cy="90" r="64" fill="none" stroke={d.color} strokeWidth={selected === d.id ? 22 : 17} pathLength="100" strokeDasharray={`${Math.max(0, share - .5)} ${100 - Math.max(0, share - .5)}`} strokeDashoffset={-start} transform="rotate(-90 90 90)"/>;
      })}
      <text x="90" y="88" textAnchor="middle" className="donut-total">{occupied.toFixed(0)}%</text><text x="90" y="108" textAnchor="middle" className="donut-caption">Allocated (gross)</text>
    </svg><div className="distribution-legend">{departments.map(d => <button key={d.id} onClick={() => onSelect(d.id)} aria-pressed={selected === d.id}><i style={{ background: d.color }}/><span>{d.name}</span><b>{d.share.toFixed(1)}%</b></button>)}<div><i style={{ background: '#475569' }}/><span>Unallocated</span><b>{free.toFixed(1)}%</b></div></div></div>
  </section>;
}
