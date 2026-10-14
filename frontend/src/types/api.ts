/**
 * Types mirroring backend API payloads.
 */

export interface SystemStatus {
  status: string;
  project_name: string;
  version: string;
  timestamp: string;
  python_version: string;
  platform: string;
  registered_algorithms: number;
  modules: Record<string, string>;
}


export interface Facility {
  id: string;
  name: string;
  width: number;
  height: number;
  area: number;
  reserved_zones?: ReservedZone[];
  metadata?: Record<string, any>;
}

export interface Department {
  id: string;
  name: string;
  required_area: number;
  min_width?: number;
  max_width?: number;
  min_height?: number;
  max_height?: number;
  min_aspect_ratio?: number;
  max_aspect_ratio?: number;
  fixed_position?: { x: number; y: number };
  metadata?: Record<string, any>;
}

export interface Flow {
  source_department: string;
  target_department: string;
  quantity: number;
  unit: string;
  cost_per_unit_distance?: number;
  product_or_process_id?: string;
}

export interface Relationship {
  department_a: string;
  department_b: string;
  relationship_type: string;
  score: number;
  reason?: string;
}

export interface Constraint {
  id: string;
  type: string;
  involved_departments: string[];
  parameters: Record<string, any>;
  classification: 'hard' | 'soft';
  penalty: number;
  metadata?: Record<string, any>;
}

export interface FacilityLayoutProblem {
  id: string;
  name: string;
  facility: Facility;
  departments: Department[];
  flows: Flow[];
  relationships: Relationship[];
  constraints: Constraint[];
  objective_config?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface ProblemSummary {
  id: string;
  name: string;
  facility_width: number;
  facility_height: number;
  facility_area: number;
  department_count: number;
  total_required_area: number;
  area_utilization: number;
  flow_count: number;
  relationship_count: number;
  constraint_count: number;
  file_path?: string;
}

export interface ProblemFingerprint {
  problem_id: string;
  department_count: number;
  total_required_area: number;
  facility_area: number;
  area_utilization: number;
  facility_width?: number;
  facility_height?: number;
  aspect_ratio_constrained_count?: number;
  has_aspect_ratio_constraints?: boolean;
  dimension_constrained_count?: number;
  has_dimension_constraints?: boolean;
  flow_count: number;
  flow_density: number;
  total_flow_volume: number;
  average_flow: number;
  max_flow: number;
  closeness_relationships_count: number;
  undesirable_relationships_count: number;
  rel_density?: number;
  fixed_departments_count: number;
  reserved_zone_count?: number;
  reserved_zone_ratio?: number;
  hard_constraints_count: number;
  soft_constraints_count: number;
  hard_constraint_types?: string[];
  soft_constraint_types?: string[];
  unavailable_features?: string[];
  area_variation: number;
  product_processes_count: number;
}

export interface ProblemValidationReport {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  fingerprint?: ProblemFingerprint;
  stats: Record<string, any>;
}

export interface ContinuousPlacement {
  department_id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  orientation_degrees?: number;
  metadata?: Record<string, any>;
}

export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface ReservedZone {
  id: string;
  type: string;
  bounding_box: BoundingBox;
  strict?: boolean;
  metadata?: Record<string, any>;
}

export interface ContinuousLayout {
  id?: string;
  problem_id?: string;
  name?: string;
  representation_type: 'continuous' | 'grid';
  facility_width: number;
  facility_height: number;
  placements: Record<string, ContinuousPlacement>;
  reserved_zones?: ReservedZone[];
  metadata?: Record<string, any>;
  layout_signature?: string;
  bounding_box?: BoundingBox;
}

export interface LayoutExampleSummary {
  id: string;
  problem_id: string;
  name: string;
  representation_type: string;
  facility_width: number;
  facility_height: number;
  department_count: number;
  filename: string;
}

export interface LayoutValidationResult {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  total_overlap_area: number;
  checked_departments: string[];
  metrics: {
    occupied_area: number;
    free_area: number;
    utilization_ratio: number;
    total_overlap_area: number;
    bounding_envelope_area: number;
    compactness: number;
  };
  signature?: string;
}

export interface ConstraintViolationInfo {
  constraint_id: string;
  constraint_type: string;
  classification: 'hard' | 'soft';
  involved_departments: string[];
  magnitude: number;
  penalty_cost: number;
  description: string;
  measured_value?: number;
  required_value?: number;
}

export interface EvaluationMetricResult {
  metric_name: string;
  display_name: string;
  value: number;
  unit: string;
  direction: 'minimize' | 'maximize';
  details: Record<string, any>;
}

export interface EvaluationReport {
  problem_id: string;
  algorithm_name: string;
  layout_signature: string;
  is_feasible: boolean;
  complete_layout?: boolean;
  is_comparable?: boolean;
  unplaced_departments?: string[];
  diagnostic_partial_values?: Record<string, number>;
  objective_values: Record<string, number>;
  normalized_values?: Record<string, number>;
  composite_score?: number;
  rank?: number;
  constraint_violations: ConstraintViolationInfo[];
  hard_violation_count: number;
  soft_violation_count: number;
  total_constraint_penalty: number;
  metrics: Record<string, EvaluationMetricResult>;
  summary_scores: Record<string, number>;
  top_contributors: Record<string, any[]>;
  evaluation_config: Record<string, any>;
  metadata: Record<string, any>;
  material_handling_cost?: number;
  flow_distance?: number;
  relationship_satisfaction_percentage?: number;
  adjacency_satisfaction_percentage?: number;
  soft_constraint_penalty?: number;
  soft_penalty?: number;
  hard_constraint_violations?: string[];
  config_hash?: string;
}

export interface ComparisonReport {
  problem_id: string;
  solution_count: number;
  reports: EvaluationReport[];
  ranking: string[];
  weights_used: Record<string, number>;
  metadata: Record<string, any>;
}

export interface AlgorithmMetadata {
  name: string;
  version: string;
  category: string;
  description?: string;
  supported_problem_types?: string[];
  default_parameters?: Record<string, any>;
  parameter_schema?: Record<string, any>;
}

export interface CORELAPConfig {
  placement_mode?: 'classical_adjacency' | 'extended_distance_weighted' | 'adjacency' | 'distance_weighted';
  initial_anchor_mode?: 'center' | 'origin' | 'bottom_left';
  candidate_gap?: number;
  aspect_ratio_target?: number;
  allow_shape_alternatives?: boolean;
  evaluate_orientations?: boolean;
  x_adjacency_penalty_multiplier?: number;
  distance_decay_factor?: number;
  separated_x_penalty_scale?: number;
  separated_x_decay_factor?: number;
  tie_break_center_compactness?: boolean;
  numerical_tolerance?: number;
  step_grid_alignment?: number | null;
  trace_level?: 'SUMMARY' | 'DETAILED';
}

export interface CORELAPTraceStep {
  step_number: number;
  selected_department: string;
  tcr: number;
  placed_relationship_score: number;
  candidate_count: number;
  selected_candidate: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  candidate_score: number;
  neighbors: string[];
  rejected_candidates: number;
  rejection_reasons: Record<string, number>;
  candidate_diagnostics?: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
    orientation_degrees?: number;
    score: number;
    neighbors: string[];
  }> | null;
}

