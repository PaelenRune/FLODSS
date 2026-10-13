# CRAFT v1.0 — Computerized Relative Allocation of Facilities Technique

## 1. Algorithm Overview & Academic Foundation
**CRAFT** (*Computerized Relative Allocation of Facilities Technique*) is the seminal **improvement heuristic** in facility layout optimization, originally formulated by **Elwood S. Buffa, Gordon C. Armour, and Thomas E. Vollmann** in 1964.

In the Facility Layout Optimization & Decision Support System (FLODSS), CRAFT v1.0 is implemented as `craft_pairwise_rectangular_v1`. Its objective is to take an existing, valid, and complete initial layout and systematically reduce the total **Material Handling Cost (MHC)** through steepest-descent pairwise department exchanges.

### Core Philosophy: Construction vs. Improvement
- **CORELAP (Phase 5/5.1)** is a *construction heuristic*: It builds a layout from scratch using Muther Systematic Layout Planning (SLP) closeness relationships.
- **CRAFT (Phase 6)** is an *improvement heuristic*: It **never** constructs a layout from an empty floor. It requires a complete, physically feasible initial layout (e.g., from a completed CORELAP run, an industrial baseline, or user specifications).
- **Strict Precondition**: Incomplete or infeasible initial layouts are rejected upfront with explicit diagnostic errors.

---

## 2. Classical CRAFT vs. FLODSS v1 (`craft_pairwise_rectangular_v1`)

| Feature | Classical CRAFT (Buffa et al., 1964) | FLODSS Implementation (`craft_pairwise_rectangular_v1`) |
| :--- | :--- | :--- |
| **Representation** | Discrete Unit Cell Grid | Continuous 2D Rectangles (`ContinuousLayout`) |
| **Department Geometry** | Irregular aggregates of unit blocks | Bounded axis-aligned rectangles with width/height limits |
| **Department Reshaping** | Freeform reshaping of unequal areas | Strictly restricted to equal-geometry and 90° rotationally matching rectangles |
| **Exchange Type** | Pairwise (2-way) or 3-way | Pairwise (2-way) steepest descent |
| **Search Objective** | Pure Material Handling Cost (MHC) | Pure Material Handling Cost (MHC) |
| **Search Strategy** | Steepest descent (best improvement) | Steepest descent with deterministic lexicographical tie-breaking |
| **Hard Constraints** | Plant perimeter and fixed departments | Plant perimeter, non-overlap, reserved zones, and problem hard constraints |

> [!NOTE]
> Classical CRAFT on discrete grids frequently produced irregular, non-functional shapes ("splattered" departments). FLODSS operates in continuous rectangular space. In v1, arbitrary unequal rectangles cannot be exchanged without dynamic slicing or floor-plan packing. FLODSS v1 explicitly recognizes this geometric boundary and reports it with full academic transparency.

---

## 3. Department Exchange Eligibility

Two departments $A$ and $B$ are evaluated for pairwise exchange according to physical feasibility rules:

### 3.1 Fixed Department Protection
If either department $A$ or $B$ has a fixed position defined (via `Department.fixed_position` or a problem-level `ConstraintType.FIXED_POSITION` constraint), the pair is **ineligible** and cannot be moved:
$$\text{is\_fixed}(A) \lor \text{is\_fixed}(B) \implies \text{Ineligible}$$

### 3.2 Case 1: Equal-Geometry Rectangles (Direct Swap)
When both dimensions match within floating-point tolerance ($\epsilon = 10^{-4}$):
$$|w_A - w_B| \le \epsilon \quad \land \quad |h_A - h_B| \le \epsilon$$
Department $A$ moves to $(x_B, y_B)$ with $(w_A, h_A)$, and Department $B$ moves to $(x_A, y_A)$ with $(w_B, h_B)$. Because they trade identical bounding boxes, no exterior overlapping is created.

