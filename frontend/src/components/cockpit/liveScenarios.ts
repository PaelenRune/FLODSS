import { useState } from 'react';
import type { ContinuousLayout, EvaluationReport, FacilityLayoutProblem, LayoutValidationResult } from '../../types/api';

export interface LiveScenario {
  id: number;
  name: string;
  layout: ContinuousLayout;
  evaluation: EvaluationReport | null;
  validation?: LayoutValidationResult | null;
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

const cleanAlgoName = (raw?: string | null) => {
  const s = (raw ?? '').trim();
  if (!s || /^continuous(_layout)?$/i.test(s)) return '';
  return s;
};

export function useCockpitScenarios(
  problem: FacilityLayoutProblem | null,
  incoming: ContinuousLayout | null,
  evaluation: EvaluationReport | null,
  algorithmLabel?: string | null,
  validation?: LayoutValidationResult | null
) {
  const problemKey = JSON.stringify(problem);
  const valid = incoming && problem && (!incoming.problem_id || incoming.problem_id === problem.id) ? incoming : null;
  const sourceKey = valid ? geometryKey(valid) : '';
  const [state, setState] = useState({ problemKey, sourceKey: '', scenarios: [] as LiveScenario[], selected: 0 });
  let current = state;
  if (state.problemKey !== problemKey) current = { problemKey, sourceKey: '', scenarios: [], selected: 0 };
  if (valid && current.sourceKey !== sourceKey) {
    const id = current.scenarios.length;
    const solverTag = cleanAlgoName(algorithmLabel) || cleanAlgoName(evaluation?.algorithm_name) || cleanAlgoName(valid.name);
    const isSampleBaseline = !solverTag || /^(örnek başlangıç yerleşimi|sample reference layout)$/i.test(solverTag);
    const scenarioName = id === 0
      ? (!isSampleBaseline ? `Solver Layout · ${solverTag}` : 'Baseline Layout')
      : (solverTag ? `Solver Layout · ${solverTag}` : `Solver Layout #${id}`);
    current = { ...current, sourceKey, selected: id, scenarios: [...current.scenarios, {
      id, name: scenarioName,
      layout: structuredClone(valid), evaluation: null, validation: null,
    }] };
  }
  const matchingEval = Boolean(
    valid?.layout_signature &&
    evaluation?.layout_signature === valid.layout_signature &&
    evaluation.problem_id === problem?.id
  );
  const matchingVal = Boolean(
    valid &&
    validation &&
    (!validation.signature || !valid.layout_signature || validation.signature === valid.layout_signature)
  );
  if (matchingEval || matchingVal) {
    const changed = current.scenarios.some(s =>
      geometryKey(s.layout) === sourceKey &&
      ((matchingEval && s.evaluation !== evaluation) || (matchingVal && s.validation !== validation))
    );
    if (changed) {
      const evAlgo = cleanAlgoName(evaluation?.algorithm_name);
      current = {
        ...current,
        scenarios: current.scenarios.map(s => geometryKey(s.layout) === sourceKey ? {
          ...s,
          name: matchingEval && evAlgo && (s.name === 'Baseline Layout' || s.name.startsWith('Solver Layout #'))
            ? `Solver Layout · ${evAlgo}`
            : s.name,
          layout: valid!,
          evaluation: matchingEval ? evaluation : s.evaluation,
          validation: matchingVal ? validation : s.validation,
        } : s),
      };
    }
  }
  if (current !== state) setState(current);
  // Only the unmodified incoming geometry may receive its backend report.
  const scenarios = current.scenarios.map(s => ({
    ...s,
    evaluation:
      valid && geometryKey(s.layout) === sourceKey && valid.layout_signature && valid.layout_signature === evaluation?.layout_signature && evaluation.problem_id === problem?.id
        ? evaluation : s.evaluation,
    validation:
      valid && geometryKey(s.layout) === sourceKey && matchingVal
        ? validation : s.validation,
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