export interface CORELAPExecutionTrace {
  algorithm_name: string;
  algorithm_version: string;
  total_departments: number;
  placed_count: number;
  execution_success: boolean;
  is_complete?: boolean;
  placed_department_count?: number;
  total_department_count?: number;
  unplaced_departments?: string[];
  termination_reason?: string | null;
  placement_order: string[];
  tcr_values: Record<string, number>;
  steps: CORELAPTraceStep[];
  failure_reason?: string | null;
  execution_time_seconds: number;
}

export interface CORELAPSolveRequest {
  problem_id?: string;
  problem?: Record<string, any>;
  config?: CORELAPConfig;
}

export interface LayoutSolution {
  problem_id: string;
  algorithm_name: string;
  algorithm_version?: string;
  is_complete?: boolean;
  placed_department_count?: number;
  total_department_count?: number;
  unplaced_departments?: string[];
  termination_reason?: string | null;
  feasibility_status?: boolean;
  execution_time_seconds?: number;
  placements?: Record<string, any>;
  metadata?: Record<string, any>;
}

export interface CORELAPSolveResponse {
  solution: LayoutSolution | Record<string, any>;
  continuous_layout: ContinuousLayout;
  trace: CORELAPExecutionTrace;
  validation: LayoutValidationResult;
  evaluation: EvaluationReport;
}

