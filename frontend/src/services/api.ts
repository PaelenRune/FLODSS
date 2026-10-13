import {
  SystemStatus,
  ProblemSummary,
  FacilityLayoutProblem,
  ProblemValidationReport,
  LayoutExampleSummary,
  ContinuousLayout,
  LayoutValidationResult,
  EvaluationReport,
  ComparisonReport,
  AlgorithmMetadata,
  CORELAPSolveRequest,
  CORELAPSolveResponse,
  CRAFTSolveRequest,
  CRAFTSolveResponse,
  ALDEPSolveRequest,
  ALDEPSolveResponse,
  BenchmarkResult,
  BenchmarkRunRequest,
  FeasibleGeneratorSolveRequest,
  FeasibleGeneratorSolveResponse,
  GASolveRequest,
  GASolveResponse,
  ParetoAnalysisResult,
  ParetoAnalyzeRequest,
  StrategyAnalyzeRequest,
  StrategyAnalyzeResponse,
  StrategySolveRequest,
  AdaptiveStrategyResult,
  AIStatusResponse,
  DataTransferPreview,
  AIExplanationResult,
  ExplainLocalRequest,
  PreviewPayloadRequest,
  GrantConsentRequest,
  GrantConsentResponse,
  ExplainGeminiRequest,
  UserProfile,
  LoginResponse,
  InvitationResponse,
  ResearchProject,
  OptimizationRunRecord,
  ExperimentDetailResponse,
  UserRole,
} from '../types/api';

let authToken: string | null = typeof window !== 'undefined' ? localStorage.getItem('flodss_token') : null;

export function setAuthToken(token: string | null) {
  authToken = token;
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem('flodss_token', token);
    } else {
      localStorage.removeItem('flodss_token');
    }
  }
}

export function getAuthToken(): string | null {
  if (!authToken && typeof window !== 'undefined') {
    authToken = localStorage.getItem('flodss_token');
  }
  return authToken;
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Accept': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function authFetch(url: string, init?: RequestInit): Promise<Response> {
  const baseHeaders = getAuthHeaders();
  const customHeaders = (init?.headers || {}) as Record<string, string>;
  return fetch(url, {
    ...init,
    headers: {
      ...baseHeaders,
      ...customHeaders,
    },
  });
}


const API_BASE = '/api';

/**
 * Fetch health status and system diagnostics from backend.
 */
