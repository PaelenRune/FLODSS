# Large Factory Empirical Investigation: FLP_INDUSTRIAL_10

**Document Reference:** `experiments/reports/LARGE_FACTORY_INVESTIGATION.md`  
**Evaluation Target:** `FLP_INDUSTRIAL_10` (Precision Machinery Manufacturing Plant, 10 Departments, Facility: $150.0 \times 80.0\,\text{m}$, Total Area: $12{,}000\,\text{m}^2$, Required Dept Area: $11{,}000\,\text{m}^2$, Net Area Utilization: $91.67\%$)  
**Benchmark Suite:** Phase 7.1 Cross-Algorithm Evaluation (CORELAP v1.0, ALDEP v1.0, CRAFT v1.0, Manual Baseline)  
**Execution Timestamp:** 2026-10-08  
**Run ID:** `bench_20261008_143223`  

---

## 1. Executive Summary

This empirical report documents the performance, mathematical behavior, geometric feasibility, and structural failure modes of classical construction heuristics (CORELAP and ALDEP) and improvement heuristics (CRAFT) on the complex 10-department industrial benchmark **`FLP_INDUSTRIAL_10`**.

Under the **Scientific Integrity Protocol**, no problem parameters, department required areas, facility dimensions, or hard constraints were altered. Incomplete and infeasible candidate solutions are strictly excluded from comparative cost rankings.

---

## 2. Direct Answers to Core Research Questions

### Q1: Did ALDEP place 10/10 departments?
**Answer:** **Yes, in the discrete grid representation (`GridLayout`).**  
In all 100 stochastic trials across 5 seeds (`[42, 101, 2024, 777, 999]`), ALDEP placed **10 out of 10 departments** onto the $30 \times 16$ discrete grid cells (cell size $L_{\text{cell}} = 5.0\,\text{m}$, total grid capacity: 480 cells, required cells: 440 cells). Every required department cell was allocated with zero cell-level collisions on the discrete grid.

### Q2: Out of 100 trials, how many complete solutions were produced?
**Answer:** **100 / 100 trials (100.0% completion rate).**  
Every single trial completed the strip-sweep sequence and placed all 10 departments. No department remained unplaced (`unplaced_departments = []`).

### Q3: Out of 100 trials, how many feasible solutions were produced?
**Answer:** **0 / 100 trials (0.0% feasibility rate).**  
When ALDEP's discrete grid allocations were mapped to the continuous block layout space (`ContinuousLayout`), **zero candidate solutions satisfied all continuous geometric constraints**.

### Q4: What was the primary failure reason in failed trials?
**Answer:** The failures stem from two interrelated geometric violations during continuous conversion:
1. **Continuous Bounding Box Overlaps:** In classical ALDEP (`allow_strip_splitting = True`), departments wrap around strip boundaries in a serpentine sweep, forming L-shaped, U-shaped, or fragmented geometry. When represented in continuous CAD/block space as minimal bounding boxes `[x, y, width, height]`, departments wrapping across strips enclose space occupied by neighboring departments, generating hard overlap violations ($> 0.0\,\text{m}^2$).
2. **Department Dimensional Constraint Violations:** Specific departments have strict minimum width constraints (e.g. `DEP_MACHINING` $W_{\min} = 30.0\,\text{m}$, `DEP_RAW_MATERIAL` $W_{\min} = 25.0\,\text{m}$, `DEP_SURFACE_TREAT` $W_{\min} = 25.0\,\text{m}$). With strip width $W_{\text{strip}} = 2 \times 5.0\,\text{m} = 10.0\,\text{m}$, department strip sections have widths of only $10.0\,\text{m}$, directly violating architectural width bounds.

### Q5: What was the effect of grid discretization?
**Answer:** Grid discretization creates a fundamental tension:
- **Discretization Rounding:** With cell size $L_{\text{cell}} = 5.0\,\text{m}$ (area $25\,\text{m}^2$/cell), continuous department areas are quantized into integer cell counts. For `FLP_INDUSTRIAL_10`, total required area is $11{,}000\,\text{m}^2 = 440$ cells out of $12{,}000\,\text{m}^2 = 480$ grid cells (91.67% cell occupancy).
- **Aspect Ratio Distortion:** While discrete cell connectivity is preserved on the grid graph, continuous bounding boxes of wrapped departments produce distorted aspect ratios ($\lambda = \frac{L_{\text{bbox}}}{W_{\text{bbox}}} > 3.0$), causing bounding box inflation and mutual collision.
- **Parametric Sensitivity:** Testing across cell sizes ($2.5\,\text{m}, 5.0\,\text{m}, 10.0\,\text{m}$) and strip widths ($2, 4, 6, 8$) demonstrated that while wider strips reduce wrap count, they increase vertical spillover, leaving zero parameter combinations capable of generating 100% strictly non-overlapping rectangular blocks in dense ($91.7\%$) space.

