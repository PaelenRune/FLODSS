import { useId, useRef, useState } from 'react';
import { AlertTriangle, Columns2, Download, Layers, Maximize, Pencil, Sparkles, ZoomIn, ZoomOut } from 'lucide-react';
import { calculateFlowMetrics, getShortDepartmentLabel, localizeBenchmarkText, localizeCockpitDeptName, useCockpitData } from './CockpitDataContext';
import { summarizeLayoutInfeasibility } from '../../utils/explainInfeasibility';
import { useLanguage } from '../../context/LanguageContext';

type Point = [number, number];
type Equipment = 'storage' | 'machine' | 'assembly' | 'packing' | 'shipping';

/** Decoration is inferred from department vocabulary, never substituted for solver geometry. */
function equipmentFor(id: string, name: string): Equipment {
  const value = `${id} ${name}`.toLocaleLowerCase('en');
  if (/shipping|receiving|logistic|sevkiyat|kabul|^lg\b/.test(value)) return 'shipping';
  if (/raw.material|finished.goods|storage|warehouse|depo|hammadde|^st\b/.test(value)) return 'storage';
  if (/machin|cutting|cnc|kesim|talaş|^mc\b/.test(value)) return 'machine';
  if (/packag|surface|paket|yüzey|^pk\b/.test(value)) return 'packing';
  return 'assembly';
}

