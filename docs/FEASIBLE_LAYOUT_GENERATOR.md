# Feasible Rectangular Layout Generator (Phase 8)

## 1. Executive Summary & Purpose

The **Feasible Rectangular Layout Generator** is an independent, constructive layout synthesis engine designed to solve the Facility Layout Problem (FLP) directly from first principles without requiring an initial layout seed and without reading or copying coordinates from existing manual baselines.

In previous phases, constructive heuristics (CORELAP and ALDEP) demonstrated significant limitations when confronted with dense industrial layout problems:
- **CORELAP (Muther SLP heuristic)**: Because CORELAP places departments one by one around the centroid of already placed departments without global spatial partitioning, it left irregular non-rectangular voids and failed on `FLP_INDUSTRIAL_10` after placing only 3 of 10 departments.
- **ALDEP (Strip-sweep heuristic)**: Standard ALDEP relies on continuous serpentine ribbon sweeps that fragment departments across multiple bends, producing non-rectangular or irregular polygons unsuitable for rigid manufacturing cells.

The Feasible Rectangular Layout Generator resolves these fundamental geometric bottlenecks by implementing **combinatorial spatial partitioning and packing algorithms** that enforce 100% rectangular feasibility:
1. **Guillotine Row / Bay Packing**: High-efficiency multi-bay partition search reflecting real-world industrial plant design principles.
2. **Free-Rectangle DFS Backtracking**: Maximal Empty Rectangle (MER) detection with candidate anchor point placement and depth-first search.
3. **Area-Preserving Slicing Tree Decomposition**: Recursive orthogonal slicing with analytical area-proportional cut ratio calculation.

---

## 2. Target Problem: FLP_INDUSTRIAL_10

| Parameter | Value | Engineering Significance |
| :--- | :--- | :--- |
| **Facility Dimensions** | $150.0\,\text{m} \times 80.0\,\text{m}$ | Total facility footprint = $12,000\,\text{m}^2$ |
| **Department Count** | 10 departments | Industrial precision machinery cell |
| **Total Required Area** | $11,000.0\,\text{m}^2$ | High-density equipment installation |
| **Area Utilization** | **$91.67\%$** | Only $8.33\%$ ($1,000\,\text{m}^2$) slack space for aisles |
| **Shape Constraints** | Min/max width, height, aspect ratio $\le 3.0$ | Rigid machinery footprints |
| **Special Constraints** | Fixed positions, dock access, hazardous clearances | Multiple hard engineering requirements |
| **Manual Baseline Available** | `LAYOUT_SAMPLE_INDUSTRIAL_10` | Exists for post-run evaluation only; **never used as seed** |

---

## 3. Architecture & Algorithmic Modules

The generator is located in `backend/app/algorithms/generator/` and consists of five decoupled components:

```
backend/app/algorithms/generator/
├── __init__.py                  # Package exports
├── models.py                    # Config, result, strategy, and termination models
├── pre_feasibility.py           # PreFeasibilityAnalyzer (early physical verification)
├── slicing_decoder.py           # AreaPreservingSlicingDecoder (exact cut ratios)
├── search_free_rectangle.py     # FreeRectangleSearchEngine (MER DFS backtracking)
├── search_guillotine_packing.py # GuillotineRowPackingEngine (industrial bay packing)
└── solver.py                    # FeasibleLayoutGenerator (BaseLayoutAlgorithm facade)
```

### 3.1 Pre-Feasibility Analyzer (`PreFeasibilityAnalyzer`)
Prior to initiating combinatorial search, the problem undergoes rigorous pre-search verification:
- **Total Area Capacity**: Confirms $\sum_{i} A_i \le A_{\text{facility}}$.
- **Legal Dimension Feasibility**: Uses `LegalDimensionGenerator` to verify that every department has at least one legal $(w, h)$ rectangle satisfying $w \times h = A$, $w \in [w_{\min}, w_{\max}]$, $h \in [h_{\min}, h_{\max}]$, and $\max(w/h, h/w) \le \text{AR}_{\max}$ within the facility envelope.
- **Fixed Department Sanity**: Validates that pre-assigned department coordinates reside inside facility boundaries.
- **Reserved Zones Sanity**: Validates structural obstacles against plant perimeter.
- **Hard Constraints Consistency**: Verifies that constraints reference existing problem departments.

If any check fails, the generator terminates immediately with `PRE_FEASIBILITY_FAILED`, avoiding wasted search budget.