export async function fetchSystemHealth(): Promise<SystemStatus> {
  const response = await fetch(`${API_BASE}/health`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Backend responded with HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Fetch catalog of available example benchmark problems.
 */
export async function fetchExampleProblems(): Promise<ProblemSummary[]> {
  const response = await fetch(`${API_BASE}/problems/examples`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch example problems (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch a complete problem specification by ID.
 */
export async function fetchExampleProblem(problemId: string): Promise<FacilityLayoutProblem> {
  const response = await fetch(`${API_BASE}/problems/examples/${encodeURIComponent(problemId)}`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to load problem '${problemId}' (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Validate a problem payload against schema and integrity rules.
 */
export async function validateProblemPayload(payload: any): Promise<ProblemValidationReport> {
  const response = await fetch(`${API_BASE}/problems/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Validation request failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch catalog of available layout examples.
 */
export async function fetchExampleLayouts(): Promise<LayoutExampleSummary[]> {
  const response = await fetch(`${API_BASE}/layouts/examples`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch layout examples (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch a specific layout example by ID.
 */
export async function fetchExampleLayout(layoutId: string): Promise<ContinuousLayout> {
  const response = await fetch(`${API_BASE}/layouts/examples/${encodeURIComponent(layoutId)}`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to load layout '${layoutId}' (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Validate a layout against a problem.
 */
export async function validateLayout(
  problemId: string,
  layout: ContinuousLayout
): Promise<LayoutValidationResult> {
  const response = await fetch(`${API_BASE}/layouts/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      problem_id: problemId,
      layout,
    }),
  });

  if (!response.ok) {
    throw new Error(`Layout validation request failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Run comprehensive multi-metric evaluation on a layout.
 */
export async function evaluateLayout(
  problemId: string,
  layout: ContinuousLayout | Record<string, any>,
  config?: Record<string, any>
): Promise<EvaluationReport> {
  const response = await fetch(`${API_BASE}/evaluation/evaluate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      problem_id: problemId,
      layout,
      config,
    }),
  });

  if (!response.ok) {
    throw new Error(`Evaluation request failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Compare multiple alternative layouts using multi-criteria normalization and ranking.
 */
export async function compareLayouts(
  problemId: string,
  layouts: Array<ContinuousLayout | Record<string, any>>,
  config?: Record<string, any>
): Promise<ComparisonReport> {
  const response = await fetch(`${API_BASE}/evaluation/compare`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify({
      problem_id: problemId,
      layouts,
      config,
    }),
  });

  if (!response.ok) {
    throw new Error(`Comparison request failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch available evaluation metrics and metadata.
 */
export async function fetchEvaluationMetrics(): Promise<any> {
  const response = await fetch(`${API_BASE}/evaluation/metrics`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch evaluation metrics (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch list of registered layout algorithms.
 */
export async function fetchAlgorithms(): Promise<AlgorithmMetadata[]> {
  const response = await fetch(`${API_BASE}/algorithms`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch algorithms (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Execute CORELAP layout construction heuristic.
 */
export async function solveCORELAP(payload: CORELAPSolveRequest): Promise<CORELAPSolveResponse> {
  const response = await fetch(`${API_BASE}/algorithms/corelap/solve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `CORELAP execution failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Execute CRAFT pairwise exchange layout improvement heuristic.
 */
export async function solveCRAFT(payload: CRAFTSolveRequest): Promise<CRAFTSolveResponse> {
  const response = await fetch(`${API_BASE}/algorithms/craft/solve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `CRAFT execution failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Execute ALDEP multi-candidate layout construction heuristic.
 */
export async function solveALDEP(payload: ALDEPSolveRequest): Promise<ALDEPSolveResponse> {
  const response = await fetch(`${API_BASE}/algorithms/aldep/solve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `ALDEP execution failed (HTTP ${response.status})`);
  }

  return response.json();
}





/**
 * Trigger systematic benchmark run across CORELAP, ALDEP, and CRAFT.
 */
export async function runBenchmark(payload?: BenchmarkRunRequest): Promise<BenchmarkResult> {
  const response = await fetch(`${API_BASE}/benchmarks/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload || {}),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Benchmark run failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch latest recorded benchmark result.
 */
export async function getLatestBenchmark(): Promise<BenchmarkResult> {
  const response = await fetch(`${API_BASE}/benchmarks/latest`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to fetch latest benchmark (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch benchmark result by specific run ID.
 */
export async function getBenchmarkResult(runId: string): Promise<BenchmarkResult> {
  const response = await fetch(`${API_BASE}/benchmarks/results/${runId}`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Benchmark run '${runId}' not found (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Execute Feasible Rectangular Layout Generator constructive search.
 */
export async function solveFeasibleGenerator(
  payload: FeasibleGeneratorSolveRequest
): Promise<FeasibleGeneratorSolveResponse> {
  const response = await fetch(`${API_BASE}/algorithms/feasible-generator/solve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Feasible Generator execution failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Execute Genetic Algorithm layout optimization.
 */
export async function solveGeneticAlgorithm(
  payload: GASolveRequest
): Promise<GASolveResponse> {
  const response = await fetch(`${API_BASE}/algorithms/genetic/solve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Genetic Algorithm execution failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Execute Pareto Frontier multi-objective analysis.
 */
export async function fetchParetoAnalysis(
  payload?: ParetoAnalyzeRequest
): Promise<ParetoAnalysisResult> {
  const response = await fetch(`${API_BASE}/pareto/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload || { problem_id: 'FLP_INDUSTRIAL_10', include_saved_baselines: true }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Pareto analysis request failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Analyze problem fingerprint and get strategy recommendation.
 */
export async function analyzeStrategy(
  payload: StrategyAnalyzeRequest
): Promise<StrategyAnalyzeResponse> {
  const response = await fetch(`${API_BASE}/strategy/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Strategy analysis failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Solve facility layout problem using Adaptive Strategy Engine.
 */
export async function solveAdaptiveStrategy(
  payload: StrategySolveRequest
): Promise<AdaptiveStrategyResult> {
  const response = await fetch(`${API_BASE}/strategy/solve`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Adaptive Strategy execution failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Fetch AI Explanation system configuration and availability.
 */
export async function fetchAIStatus(): Promise<AIStatusResponse> {
  const response = await fetch(`${API_BASE}/ai/status`, {
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch AI status (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Preview sanitized AI explanation payload and obtain cryptographic consent token.
 */
export async function previewAIPayload(
  payload: PreviewPayloadRequest
): Promise<DataTransferPreview> {
  const response = await fetch(`${API_BASE}/ai/preview-payload`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to generate AI preview (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Generate 100% offline, deterministic rule-based decision explanation.
 */
export async function explainLocal(
  payload: ExplainLocalRequest
): Promise<AIExplanationResult> {
  const response = await fetch(`${API_BASE}/ai/explain-local`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Local explanation failed (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Grant explicit human consent and receive a single-use authorization token.
 */
export async function grantAIConsent(
  payload: GrantConsentRequest
): Promise<GrantConsentResponse> {
  const response = await fetch(`${API_BASE}/ai/grant-consent`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Failed to grant AI consent (HTTP ${response.status})`);
  }

  return response.json();
}

/**
 * Generate grounded decision explanation via Gemini API with user consent token.
 */
export async function explainGemini(
  payload: ExplainGeminiRequest
): Promise<AIExplanationResult> {
  const response = await fetch(`${API_BASE}/ai/explain-gemini`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || `Gemini explanation failed (HTTP ${response.status})`);
  }

  return response.json();
}


// ============================================================================
// Phase 14.1 Controlled Research Access & Data Isolation Endpoints
// ============================================================================

export async function loginApi(req: { email: string; password: string }): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Login failed (HTTP ${res.status})`);
  }
  const data: LoginResponse = await res.json();
  setAuthToken(data.session_token);
  return data;
}

export async function demoLoginApi(): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/demo-login`, {
    method: 'POST',
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Demo login failed (HTTP ${res.status})`);
  }
  const data: LoginResponse = await res.json();
  setAuthToken(data.session_token);
  return data;
}

export async function logoutApi(): Promise<void> {
  try {
    await authFetch(`${API_BASE}/auth/logout`, { method: 'POST' });
  } finally {
    setAuthToken(null);
  }
}

export async function getMeApi(): Promise<UserProfile> {
  const res = await authFetch(`${API_BASE}/auth/me`);
  if (!res.ok) {
    throw new Error(`Failed to load user profile (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getUsersApi(): Promise<UserProfile[]> {
  const res = await authFetch(`${API_BASE}/auth/users`);
  if (!res.ok) {
    throw new Error(`Failed to load users (HTTP ${res.status})`);
  }
  return res.json();
}

export async function updateUserStatusApi(
  userId: string,
  update: { is_active?: boolean; allow_gemini?: boolean; role?: UserRole }
): Promise<UserProfile> {
  const res = await authFetch(`${API_BASE}/auth/users/${encodeURIComponent(userId)}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(update),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update user status (HTTP ${res.status})`);
  }
  return res.json();
}

export async function createInvitationApi(req: {
  email: string;
  role: UserRole;
  full_name?: string;
}): Promise<InvitationResponse> {
  const res = await authFetch(`${API_BASE}/auth/invitations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create invitation (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getInvitationsApi(): Promise<InvitationResponse[]> {
  const res = await authFetch(`${API_BASE}/auth/invitations`);
  if (!res.ok) {
    throw new Error(`Failed to load invitations (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getInvitationByTokenApi(token: string): Promise<InvitationResponse> {
  const res = await fetch(`${API_BASE}/auth/invitations/${encodeURIComponent(token)}`, {
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Invitation not found or expired (HTTP ${res.status})`);
  }
  return res.json();
}

export async function acceptInvitationApi(req: {
  token: string;
  full_name: string;
  password: string;
}): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/invitations/accept`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to accept invitation (HTTP ${res.status})`);
  }
  const data: LoginResponse = await res.json();
  setAuthToken(data.session_token);
  return data;
}

export async function getProjectsApi(): Promise<ResearchProject[]> {
  const res = await authFetch(`${API_BASE}/projects`);
  if (!res.ok) {
    throw new Error(`Failed to load research projects (HTTP ${res.status})`);
  }
  return res.json();
}

export async function createProjectApi(req: { name: string; description?: string }): Promise<ResearchProject> {
  const res = await authFetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to create research project (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getProjectApi(projectId: string): Promise<ResearchProject> {
  const res = await authFetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}`);
  if (!res.ok) {
    throw new Error(`Failed to load project details (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getProjectProblemsApi(projectId: string): Promise<any[]> {
  const res = await authFetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/problems`);
  if (!res.ok) {
    throw new Error(`Failed to load project problems (HTTP ${res.status})`);
  }
  return res.json();
}

export async function saveProblemToProjectApi(projectId: string, problem: any): Promise<any> {
  const res = await authFetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/problems`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(problem),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to save problem to project (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getProjectExperimentsApi(projectId: string): Promise<OptimizationRunRecord[]> {
  const res = await authFetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/experiments`);
  if (!res.ok) {
    throw new Error(`Failed to load experiment runs (HTTP ${res.status})`);
  }
  return res.json();
}

export async function saveExperimentApi(projectId: string, req: any): Promise<OptimizationRunRecord> {
  const res = await authFetch(`${API_BASE}/projects/${encodeURIComponent(projectId)}/experiments`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to save experiment run (HTTP ${res.status})`);
  }
  return res.json();
}

export async function getExperimentRunApi(runId: string): Promise<ExperimentDetailResponse> {
  const res = await authFetch(`${API_BASE}/experiments/${encodeURIComponent(runId)}`);
  if (!res.ok) {
    throw new Error(`Failed to load experiment run (HTTP ${res.status})`);
  }
  return res.json();
}
