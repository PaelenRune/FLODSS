import React from 'react';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { buildCockpitData, calculateFlowMetrics, percentageDelta } from '../src/components/cockpit/CockpitDataContext';
import { swapDepartments } from '../src/components/cockpit/liveScenarios';
import { buildQuickSvgDocument, CockpitOverview } from '../src/components/cockpit/CockpitOverview';
import { LanguageProvider } from '../src/context/LanguageContext';
import { summarizeSolverError } from '../src/utils/explainInfeasibility';
import type { ContinuousLayout, EvaluationReport, FacilityLayoutProblem, LayoutValidationResult } from '../src/types/api';

const problem: FacilityLayoutProblem = {
  id: 'live-test', name: 'Live integration fixture',
  facility: { id: 'f', name: 'Test facility', width: 100, height: 50, area: 5000 },
  departments: [
    { id: 'A', name: 'Actual cutting', required_area: 100 },
    { id: 'B', name: 'Actual packing', required_area: 200 },
  ],
  flows: [
    { source_department: 'A', target_department: 'B', quantity: 123, unit: 'units' },
    { source_department: 'A', target_department: 'B', quantity: 7, unit: 'units' },
  ], relationships: [], constraints: [],
};
const layout: ContinuousLayout = {
  problem_id: problem.id, representation_type: 'continuous', facility_width: 100, facility_height: 50,
  placements: {
    A: { department_id: 'A', x: 0, y: 0, width: 10, height: 10 },
    B: { department_id: 'B', x: 20, y: 0, width: 20, height: 10 },
  },
};
const first = buildCockpitData(problem, layout, null);
assert.equal(first.live, true);
assert.equal(first.departments[0].area, 100);
assert.equal(first.departments[0].share, 2);
assert.equal(first.flows[0][1], 130);
assert.equal(first.flows[1][0], 0);
const nextLayout = { ...layout, placements: { ...layout.placements, A: { ...layout.placements.A, x: 50, width: 20 } } };
const next = buildCockpitData(problem, nextLayout, null);
assert.notEqual(first.departments[0].x, next.departments[0].x);
assert.equal(next.departments[0].area, 200);
assert.equal(buildCockpitData(problem, { ...layout, problem_id: 'wrong-problem' }, null).layout, null);
assert.equal(buildCockpitData(problem, null, null).departments[0].area, 0);
assert.equal(buildCockpitData(null, null, null).live, false);
const evaluation = { problem_id: problem.id, layout_signature: 'first', algorithm_name: 'GA', is_feasible: true, flow_distance: 777, material_handling_cost: 888 } as EvaluationReport;
assert.equal(buildCockpitData(problem, { ...layout, layout_signature: 'first' }, evaluation).evaluation, evaluation);
assert.equal(buildCockpitData(problem, { ...layout, layout_signature: 'second' }, evaluation).evaluation, null);
const evaluatedMarkup = renderToStaticMarkup(
  <LanguageProvider initialLang="en">
    <CockpitOverview problem={problem} layout={{ ...layout, layout_signature: 'first' }} evaluation={evaluation} onOpenWorkspace={() => {}}/>
  </LanguageProvider>
);
assert.match(evaluatedMarkup, /777/);
assert.match(evaluatedMarkup, /888/);

const render = (currentLayout: ContinuousLayout | null, initialLang: 'tr' | 'en' = 'en') =>
  renderToStaticMarkup(
    <LanguageProvider initialLang={initialLang}>
      <CockpitOverview problem={problem} layout={currentLayout} evaluation={null} onOpenWorkspace={() => {}}/>
    </LanguageProvider>
  );
