import { useState } from 'react';
import type { ContinuousLayout, EvaluationReport, FacilityLayoutProblem } from '../../types/api';

export interface LiveScenario {
  id: number;
  name: string;
  layout: ContinuousLayout;
  evaluation: EvaluationReport | null;
}

export const geometryKey = (layout: ContinuousLayout) => JSON.stringify(layout.placements);

/** Exchange centroids, preserving each department's dimensions and identity. */
export function swapDepartments(layout: ContinuousLayout, first: string, second: string): ContinuousLayout {
  const a = layout.placements[first], b = layout.placements[second];
  if (!a || !b || first === second) return layout;
  return {
    ...layout, id: undefined, layout_signature: undefined, bounding_box: undefined,
    name: `What-If: ${first} ↔ ${second}`,
    placements: {
      ...layout.placements,
      [first]: { ...a, x: b.x + b.width / 2 - a.width / 2, y: b.y + b.height / 2 - a.height / 2 },
      [second]: { ...b, x: a.x + a.width / 2 - b.width / 2, y: a.y + a.height / 2 - b.height / 2 },
    },
  };
}

export function useCockpitScenarios(problem: FacilityLayoutProblem | null, incoming: ContinuousLayout | null, evaluation: EvaluationReport | null) {
  const problemKey = JSON.stringify(problem);
  const valid = incoming && problem && (!incoming.problem_id || incoming.problem_id === problem.id) ? incoming : null;
  const sourceKey = valid ? geometryKey(valid) : '';
  const [state, setState] = useState({ problemKey, sourceKey: '', scenarios: [] as LiveScenario[], selected: 0 });
  let current = state;
  if (state.problemKey !== problemKey) current = { problemKey, sourceKey: '', scenarios: [], selected: 0 };
  if (valid && current.sourceKey !== sourceKey) {
    const id = current.scenarios.length;
    current = { ...current, sourceKey, selected: id, scenarios: [...current.scenarios, {
      id, name: id === 0 ? 'Baseline Layout' : `Solver Layout · ${evaluation?.algorithm_name || valid.name || id}`,
      layout: structuredClone(valid), evaluation: null,
    }] };
  }
  if (valid?.layout_signature && evaluation?.layout_signature === valid.layout_signature && evaluation.problem_id === problem?.id) {
    const changed = current.scenarios.some(s => geometryKey(s.layout) === sourceKey && s.evaluation !== evaluation);
    if (changed) current = { ...current, scenarios: current.scenarios.map(s => geometryKey(s.layout) === sourceKey ? { ...s, layout: valid, evaluation } : s) };
  }
  if (current !== state) setState(current);
  // Only the unmodified incoming geometry may receive its backend report.
  const scenarios = current.scenarios.map(s => ({ ...s, evaluation:
    valid && geometryKey(s.layout) === sourceKey && valid.layout_signature && valid.layout_signature === evaluation?.layout_signature && evaluation.problem_id === problem?.id
      ? evaluation : s.evaluation,
    layout: valid && geometryKey(s.layout) === sourceKey ? valid : s.layout,
  }));
  return {
    scenarios, selected: current.selected,
    select: (selected: number) => setState(s => s.scenarios.some(item => item.id === selected) ? { ...s, selected } : s),
    swap: (first: string, second: string) => setState(s => {
      const active = s.scenarios.find(item => item.id === s.selected);
      if (!active) return s;
      const layout = swapDepartments(active.layout, first, second);
      if (layout === active.layout) return s;
      const id = s.scenarios.length;
      return { ...s, selected: id, scenarios: [...s.scenarios, { id, name: `What-If Modified Layout · ${id}: ${first} ↔ ${second}`, layout, evaluation: null }] };
    }),
  };
}

export type CockpitScenarios = ReturnType<typeof useCockpitScenarios>;