### 3.2 Area-Preserving Slicing Tree Decoder (`AreaPreservingSlicingDecoder`)
Based on Otten (1982) and Wong & Liu (1986):
- Evaluates binary slicing trees where internal nodes represent orthogonal cuts ($H$ or $V$) and leaves represent individual departments.
- Computes subtree required areas bottom-up:
  $$\text{Area}(u) = \text{Area}(u_{\text{left}}) + \text{Area}(u_{\text{right}})$$
- Computes analytical, area-proportional cut ratios:
  $$\alpha = \frac{\text{Area}(u_{\text{left}})}{\text{Area}(u_{\text{left}}) + \text{Area}(u_{\text{right}})}$$
- Partitions parent bounding boxes recursively and verifies that leaf dimensions respect min/max bounds and aspect ratio limits.

### 3.3 Free-Rectangle DFS Search Engine (`FreeRectangleSearchEngine`)
Implements depth-first search over continuous space:
- **Department Ordering**: Heuristics include `most_constrained_first`, `largest_area_first`, `flow_volume_descending`, and `relationship_weight_descending`.
- **Maximal Empty Rectangles (MER)**: Utilizes `FreeRectangleDetector` to identify valid open regions after each placement.
- **Candidate Placements**: Generates anchor coordinates (Bottom-Left, Top-Left, Bottom-Right, Top-Right) and aligns with existing department edges.
- **Deduplication & Feasibility Checking**: Validates candidates against `PlacementFeasibilityChecker` (boundaries, overlap, aspect ratio, reserved zones).
- **Backtracking & Budget Control**: Strict limits on `max_nodes`, `max_backtracks`, and `max_runtime_seconds`.

### 3.4 Guillotine Row Packing Engine (`GuillotineRowPackingEngine`)
Designed specifically for dense industrial facilities with $90\%+$ area utilization:
- Human facility planners organize machine cells along parallel logistics bays or aisles.
- The engine explores multi-bay horizontal/vertical partitions where departments within each bay share a uniform bay height or width.
- Candidate allocations systematically test valid row heights and department sequences to achieve exact $100\%$ area conservation with zero overlap.

### 3.5 Solver Facade (`FeasibleLayoutGenerator`)
Registered in `AlgorithmRegistry` under `"feasible_layout_generator"` and `"feasible_generator"`.
- Implements `BaseLayoutAlgorithm` interface: `solve(problem)` returns `LayoutSolution`.
- Rich interface: `solve_with_result(problem, config)` returns `Tuple[LayoutSolution, GeneratorResult]`.

---

## 4. Engineering Feasibility Guarantees

Every layout produced by the generator satisfies all strict feasibility requirements:

| Feasibility Rule | Mathematical Condition | Verification Tool |
| :--- | :--- | :--- |
| **Area Conservation** | $|w_i \cdot h_i - A_{i,\text{req}}| / A_{i,\text{req}} \le 0.05$ | `LayoutValidator` & `PlacementFeasibilityChecker` |
| **Dimension Bounds** | $w_i \in [w_{i,\min}, w_{i,\max}],\; h_i \in [h_{i,\min}, h_{i,\max}]$ | `LegalDimensionGenerator` |
| **Aspect Ratio Bounds** | $\max(w_i / h_i, h_i / w_i) \le \text{AR}_{i,\max}$ | `PlacementFeasibilityChecker` |
| **Facility Containment** | $x_i \ge 0, y_i \ge 0, x_i + w_i \le W_{\text{fac}}, y_i + h_i \le H_{\text{fac}}$ | `GeometryEngine` & `LayoutValidator` |
| **Zero Overlap** | $\text{Area}(B_i \cap B_j) = 0 \quad \forall i \neq j$ | `LayoutValidator.total_overlap_area == 0.0` |
| **Fixed Positions** | $(x_i, y_i) = (x_{i,\text{fixed}}, y_{i,\text{fixed}})$ | `PreFeasibilityAnalyzer` & `PlacementFeasibilityChecker` |
| **Reserved Zones** | $\text{Area}(B_i \cap R_k) = 0 \quad \forall i, k$ | `LayoutValidator` |
| **Hard Constraints** | Zero hard constraint violations | `EvaluationEngine.hard_violation_count == 0` |

---

## 5. Benchmark Performance & Comparative Results

### 5.1 Problem Execution Summary

