import { useId, useRef, useState } from 'react';
import { Layers, Maximize, ZoomIn, ZoomOut } from 'lucide-react';
import { useCockpitData } from './CockpitDataContext';

export function LiveFactoryCanvas({ selected, onSelect }: { selected: string | null; onSelect: (id: string) => void }) {
  const { departments, flows, problem, layout } = useCockpitData();
  const [flat, setFlat] = useState(false);
  const [showFlows, setShowFlows] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const arrow = useId().replace(/:/g, '');
  const scale = problem ? Math.min(278 / problem.facility.width, 237 / problem.facility.height) : 1;
  const width = (problem?.facility.width ?? 0) * scale, height = (problem?.facility.height ?? 0) * scale;
  const point = (x: number, y: number, z = 0) => flat ? [100 + x * 1.9, 50 + y * 1.5 - z] : [390 + (x - y) * 1.22, 65 + (x + y) * .64 - z];
  const polygon = (x: number, y: number, w: number, h: number, z = 0) => [point(x, y, z), point(x + w, y, z), point(x + w, y + h, z), point(x, y + h, z)].map(p => p.join(',')).join(' ');
  const edges = flows.flatMap((row, from) => row.flatMap((quantity, to) => quantity > 0 && from !== to && departments[from].w > 0 && departments[to].w > 0 ? [{ from, to, quantity }] : [])).sort((a, b) => b.quantity - a.quantity).slice(0, 30);
  const active = departments.find(d => d.id === selected);
  return <section className="cockpit-panel factory-panel">
    <div className="factory-heading"><div><h2>Factory layout <span>Actual solver geometry</span></h2><p>{problem?.facility.name} <span className="status-pill">{layout ? 'Current layout' : 'Awaiting layout'}</span></p></div><div className="canvas-modes"><button aria-pressed={!flat} onClick={() => setFlat(false)}>3D Isometric</button><button aria-pressed={flat} onClick={() => setFlat(true)}>2D Orthographic</button></div></div>
    <div className="factory-stage"><svg viewBox="0 0 820 485" role="img" aria-label={`Current layout for ${problem?.name}, ${departments.length} departments`} onPointerDown={event => {
      if ((event.target as Element).closest('[data-department]')) return;
      drag.current = { x: event.clientX, y: event.clientY, px: pan.x, py: pan.y }; event.currentTarget.setPointerCapture(event.pointerId);
    }} onPointerMove={event => {
      if (!drag.current) return;
      const factor = 820 / event.currentTarget.getBoundingClientRect().width;
      setPan({ x: drag.current.px + (event.clientX - drag.current.x) * factor, y: drag.current.py + (event.clientY - drag.current.y) * factor });
    }} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
      <defs><marker id={arrow} markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0L6 3L0 6" fill="none" stroke="#59f2ff"/></marker></defs>
      <g transform={`translate(${pan.x} ${pan.y}) translate(410 240) scale(${zoom}) translate(-410 -240)`}>
        <polygon points={polygon(0, 0, width, height)} fill="#182332" stroke="#60778c"/>
        {problem?.facility.reserved_zones?.map(zone => {
          const b = zone.bounding_box;
          return <polygon key={zone.id} points={polygon(b.x_min * scale, b.y_min * scale, (b.x_max - b.x_min) * scale, (b.y_max - b.y_min) * scale)} fill="#64748b55" stroke="#94a3b8"><title>{`${zone.type}: ${zone.id}`}</title></polygon>;
        })}
        {departments.filter(d => d.w > 0 && d.h > 0).map(d => <g key={d.id} data-department={d.id} role="button" tabIndex={0} aria-label={`${d.name}, ${d.area} square meters`} aria-pressed={selected === d.id} onClick={() => onSelect(d.id)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(d.id); } }}>
          <polygon points={polygon(d.x, d.y, d.w, d.h, flat ? 0 : 5)} fill={d.dark} stroke={selected === d.id ? '#fff' : d.color} strokeWidth={selected === d.id ? 3 : 1.5}><title>{`${d.name}: ${d.area.toFixed(1)} m² allocated / ${d.required} m² required`}</title></polygon>
          <text x={point(d.x + d.w / 2, d.y + d.h / 2, flat ? 0 : 5)[0]} y={point(d.x + d.w / 2, d.y + d.h / 2, flat ? 0 : 5)[1]} textAnchor="middle" fill={d.color} fontSize="10" pointerEvents="none">{d.id}</text>
        </g>)}
        {showFlows && edges.map(({ from, to, quantity }) => {
          const a = departments[from], b = departments[to];
          const source = point(a.x + a.w / 2, a.y + a.h / 2, 10), target = point(b.x + b.w / 2, b.y + b.h / 2, 10);
          return <path key={`${from}-${to}`} d={`M${source} Q${(source[0] + target[0]) / 2} ${(source[1] + target[1]) / 2 - 25} ${target}`} fill="none" stroke="#59f2ff" opacity=".65" markerEnd={`url(#${arrow})`}><title>{`${a.name} → ${b.name}: ${quantity}`}</title></path>;
        })}
      </g>
      {!layout && <text x="410" y="425" textAnchor="middle" fill="#94a3b8">Run a solver or import a matching layout</text>}
    </svg><div className="canvas-toolbar"><button className="icon-button" aria-label="Zoom in" onClick={() => setZoom(z => Math.min(3, z + .15))}><ZoomIn size={17}/></button><button className="icon-button" aria-label="Zoom out" onClick={() => setZoom(z => Math.max(.5, z - .15))}><ZoomOut size={17}/></button><button className="icon-button" aria-label="Reset view" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}><Maximize size={17}/></button><span>{Math.round(zoom * 100)}%</span></div></div>
    <div className="factory-bottom"><button className={`flow-toggle ${showFlows ? 'enabled' : ''}`} aria-pressed={showFlows} onClick={() => setShowFlows(value => !value)}><Layers size={14}/>Flow vectors<i/></button><span className="factory-inspection">{active ? `${active.name}: ${active.area.toFixed(1)} / ${active.required} m²` : `${departments.filter(d => d.w > 0).length}/${departments.length} placed · top 30 directed flows`}</span></div>
  </section>;
}