const markup = render(layout), updated = render(nextLayout);
assert.match(markup, /Actual cutting/);
assert.match(markup, /130/);
assert.match(markup, /Actual solver geometry/);
assert.doesNotMatch(markup, /Illustrative portfolio dataset|3,210\/month saved/);
assert.match(markup, /Baseline Layout/);
assert.ok(markup.includes((3250).toLocaleString(undefined, { maximumFractionDigits: 2 })));
assert.match(markup, /0% vs Baseline/);
assert.notEqual(markup, updated);
assert.match(render(null), /Awaiting layout/);
const trMarkup = render(layout, 'tr');
assert.match(trMarkup, /Tesis Yerleşim/);
assert.match(trMarkup, /Gerçek çözücü geometrisi/);
assert.match(trMarkup, /İlk yerleşim/);
assert.match(trMarkup, /2B Üstten/);
assert.doesNotMatch(trMarkup, /NaN|Infinity/);
const emptyTrMarkup = render(null, 'tr');
assert.match(emptyTrMarkup, /Yerleşim bekleniyor/);
assert.match(emptyTrMarkup, /Başlangıç planını oluştur/);
assert.match(emptyTrMarkup, /Yerleşim oluşturulunca hesaplanır/);
const commandBarMarkup = renderToStaticMarkup(
  <LanguageProvider initialLang="tr">
    <CockpitOverview
      problem={problem}
      layout={layout}
      evaluation={null}
      onQuickSolve={() => {}}
      onOpenWorkspace={() => {}}
    />
  </LanguageProvider>
);
assert.match(commandBarMarkup, /Yerleşimi iyileştir/);
assert.match(commandBarMarkup, /İyileştirilmiş planı üretip iki sonucu karşılaştırabilirsiniz/);
assert.match(commandBarMarkup, /2B planı indir \(SVG · İlk yerleşim\)/);
assert.match(commandBarMarkup, /akış çizildi \(tümü maliyette\)/);
const partialLayout: ContinuousLayout = {
  ...layout,
  placements: { A: layout.placements.A },
};
const partialMarkup = renderToStaticMarkup(
  <LanguageProvider initialLang="tr">
    <CockpitOverview problem={problem} layout={partialLayout} evaluation={null} onOpenWorkspace={() => {}}/>
  </LanguageProvider>
);
assert.match(partialMarkup, /<strong>Kısmi<\/strong>/);
assert.match(partialMarkup, /Eksik yerleşim — gerçek çözüm değildir/);
assert.match(partialMarkup, /yanıltıcıdır/);
assert.match(partialMarkup, /akış hesap dışı/);
assert.doesNotMatch(partialMarkup, /<strong>-\d+%/);
assert.doesNotMatch(partialMarkup, /İlk yerleşime göre/);
const badValidation: LayoutValidationResult = {
  is_valid: false,
  errors: [
    "Overlap detected between department 'A' and 'B'.",
    "Department 'A' aspect ratio (10.00) exceeds max_aspect_ratio (2.00).",
  ],
  warnings: [],
  total_overlap_area: 25,
  checked_departments: ['A', 'B'],
  metrics: { occupied_area: 300, free_area: 4700, utilization_ratio: 0.06, total_overlap_area: 25, bounding_envelope_area: 300, compactness: 1 },
  signature: 'bad-sig',
};
const infeasibleMarkup = renderToStaticMarkup(
  <LanguageProvider initialLang="tr">
    <CockpitOverview problem={problem} layout={{ ...layout, layout_signature: 'bad-sig' }} evaluation={null} validation={badValidation} onOpenWorkspace={() => {}}/>
  </LanguageProvider>
);
assert.match(infeasibleMarkup, /Geçersiz çözüm — gerçekte uygulanamaz/);
assert.match(infeasibleMarkup, /yanıltıcıdır/);
assert.match(infeasibleMarkup, /bölüm çakışması/);
assert.match(infeasibleMarkup, /en-boy oranı kısıtı/);
assert.match(summarizeSolverError('Overlap detected between DEP_A and DEP_B', (tr, _en) => tr), /çakışan bölümler/);
const adaptiveLayout: ContinuousLayout = {
  ...layout,
  name: 'Adaptive Strategy Engine',
  layout_signature: 'adaptive-sig',
};
const adaptiveEval = {
  problem_id: problem.id,
  layout_signature: 'adaptive-sig',
  algorithm_name: 'Adaptive Strategy Engine',
  is_feasible: true,
  objective_values: { material_handling_cost: 104255.72, flow_distance: 91616.4 },
} as unknown as EvaluationReport;
const adaptiveMarkup = renderToStaticMarkup(
  <LanguageProvider initialLang="tr">
    <CockpitOverview problem={problem} layout={adaptiveLayout} evaluation={adaptiveEval} onOpenWorkspace={() => {}}/>
  </LanguageProvider>
);
assert.match(adaptiveMarkup, /Adaptive Strategy Engine · 2\/2 bölüm · Uygun/);
assert.match(adaptiveMarkup, /104[.,]255[.,]72/);
const svgOutput = buildQuickSvgDocument(problem, layout, problem.departments, (tr, _en) => tr);
assert.ok(svgOutput.startsWith('<?xml version="1.0"') && svgOutput.includes('<svg') && svgOutput.includes('</svg>') && svgOutput.length > 300);
const benchmarkSample: FacilityLayoutProblem = {
  ...problem,
  id: 'FLP_INDUSTRIAL_10',
  name: 'Precision Machinery Manufacturing Plant (10 Departments)',
  facility: { ...problem.facility, name: 'Heavy Equipment Advanced Production Hall' },
  departments: [
    { ...problem.departments[0], id: 'DEP_RAW_MATERIAL', name: 'Raw Material Warehouse & Sheet Storage' },
    { ...problem.departments[1], id: 'DEP_CUTTING', name: 'Laser Cutting & Sawing Cell' },
  ],
};
const benchmarkLayout: ContinuousLayout = {
  ...layout,
  problem_id: 'FLP_INDUSTRIAL_10',
  placements: {
    DEP_RAW_MATERIAL: { ...layout.placements.A, department_id: 'DEP_RAW_MATERIAL' },
    DEP_CUTTING: { ...layout.placements.B, department_id: 'DEP_CUTTING' },
  },
};
const trBenchmarkMarkup = renderToStaticMarkup(
  <LanguageProvider initialLang="tr">
    <CockpitOverview problem={benchmarkSample} layout={benchmarkLayout} evaluation={null} onOpenWorkspace={() => {}}/>
  </LanguageProvider>
);
assert.match(trBenchmarkMarkup, /Hassas Makine Üretim Tesisi \(10 Bölüm\)/);
assert.match(trBenchmarkMarkup, /Ağır Makine İleri Üretim Holü/);
assert.match(trBenchmarkMarkup, /Hammadde Deposu ve Sac Stoklama/);
assert.doesNotMatch(trBenchmarkMarkup, /Raw Material Warehouse/);
const enBenchmarkMarkup = renderToStaticMarkup(
  <LanguageProvider initialLang="en">
    <CockpitOverview problem={benchmarkSample} layout={benchmarkLayout} evaluation={null} onOpenWorkspace={() => {}}/>
  </LanguageProvider>
);
assert.match(enBenchmarkMarkup, /Precision Machinery Manufacturing Plant \(10 Departments\)/);
assert.match(enBenchmarkMarkup, /Raw Material Warehouse &amp; Sheet Storage/);
console.log('Cockpit bridge: geometry updates, directional flows, live rendering and empty/mismatched layout checks passed.');