| Problem | Algorithm Strategy | Placed / Total | Success | Runtime | Hard Violations | Termination Reason |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **FLP_ACADEMIC_4** | Guillotine Row Packing | **4 / 4 (100%)** | **True** | 0.0019s | 0 | `SUCCESS_FEASIBLE_FOUND` |
| **FLP_ACADEMIC_4** | Free Rectangle DFS | **4 / 4 (100%)** | **True** | 0.0021s | 0 | `SUCCESS_FEASIBLE_FOUND` |
| **FLP_MEDIUM_6** | Free Rectangle DFS | **6 / 6 (100%)** | **True** | 0.0022s | 0 | `SUCCESS_FEASIBLE_FOUND` |
| **FLP_INDUSTRIAL_10** | Free Rectangle DFS | 9 / 10 (90%) | False | 0.2987s | 0 | `SEARCH_BUDGET_EXHAUSTED` |
| **FLP_INDUSTRIAL_10** | Guillotine Row Packing | **10 / 10 (100%)** | **True** | **0.0110s** | **0** | **`SUCCESS_FEASIBLE_FOUND`** |

### 5.2 FLP_INDUSTRIAL_10: Generated Solution vs Manual Baseline

| Metric | Generated Feasible Layout (Guillotine) | Complete Manual Baseline (`sample_layout.json`) | Delta (%) |
| :--- | :---: | :---: | :---: |
| **Placed Departments** | **10 / 10 (100%)** | 10 / 10 (100%) | 0.0% |
| **Feasibility Status** | **100% Feasible** | 100% Feasible | Match |
| **Total Overlap Area** | **0.00 m²** | 0.00 m² | 0.0% |
| **Hard Violations** | **0** | 0 | 0 |
| **Soft Violations** | 1 | 0 | +1 |
| **Area Utilization** | 91.67% | 91.67% | 0.0% |
| **Material Handling Cost (MHC)** | **$180,263.94** | $139,498.75 | +29.2% |
| **Flow-Distance Score** | 153,551.14 | 117,893.75 | +30.2% |
| **Adjacency Satisfaction** | 44.17% | 55.47% | -11.3% |
| **Execution Runtime** | **0.011s** | N/A (Manual human design) | Instant |

> [!NOTE]
> The generated solution achieves **complete 10/10 rectangular feasibility in 11 milliseconds** from scratch without human intervention. Its higher MHC (\$180,263.94 vs \$139,498.75) is expected because the generator focuses on geometric feasibility construction rather than flow-cost pairwise optimization. This generated layout provides the ideal feasible starting seed for CRAFT improvement heuristics in subsequent phases.

---

## 6. Honest Failure Reporting & Benchmark Integrity

In adherence to Phase 5.1 and Phase 8 specifications:
- When a search strategy exhausts its node budget (e.g. Free Rectangle DFS on dense $91.7\%$ industrial packing placing 9 of 10 departments), the generator **does NOT fabricate coordinates or claim success**.
- It honestly returns `success=False`, `complete=False`, `termination_reason=SEARCH_BUDGET_EXHAUSTED`, and provides comprehensive `failure_diagnostics` recording candidate rejections by category (boundary, overlap, aspect ratio, capacity).
- Partial layouts are strictly excluded from apples-to-apples benchmark rankings.

---

## 7. API Endpoints & Frontend Integration

### 7.1 Backend API Endpoint
```http
POST /api/algorithms/feasible-generator/solve
Content-Type: application/json

{
  "problem_id": "FLP_INDUSTRIAL_10",
  "config": {
    "strategy": "guillotine_row_packing",
    "ordering_strategy": "most_constrained_first",
    "max_nodes": 3000,
    "max_backtracks": 1500,
    "max_runtime_seconds": 10.0,
    "max_shape_alternatives": 8,
    "candidate_limit_per_department": 12
  }
}
```

Response payload includes:
- `solution`: Standard `LayoutSolution` domain model.
- `result`: Rich `GeneratorResult` with search statistics and failure diagnostics.
- `validation`: `LayoutValidationResult` with overlap area and boundary verification.
- `evaluation`: Multi-criteria `EvaluationReport` (MHC, flow-distance, adjacency satisfaction).

### 7.2 Frontend User Interface
Integrated into `frontend/src/components/AlgorithmRunnerCard.tsx`:
- New dedicated tab: **Feasible Generator (Phase 8)**.
- Interactive controls for search strategy, department ordering, tree node budget, backtrack budget, timeout, shape alternatives, and candidate limits.
- Real-time rendering on 2D `<LayoutCanvas />`.
- Validation and multi-criteria evaluation scorecards.
- Diagnostic failure display with rejected candidate categories when search bounds are exceeded.