### 3.3 Case 2: 90° Rotational Match (Transverse Match)
When dimensions match inversely:
$$|w_A - h_B| \le \epsilon \quad \land \quad |h_A - w_B| \le \epsilon$$
If `allow_rotational_swaps` is enabled, $A$ and $B$ can exchange positions with a 90° rotation, provided:
1. Neither department has `fixed_orientation == True`.
2. Department $A$'s rotated dimensions $(h_A, w_A)$ satisfy $A$'s `min_width`, `max_width`, `min_height`, `max_height`, and `max_aspect_ratio`.
3. Department $B$'s rotated dimensions $(h_B, w_B)$ satisfy $B$'s dimensional constraints.

### 3.4 Case 3: Unequal Shapes
Unequal-dimension rectangles without valid transverse rotation cannot be exchanged directly in continuous rectangular space without altering neighboring department geometry.
- These pairs are marked **ineligible** in v1.
- Adjacent touching departments with unequal shapes are identified and reported in the diagnostic metadata (`unequal_adjacent_pairs`) as candidates for future continuous slicing engines.

---

## 4. Candidate Swap Validation & Feasibility Preservation

For every eligible pair $(A, B)$, the candidate layout is validated before scoring:
1. **Perimeter Containment**: All departments remain inside the facility $[0, W] \times [0, H]$.
2. **Volumetric Non-Overlap**: $\text{OverlapArea}(P_i, P_j) \le \epsilon$ for all department pairs.
3. **Reserved Zones**: Zero overlap with structural columns or safety corridors.
4. **Hard Constraints**: Evaluated via `ConstraintEngine`. Any violation with `classification == HARD` immediately disqualifies the candidate.

Only **strictly feasible** candidate swaps are evaluated for cost reduction.

---

## 5. Objective Function: Material Handling Cost (MHC)

CRAFT optimizes purely the **Material Handling Cost (MHC)**:

$$\text{MHC} = \sum_{k \in \mathcal{F}} f_k \cdot d(c_{\text{src}(k)}, c_{\text{tgt}(k)}) \cdot c_k$$

Where:
- $\mathcal{F}$ is the set of directed flows between departments.
- $f_k$ is the flow intensity (loads/period).
- $c_k$ is the handling cost per unit distance (default: $1.0$).
- $c_i = (x_i + \frac{w_i}{2}, y_i + \frac{h_i}{2})$ is the geometric centroid of department $i$.
- $d(c_i, c_j)$ is the centroid distance. By default, **Manhattan / Rectilinear distance** ($L_1$) is used, representing orthogonal plant aisles:
  $$d_{\text{Manhattan}}(c_i, c_j) = |x_i - x_j| + |y_i - y_j|$$

### Multi-Objective Decoupling
During the search loop, CRAFT optimizes **exclusively** MHC. No relationship scores or arbitrary penalties are blended into the search objective. Following optimization, the complete suite of multi-objective metrics (Flow-Distance, Relationship Satisfaction, Area Utilization, Soft Constraint Penalties) is computed and reported via the standardized `EvaluationEngine`.

---

## 6. Optimization Loop & Deterministic Tie-Breaking

1. **Initialization**: Set $L^{(0)} = \text{initial\_layout}$ and compute $\text{MHC}^{(0)}$.
2. **Iteration $t \ge 1$**:
   - Enumerate all eligible department pairs $(A, B)$ sorted lexicographically by $(A, B)$ with $A < B$.
   - For each eligible pair, construct candidate layout $L_{(A,B)}$ and validate feasibility.
   - For feasible candidates, calculate candidate cost $\text{MHC}_{(A,B)}$ and improvement:
     $$\Delta\text{MHC}_{(A,B)} = \text{MHC}^{(t-1)} - \text{MHC}_{(A,B)}$$
   - Select the candidate with the maximum improvement:
     $$(A^*, B^*) = \arg\max_{(A, B)} \Delta\text{MHC}_{(A,B)}$$
   - **Deterministic Tie-Breaking**: If multiple pairs achieve the identical improvement within numerical tolerance ($10^{-6}$), the pair with the lexicographically smaller department IDs is selected.