export interface CRAFTConfig {
  max_iterations?: number;
  min_improvement_threshold?: number;
  allow_rotational_swaps?: boolean;
  distance_metric?: string;
  default_cost_per_unit_distance?: number;
  numerical_tolerance?: number;
  trace_level?: 'SUMMARY' | 'DETAILED';
}

export interface CRAFTSwapStep {
  iteration: number;
  dept_a: string;
  dept_b: string;
  is_rotational: boolean;
  mhc_before: number;
  mhc_after: number;
  improvement: number;
  cumulative_improvement: number;
  layout_signature: string;
}

export interface CRAFTTraceStep {
  iteration: number;
  current_mhc: number;
  candidate_pairs: number;
  feasible_candidates: number;
  rejected_candidates: number;
  rejection_breakdown: Record<string, number>;
  selected_swap?: CRAFTSwapStep | null;
  mhc_before: number;
  mhc_after: number;
  improvement: number;
  cumulative_improvement: number;
  layout_signature: string;
  candidate_evaluations?: Array<{
    pair: [string, string];
    is_rotational: boolean;
    is_feasible: boolean;
    rejection_reason?: string | null;
    mhc_after?: number | null;
    improvement?: number | null;
  }> | null;
}

export interface CRAFTExecutionTrace {
  algorithm_name: string;
  algorithm_version: string;
  initial_mhc: number;
  final_mhc: number;
  absolute_improvement: number;
  percentage_improvement: number;
  total_iterations: number;
  iteration_count?: number;
  total_swaps_accepted: number;
  termination_reason: string;
  steps: CRAFTTraceStep[];
  execution_time_seconds: number;
}

export interface CRAFTSolverResult {
  algorithm_name: string;
  algorithm_version: string;
  initial_layout_signature: string;
  final_layout_signature: string;
  is_complete: boolean;
  is_feasible: boolean;
  termination_reason: string;
  iterations: number;
  accepted_swaps: CRAFTSwapStep[];
  initial_mhc: number;
  final_mhc: number;
  absolute_improvement: number;
  percentage_improvement: number;
  trace: CRAFTExecutionTrace;
  final_layout: ContinuousLayout;
  metadata?: Record<string, any>;
}

export interface CRAFTSolveRequest {
  problem_id?: string;
  problem?: Record<string, any>;
  initial_layout_id?: string;
  initial_layout?: Record<string, any>;
  config?: CRAFTConfig;
  evaluation_config?: Record<string, any>;
}

export interface CRAFTSolveResponse {
  solution: LayoutSolution | Record<string, any>;
  continuous_layout: ContinuousLayout;
  initial_layout: ContinuousLayout;
  result: CRAFTSolverResult;
  initial_evaluation: EvaluationReport;
  final_evaluation: EvaluationReport;
  trace: CRAFTExecutionTrace;
}

export interface ALDEPConfig {
  number_of_candidates?: number;
  random_seed?: number;
  cell_size?: number;
  strip_width_cells?: number;
  sweep_direction?: 'VERTICAL' | 'HORIZONTAL';
  selection_threshold?: number;
  tie_breaker?: 'RANDOM_AMONG_MAX' | 'RANDOM_AMONG_THRESHOLD';
  allow_strip_splitting?: boolean;
  serpentine_sweep?: boolean;
  trace_level?: 'SUMMARY' | 'DETAILED';
}

export interface ALDEPSelectionStep {
  step_number: number;
  last_department_id?: string | null;
  unplaced_candidates: string[];
  candidate_scores: Record<string, number>;
  threshold: number;
  eligible_candidates: string[];
  selection_mode: string;
  selected_department: string;
}

export interface ALDEPDepartmentShapeDiagnostic {
  department_id: string;
  required_area: number;
  allocated_cells: number;
  allocated_area: number;
  area_error: number;
  area_error_pct: number;
  bounding_box: BoundingBox;
  is_rectangular: boolean;
  aspect_ratio: number;
  grid_cells?: Array<[number, number]>;
}

export interface ALDEPCandidateResult {
  candidate_index: number;
  seed: number;
  department_order: string[];
  layout_signature: string;
  is_complete: boolean;
  is_feasible: boolean;
  is_duplicate: boolean;
  duplicate_of_index?: number | null;
  placed_department_count: number;
  total_department_count: number;
  unplaced_departments: string[];
  termination_reason: string;
  material_handling_cost?: number | null;
  flow_distance?: number | null;
  relationship_score?: number | null;
  area_utilization?: number | null;
  shape_diagnostics: Record<string, ALDEPDepartmentShapeDiagnostic>;
  continuous_layout: ContinuousLayout;
  grid_layout?: Record<string, any> | null;
  selection_steps: ALDEPSelectionStep[];
}