### Q6: How did the failure modes of CORELAP and ALDEP differ?
**Answer:** CORELAP and ALDEP exhibit diametrically opposed failure modes:
| Dimension | CORELAP (Continuous Block Heuristic) | ALDEP (Discrete Grid Heuristic) |
| :--- | :--- | :--- |
| **Space Representation** | Continuous $\mathbb{R}^2$ coordinate blocks with rigid rectangular dimensions | Discrete $\mathbb{Z}^2$ grid cells ($30 \times 16$ array) |
| **Placement Mechanism** | Greedy boundary-touching candidate search ($C > 5{,}000$ points) | Deterministic serpentine strip-sweep filling |
| **Department Shape** | Strictly rectangular ($W \times H$ guaranteed) | Serpentine / irregular multi-cell clusters |
| **Placed Count** | **5 / 10 departments placed** (5 unplaced) | **10 / 10 departments placed** (0 unplaced) |
| **Failure Point** | **Geometric fragmentation exhaustion**: After placing 5 departments, remaining rectangular space is fragmented into non-contiguous pockets too small for the remaining large departments (`DEP_ASSEMBLY`, `DEP_FINISHED_GOODS`). | **Continuous conversion incompatibility**: Discrete cells are 100% valid, but irregular serpentine shapes cannot be represented as non-overlapping continuous rectangles. |
| **Feasibility Outcome** | Incomplete layout $\to$ Infeasible | Complete on grid $\to$ Infeasible in continuous space |

### Q7: If feasible ALDEP solutions exist, did they achieve better MHC than the manual baseline?
**Answer:** **No feasible ALDEP solutions were produced (0 / 100).**  
Because all 100 candidates violate continuous geometric feasibility, their raw mathematical handling cost is not academically comparable to the complete manual baseline. Under our Scientific Integrity Protocol, infeasible solutions cannot claim superiority.  
*(Diagnostic note: Raw unvalidated grid-level MHC for ALDEP candidates averaged $\sim 56{,}000$, but this theoretical value is invalid due to overlapping spatial boundaries.)*

### Q8: Did CRAFT improve feasible ALDEP solutions?
**Answer:** **CRAFT could not be executed on ALDEP solutions for `FLP_INDUSTRIAL_10`.**  
CRAFT is an improvement heuristic requiring a strictly valid and feasible initial continuous layout (`LayoutValidator.validate(problem, initial_layout) == True`). Since no ALDEP candidate met the feasibility criteria, CRAFT rejected them to prevent propagating geometric corruption.  
When executed on the **Manual Baseline** (`LAYOUT_SAMPLE_INDUSTRIAL_10`, Initial MHC: $139{,}498.75$), CRAFT evaluated all eligible pairwise exchanges and terminated with `NO_IMPROVING_SWAP` ($0$ accepted swaps), confirming that the manual baseline represents a strict local optimum under rectangular department swap constraints.

---

## 3. Detailed Data Breakdown for `FLP_INDUSTRIAL_10`

### 3.1 ALDEP Multi-Seed Campaign Results

- **Total Trials Evaluated:** 100
- **Random Seeds Evaluated:** `[42, 101, 2024, 777, 999]` (20 candidates per seed)
- **Unique Layout Signatures Produced:** 59
- **Duplicate Layouts Detected:** 41 (41.0% duplicate rate across the campaign)
- **Grid Placement Completeness:** 100 / 100 (100.0%)
- **Continuous Geometric Feasibility:** 0 / 100 (0.0%)
- **Mean Execution Time per Trial:** $0.01397\,\text{s}$
- **Total Campaign Runtime:** $1.397\,\text{s}$

### 3.2 CORELAP Deterministic Run Results

- **Mode:** `classical_adjacency` (center anchor)
- **Departments Placed:** 5 (`DEP_CUTTING`, `DEP_MACHINING`, `DEP_RAW_MATERIAL`, `DEP_MAINTENANCE`, `DEP_WELDING`)
- **Departments Unplaced:** 5 (`DEP_ASSEMBLY`, `DEP_FINISHED_GOODS`, `DEP_QUALITY`, `DEP_SHIPPING`, `DEP_SURFACE_TREAT`)
- **Termination Reason:** `FAILED_NO_FEASIBLE_CANDIDATE`
- **Rejection Diagnostics:**
  - Out of Bounds Rejections: $3{,}306$ candidate positions
  - Overlap with Placed Departments: $1{,}784$ candidate positions
  - Overlap with Reserved Zones: $0$
- **Runtime:** $0.5069\,\text{s}$

### 3.3 CRAFT Improvement Heuristic Run Results

- **Initial Baseline Source:** Expert Manual Engineering Baseline (`LAYOUT_SAMPLE_INDUSTRIAL_10`)
- **Initial Material Handling Cost:** $139{,}498.75$
- **Final Material Handling Cost:** $139{,}498.75$
- **Accepted Swaps:** $0$
- **Percentage Improvement:** $0.00\%$
- **Termination Reason:** `NO_IMPROVING_SWAP`
- **Runtime:** $0.0115\,\text{s}$

---

## 4. Methodological Conclusions and Recommendations for Metaheuristics (Phase 8+)

1. **Classic Heuristic Bottleneck in Dense Layouts:** Both CORELAP (1967) and ALDEP (1967) fail to provide feasible solutions for high-density industrial facilities ($\ge 90\%$ area utilization, 10 departments) with rigid dimensional requirements.
2. **Need for Flexible Representation in Phase 8:** Future metaheuristic stages (Genetic Algorithm, Simulated Annealing) must utilize flexible representation techniques such as:
   - Slicing Tree (Normalized Polish Expression)
   - Sequence-Pair representation
   - Flexible Bay Structure (FBS)
   These representations inherently guarantee 100% non-overlapping rectangular department geometry while dynamically adjusting aspect ratios.