export function LiveFactoryCanvas({ selected, onSelect }: { selected: string | null; onSelect: (id: string) => void }) {
  const { lang, t } = useLanguage();
  const { departments, flows, problem, layout, evaluation, validation, metrics, swap, scenarios = [], selectedScenario = 0, selectScenario, metricConfig, onCreateSampleLayout, onEditPlan, onDownloadPlanSvg } = useCockpitData();
  const [swapMode, setSwapMode] = useState(false);
  const [compareSideBySide, setCompareSideBySide] = useState(false);
  const selectDepartment = (id: string) => {
    if (swapMode && selected && selected !== id) {
      swap?.(selected, id);
      setSwapMode(false);
    } else {
      onSelect(id);
      setSwapMode(false);
    }
  };
  const [flat, setFlat] = useState(false);
  const [showFlows, setShowFlows] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const id = useId().replace(/:/g, '');
  // Match the uniform scale used by buildCockpitData, including long/narrow facilities.
  const scale = problem ? Math.min(278 / problem.facility.width, 237 / problem.facility.height) : 1;
  const width = (problem?.facility.width ?? 0) * scale;
  const height = (problem?.facility.height ?? 0) * scale;
  const originX = 410 - (width - height) * .61;
  const p = (x: number, y: number, z = 0): Point => flat
    ? [410 - width * .95 + x * 1.9, 48 + y * 1.38]
    : [originX + (x - y) * 1.22, 92 + (x + y) * .64 - z];
  const points = (vertices: Point[]) => vertices.map(v => v.join(',')).join(' ');
  const polygon = (x: number, y: number, w: number, h: number, z = 0) => points([p(x, y, z), p(x + w, y, z), p(x + w, y + h, z), p(x, y + h, z)]);
  const box = (x: number, y: number, w: number, h: number, z: number, top: string, side: string, stroke = '#c7e1ef30', base = 0) => <g>
    {!flat && <>
      <polygon points={points([p(x, y + h, base), p(x + w, y + h, base), p(x + w, y + h, z), p(x, y + h, z)])} fill={side} stroke={stroke} strokeWidth=".55"/>
      <polygon points={points([p(x + w, y, base), p(x + w, y + h, base), p(x + w, y + h, z), p(x + w, y, z)])} fill={side} stroke={stroke} strokeWidth=".55" style={{ filter: 'brightness(.72)' }}/>
    </>}
    <polygon points={polygon(x, y, w, h, z)} fill={top} stroke={stroke} strokeWidth=".7"/>
  </g>;
  const placed = departments.filter(d => d.w > 0 && d.h > 0);
  const sorted = [...placed].sort((a, b) => a.x + a.y + (a.w + a.h) / 2 - b.x - b.y - (b.w + b.h) / 2);
  const allEdges = flows.flatMap((row, from) => row.flatMap((quantity, to) =>
    quantity > 0 && from !== to && departments[from]?.w > 0 && departments[to]?.w > 0
      ? [{ from, to, quantity }] : [])).sort((a, b) => b.quantity - a.quantity);
  const relatedEdges = selected ? allEdges.filter(e => departments[e.from].id === selected || departments[e.to].id === selected) : allEdges;
  const edges = relatedEdges.slice(0, selected ? 12 : 16);
  const maxFlow = allEdges[0]?.quantity ?? 1;
  const active = departments.find(d => d.id === selected);
  const bayCount = Math.max(1, Math.min(4, Math.floor(width / 60)));
  const bayPitch = width / bayCount;
  const bayWidth = Math.min(32, bayPitch * .6);
  const wall = Math.min(3, width / 12, height / 12);
  const columnsX = Math.max(2, Math.ceil(width / 38));
  const columnsY = Math.max(2, Math.ceil(height / 38));

  const equipment = (dept: typeof departments[number], base: number) => {
    const kind = equipmentFor(dept.id, dept.name);
    const inset = Math.min(5, dept.w * .12, dept.h * .12);
    const usableW = dept.w - inset * 2, usableH = dept.h - inset * 2;
    // Bound equipment count for large solver problems; fit even tiny departments without spilling.
    const cols = Math.max(1, Math.min(4, Math.floor(usableW / 23)));
    const rows = Math.max(1, Math.min(3, Math.floor(usableH / 25)));
    const cw = usableW / cols, ch = usableH / rows;
    const rise = Math.min(15, cw * .65, ch * .65);
    return Array.from({ length: cols * rows }, (_, i) => {
      const x = dept.x + inset + (i % cols) * cw;
      const y = dept.y + inset + Math.floor(i / cols) * ch;
      const w = cw * .64, h = ch * .57;
      return <g key={i} className={`factory-equipment equipment-${kind}`} pointerEvents="none">
        {kind === 'storage' ? <>
          {box(x, y, w, h, base + rise, '#9b7148', '#503a2b', '#d5a77980', base)}
          {[.24, .61].map(t => <g key={t}>
            {box(x + w * .08, y + h * .08, w * .84, h * .84, base + rise * t, '#d0a16a', '#86603d', '#ecd2a34d', base + rise * Math.max(0, t - .16))}
            <path d={`M${p(x, y + h, base + rise * t)} L${p(x + w, y + h, base + rise * t)}`} stroke="#e4c08b" strokeWidth="1"/>
          </g>)}
          {[0, 1].map(t => <path key={t} d={`M${p(x + w * t, y + h, base)} L${p(x + w * t, y + h, base + rise + 2)}`} stroke="#b4bfca" strokeWidth="1.3"/>)}
        </> : kind === 'machine' ? <>
          {box(x, y, w, h, base + rise * .7, '#7e9eb9', '#304b63', undefined, base)}
          {box(x + w * .16, y + h * .1, w * .65, h * .5, base + rise, '#b0c5d4', '#536b80', undefined, base + rise * .7)}
          {box(x + w * .28, y + h * .21, w * .38, h * .25, base + rise + .3, '#163347', '#163347')}
          <circle cx={p(x + w * .9, y + h * .85, base + rise * .7)[0]} cy={p(x + w * .9, y + h * .85, base + rise * .7)[1]} r="1.3" fill="#72ffcc"/>
        </> : kind === 'packing' ? <>
          {box(x, y, cw * .87, h * .45, base + rise * .55, '#577d7d', '#294b50', undefined, base)}
          {Array.from({ length: 5 }, (_, n) => <g key={n}>{box(x + n * cw * .17, y, cw * .12, h * .45, base + rise * .58, '#b3c3c2', '#527373', undefined, base + rise * .55)}</g>)}
          {box(x + w * .3, y + h * .57, w * .48, h * .4, base + rise * .8, '#c5aa80', '#7a6040', undefined, base)}
        </> : kind === 'shipping' ? <>
          {box(x, y, w, h, base + rise * .22, '#6e8390', '#344754', undefined, base)}
          {box(x + w * .12, y + h * .15, w * .48, h * .65, base + rise, '#c5a079', '#796044', undefined, base + rise * .22)}
          {box(x + w * .65, y + h * .3, w * .3, h * .5, base + rise * .7, '#b59670', '#6b5038', undefined, base + rise * .22)}
        </> : <>
          {box(x, y, w, h, base + rise * .48, '#9c8cb7', '#4d4167', undefined, base)}
          {box(x + w * .25, y + h * .2, w * .4, h * .55, base + rise * .85, '#c5bcdb', '#796b96', undefined, base + rise * .48)}
          {box(x + w * .76, y + h * .15, w * .1, h * .2, base + rise, '#f0c273', '#9d743c', undefined, base + rise * .48)}
        </>}
      </g>;
    });
  };

  // Reserve projected label rectangles. Small/crowded zones use a numbered badge + full legend.
  const displayDeptName = (d: { id: string; name: string }) => localizeCockpitDeptName(d, true, t);
  const occupied: { x: number; y: number; w: number; h: number }[] = [];
  const labels = placed.map(dept => {
    const index = departments.indexOf(dept) + 1;
    const available = Math.min(145, dept.w * (flat ? 1.9 : 1.38) - 8);
    const compact = available < 48 || dept.h < 18;
    const maxChars = Math.max(4, Math.floor(available / 4.6));
    const fullName = displayDeptName(dept);
    const name = fullName.length > maxChars ? `${fullName.slice(0, maxChars - 1)}…` : fullName;
    const textWidth = Math.max(name.length * 4.6, 45);
    const candidates = [.9, .55, .25].map(fraction => p(dept.x + 3, dept.y + dept.h * fraction, flat ? 0 : 22));
    const position = !compact ? candidates.find(([x, y]) => {
      const rect = { x: x - 3, y: y - 12, w: textWidth * (flat ? 1 : .9) + 7, h: (flat ? 0 : textWidth * .47) + 24 };
      if (occupied.some(r => rect.x < r.x + r.w && rect.x + rect.w > r.x && rect.y < r.y + r.h && rect.y + rect.h > r.y)) return false;
      occupied.push(rect);
      return true;
    }) : undefined;
    return { dept, index, name, position };
  });

  const baselineScenario = scenarios[0] ?? null;
  const optimizedScenario = scenarios.length > 1 ? scenarios[scenarios.length - 1] : null;
  const activeScenario = scenarios.find(s => s.id === selectedScenario) ?? optimizedScenario ?? baselineScenario;
  const isViewingOptimized = Boolean(optimizedScenario && activeScenario && activeScenario.id !== baselineScenario?.id);
  const isSideBySide = compareSideBySide && Boolean(baselineScenario && optimizedScenario && problem);

  const baselineStats = problem && baselineScenario ? calculateFlowMetrics(problem, baselineScenario.layout, metricConfig) : null;
  const optimizedStats = problem && optimizedScenario ? calculateFlowMetrics(problem, optimizedScenario.layout, metricConfig) : null;
  const baselinePlacedCount = baselineScenario ? Object.keys(baselineScenario.layout.placements).length : 0;
  const optPlacedCount = optimizedScenario ? Object.keys(optimizedScenario.layout.placements).length : 0;
  const baselineComplete = Boolean(baselineStats && baselineStats.missingFlows === 0 && baselinePlacedCount >= departments.length);
  const optComplete = Boolean(optimizedStats && optimizedStats.missingFlows === 0 && optPlacedCount >= departments.length);
  const baseFeasible = baselineScenario?.evaluation ? baselineScenario.evaluation.is_feasible : true;
  const optFeasible = optimizedScenario?.evaluation ? optimizedScenario.evaluation.is_feasible : true;
  const bothComparable = baselineComplete && optComplete && baseFeasible && optFeasible;
  const costDeltaPct = bothComparable && baselineStats && optimizedStats && baselineStats.handlingCost > 0
    ? ((optimizedStats.handlingCost - baselineStats.handlingCost) / baselineStats.handlingCost) * 100
    : null;
  const distDeltaPct = bothComparable && baselineStats && optimizedStats && baselineStats.flowDistance > 0
    ? ((optimizedStats.flowDistance - baselineStats.flowDistance) / baselineStats.flowDistance) * 100
    : null;
  const formatChangePhrase = (metricLabel: string, pct: number) => {
    const absStr = Math.abs(pct).toLocaleString(lang === 'tr' ? 'tr-TR' : 'en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    if (pct < -0.05) return t(`${metricLabel} %${absStr} azaldı`, `${metricLabel} -${absStr}%`);
    if (pct > 0.05) return t(`${metricLabel} %${absStr} arttı`, `${metricLabel} +${absStr}%`);
    return t(`${metricLabel} değişmedi`, `${metricLabel} unchanged`);
  };

  const infeasibility = summarizeLayoutInfeasibility(
    problem ?? null,
    layout ?? null,
    validation,
    evaluation,
    metrics?.missingFlows ?? 0,
    t
  );

  const rawScenName = activeScenario?.name ?? '';
  const activePlanTitle = !rawScenName || rawScenName === 'Baseline Layout'
    ? t('İlk yerleşim', 'Baseline layout')
    : rawScenName.startsWith('Solver Layout · ')
      ? rawScenName.slice('Solver Layout · '.length).trim()
      : rawScenName.startsWith('Solver Layout #')
        ? `${t('Optimize edilmiş', 'Optimized')} #${rawScenName.slice('Solver Layout #'.length)}`
        : rawScenName.startsWith('What-If')
          ? t('Senaryo denemesi', 'What-If scenario')
          : rawScenName;
  const feasTag = infeasibility.status === 'partial'
    ? t('Kısmi', 'Partial')
    : infeasibility.status === 'infeasible'
      ? t('Uygun değil', 'Infeasible')
      : t('Uygun', 'Feasible');

  return <section className="cockpit-panel factory-panel live-factory-panel">
    <div className="factory-heading"><div><h2>{t('Fabrika yerleşimi', 'Factory layout')} <span>{t('Gerçek çözücü geometrisi', 'Actual solver geometry')}</span></h2><p>{localizeBenchmarkText(problem?.facility.name, t)} <span className="status-pill">{!layout ? t('Yerleşim bekleniyor', 'Awaiting layout') : `${activePlanTitle} · ${placed.length}/${departments.length} ${t('bölüm', 'depts')} · ${feasTag}`}</span></p></div><div className="canvas-modes"><button aria-pressed={!flat} onClick={() => setFlat(false)}>{t('3B İzometrik', '3D Isometric')}</button><button aria-pressed={flat} onClick={() => setFlat(true)}>{t('2B Üstten', '2D Top-Down')}</button></div></div>
    {baselineScenario && (
      <div className="plan-compare-bar">
        <div className="compare-switch" role="group" aria-label={t('Görünüm seçimi', 'Plan comparison switch')}>
          <button
            type="button"
            aria-pressed={!isSideBySide && !isViewingOptimized}
            onClick={() => { setCompareSideBySide(false); selectScenario?.(baselineScenario.id); }}
          >
            {t('İlk yerleşim', 'Baseline layout')}
          </button>
          <button
            type="button"
            disabled={!optimizedScenario}
            aria-pressed={!isSideBySide && isViewingOptimized}
            onClick={() => { if (optimizedScenario) { setCompareSideBySide(false); selectScenario?.(optimizedScenario.id); } }}
          >
            {t('Optimize edilmiş', 'Optimized')}
          </button>
          <button
            type="button"
            disabled={!optimizedScenario}
            aria-pressed={isSideBySide}
            onClick={() => optimizedScenario && setCompareSideBySide(v => !v)}
          >
            <Columns2 size={12}/> {t('Yan yana', 'Side by side')}
          </button>
        </div>
        {bothComparable && costDeltaPct !== null && distDeltaPct !== null ? (
          <div className={`improvement-pill ${costDeltaPct <= 0 ? 'improved' : 'worsened'}`}>
            <span>{formatChangePhrase(t('Taşıma maliyeti', 'Handling cost'), costDeltaPct)}</span>
            <b>·</b>
            <span>{formatChangePhrase(t('Mesafe', 'Distance'), distDeltaPct)}</span>
          </div>
        ) : optimizedScenario ? (
          <div className="improvement-pill infeasible">
            <span>
              {!optComplete
                ? t(
                    `Karşılaştırılamaz · ${optPlacedCount}/${departments.length} bölüm · ${optimizedStats?.missingFlows ?? 0} akış hesap dışı`,
                    `Not comparable · ${optPlacedCount}/${departments.length} depts · ${optimizedStats?.missingFlows ?? 0} flows excluded`
                  )
                : !baselineComplete
                  ? t(
                      `Karşılaştırılamaz · İlk plan kısmi (${baselinePlacedCount}/${departments.length} bölüm)`,
                      `Not comparable · Baseline partial (${baselinePlacedCount}/${departments.length} depts)`
                    )
                  : !baseFeasible && !optFeasible
                    ? t('Karşılaştırılamaz · İki plan da uygun değil (kısıt veya çakışma ihlali)', 'Not comparable · Both plans are infeasible (constraint or overlap violation)')
                    : !baseFeasible
                      ? t('Karşılaştırılamaz · İlk yerleşim uygun değil (kısıt veya çakışma ihlali); optimize edilmiş plan uygun', 'Not comparable · Baseline is infeasible (constraint or overlap violation); optimized plan is feasible')
                      : t('Karşılaştırılamaz · Optimize edilmiş plan uygun değil (kısıt veya çakışma ihlali)', 'Not comparable · Optimized plan is infeasible (constraint or overlap violation)')}
            </span>
          </div>
        ) : (
          <span className="next-step-hint">
            {t('İyileştirilmiş planı üretip iki sonucu karşılaştırabilirsiniz ("Yerleşimi iyileştir").', 'Run "Improve layout" to generate an optimized plan and compare both results.')}
          </span>
        )}
      </div>
    )}
    {layout && infeasibility.status !== 'feasible' && (
      <div className={`infeasible-warning-banner ${infeasibility.status}`} role="alert">
        <div className="iwb-head">
          <AlertTriangle size={16}/>
          <strong>{infeasibility.headline}</strong>
        </div>
        <p className="iwb-note">{infeasibility.misleadingCostNote}</p>
        {infeasibility.reasons.length > 0 && (
          <ul className="iwb-reasons">
            {infeasibility.reasons.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        )}
        {infeasibility.technicalDetails && (
          <details className="iwb-details">
            <summary>{t('Teknik ihlal ayrıntıları', 'Technical violation details')}</summary>
            <pre>{infeasibility.technicalDetails}</pre>
          </details>
        )}
      </div>
    )}
    {isSideBySide && baselineScenario && optimizedScenario && problem ? (
      <div className="side-by-side-grid">
        {[
          { label: t('İlk yerleşim', 'Baseline layout'), scen: baselineScenario, stats: baselineStats, feasible: baseFeasible },
          { label: t('Optimize edilmiş', 'Optimized'), scen: optimizedScenario, stats: optimizedStats, feasible: optFeasible },
        ].map(({ label, scen, stats, feasible }, idx) => (
          <div key={scen.id} className={`side-by-side-card ${idx === 1 ? 'optimized' : ''}`}>
            <div className="sbs-head">
              <strong>{label}{!feasible && <em className="sbs-infeasible"> · {t('Uygun değil', 'Infeasible')}</em>}</strong>
              {stats && (
                <span>
                  MHC: {stats.handlingCost.toLocaleString(undefined, { maximumFractionDigits: 0 })} · {t('Mesafe', 'Dist')}: {stats.flowDistance.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              )}
            </div>
            <svg viewBox={`0 0 ${problem.facility.width} ${problem.facility.height}`} className="sbs-svg" role="img" aria-label={label}>
              <rect x="0" y="0" width={problem.facility.width} height={problem.facility.height} fill="#0b1220" stroke="#334155" strokeWidth="1"/>
              {departments.map(d => {
                const pl = scen.layout.placements[d.id];
                if (!pl) return null;
                const ry = problem.facility.height - pl.y - pl.height;
                const fullName = localizeCockpitDeptName(d, true, t);
                const shortName = getShortDepartmentLabel(d, t);
                return (
                  <g key={d.id} onClick={() => selectDepartment(d.id)} style={{ cursor: 'pointer' }}>
                    <title>{`${fullName}: ${pl.width.toFixed(1)}×${pl.height.toFixed(1)} m (${(pl.width * pl.height).toFixed(0)} m²)`}</title>
                    <rect x={pl.x} y={ry} width={pl.width} height={pl.height} fill={d.dark} stroke={selected === d.id ? '#ffffff' : d.color} strokeWidth={selected === d.id ? 1.5 : 0.9} fillOpacity="0.88"/>
                    <text x={pl.x + pl.width / 2} y={ry + pl.height / 2} textAnchor="middle" dominantBaseline="middle" fill="#f8fafc" fontSize={Math.max(3.2, Math.min(5.2, pl.height * 0.22))}>
                      {shortName}
                    </text>
                  </g>
                );
              })}
            </svg>
            <div className="sbs-actions">
              {onEditPlan && (
                <button type="button" className="sbs-action-btn" onClick={() => onEditPlan(scen.id)}>
                  <Pencil size={12}/>
                  {t('Bu planı düzenle', 'Edit this plan')}
                </button>
              )}
              {onDownloadPlanSvg && (
                <button type="button" className="sbs-action-btn secondary" onClick={() => onDownloadPlanSvg(scen.id)}>
                  <Download size={12}/>
                  {t('2B planı indir (SVG)', 'Download 2D (SVG)')}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    ) : (
    <div className="factory-stage"><svg viewBox="0 0 820 485" role="img" aria-label={t(`Etkileşimli 3B fabrika: ${localizeBenchmarkText(problem?.name, t)}, ${placed.length} yerleştirilmiş bölüm, yükleme rampaları ve malzeme akışları. Ekipman ve kamyonlar temsilidir.`, `Interactive 3D factory: ${problem?.name}, ${placed.length} placed departments, loading docks and material flows. Equipment and trucks are illustrative.`)} onPointerDown={event => {
      if ((event.target as Element).closest('[data-department]')) return;
      drag.current = { x: event.clientX, y: event.clientY, px: pan.x, py: pan.y }; event.currentTarget.setPointerCapture(event.pointerId);
    }} onPointerMove={event => {
      if (!drag.current) return;
      const factor = 820 / event.currentTarget.getBoundingClientRect().width;
      setPan({ x: drag.current.px + (event.clientX - drag.current.x) * factor, y: drag.current.py + (event.clientY - drag.current.y) * factor });
    }} onPointerUp={() => { drag.current = null; }} onPointerCancel={() => { drag.current = null; }}>
      <defs>
        <pattern id={`${id}grid`} width="32" height="20" patternUnits="userSpaceOnUse" patternTransform="skewX(-30)"><path d="M32 0H0V20" fill="none" stroke="#344c60" strokeWidth=".5"/></pattern>
        <filter id={`${id}glow`} x="-100%" y="-200%" width="300%" height="500%"><feGaussianBlur stdDeviation="3"/></filter>
        <marker id={`${id}arrow`} markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0L6 3L0 6" fill="none" stroke="#8ff5ff" strokeWidth="1.2"/></marker>
        <radialGradient id={`${id}ambient`}><stop stopColor="#14506a" stopOpacity=".35"/><stop offset="1" stopColor="#101622" stopOpacity="0"/></radialGradient>
      </defs>
      <rect width="820" height="485" fill={`url(#${id}grid)`} opacity=".3"/><ellipse cx="410" cy="280" rx="380" ry="210" fill={`url(#${id}ambient)`}/>
      <g transform={`translate(${pan.x} ${pan.y}) translate(410 242) scale(${zoom}) translate(-410 -242)`}>
        <g className="factory-shell">
          {box(-7, -7, width + 14, height + 14, 0, '#293b4b', '#101c2b', '#6e8b9d66', -9)}
          {box(0, 0, width, height, .5, '#243341', '#182534', '#6f879750')}
          {/* The rear walls retain full height; front cutaway walls keep every zone inspectable. */}
          {box(-wall, -wall, width + wall * 2, wall, 29, '#8194a1', '#354d5e')}
          {box(-wall, 0, wall, height, 29, '#8d9da9', '#405767')}
          {Array.from({ length: columnsX + 1 }, (_, i) => <g key={`x${i}`}>{box(i * width / columnsX - wall / 2, -wall, wall, wall * 1.8, 36, '#b1c2cd', '#556f80')}</g>)}
          {Array.from({ length: columnsY + 1 }, (_, i) => <g key={`y${i}`}>{box(-wall, i * height / columnsY, wall * 1.8, wall, 36, '#b1c2cd', '#556f80')}</g>)}
          {Array.from({ length: 9 }, (_, i) => <path key={i} d={`M${p(width * i / 8, 0, 1)} L${p(width * i / 8, height, 1)} M${p(0, height * i / 8, 1)} L${p(width, height * i / 8, 1)}`} stroke="#718b9f" strokeOpacity=".12" strokeWidth=".6"/>)}
        </g>
        {problem?.facility.reserved_zones?.map(zone => {
          const b = zone.bounding_box;
          return <polygon key={zone.id} points={polygon(b.x_min * scale, b.y_min * scale, (b.x_max - b.x_min) * scale, (b.y_max - b.y_min) * scale, 1)} fill="#64748b55" stroke="#94a3b8" strokeDasharray="3 3"><title>{`${zone.type}: ${zone.id}`}</title></polygon>;
        })}
        {sorted.map(d => {
          const base = selected === d.id ? 12 : 7;
          const deptLabel = displayDeptName(d);
          return <g key={d.id} data-department={d.id} className={`factory-zone ${selected === d.id ? 'active-zone' : ''}`} role="button" tabIndex={0} aria-label={t(`${deptLabel}, ${d.area.toFixed(1)} metrekare. ${swapMode ? 'Seçili bölümle yer değiştir' : 'Bölümü incele'}`, `${deptLabel}, ${d.area.toFixed(1)} square meters. ${swapMode ? 'Swap with selected department' : 'Inspect department'}`)} aria-pressed={selected === d.id} onClick={() => selectDepartment(d.id)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); selectDepartment(d.id); } }}>
            <title>{t(`${deptLabel}: ${d.area.toFixed(1)} m² tahsis edilen / ${d.required} m² gerekli. Ekipmanlar temsilidir.`, `${deptLabel}: ${d.area.toFixed(1)} m² allocated / ${d.required} m² required. Equipment illustrative.`)}</title>
            {box(d.x, d.y, d.w, d.h, base, d.dark, d.dark, selected === d.id ? '#edffff' : d.color)}
            <polygon points={polygon(d.x + d.w * .025, d.y + d.h * .025, d.w * .95, d.h * .95, base + .1)} fill={d.color} opacity=".09" pointerEvents="none"/>
            {equipment(d, base)}
          </g>;
        })}
        <g className="factory-docks" pointerEvents="none">
          {box(width, 0, wall, height, 5, '#728a9b', '#354959')}
          {Array.from({ length: bayCount }, (_, i) => {
            const center = bayPitch * (i + .5), x = center - bayWidth / 2;
            const gapStart = bayPitch * i, gapWidth = (bayPitch - bayWidth) / 2;
            const truckW = bayWidth * .68, truckX = center - truckW / 2;
            return <g key={i} data-loading-bay={i + 1}>
              {box(gapStart, height, gapWidth, wall, 10, '#8295a3', '#3e5365')}
              {box(center + bayWidth / 2, height, gapWidth, wall, 10, '#8295a3', '#3e5365')}
              {box(x, height, bayWidth, 6, 3, '#8597a1', '#425868')}
              {box(x, height, Math.min(2, bayWidth * .1), wall, 21, '#c1cdd4', '#526a7a')}
              {box(x + bayWidth - Math.min(2, bayWidth * .1), height, Math.min(2, bayWidth * .1), wall, 21, '#c1cdd4', '#526a7a')}
              {!flat && <g className="factory-truck">
                {box(truckX - 1, height + 9, truckW + 2, 40, 4, '#222d39', '#080f18')}
                {[12, 33, 44].map(offset => <g key={offset}>{box(truckX - 2, height + offset, 3, 5, 5, '#26313c', '#080c13')}{box(truckX + truckW - 1, height + offset, 3, 5, 5, '#26313c', '#080c13')}</g>)}
                {box(truckX, height + 7, truckW, 29, 18, i % 2 ? '#c4cdd4' : '#90a7b8', '#4e667a', '#d3e2ed70', 4)}
                {[.2, .4, .6, .8].map(t => <path key={t} d={`M${p(truckX, height + 7 + 29 * t, 18.1)} L${p(truckX + truckW, height + 7 + 29 * t, 18.1)}`} stroke="#ecf4f7" opacity=".3" strokeWidth=".6"/>)}
                {box(truckX, height + 37, truckW, 12, 14, i % 2 ? '#bd5a61' : '#d3dce1', '#4b6173', undefined, 4)}
                {box(truckX + truckW * .12, height + 39, truckW * .76, 4, 14.5, '#16374c', '#16374c')}
              </g>}
            </g>;
          })}
        </g>
        {showFlows && edges.map(({ from, to, quantity }) => {
          const a = departments[from], b = departments[to];
          const source = p(a.x + a.w / 2, a.y + a.h / 2, 24);
          const target = p(b.x + b.w / 2, b.y + b.h / 2, 24);
          const distance = Math.hypot(source[0] - target[0], source[1] - target[1]);
          const arcHeight = flat ? 8 : Math.min(90, distance * .23);
          const path = `M${source} Q${(source[0] + target[0]) / 2} ${(source[1] + target[1]) / 2 - arcHeight - (flat ? 0 : 35)} ${target}`;
          const intensity = Math.sqrt(quantity / maxFlow);
          return <g key={`${from}-${to}`} className="factory-flow" pointerEvents="none" opacity={.45 + intensity * .55}>
            <title>{`${displayDeptName(a)} → ${displayDeptName(b)}: ${quantity}`}</title>
            <path d={path} fill="none" stroke="#00eaff" strokeWidth={5 + intensity * 3} opacity=".35" filter={`url(#${id}glow)`}/>
            <path d={path} fill="none" stroke="#59eafa" strokeWidth={.9 + intensity * 1.1} markerEnd={`url(#${id}arrow)`}/>
            <path className="flow-pulse" d={path} fill="none" stroke="#e2ffff" strokeWidth="2.2" strokeDasharray="4 24" style={{ animationDelay: `${-from * .23}s` }}/>
            <circle cx={source[0]} cy={source[1]} r="2.4" fill="#a1faff"/>
          </g>;
        })}
        <g className="factory-labels" pointerEvents="none">
          {labels.map(({ dept, index, name, position }) => {
            const anchor = position ?? p(dept.x + dept.w / 2, dept.y + dept.h / 2, 27);
            return <g key={dept.id} transform={`translate(${anchor})${position && !flat ? ' rotate(27.7)' : ''}`}>
              {position ? <text fill={dept.color} fontSize="8.5" fontWeight="600" stroke="#101c2b" strokeWidth="3" paintOrder="stroke" strokeLinejoin="round"><tspan>{name}</tspan><tspan x="0" dy="11" fontSize="7.5" fill="#c8dbe6" fontWeight="400">{dept.area.toLocaleString(undefined, { maximumFractionDigits: 0 })} m²</tspan></text>
                : <><circle r="8" fill="#142334" stroke={dept.color}/><text textAnchor="middle" dy="3" fill="#e8f8ff" fontSize="8">{index}</text></>}
            </g>;
          })}
        </g>
        <text x="410" y="38" textAnchor="middle" fill="#8da7b9" fontSize="9">{problem?.facility.width} × {problem?.facility.height} m · {((problem?.facility.width ?? 0) * (problem?.facility.height ?? 0)).toLocaleString()} m²</text>
      </g>
      {!layout && <text x="410" y="455" textAnchor="middle" fill="#64748b" fontSize="10">{t('Yerleşim oluşturulduğunda 3B plan ve metrikler otomatik hesaplanır', '3D plan and metrics are computed automatically once a layout exists')}</text>}
    </svg>
    {!layout && (
      <div className="empty-canvas-cta">
        <p>{t('Bu problem için henüz yerleşim oluşturulmadı.', 'No layout has been generated for this problem yet.')}</p>
        <button type="button" className="cockpit-btn-primary" onClick={() => onCreateSampleLayout?.()}>
          <Sparkles size={14}/>
          {t('Başlangıç planını oluştur', 'Create baseline layout')}
        </button>
      </div>
    )}
    <div className="canvas-toolbar"><button className="icon-button" aria-label={t('Yakınlaştır', 'Zoom in')} onClick={() => setZoom(z => Math.min(3, z + .15))}><ZoomIn size={17}/></button><button className="icon-button" aria-label={t('Uzaklaştır', 'Zoom out')} onClick={() => setZoom(z => Math.max(.5, z - .15))}><ZoomOut size={17}/></button><button className="icon-button" aria-label={t('Görünümü sıfırla', 'Reset view')} onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}><Maximize size={17}/></button><span>{Math.round(zoom * 100)}%</span></div></div>
    )}
    <div className="live-factory-legend" aria-label={t('Bölüm seçimi ve tahsis edilen alanlar', 'Department selection and allocated areas')}>{placed.map(d => <button key={d.id} aria-pressed={selected === d.id} onClick={() => selectDepartment(d.id)} title={`${displayDeptName(d)}: ${d.area.toFixed(1)} / ${d.required} m²`}><i style={{ background: d.color }}>{departments.indexOf(d) + 1}</i><span>{displayDeptName(d)}</span><small>{d.area.toLocaleString(undefined, { maximumFractionDigits: 0 })} m²</small></button>)}</div>
    {active && swap && <div className="factory-bottom"><button className={`flow-toggle ${swapMode ? 'enabled' : ''}`} aria-pressed={swapMode} disabled={placed.length < 2} onClick={() => setSwapMode(value => !value)}>{swapMode ? t('Değişimi iptal et', 'Cancel swap') : t('Yer değiştir…', 'Swap with…')}</button><span className="factory-inspection" role="status">{swapMode ? t(`Ağırlık merkezlerini ${displayDeptName(active)} ile değiştirmek için başka bir bölüm seçin.`, `Choose another department to swap centroids with ${displayDeptName(active)}.`) : t('Senaryo denemesi: boyutlar korunur; uygunluk henüz doğrulanmadı.', 'What-If: dimensions preserved; feasibility not yet validated.')}</span></div>}
    <div className="factory-bottom"><button className={`flow-toggle ${showFlows ? 'enabled' : ''}`} aria-pressed={showFlows} onClick={() => setShowFlows(value => !value)}><Layers size={14}/>{t('Akış vektörleri', 'Flow vectors')}<i/></button><span className="factory-inspection">{active ? `${displayDeptName(active)}: ${active.area.toFixed(1)} / ${active.required} m²` : metrics && metrics.missingFlows > 0 ? t(`${placed.length}/${departments.length} yerleştirildi · ${metrics.missingFlows} akış hesap dışı · ${edges.length} çizildi`, `${placed.length}/${departments.length} placed · ${metrics.missingFlows} flows excluded · ${edges.length} drawn`) : t(`${placed.length}/${departments.length} yerleştirildi · ${edges.length}/${allEdges.length} akış çizildi (tümü maliyette) · temsili ekipman`, `${placed.length}/${departments.length} placed · ${edges.length}/${allEdges.length} flows drawn (all in cost) · illustrative equipment`)}</span></div>
  </section>;
}
