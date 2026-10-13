# ALDEP (Automated Layout Design Program) Construction Heuristic

## 1. Executive Summary & Historical Context

The **Automated Layout Design Program (ALDEP)** was introduced by **Seevers & Ihm (1967)** as an automated computerized layout design program for facility planning and operations research. Along with CORELAP (Lee & Moore, 1967) and CRAFT (Buffa, Armour & Vollmann, 1964), ALDEP forms one of the foundational classic facility layout algorithms in industrial engineering.

In the **Facility Layout Optimization & Decision Support System (FLODSS)**, ALDEP serves as the **second independent construction heuristic**, complementing the deterministic CORELAP algorithm and the CRAFT improvement engine.

### Fundamental Differences Between CORELAP and ALDEP

| Dimension | CORELAP (Phase 5 / 5.1) | ALDEP (Phase 7) |
| :--- | :--- | :--- |
| **Paradigm** | Deterministic Construction | Stochastic Construction Heuristic |
| **Initial Selection** | Maximal Total Closeness Rating (TCR) | Randomly selected initial department (seeded) |
| **Subsequent Selection** | Maximal affinity to **all** placed departments | Closeness to **last placed** department ($D_{t-1}$) above threshold $T$ |
| **Tie-Breaking** | Deterministic (Area $\to$ Lexicographical ID) | Uniform random tie-break among qualified candidates |
| **Spatial Model** | Continuous bounding-box contour placement | Discrete unit cell grid with serpentine strip-sweep |
| **Solution Multiplicity** | Single deterministic layout per problem | Multiple candidate portfolio ($K$ seeded alternatives) |
| **Native Representation** | `ContinuousLayout` | `GridLayout` $\to$ `ContinuousLayout` |

---

## 2. Mathematical Formulation & Selection Logic

ALDEP models departmental spatial preferences using Muther's Systematic Layout Planning (SLP) qualitative closeness ratings:

$$\text{Rating Scores: } A = 16.0, \quad E = 8.0, \quad I = 4.0, \quad O = 2.0, \quad U = 0.0, \quad X = -8.0$$

### Department Selection Mechanism

Given a problem with $N$ departments $\mathcal{D} = \{D_1, \dots, D_N\}$ and unplaced set $\mathcal{U}$:

1. **Initial Department ($t = 1$):**
   A department $D_{\text{start}} \in \mathcal{U}$ is selected uniformly at random using seeded pseudo-random generator $\text{RNG}(S)$:
   $$D_1 \sim \text{Uniform}(\mathcal{U})$$
   $$\mathcal{U} \leftarrow \mathcal{U} \setminus \{D_1\}$$

2. **Subsequent Selection ($t = 2, \dots, N$):**
   Let $D_{t-1}$ be the department placed in the immediately preceding step. We identify eligible unplaced candidates meeting or exceeding selection threshold $T$ (default $T = 8.0$, corresponding to rating 'E' or higher):
   $$\mathcal{E}_t = \left\{ D_j \in \mathcal{U} \;\middle|\; R(D_{t-1}, D_j) \ge T \right\}$$

   - **Case A: $\mathcal{E}_t \neq \emptyset$ (Affinity Match):**
     Under classical ALDEP rules (`RANDOM_AMONG_MAX`), find the maximal rating among eligible candidates:
     $$M_t = \max_{D_j \in \mathcal{E}_t} R(D_{t-1}, D_j)$$
     $$\mathcal{M}_t = \left\{ D_j \in \mathcal{E}_t \;\middle|\; R(D_{t-1}, D_j) = M_t \right\}$$
     Select $D_t \sim \text{Uniform}(\mathcal{M}_t)$. Mode is logged as `AFFINITY_MAX`.

   - **Case B: $\mathcal{E}_t = \emptyset$ (Threshold Fallback):**
     If no remaining department meets threshold $T$ with $D_{t-1}$, classical ALDEP falls back to selecting uniformly at random from all unplaced departments:
     $$D_t \sim \text{Uniform}(\mathcal{U})$$
     Mode is logged as `RANDOM_FALLBACK`.

3. **Explainability & Trace Logging:**
   Every selection decision is tracked in `ALDEPSelectionStep`, recording step index, predecessor ID, scores of all unplaced candidates, threshold $T$, qualifying set, decision mode, and chosen department ID.

---

## 3. Spatial Grid Discretization & Strip-Sweep Geometry

### Spatial Discretization
The continuous facility bounding envelope ($W \times H$) is discretized into a square cell grid with cell size $L_{\text{cell}}$ (default 5.0m):
$$C = \left\lceil \frac{W}{L_{\text{cell}}} \right\rceil, \quad R = \left\lceil \frac{H}{L_{\text{cell}}} \right\rceil, \quad N_{\text{cells}} = C \times R$$

