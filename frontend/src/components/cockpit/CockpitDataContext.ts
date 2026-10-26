import { createContext, useContext } from 'react';
import type { ContinuousLayout, EvaluationReport, FacilityLayoutProblem } from '../../types/api';
import { departments, flows } from './data';
import type { LiveScenario } from './liveScenarios';

export interface FlowMetrics {
  euclideanDistance: number;
  manhattanDistance: number;
  euclideanCost: number;
  manhattanCost: number;
  flowDistance: number;
  handlingCost: number;
  metric: string;
  missingFlows: number;
}

/** Directed flows are counted once per record, in physical (not display) units. */
export function calculateFlowMetrics(problem: FacilityLayoutProblem, layout: ContinuousLayout | null, config = problem.objective_config ?? {}): FlowMetrics {
  let euclideanDistance = 0, manhattanDistance = 0, euclideanCost = 0, manhattanCost = 0, missingFlows = 0;
  const defaultCost = Number.isFinite(config.default_cost_per_unit_distance) ? config.default_cost_per_unit_distance : 1;
  for (const flow of problem.flows) {
    const a = layout?.placements[flow.source_department], b = layout?.placements[flow.target_department];
    if (!a || !b) { if (flow.quantity !== 0) missingFlows++; continue; }
    const dx = a.x + a.width / 2 - b.x - b.width / 2;
    const dy = a.y + a.height / 2 - b.y - b.height / 2;
    const euclidean = Math.hypot(dx, dy) * flow.quantity;
    const manhattan = (Math.abs(dx) + Math.abs(dy)) * flow.quantity;
    const cost = flow.cost_per_unit_distance ?? defaultCost;
    euclideanDistance += euclidean; manhattanDistance += manhattan;
    euclideanCost += euclidean * cost; manhattanCost += manhattan * cost;
  }
  const metric = String(config.distance_metric ?? 'manhattan');
  const euclidean = metric === 'euclidean';
  return { euclideanDistance, manhattanDistance, euclideanCost, manhattanCost, metric,
    flowDistance: euclidean ? euclideanDistance : manhattanDistance,
    handlingCost: euclidean ? euclideanCost : manhattanCost, missingFlows };
}

export function percentageDelta(value: number, baseline: number): string {
  if (baseline === 0) return value === 0 ? '0%' : 'new (zero baseline)';
  const delta = (value - baseline) / Math.abs(baseline) * 100;
  return `${delta > 0 ? '+' : ''}${Number(delta.toFixed(1))}%`;
}

export interface CockpitData {
  departments: typeof departments;
  flows: number[][];
  live: boolean;
  problem?: FacilityLayoutProblem;
  layout?: ContinuousLayout | null;
  evaluation?: EvaluationReport | null;
  metrics?: FlowMetrics;
  baselineMetrics?: FlowMetrics;
  metricConfig?: Record<string, unknown>;
  scenarios?: LiveScenario[];
  selectedScenario?: number;
  selectScenario?: (id: number) => void;
  swap?: (first: string, second: string) => void;
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
    && !!matchingLayout.layout_signature && matchingLayout.layout_signature === evaluation.layout_signature
    ? evaluation : null;
  return { departments: liveDepartments, flows: matrix, live: true, problem, layout: matchingLayout, evaluation: matchingEvaluation,
    metrics: calculateFlowMetrics(problem, matchingLayout, { ...problem.objective_config, ...matchingEvaluation?.evaluation_config }) };
}