3. **Acceptance Criterion**:
   - If $\Delta\text{MHC}^* > \text{min\_improvement\_threshold}$ (default: $0.01$):
     Accept swap: $L^{(t)} = L_{(A^*, B^*)}$, update $\text{MHC}^{(t)} = \text{MHC}^*$, and record trace.
   - Else: Terminate search with `NO_IMPROVING_SWAP`.
4. **Stopping Conditions**:
   - `NO_IMPROVING_SWAP`: No candidate swap achieves an improvement exceeding the threshold.
   - `NO_ELIGIBLE_SWAPS`: No physically eligible candidate swaps exist.
   - `MAX_ITERATIONS_REACHED`: Optimization loop reaches the user-defined iteration limit.

### Non-Increasing Invariant
Because a swap is accepted only if $\Delta\text{MHC} > \text{min\_improvement\_threshold} > 0$, the Material Handling Cost is strictly non-increasing across all iterations:
$$\text{MHC}^{(t)} < \text{MHC}^{(t-1)} \quad \forall t \ge 1$$

---

## 7. Academic Verification & Hand Calculations

### 7.1 Three-Department Hand-Calculated Fixture
Consider three $10 \times 10$ m departments placed along the X-axis in a $50 \times 20$ m facility:
- Department A: origin $(0, 0)$, centroid $(5, 5)$
- Department B: origin $(10, 0)$, centroid $(15, 5)$
- Department C: origin $(20, 0)$, centroid $(25, 5)$

**Flows**:
- Flow 1: A $\to$ C = $10$ loads/day, unit cost = $1.0$. Distance $d(A, C) = |25 - 5| = 20$ m. Cost = $200.0$.
- Flow 2: B $\to$ C = $2$ loads/day, unit cost = $1.0$. Distance $d(B, C) = |25 - 15| = 10$ m. Cost = $20.0$.
- **Initial MHC**: $200.0 + 20.0 = 220.0$.

**Iteration 1 Candidate Swaps**:
1. Swap $(A, B)$:
   - A at $(10, 0)$, B at $(0, 0)$, C at $(20, 0)$.
   - $d(A, C) = 10 \implies 10 \times 10 = 100$.
   - $d(B, C) = 20 \implies 2 \times 20 = 40$.
   - $\text{MHC} = 140.0$, Improvement $\Delta\text{MHC} = 220 - 140 = 80.0$.
2. Swap $(B, C)$:
   - A at $(0, 0)$, B at $(20, 0)$, C at $(10, 0)$.
   - $d(A, C) = 10 \implies 10 \times 10 = 100$.
   - $d(B, C) = 10 \implies 2 \times 10 = 20$.
   - $\text{MHC} = 120.0$, Improvement $\Delta\text{MHC} = 220 - 120 = 100.0$. (**Unique Optimum**)
3. Swap $(A, C)$:
   - $d(A, C) = 20, d(B, C) = 10 \implies \text{MHC} = 220.0$, $\Delta\text{MHC} = 0.0$.

**Result**:
Candidate $(B, C)$ achieves the highest improvement ($100.0$) and is accepted.
In Iteration 2, evaluating all candidate swaps reveals no further cost reduction ($\Delta\text{MHC} \le 0$). CRAFT terminates with `NO_IMPROVING_SWAP`. Final MHC = $120.0$ (verified in `backend/tests/test_craft.py`).

### 7.2 Single Flow with Fixed Receiving Dock
When Department A is fixed at $(0, 0)$ (representing a fixed receiving dock) with a single flow A $\to$ C = $10$ loads/day:
- Initial placement: A at $(0, 0)$, B at $(10, 0)$, C at $(20, 0)$.
- Distance $d(A, C) = 20 \implies \text{Initial MHC} = 200.0$.
- Because A is fixed, only pair $(B, C)$ is eligible.
- Swapping B $\leftrightarrow$ C places C adjacent to A at $(10, 0)$. Distance $d(A, C) = 10$.
- **Final MHC**: $10 \times 10 = 100.0$ (Improvement: $100.0$, $50.0\%$).

---

## 8. Benchmark Results & Scientific Diagnostics