export interface ALDEPExecutionTrace {
  algorithm_name: string;
  algorithm_version: string;
  number_of_candidates: number;
  unique_candidate_count: number;
  feasible_candidate_count: number;
  complete_candidate_count: number;
  best_candidate_index: number;
  best_candidate_seed: number;
  execution_time_seconds: number;
  best_selection_steps: ALDEPSelectionStep[];
}

export interface ALDEPSolverResult {
  algorithm_name: string;
  algorithm_version: string;
  best_candidate: ALDEPCandidateResult;
  candidates: ALDEPCandidateResult[];
  trace: ALDEPExecutionTrace;
}

export interface ALDEPSolveRequest {
  problem_id?: string;
  problem?: Record<string, any>;
  config?: ALDEPConfig;
}

export interface ALDEPSolveResponse {
  solution: LayoutSolution | Record<string, any>;
  continuous_layout: ContinuousLayout;
  grid_layout?: Record<string, any> | null;
  best_candidate: ALDEPCandidateResult;
  candidates: ALDEPCandidateResult[];
  result: ALDEPSolverResult;
  trace: ALDEPExecutionTrace;
  validation: LayoutValidationResult;
  evaluation: EvaluationReport;
}





export interface BenchmarkComparisonRow {
  algorithm: string;
  problem_id: string;
  run_or_seed: string;
  complete: boolean;
  feasible: boolean;
  mhc?: number | null;
  flow_distance?: number | null;
  relationship_satisfaction?: number | null;
  constraint_violations: number;
  runtime_seconds: number;
  notes?: string | null;
}

export interface ALDEPProblemSummary {
  problem_id: string;
  total_trials: number;
  complete_count: number;
  completion_rate: number;
  feasible_count: number;
  feasibility_rate: number;
  unique_layout_count: number;
  duplicate_count: number;
  best_mhc?: number | null;
  median_mhc?: number | null;
  worst_mhc?: number | null;
  std_mhc?: number | null;
  sample_size_mhc: number;
  sample_description: string;
  best_feasible_signature?: string | null;
  mean_runtime_seconds: number;
  total_runtime_seconds: number;
}

export interface BenchmarkConfig {
  problem_ids?: string[];
  aldep_seeds?: number[];
  aldep_candidates_per_seed?: number;
  aldep_cell_size?: number;
  aldep_strip_width_cells?: number;
  aldep_allow_strip_splitting?: boolean;
  craft_max_iterations?: number;
  evaluation_config?: Record<string, any>;
}

export interface BenchmarkResult {
  run_id: string;
  timestamp: string;
  config: BenchmarkConfig;
  comparison_table: BenchmarkComparisonRow[];
  aldep_summaries: Record<string, ALDEPProblemSummary>;
  aldep_candidates: any[];
  corelap_records: any[];
  craft_records: any[];
  metadata: Record<string, any>;
}

export interface BenchmarkRunRequest {
  config?: BenchmarkConfig;
}

export type GeneratorStrategy = 'free_rectangle_dfs' | 'slicing_tree_decomposition' | 'guillotine_row_packing';
export type DepartmentOrderingStrategy = 'most_constrained_first' | 'largest_area_first' | 'flow_volume_descending' | 'relationship_weight_descending';
export type GeneratorTerminationReason = 'SUCCESS_FEASIBLE_FOUND' | 'SEARCH_BUDGET_EXHAUSTED' | 'SEARCH_SPACE_EXHAUSTED' | 'PRE_FEASIBILITY_FAILED' | 'TIMEOUT';

export interface GeneratorConfig {
  strategy?: GeneratorStrategy;
  ordering_strategy?: DepartmentOrderingStrategy;
  max_nodes?: number;
  max_backtracks?: number;
  max_runtime_seconds?: number;
  time_budget_seconds?: number;
  max_shape_alternatives?: number;
  candidate_limit_per_department?: number;
  tolerance?: number;
  random_seed?: number;
}

export interface GeneratorResult {
  success: boolean;
  complete: boolean;
  feasible: boolean;
  problem_id: string;
  strategy: string;
  layout?: ContinuousLayout | null;
  layout_signature?: string | null;
  placed_department_count: number;
  total_department_count: number;
  nodes_explored: number;
  backtracks: number;
  candidates_rejected: number;
  runtime_seconds: number;
  termination_reason: GeneratorTerminationReason;
  failure_diagnostics: Record<string, any>;
  metadata: Record<string, any>;
}

