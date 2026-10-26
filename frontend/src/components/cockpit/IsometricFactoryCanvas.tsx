import { useId, useRef, useState } from 'react';
import { ZoomIn, ZoomOut, Maximize, Move, Layers } from 'lucide-react';
import { departments } from './data';

interface Props { selected: string | null; onSelect: (id: string) => void; scenario: number }
export function IsometricFactoryCanvas({ selected, onSelect, scenario }: Props) {
  const [flat, setFlat] = useState(false);
  const [flow, setFlow] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const id = useId().replace(/:/g, '');
  const p = (x: number, y: number, z = 0): [number, number] => flat ? [120 + x * 1.75, 35 + y * 1.38 - z * .15] : [390 + (x - y) * 1.22, 78 + (x + y) * .64 - z];
  const points = (v: [number, number][]) => v.map(a => a.join(',')).join(' ');
  const scenarioZone = (dept: typeof departments[number]) => {
    const swap = scenario === 0 ? { ST: 'PK', PK: 'ST' } : scenario === 2 ? { MC: 'AS', AS: 'MC' } : {};
    return departments.find(d => d.id === swap[dept.id as keyof typeof swap]) ?? dept;
  };
  const zoneTransform = (dept: typeof departments[number]) => {
    const target = scenarioZone(dept);
    const sx = target.w / dept.w, sy = target.h / dept.h;
    const a = flat ? sx : (sx + sy) / 2, b = flat ? 0 : .64 / 1.22 * (sx - sy) / 2;
    const c = flat ? 0 : 1.22 / .64 * (sx - sy) / 2, d = flat ? sy : (sx + sy) / 2;
    const origin = p(dept.x, dept.y), destination = p(target.x, target.y);
    return `matrix(${a} ${b} ${c} ${d} ${destination[0] - a * origin[0] - c * origin[1]} ${destination[1] - b * origin[0] - d * origin[1]})`;
  };
  const box = (x: number, y: number, w: number, h: number, z: number, top: string, side: string, stroke = '#ffffff22') => <g key={`${x}-${y}-${z}`}>
    <polygon points={points([p(x, y + h), p(x + w, y + h), p(x + w, y + h, z), p(x, y + h, z)])} fill={side} stroke={stroke} strokeWidth=".6" />
    <polygon points={points([p(x + w, y), p(x + w, y + h), p(x + w, y + h, z), p(x + w, y, z)])} fill={side} stroke={stroke} strokeWidth=".6" opacity=".75" />
    <polygon points={points([p(x, y, z), p(x + w, y, z), p(x + w, y + h, z), p(x, y + h, z)])} fill={top} stroke={stroke} strokeWidth=".7" />
  </g>;
  const active = departments.find(d => d.id === selected);
  return <section className="cockpit-panel factory-panel"><div className="factory-heading"><div><h2>Factory layout <span>Department & flow allocation</span></h2><p>4-bay production plant <span className="status-pill">{scenario === 1 ? 'Optimized' : scenario === 0 ? 'Baseline' : 'Alternative'}</span></p></div><div className="canvas-modes"><button aria-pressed={!flat} onClick={() => setFlat(false)}>3D Isometric</button><button aria-pressed={flat} onClick={() => setFlat(true)}>2D Orthographic</button></div></div>
    <div className="factory-stage"><svg ref={svg} viewBox="0 0 820 485" role="img" aria-label="Interactive isometric factory with five departments, machines, loading docks and material flow" onPointerDown={e => { if ((e.target as Element).closest('[data-department]')) return; drag.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }; e.currentTarget.setPointerCapture(e.pointerId); }} onPointerMove={e => { if (!drag.current || !svg.current) return; const scale = 820 / svg.current.getBoundingClientRect().width; setPan({ x: drag.current.px + (e.clientX - drag.current.x) * scale, y: drag.current.py + (e.clientY - drag.current.y) * scale }); }} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
      <defs><pattern id={`${id}grid`} width="30" height="18" patternUnits="userSpaceOnUse" patternTransform="skewX(-30)"><path d="M30 0H0V18" fill="none" stroke="#25364b" strokeWidth=".5" /></pattern><filter id={`${id}glow`} x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3" /></filter><marker id={`${id}arrow`} markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6" fill="none" stroke="#59f2ff" strokeWidth="1.4" /></marker><radialGradient id={`${id}ambient`}><stop stopColor="#14344a" stopOpacity=".5"/><stop offset="1" stopColor="#101622" stopOpacity="0"/></radialGradient></defs>
      <rect width="820" height="485" fill={`url(#${id}grid)`} opacity=".35"/><ellipse cx="410" cy="290" rx="350" ry="200" fill={`url(#${id}ambient)`}/>
      <g transform={`translate(${pan.x} ${pan.y}) translate(410 245) scale(${zoom}) translate(-410 -245)`}>
        {box(-8, -8, 306, 269, 7, '#293544', '#121b29')}
        {box(-5, -5, 298, 5, 32, '#7e8c99', '#354555')}{box(288, 0, 5, 249, 32, '#788994', '#384858')}
        {Array.from({ length: 9 }, (_, i) => <g key={i}>{box(288, i * 29, 5, 3, 40, '#a3b0ba', '#485966')}{box(i * 33, -5, 3, 5, 40, '#a3b0ba', '#485966')}</g>)}
        {departments.map(d => <g key={d.id} transform={zoneTransform(d)} data-department={d.id} role="button" tabIndex={0} aria-label={`${d.name}, ${d.area} square meters. Inspect department`} aria-pressed={selected === d.id} onClick={() => onSelect(d.id)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(d.id); } }} className={`factory-zone ${selected === d.id ? 'active-zone' : ''}`}>
          <title>{d.name} · {d.area} m² allocated · {d.required} m² required</title>
          {box(d.x, d.y, d.w, d.h, selected === d.id ? 5 : 2, `${d.dark}`, d.dark, d.color)}
          {d.id === 'ST' && Array.from({ length: 4 }, (_, i) => <g key={i}>{box(20 + i * 22, 23, 13, 54, 22, '#b78043', '#644122')}{[0, 1, 2].map(j => box(21 + i * 22, 25 + j * 16, 11, 12, 26, '#c59a68', '#805f39'))}</g>)}
          {d.id === 'MC' && Array.from({ length: 8 }, (_, i) => <g key={i}>{box(136 + i % 4 * 34, 24 + Math.floor(i / 4) * 34, 23, 22, 15, '#7798b5', '#344c68')}{box(140 + i % 4 * 34, 27 + Math.floor(i / 4) * 34, 12, 10, 23, '#9cb6c9', '#47647d')}<circle cx={p(150 + i % 4 * 34, 42 + Math.floor(i / 4) * 34, 18)[0]} cy={p(150 + i % 4 * 34, 42 + Math.floor(i / 4) * 34, 18)[1]} r="1.7" fill="#67e8f9"/></g>)}
          {d.id === 'AS' && Array.from({ length: 6 }, (_, i) => <g key={i}>{box(137 + i % 3 * 45, 126 + Math.floor(i / 3) * 29, 31, 14, 13, '#aa95d5', '#534176')}{box(147 + i % 3 * 45, 129 + Math.floor(i / 3) * 29, 9, 8, 20, '#d1c5ec', '#786398')}</g>)}
          {d.id === 'PK' && <g>{box(23, 130, 77, 12, 10, '#749e95', '#244f48')}{Array.from({ length: 7 }, (_, i) => box(25 + i * 10, 131, 7, 10, 12, '#bcc8c0', '#46665a'))}{Array.from({ length: 6 }, (_, i) => box(24 + i % 3 * 26, 154 + Math.floor(i / 3) * 14, 17, 11, 11, '#bba17c', '#706045'))}</g>}
          {d.id === 'LG' && Array.from({ length: 6 }, (_, i) => <g key={i}>{box(23 + i * 41, 211, 27, 19, 5, '#77525b', '#42232e')}{box(27 + i * 41, 214, 17, 12, 14, '#c49e79', '#775b43')}</g>)}
          <text x={p(d.x + 5, d.y + d.h - 4, 4)[0]} y={p(d.x + 5, d.y + d.h - 4, 4)[1]} fill={d.color} fontSize="9" fontWeight="600" transform={flat ? undefined : `rotate(27.7 ${p(d.x + 5, d.y + d.h - 4, 4).join(' ')})`}>{d.name} · {d.area} m²</text>
        </g>)}
        {Array.from({ length: 4 }, (_, i) => <g key={i}>{box(14 + i * 72, 250, 39, 5, 16, '#758390', '#344553')}{box(15 + i * 72, 253, 3, 3, 27, '#9ba7af', '#455562')}{box(49 + i * 72, 253, 3, 3, 27, '#9ba7af', '#455562')}</g>)}
        {[30, 146, 222].map((x, i) => <g key={x}>{box(x, 270, 24, 45, 18, i === 1 ? '#c4cbd1' : '#8799aa', '#435466')}{box(x, 316, 24, 17, 15, i === 1 ? '#b5454f' : '#d3d8db', '#596775')}{box(x + 3, 318, 18, 5, 17, '#193d51', '#193d51')}{[275, 306, 322].map(y => box(x - 2, y, 3, 6, 5, '#18202a', '#060b12'))}</g>)}
        {flow && [[0, 1], [1, 2], [2, 3], [3, 4]].map(([from, to], i) => { const source = scenarioZone(departments[from]), target = scenarioZone(departments[to]); const a = p(source.x + source.w * .55, source.y + source.h * .65, 26), b = p(target.x + target.w * .5, target.y + target.h * .5, 26); const path = `M${a} Q${(a[0] + b[0]) / 2} ${(a[1] + b[1]) / 2 - 35} ${b}`; return <g key={i} pointerEvents="none"><path d={path} fill="none" stroke="#00eaff" strokeWidth="7" opacity=".3" filter={`url(#${id}glow)`}/><path d={path} fill="none" stroke="#59f2ff" strokeWidth="1.8" markerEnd={`url(#${id}arrow)`}/><path className="flow-pulse" d={path} fill="none" stroke="#e2ffff" strokeWidth="3" strokeDasharray="3 25"/></g>; })}
        <text x={p(305, 100)[0]} y={p(305, 100)[1]} fill="#60778c" fontSize="9">120 m</text><text x={p(80, -28)[0]} y={p(80, -28)[1]} fill="#60778c" fontSize="9">Production floor · 3,000 m²</text>
      </g>
    </svg><div className="canvas-toolbar"><button className="icon-button" aria-label="Zoom in" onClick={() => setZoom(z => Math.min(2, z + .15))}><ZoomIn size={17}/></button><button className="icon-button" aria-label="Zoom out" onClick={() => setZoom(z => Math.max(.55, z - .15))}><ZoomOut size={17}/></button><button className="icon-button" aria-label="Reset view" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}><Maximize size={16}/></button><span>{Math.round(zoom * 100)}%</span></div><div className="canvas-orientation"><span>N</span><svg viewBox="0 0 40 40"><path d="M20 4V34M20 34L5 25M20 34L35 25" stroke="#547184" fill="none"/><path d="M20 4L17 12H23Z" fill="#00d8e8"/></svg></div></div>
    <div className="factory-bottom"><button className={`flow-toggle ${flow ? 'enabled' : ''}`} aria-pressed={flow} onClick={() => setFlow(!flow)}><Layers size={14}/><span>Flow vectors</span><i/></button><span className="factory-inspection">{active ? `${active.name} · ${active.area} m² allocated / ${active.required} m² required` : <><Move size={12}/> Drag to pan · select a department</>}</span></div>
  </section>;
}
