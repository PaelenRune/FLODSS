import React from 'react';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { renderToStaticMarkup } from 'react-dom/server';
import { buildCockpitData } from '../src/components/cockpit/CockpitDataContext';
import { CockpitOverview } from '../src/components/cockpit/CockpitOverview';
import type { ContinuousLayout, EvaluationReport, FacilityLayoutProblem } from '../src/types/api';

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
const evaluatedMarkup = renderToStaticMarkup(<CockpitOverview problem={problem} layout={{ ...layout, layout_signature: 'first' }} evaluation={evaluation} onOpenWorkspace={() => {}}/>);
assert.match(evaluatedMarkup, /777/);
assert.match(evaluatedMarkup, /888/);

const render = (currentLayout: ContinuousLayout | null) => renderToStaticMarkup(<CockpitOverview problem={problem} layout={currentLayout} evaluation={null} onOpenWorkspace={() => {}}/>);
const markup = render(layout), updated = render(nextLayout);
assert.match(markup, /Actual cutting/);
assert.match(markup, /130/);
assert.match(markup, /Actual solver geometry/);
assert.doesNotMatch(markup, /Illustrative portfolio dataset|3,210\/month saved|Baseline Layout/);
assert.notEqual(markup, updated);
assert.match(render(null), /Awaiting layout/);
console.log('Cockpit bridge: geometry updates, directional flows, live rendering and empty/mismatched layout checks passed.');

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
const factoryMarkup = renderToStaticMarkup(<CockpitOverview problem={factory} layout={factoryLayout} evaluation={null} onOpenWorkspace={() => {}}/>);
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
const denseMarkup = renderToStaticMarkup(<CockpitOverview problem={denseFactory} layout={factoryLayout} evaluation={null} onOpenWorkspace={() => {}}/>);
assert.equal((denseMarkup.match(/class="factory-flow"/g) ?? []).length, 16, 'Dense matrices must not overwhelm the scene');
for (const [width, height] of [[1000, 10], [10, 1000]]) {
  const narrow = { ...factory, facility: { ...factory.facility, width, height } };
  const narrowLayout = { ...factoryLayout, placements: Object.fromEntries(factoryIds.map((id, i) => [id, { department_id: id, x: width / 10 * i, y: 0, width: width / 10, height }])) };
  const narrowMarkup = renderToStaticMarkup(<CockpitOverview problem={narrow} layout={narrowLayout} evaluation={null} onOpenWorkspace={() => {}}/>);
  assert.equal((narrowMarkup.match(/data-department=/g) ?? []).length, 10);
  assert.doesNotMatch(narrowMarkup, /NaN|Infinity/);
}
if (process.env.COCKPIT_VISUAL_HTML) {
  const css = readFileSync('src/components/cockpit/cockpit.css', 'utf8');
  writeFileSync(process.env.COCKPIT_VISUAL_HTML, `<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#0a0d14;color:#e7edf6;font-family:'Segoe UI',sans-serif}*{box-sizing:border-box}button{font-family:inherit}main{padding:24px;max-width:1550px;margin:auto}${css}</style></head><body><main>${factoryMarkup}</main></body></html>`);
}
console.log('Live factory engine: 10-department 12,000 m² shell, extrusions, all equipment types, trucks, curved pulses, flow cap, narrow layouts and analytics panels passed.');