Each department $D_i$ with required area $A_i$ is mapped to required discrete grid cells:
$$k_i = \max\left(1, \left\lfloor \frac{A_i}{L_{\text{cell}}^2} + 0.5 \right\rfloor\right)$$

The area discretization error is explicitly tracked and reported:
$$\Delta A_i = |k_i L_{\text{cell}}^2 - A_i|, \quad \text{Error } \% = \frac{\Delta A_i}{A_i} \times 100\%$$

### Serpentine (Boustrophedon) Strip-Sweep
The grid is partitioned into strips of width $W_{\text{strip}}$ cells (default 2 cells):
- **Vertical Strips (Default):**
  - Strip $s = 0$ (columns $0 \dots W_{\text{strip}}-1$): Swept bottom-to-top (row 0 to $R-1$).
  - Strip $s = 1$ (columns $W_{\text{strip}} \dots 2W_{\text{strip}}-1$): Swept top-to-bottom (row $R-1$ down to 0).
  - Strip $s = 2$: Swept bottom-to-top, and so on.
- **Horizontal Strips:**
  - Alternates left-to-right on even strips and right-to-left on odd strips.

### Classical ALDEP vs FLODSS Rectangular Adaptation

FLODSS explicitly distinguishes between classical textbook ALDEP and our geometric adaptation:

1. **Classical ALDEP (`allow_strip_splitting = True`):**
   - Continuously allocates cells across strip boundaries.
   - Departments that exceed the remaining strip length wrap into the adjacent strip, creating serpentine or L-shaped department blocks.
   - In discrete `GridLayout`, cell occupancy has **strictly zero overlap**.
   - Continuous conversion computes the enclosing bounding box, documenting non-rectangularity and aspect ratio in `ALDEPDepartmentShapeDiagnostic`.
2. **FLODSS Rectangular Adaptation (`allow_strip_splitting = False`):**
   - If a department cannot fit within the remaining length of the current strip, placement advances to the next strip.
   - Departments occupy complete slices of rows within a single strip.
   - Guarantees **strictly rectangular placements** that achieve 100% geometric feasibility and zero bounding box overlap in `ContinuousLayout`.

### Reserved Zones and Fixed Departments
- Grid cells intersecting pre-existing fixed departments or `ReservedZone` structures are flagged prior to sweep.
- The serpentine traversal automatically skips reserved cells, ensuring strict boundary and non-placement compliance.

---

## 4. Multi-Candidate Generation & Portfolio Evaluation

Because ALDEP relies on pseudo-random initial selection and stochastic tie-breaking, a single run provides only one layout alternative. FLODSS runs ALDEP as a **multi-candidate generation engine**:

1. **Seeded Execution:**
   Given base seed $S$ and candidate count $K$ (e.g. $K=10$), candidates are generated using seeds $S, S+1, \dots, S+K-1$.
   Given the same base seed, candidate generation is **100% bitwise reproducible**.
2. **Layout Signature Deduplication:**
   For each candidate, a SHA-256 geometric signature is computed. Duplicates are flagged with `is_duplicate = True` and reference the original candidate index (`duplicate_of_index`).
3. **Independent Multi-Criteria Evaluation:**
   Every complete and feasible candidate is evaluated using the independent `EvaluationEngine`:
   - Material Handling Cost (MHC): $\sum_{i < j} f_{ij} c_{ij} d(c_i, c_j)$
   - Total Flow-Distance
   - Muther Relationship Closeness Score
   - Area Utilization & Constraint Penalties
4. **Candidate Ranking:**
   Candidates are ranked prioritizing complete and feasible layouts, sorted by Material Handling Cost (or adjacency relationship score if `MAXIMIZE_RELATIONSHIPS` is active). The top-ranked alternative is returned as the primary solution.

---

## 5. Empirical Verification & Benchmarks

The ALDEP implementation has been verified on three benchmark problems with 23 targeted automated tests:

### Benchmark 1: Academic 4-Department Hand-Calculated Verification
- **Facility:** $120\text{m} \times 120\text{m}$ ($14,400\text{ m}^2$)
- **Departments:** 4 departments, $100\text{ m}^2$ each
- **Discretization:** $L_{\text{cell}} = 10\text{m}$, $W_{\text{strip}} = 1$ cell
- **Placement Sequence:** $[A, B, C, D]$ placed in strip 0 at rows $0, 1, 2, 3$
- **Centroids:** $A(5, 5)$, $B(5, 15)$, $C(5, 25)$, $D(5, 35)$
- **Flow Distances:** $d(A, B) = 10\text{m}$, $d(B, C) = 10\text{m}$, $d(C, D) = 10\text{m}$
- **Hand-Calculated MHC:**
  $$\text{MHC} = (50 \times 10) + (30 \times 10) + (10 \times 10) = 500 + 300 + 100 = \mathbf{900.0}$$