### Benchmark 1: `FLP_MEDIUM_6` (6 Departments)
- **Initial Layout Source**: Completed CORELAP v1.0 solution.
- **Initial Feasibility**: True (100% placed, zero overlaps).
- **Initial MHC**: **$53,510.00**
- **Accepted Swaps**: 2 exchanges:
  1. `DEP_ASSEMBLY` $\leftrightarrow$ `DEP_RECEIVING` (Equal geometry: $20.0 \times 40.0$ m).
  2. `DEP_TESTING` $\leftrightarrow$ `DEP_PACKAGING` (Equal geometry: $15.0 \times 33.33$ m).
- **Final MHC**: **$39,830.00**
- **Absolute Improvement**: **-$13,680.00**
- **Percentage Improvement**: **25.57%**
- **Termination Reason**: `NO_IMPROVING_SWAP`

### Benchmark 2: `FLP_INDUSTRIAL_10` (10 Departments)
- **Initial Layout Source**: Complete manual engineering baseline (`LAYOUT_SAMPLE_INDUSTRIAL_10`).
- **Initial Feasibility**: True (100% placed, zero overlaps).
- **Initial MHC**: **$139,498.75**
- **Accepted Swaps**: 0 exchanges.
- **Final MHC**: **$139,498.75**
- **Improvement**: $0.00 (0.00%)
- **Termination Reason**: `NO_IMPROVING_SWAP`

> [!IMPORTANT]
> **Scientific Integrity Analysis on `FLP_INDUSTRIAL_10`**:
> In the 10-department industrial layout, only two pairs share equal dimensions:
> - `DEP_RAW_MATERIAL` ($32.5 \times 40$) vs `DEP_FINISHED_GOODS` ($32.5 \times 40$)
> - `DEP_WELDING` ($27.5 \times 40$) vs `DEP_SURFACE_TREAT` ($27.5 \times 40$)
>
> Swapping `RAW_MATERIAL` (at the intake dock $x=0$) with `FINISHED_GOODS` (at the shipping dock $x=110$) drastically increases the transport distance for high-volume raw sheet delivery into `CUTTING`, severely worsening MHC. Swapping `WELDING` and `SURFACE_TREAT` increases distances to `MACHINING` and `ASSEMBLY`.
> Consequently, **no eligible exchange reduces MHC**.
> CRAFT terminates immediately with `NO_IMPROVING_SWAP`. This is an honest, mathematically sound finding: the manual layout is already a local optimum with respect to pairwise swaps of matching rectangles.

---

## 9. API & Execution Architecture

### Endpoint
`POST /api/algorithms/craft/solve`

### Request Payload (`CRAFTSolveRequest`)
```json
{
  "problem_id": "FLP_MEDIUM_6",
  "initial_layout_id": "LAYOUT_SAMPLE_INDUSTRIAL_10",
  "config": {
    "max_iterations": 50,
    "min_improvement_threshold": 0.01,
    "allow_rotational_swaps": true,
    "trace_level": "SUMMARY"
  }
}
```

### Response Payload (`CRAFTSolveResponse`)
- `solution`: Standard domain `LayoutSolution`.
- `continuous_layout`: Optimized continuous layout.
- `initial_layout`: Baseline layout.
- `result`: `CRAFTSolverResult` with iteration count, accepted swaps, initial/final MHC, and percentage improvement.
- `initial_evaluation` & `final_evaluation`: Standardized reports from `EvaluationEngine`.
- `trace`: Step-by-step diagnostic log (`CRAFTExecutionTrace`).

---

## 10. Scope Boundaries

This implementation is restricted to **Phase 6: CRAFT Improvement Heuristic v1**.
The following capabilities are explicitly deferred to future phases:
- Three-way exchanges (3-way CRAFT)
- Dynamic slicing-tree or free-form department reshaping
- ALDEP (Automated Layout Design Program)
- Genetic Algorithms (GA) & Simulated Annealing (SA)
- Non-dominated Sorting Genetic Algorithm II (NSGA-II)
- Mixed-Integer Linear Programming (MILP)
- Gemini AI Decision Support