export interface FeasibleGeneratorSolveRequest {
  problem_id?: string;
  problem?: Record<string, any>;
  config?: GeneratorConfig;
}

export interface FeasibleGeneratorSolveResponse {
  solution?: LayoutSolution | null;
  result: GeneratorResult;
  validation?: LayoutValidationResult | null;
  evaluation?: EvaluationReport | null;
  continuous_layout?: ContinuousLayout;
}

export type GATerminationReason =
  | 'max_generations_reached'
  | 'stagnation_limit_reached'
  | 'timeout'
  | 'target_reached';

export interface GAConfig {
  population_size?: number;
  generations?: number;
  max_generations?: number;
  crossover_rate?: number;
  mutation_rate?: number;
  elitism_count?: number;
  tournament_size?: number;
  random_seed?: number;
  max_runtime_seconds?: number;
  stagnation_limit?: number;
  soft_penalty_weight?: number;
  infeasible_penalty?: number;
  min_bays?: number;
  max_bays?: number;
  orientation?: string;
  seed_with_guillotine?: boolean;
  tolerance?: number;
}

export interface BayChromosome {
  order: string[];
  bay_sizes: number[];
  orientation: string;
}

export interface GenerationRecord {
  generation: number;
  best_fitness: number;
  best_mhc: number;
  best_soft_penalty: number;
  avg_fitness: number;
  best_is_feasible: boolean;
  diversity: number;
}

export interface GAResult {
  best_solution: LayoutSolution;
  best_layout: ContinuousLayout;
  best_chromosome: BayChromosome;
  best_fitness: number;
  best_mhc: number;
  best_soft_penalty: number;
  is_feasible: boolean;
  generation_count: number;
  termination_reason: GATerminationReason;
  runtime_seconds: number;
  history: GenerationRecord[];
  initial_mhc: number;
  improvement_mhc: number;
  improvement_percentage: number;
}

export interface GASolveRequest {
  problem_id?: string;
  problem?: Record<string, any>;
  config?: GAConfig;
}

export interface GASolveResponse {
  solution: LayoutSolution;
  continuous_layout: ContinuousLayout;
  result: GAResult;
  validation: LayoutValidationResult;
  evaluation: EvaluationReport;
}

// ---------------------------------------------------------------------------
// Phase 10: Multi-Objective & Pareto Frontier Types
// ---------------------------------------------------------------------------

export interface ObjectiveDefinition {
  id: string;
  name: string;
  direction: 'minimize' | 'maximize';
  unit: string;
  description?: string;
  weight: number;
  tolerance: number;
}

export interface ParetoCandidate {
  candidate_id: string;
  algorithm_source: string;
  layout_signature: string;
  problem_id: string;
  problem_composite_hash: string;
  evaluation_config_hash: string;
  objective_values: Record<string, number>;
  auxiliary_metrics: Record<string, any>;
  is_complete: boolean;
  is_feasible: boolean;
  hard_violations_count: number;
  soft_violations_count: number;
  pareto_rank?: number;
  is_non_dominated: boolean;
  dominated_by: string[];
  dominates: string[];
  normalized_utility?: number;
  placements?: Record<string, any>;
  metadata: Record<string, any>;
}

export interface ExcludedCandidate {
  candidate_id: string;
  algorithm_source: string;
  layout_signature?: string;
  reason: string;
  details?: Record<string, any>;
}

export interface DecisionSupportRecommendation {
  profile_name: string;
  recommended_candidate_id: string;
  utility_score: number;
  is_on_pareto_frontier: boolean;
  priority_weights: Record<string, number>;
  rationale: string;
}

export interface ParetoAnalysisResult {
  problem_id: string;
  problem_composite_hash: string;
  evaluation_config_hash: string;
  total_candidates_evaluated: number;
  valid_candidates_count: number;
  excluded_candidates_count: number;
  frontier_count: number;
  frontier_candidate_ids: string[];
  ranks: Record<number, string[]>;
  candidates: ParetoCandidate[];
  excluded: ExcludedCandidate[];
  objectives: ObjectiveDefinition[];
  recommendations: Record<string, DecisionSupportRecommendation>;
}

