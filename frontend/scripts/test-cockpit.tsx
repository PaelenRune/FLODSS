import React from 'react';
import assert from 'node:assert/strict';
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