const diagonal = { ...layout, layout_signature: 'original', placements: { ...layout.placements, B: { ...layout.placements.B, x: 20, y: 40 } } };
const weighted = { ...problem, flows: [
  { ...problem.flows[0], quantity: 2, cost_per_unit_distance: 3 },
  { ...problem.flows[0], source_department: 'B', target_department: 'A', quantity: 4 },
] };
const distances = calculateFlowMetrics(weighted, diagonal);
assert.equal(distances.manhattanDistance, 390);
assert.equal(distances.euclideanDistance, 6 * Math.hypot(25, 40));
assert.equal(distances.manhattanCost, 650);
assert.equal(calculateFlowMetrics(weighted, diagonal, { distance_metric: 'euclidean', default_cost_per_unit_distance: 2 }).handlingCost, 14 * Math.hypot(25, 40));
const swapped = swapDepartments(diagonal, 'A', 'B');
assert.equal(swapped.placements.A.x + swapped.placements.A.width / 2, 30);
assert.equal(swapped.placements.B.x + swapped.placements.B.width / 2, 5);
assert.equal(swapped.placements.A.width, diagonal.placements.A.width);
assert.equal(diagonal.placements.A.x, 0, 'Baseline must remain immutable');
assert.equal(swapped.layout_signature, undefined);
assert.equal(buildCockpitData(problem, swapped, evaluation).evaluation, null);
assert.equal(swapDepartments(diagonal, 'A', 'unknown'), diagonal);
assert.equal(calculateFlowMetrics(problem, null).missingFlows, 2);
assert.equal(percentageDelta(72, 100), '-28%');
assert.equal(percentageDelta(0, 0), '0%');
assert.equal(percentageDelta(1, 0), 'new (zero baseline)');
const thirdProblem = { ...problem, departments: [...problem.departments, { id: 'C', name: 'Assembly', required_area: 100 }], flows: [{ ...problem.flows[0], target_department: 'C' }] };
const thirdLayout = { ...diagonal, placements: { ...diagonal.placements, C: { department_id: 'C', x: 60, y: 0, width: 10, height: 10 } } };
assert.notEqual(calculateFlowMetrics(thirdProblem, thirdLayout).handlingCost, calculateFlowMetrics(thirdProblem, swapDepartments(thirdLayout, 'A', 'B')).handlingCost);
console.log('Instant metrics: both distances, directional/unit costs, partial layouts, immutable centroid swaps, stale evaluation rejection and zero-baseline deltas passed.');