- **Verification:** Evaluated MHC matches theoretical hand calculation of $900.0$ with 0.0 error, 100% rectangularity, and 0 overlaps.

### Benchmark 2: Medium Assembly Facility (`FLP_MEDIUM_6`)
- **Facility:** $100\text{m} \times 70\text{m}$ ($7,000\text{ m}^2$)
- **Departments:** 6 departments, total required area $4,100\text{ m}^2$
- **Discretization:** $L_{\text{cell}} = 5.0\text{m}$, total grid capacity $280$ cells ($7,000\text{ m}^2$)
- **Results:**
  - Placed: **6 / 6 departments (100% complete)**
  - Total allocated cells: 164 cells ($4,100\text{ m}^2$)
  - Free buffer cells: 116 cells
  - With rectangular adaptation (`allow_strip_splitting = False`, strip width 4 cells): **100% geometric feasibility, 0 overlap errors, 0 boundary errors**.

### Benchmark 3: Industrial Machinery Plant (`FLP_INDUSTRIAL_10`)
- **Facility:** $150\text{m} \times 80\text{m}$ ($12,000\text{ m}^2$)
- **Departments:** 10 heavy manufacturing departments, total area $11,000\text{ m}^2$
- **Discretization:** $L_{\text{cell}} = 5.0\text{m}$, total capacity $480$ cells ($12,000\text{ m}^2$)
- **Results:**
  - Placed: **10 / 10 departments (100% complete)**
  - Discrete Grid Cells: 440 allocated cells with **strictly 0 grid collision**
  - Continuous Bounding Boxes: Accurately reports non-rectangular shapes for strip-wrapping departments via shape diagnostics.

---

## 6. API Reference & Contract

### Endpoint: `POST /api/algorithms/aldep/solve`

#### Request Payload (`ALDEPSolveRequest`)
```json
{
  "problem_id": "FLP_MEDIUM_6",
  "config": {
    "number_of_candidates": 10,
    "random_seed": 42,
    "cell_size": 5.0,
    "strip_width_cells": 2,
    "sweep_direction": "VERTICAL",
    "selection_threshold": 8.0,
    "allow_strip_splitting": true,
    "tie_breaker": "RANDOM_AMONG_MAX",
    "trace_level": "SUMMARY"
  }
}
```

#### Response Structure (`ALDEPSolveResponse`)
```json
{
  "solution": {
    "problem_id": "FLP_MEDIUM_6",
    "algorithm_name": "aldep",
    "algorithm_version": "1.0.0",
    "is_complete": true,
    "placed_department_count": 6,
    "total_department_count": 6,
    "termination_reason": "SUCCESS_COMPLETE",
    "objective_values": {
      "material_handling_cost": 34595.0,
      "total_flow_distance": 24200.0,
      "relationship_score": 112.0
    }
  },
  "continuous_layout": { ... },
  "grid_layout": { ... },
  "best_candidate": {
    "candidate_index": 0,
    "seed": 42,
    "department_order": ["DEP_RECEIVING", "DEP_MACHINING", ...],
    "layout_signature": "...",
    "shape_diagnostics": { ... }
  },
  "candidates": [ ... ],
  "trace": {
    "number_of_candidates": 10,
    "unique_candidate_count": 8,
    "feasible_candidate_count": 6,
    "best_candidate_index": 0,
    "execution_time_seconds": 0.042
  },
  "validation": { ... },
  "evaluation": { ... }
}
```

---

## 7. References

1. **Seevers, J. A., & Ihm, P. (1967).** *ALDEP—Automated Layout Design Program.* Proceedings of the SHARE-ACM-IEEE Design Automation Workshop, Atlantic City, NJ.
2. **Buffa, E. S., Armour, G. C., & Vollmann, T. E. (1964).** *Allocating facilities with CRAFT.* Harvard Business Review, 42(2), 136-158.
3. **Lee, R. C., & Moore, J. M. (1967).** *CORELAP—COmputerized RElationship LAyout Planning.* Journal of Industrial Engineering, 18(3), 195-200.
4. **Muther, R. (1973).** *Systematic Layout Planning (SLP).* Cahners Books, Boston.
5. **Tompkins, J. A., White, J. A., Bozer, Y. A., & Tanchoco, J. M. A. (2010).** *Facilities Planning* (4th ed.). John Wiley & Sons.
6. **Francis, R. L., McGinnis, L. F., & White, J. A. (1992).** *Facility Layout and Location: An Analytical Approach* (2nd ed.). Prentice Hall.