export interface ParetoAnalyzeRequest {
  problem_id?: string;
  problem?: Record<string, any>;
  candidates?: Record<string, any>[];
  include_saved_baselines?: boolean;
  objectives?: ObjectiveDefinition[];
  priority_weights?: Record<string, number>;
}

// ==========================================
// Phase 11: Adaptive Strategy Engine Types
// ==========================================

export interface StrategyPipeline {
  archetype: string;
  name: string;
  rule_id: string;
  rule_description: string;
  trigger_conditions: Record<string, any>;
  primary_algorithm: string;
  improvement_algorithms: string[];
  fallback_algorithm?: string;
  rationale: string;
  non_working_conditions: string[];
}

export interface DecisionTraceStep {
  step_index: number;
  action: string;
  rule_id?: string;
  rule_description?: string;
  selected_algorithm: string;
  algorithm_category: string;
  parameters_used: Record<string, any>;
  execution_time_seconds: number;
  success: boolean;
  is_complete: boolean;
  is_feasible: boolean;
  failure_reason?: string;
  was_fallback: boolean;
  layout_signature?: string;
  objective_values: Record<string, number>;
  next_action_rationale: string;
}

export interface ProvenanceRecord {
  algorithm_name: string;
  algorithm_version: string;
  random_seed?: number;
  input_layout_signature?: string;
  runtime_seconds: number;
  step_index: number;
}

export interface PortfolioCandidateItem {
  candidate_id: string;
  source_algorithm: string;
  source_version: string;
  source_seed?: number;
  input_layout_signature?: string;
  output_layout_signature: string;
  problem_hash: string;
  evaluation_config_hash: string;
  feasibility: boolean;
  completeness: boolean;
  material_handling_cost?: number;
  relationship_satisfaction?: number;
  soft_penalty?: number;
  runtime_seconds: number;
  trace: Record<string, any>;
  rejection_reason?: string;
  provenance_sources: ProvenanceRecord[];
  solution?: LayoutSolution;
}

export interface CandidatePortfolio {
  total_candidates_generated: number;
  unique_candidates_count: number;
  feasible_candidates_count: number;
  infeasible_candidates_count: number;
  items: PortfolioCandidateItem[];
  deduplication_map: Record<string, string[]>;
  total_candidates_count?: number;
}

export interface AdaptiveConfig {
  max_total_runtime_seconds?: number;
  time_limit_seconds?: number;
  max_algorithm_calls?: number;
  max_candidates?: number;
  ga_population_size?: number;
  ga_generations?: number;
  random_seed?: number;
  fallback_enabled?: boolean;
}

export interface AdaptiveStrategyResult {
  problem_id: string;
  fingerprint: ProblemFingerprint;
  selected_strategy: StrategyPipeline;
  execution_trace: DecisionTraceStep[];
  candidate_portfolio: CandidatePortfolio;
  feasible_status: boolean;
  canonical_evaluations: any[];
  pareto_frontier: ParetoAnalysisResult;
  final_recommendation?: Record<string, any>;
  termination_reason: string;
  total_runtime_seconds: number;
  total_algorithm_calls: number;
  best_continuous_layout?: ContinuousLayout;
  execution_status?: string;
  validation_status?: string;
  is_feasible?: boolean;
  selected_algorithm?: string;
  failure_reason?: string | null;
  best_validation?: LayoutValidationResult | null;
  best_evaluation?: EvaluationReport | null;
  fallback_trace?: any[];
}

export interface StrategyAnalyzeRequest {
  problem_id?: string;
  problem?: FacilityLayoutProblem;
  has_initial_layout?: boolean;
}

export interface StrategyAnalyzeResponse {
  problem_id: string;
  fingerprint: ProblemFingerprint;
  selected_strategy: StrategyPipeline;
}

export interface StrategySolveRequest {
  problem_id?: string;
  problem?: FacilityLayoutProblem;
  config?: AdaptiveConfig;
  initial_layout?: Record<string, any>;
}

// ==========================================
// Phase 12: Gemini AI Decision Explanation Types
// ==========================================

export type ExplanationMode = 'local' | 'gemini';

export type PresetQuestionType =
  | 'why_strategy_selected'
  | 'why_feasible'
  | 'pareto_comparison'
  | 'soft_penalty_explanation'
  | 'fallback_reason'
  | 'global_optimality_query'
  | 'custom';

