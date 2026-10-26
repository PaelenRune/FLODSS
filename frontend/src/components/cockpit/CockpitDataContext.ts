import { createContext, useContext } from 'react';
import type { ContinuousLayout, EvaluationReport, FacilityLayoutProblem } from '../../types/api';
import { departments, flows } from './data';

export interface CockpitData {
  departments: typeof departments;
  flows: number[][];
  live: boolean;
  problem?: FacilityLayoutProblem;
  layout?: ContinuousLayout | null;
  evaluation?: EvaluationReport | null;
}

export const referenceData: CockpitData = { departments, flows, live: false };
export const CockpitDataContext = createContext<CockpitData>(referenceData);
export const useCockpitData = () => useContext(CockpitDataContext);

/** Use one uniform display scale and never invent missing solver placements. */
export function buildCockpitData(problem: FacilityLayoutProblem | null, layout: ContinuousLayout | null, evaluation: EvaluationReport | null): CockpitData {
  if (!problem) return referenceData;
  const matchingLayout = layout && (!layout.problem_id || layout.problem_id === problem.id) ? layout : null;
  const scale = Math.min(278 / problem.facility.width, 237 / problem.facility.height);
  const area = problem.facility.width * problem.facility.height;
  const liveDepartments = problem.departments.map((dept, i) => {
    const placement = matchingLayout?.placements[dept.id];
    const allocated = placement ? placement.width * placement.height : 0;
    return {
      ...departments[i % departments.length], id: dept.id, name: dept.name,
      area: allocated, required: dept.required_area, share: area > 0 ? allocated / area * 100 : 0,
      x: placement ? placement.x * scale : 0, y: placement ? placement.y * scale : 0,
      w: placement ? placement.width * scale : 0, h: placement ? placement.height * scale : 0,
    };
  });
  const indices = new Map(problem.departments.map((dept, i) => [dept.id, i]));
  const matrix = liveDepartments.map(() => liveDepartments.map(() => 0));
  for (const flow of problem.flows) {
    const from = indices.get(flow.source_department), to = indices.get(flow.target_department);
    if (from !== undefined && to !== undefined) matrix[from][to] += flow.quantity;
  }
  const matchingEvaluation = matchingLayout && evaluation?.problem_id === problem.id
    && (!matchingLayout.layout_signature || matchingLayout.layout_signature === evaluation.layout_signature)
    ? evaluation : null;
  return { departments: liveDepartments, flows: matrix, live: true, problem, layout: matchingLayout, evaluation: matchingEvaluation };
}