// The reference mock-up must not be richer than an actual 12,000 m² solver result.
const factoryIds = ['DEP_RAW_MATERIAL', 'DEP_CUTTING', 'DEP_MACHINING', 'DEP_WELDING', 'DEP_ASSEMBLY', 'DEP_SURFACE_TREAT', 'DEP_PACKAGING', 'DEP_FINISHED_GOODS', 'DEP_SHIPPING', 'DEP_RECEIVING'];
const factoryNames = ['Raw material warehouse', 'Cutting', 'CNC machining', 'Welding', 'Assembly', 'Surface treatment', 'Packaging', 'Finished goods', 'Shipping', 'Receiving'];
const factory: FacilityLayoutProblem = {
  ...problem, id: 'factory-12000', name: '12,000 m² production plant',
  facility: { id: 'production', name: '10-department production plant', width: 120, height: 100, area: 12000 },
  departments: factoryIds.map((id, i) => ({ id, name: factoryNames[i], required_area: 1000 })),
  flows: factoryIds.slice(0, -1).map((source_department, i) => ({ source_department, target_department: factoryIds[i + 1], quantity: 1000 - i * 75, unit: 'units/day' })),
};
const factoryLayout: ContinuousLayout = {
  problem_id: factory.id, representation_type: 'continuous', facility_width: 120, facility_height: 100,
  placements: Object.fromEntries(factoryIds.map((id, i) => [id, { department_id: id, x: i % 5 * 24, y: Math.floor(i / 5) * 50, width: 24, height: 50 }])),
};
const factoryMarkup = renderToStaticMarkup(
  <LanguageProvider initialLang="en">
    <CockpitOverview problem={factory} layout={factoryLayout} evaluation={null} onOpenWorkspace={() => {}}/>
  </LanguageProvider>
);
assert.equal((factoryMarkup.match(/data-department=/g) ?? []).length, 10);
assert.equal((factoryMarkup.match(/class="factory-flow"/g) ?? []).length, 9);
assert.equal((factoryMarkup.match(/class="factory-truck"/g) ?? []).length, 4);
for (const kind of ['storage', 'machine', 'assembly', 'packing', 'shipping']) assert.match(factoryMarkup, new RegExp(`equipment-${kind}`));
assert.match(factoryMarkup, /factory-shell/);
assert.match(factoryMarkup, /factory-docks/);
assert.match(factoryMarkup, /stroke-dasharray="4 24"/);
assert.match(factoryMarkup, /cockpit-analytics/);
assert.match(factoryMarkup, /cockpit-secondary/);
assert.doesNotMatch(factoryMarkup, /NaN|Infinity/);

const denseFactory = { ...factory, flows: factoryIds.flatMap(source_department => factoryIds.filter(id => id !== source_department).map(target_department => ({ source_department, target_department, quantity: 100, unit: 'units/day' }))) };
const denseMarkup = renderToStaticMarkup(
  <LanguageProvider initialLang="en">
    <CockpitOverview problem={denseFactory} layout={factoryLayout} evaluation={null} onOpenWorkspace={() => {}}/>
  </LanguageProvider>
);
assert.equal((denseMarkup.match(/class="factory-flow"/g) ?? []).length, 16, 'Dense matrices must not overwhelm the scene');
for (const [width, height] of [[1000, 10], [10, 1000]]) {
  const narrow = { ...factory, facility: { ...factory.facility, width, height } };
  const narrowLayout = { ...factoryLayout, placements: Object.fromEntries(factoryIds.map((id, i) => [id, { department_id: id, x: width / 10 * i, y: 0, width: width / 10, height }])) };
  const narrowMarkup = renderToStaticMarkup(
    <LanguageProvider initialLang="en">
      <CockpitOverview problem={narrow} layout={narrowLayout} evaluation={null} onOpenWorkspace={() => {}}/>
    </LanguageProvider>
  );
  assert.equal((narrowMarkup.match(/data-department=/g) ?? []).length, 10);
  assert.doesNotMatch(narrowMarkup, /NaN|Infinity/);
}
if (process.env.COCKPIT_VISUAL_HTML) {
  const css = readFileSync('src/components/cockpit/cockpit.css', 'utf8');
  writeFileSync(process.env.COCKPIT_VISUAL_HTML, `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#0a0d14;color:#e7edf6;font-family:'Segoe UI',sans-serif}*{box-sizing:border-box}button{font-family:inherit}main{padding:24px;max-width:1550px;margin:auto}${css}</style></head><body><main>${factoryMarkup}</main></body></html>`);
}
console.log('Live factory engine: 10-department 12,000 m² shell, extrusions, all equipment types, trucks, curved pulses, flow cap, narrow layouts and analytics panels passed.');