export interface SanitizedPayloadDepartment {
  dept_alias: string;
  required_area: number;
  category: string;
}

export interface SanitizedAIExplanationPayload {
  problem_id: string;
  facility_dimensions: Record<string, number>;
  department_count: number;
  area_utilization_pct: number;
  anonymized_departments: SanitizedPayloadDepartment[];
  selected_strategy_name: string;
  selected_archetype: string;
  primary_algorithm: string;
  fallback_triggered: boolean;
  fallback_reason?: string;
  canonical_metrics: Record<string, number>;
  violations_summary: Record<string, any>;
  pareto_rank?: number;
  is_non_dominated?: boolean;
  alternative_comparison?: Record<string, any>;
  question_type: string;
  question_text: string;
  payload_hash: string;
}

export interface DataTransferPreview {
  provider: string;
  target_model: string;
  purpose: string;
  privacy_impact: string;
  whitelisted_fields: string[];
  excluded_sensitive_fields: string[];
  payload: SanitizedAIExplanationPayload;
  payload_hash: string;
  consent_token: string;
}

export interface StructuredAIExplanation {
  summary: string;
  main_reasons: string[];
  strengths: string[];
  risks: string[];
  trade_offs: string[];
  limitations: string[];
  evidence_references: string[];
  global_optimality_disclaimer: string;
}

export interface AIExplanationResult {
  mode: ExplanationMode;
  question: string;
  explanation: StructuredAIExplanation;
  verified_canonical_metrics: Record<string, any>;
  provenance: Record<string, any>;
  validation_passed: boolean;
  fallback_to_local_used: boolean;
  fallback_reason?: string;
}

export interface AIStatusResponse {
  ai_enabled: boolean;
  gemini_model: string;
  has_api_key: boolean;
  supported_modes: string[];
  default_mode: string;
  timeout_seconds: number;
  confidentiality_guarantee: string;
}

export interface ExplainLocalRequest {
  problem_id: string;
  question_type: PresetQuestionType;
  custom_question?: string;
  layout_signature?: string;
  comparison_layout_signature?: string;
}

export interface PreviewPayloadRequest {
  problem_id: string;
  question_type: PresetQuestionType;
  custom_question?: string;
  layout_signature?: string;
  comparison_layout_signature?: string;
  client_session_id?: string;
}

export interface GrantConsentRequest {
  payload_hash: string;
  client_session_id?: string;
  consent_acknowledged: boolean;
  opt_in_exact_dimensions?: boolean;
  opt_in_exact_areas?: boolean;
  opt_in_financial_costs?: boolean;
}

export interface GrantConsentResponse {
  consent_token: string;
  payload_hash: string;
  client_session_id: string;
  expires_at: string;
  single_use: boolean;
}

export interface ExplainGeminiRequest {
  problem_id: string;
  question_type: PresetQuestionType;
  custom_question?: string;
  layout_signature?: string;
  comparison_layout_signature?: string;
  payload_hash: string;
  consent_token: string;
  client_session_id?: string;
}

// --- Phase 14.1 Controlled Research Access & Isolation Types ---

export type UserRole = 'ADMIN' | 'RESEARCHER' | 'VIEWER';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  allow_gemini: boolean;
  created_at: string;
}

export interface LoginResponse {
  session_token: string;
  user: UserProfile;
  expires_at: string;
}

export interface InvitationResponse {
  id: string;
  token: string;
  email: string;
  role: UserRole;
  created_by_user_id: string;
  created_at: string;
  expires_at: string;
  used_at?: string | null;
  is_revoked: boolean;
}

export interface ResearchProject {
  id: string;
  name: string;
  description?: string | null;
  owner_user_id: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  problem_count: number;
  run_count: number;
}

export interface OptimizationRunRecord {
  id: string;
  project_id: string;
  problem_id: string;
  user_id: string;
  algorithm_name: string;
  algorithm_version: string;
  flodss_version: string;
  parameters: Record<string, any>;
  random_seed: number;
  status: string;
  termination_reason?: string | null;
  runtime_ms: number;
  problem_hash: string;
  evaluation_config_hash: string;
  layout_signature?: string | null;
  is_feasible: boolean;
  canonical_metrics?: Record<string, any> | null;
  created_at: string;
  completed_at?: string | null;
}

export interface ExperimentDetailResponse {
  run: OptimizationRunRecord;
  layout?: Record<string, any> | null;
  evaluation?: Record<string, any> | null;
}

