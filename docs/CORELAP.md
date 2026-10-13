# CORELAP v1.0 — Computerized Relationship Layout Planning

## 1. Algorithm Overview & Academic Foundation
**CORELAP** (*Computerized Relationship Layout Planning*) is the foundational **construction heuristic** for plant layout optimization, originally introduced by R. C. Lee and J. M. Moore in 1967.

In the Facility Layout Optimization & Decision Support System (FLODSS), CORELAP v1.0 serves as the primary **deterministic construction solver**. Its objective is to build an initial continuous layout from qualitative Muther Systematic Layout Planning (SLP) closeness relationships and department area requirements from scratch without pre-existing coordinates or stochastic sampling.

### Core Philosophy: Construction vs. Improvement
- **CORELAP is a construction heuristic**: It starts with an empty facility floor and adds departments one by one in a greedy sequence dictated by relationship affinity.
- **Subsequent phases**: The resulting feasible seed layout can be passed to improvement heuristics such as CRAFT (pairwise exchange), Genetic Algorithms, or Simulated Annealing.

---

## 2. Classical Algorithm vs. FLODSS Extensions

| Feature | Classical CORELAP (Lee & Moore 1967) | FLODSS Implementation |
| :--- | :--- | :--- |
| **Representation** | Discrete Unit Grid (equal-sized squares) | Continuous Rectangular Layout (`ContinuousLayout`) |
| **Department Shapes** | Irregular collections of unit grid cells | Bounded rectangles with aspect ratio constraints |
| **Shape Generation** | Aggregation of unit square cells | Deterministic legal dimensions, neighbor matching, and 0°/90° orientations |
| **Adjacency Scoring** | Unit border contact counting | Shared boundary contact length ($L_{\text{shared}}$ in meters) |
| **Distance Scoring** | None (pure adjacency) | Configurable Mode B (`extended_distance_weighted`) with decay |
| **Brownfield Support** | None | Pre-placement of fixed departments at Step 0 |

---

## 3. Muther SLP Relationship Weights
Closeness ratings between department pairs map into numerical affinity weights according to Muther's Systematic Layout Planning (SLP) standards, centralized in `app.models.relationship.RELATIONSHIP_DEFAULT_SCORES`:

| Rating Code | Description | Numerical Score $w_{ij}$ |
| :---: | :--- | :---: |
| **A** | Absolutely Necessary | **+16.0** |
| **E** | Especially Important | **+8.0** |
| **I** | Important | **+4.0** |
| **O** | Ordinary Closeness | **+2.0** |
| **U** | Unimportant | **0.0** |
| **X** | Undesirable (Prohibited Closeness) | **-8.0** |

*Rules*:
1. Any department pair without an explicit relationship in the problem definition defaults strictly to $U = 0.0$.
2. Relationships are symmetric: $w_{ij} = w_{ji}$.

---

## 4. Total Closeness Rating (TCR) Formulation
For every department $i \in \mathcal{D}$, its Total Closeness Rating ($\text{TCR}_i$) measures its aggregate affinity across the entire facility:

$$\text{TCR}_i = \sum_{j \neq i, j \in \mathcal{D}} w_{ij}$$

Departments with higher TCR values represent central organizational hubs and are placed early.

---

## 5. Department Selection & Deterministic Tie-Breaking

### 5.1 Initial Department Selection
The first unplaced department placed on the floor is selected using strict lexicographical tie-breaking:
1. **Highest TCR** ($\max \text{TCR}_i$)
2. **Largest Required Area** ($\max \text{required\_area}_i$)
3. **Alphabetical Department ID** (ascending `id` for strict determinism)

### 5.2 Subsequent Department Selection
At each step $k > 1$, unplaced departments are ranked based on their affinity with departments already positioned on the facility floor:

$$\text{PlacementScore}_i = \sum_{j \in \mathcal{P}} w_{ij}$$

where $\mathcal{P}$ is the set of currently placed departments.
Tie-breaking order:
1. **Highest Placement Score** ($\max \text{PlacementScore}_i$)
2. **Highest Global TCR** ($\max \text{TCR}_i$)
3. **Largest Required Area** ($\max \text{required\_area}_i$)
4. **Alphabetical Department ID** (ascending `id`)

---

## 6. Placement Scoring Modes

### Mode A: Classical Adjacency (`classical_adjacency`, Default)
Adheres strictly to the Muther / Lee & Moore principle: only direct boundary contact generates affinity score.
$$\text{Score}(c) = \sum_{j \in \mathcal{P}, \text{adjacent}} w_{ij} \cdot \max(1.0, L_{\text{shared}})$$

Non-adjacent departments contribute exactly $0.0$. No unexplained constants or distance decays are applied. If an adjacent department has an undesirable $X$-relationship ($w_{ij} = -8.0$), the penalty scales with the contact length.

### Mode B: Extended Distance-Weighted (`extended_distance_weighted`)
For continuous optimization problems where non-touching departments still benefit from proximity:
$$\text{Score}(c) = \sum_{j \in \mathcal{P}} \begin{cases}
w_{ij} \cdot \max(1.0, L_{\text{shared}}) & \text{if adjacent and } w_{ij} > 0 \\
w_{ij} \cdot \max(1.0, L_{\text{shared}}) \cdot M_X & \text{if adjacent and } w_{ij} < 0 \ (X\text{-rating}) \\
\frac{w_{ij}}{1.0 + \alpha \cdot d_{\text{Manhattan}}} & \text{if separated and } w_{ij} > 0 \\
-\frac{|w_{ij}| \cdot S_X}{1.0 + \beta \cdot d_{\text{Manhattan}}} & \text{if separated and } w_{ij} < 0
\end{cases}$$

All coefficients ($\alpha, \beta, M_X, S_X$) are explicitly exposed in `CORELAPConfig`.

---

## 7. Solution Completeness & Benchmark Integrity (Phase 5.1)

### 7.1 Formal Completion Status
Partial layouts must never be treated as valid complete optimization results. The solver and trace explicitly report:
- `is_complete`: Boolean flag (`True` only when all problem departments are placed).
- `placed_department_count` & `total_department_count`.
- `unplaced_departments`: List of department IDs omitted from the layout.
- `termination_reason`: One of `SUCCESS_COMPLETE`, `FAILED_NO_FEASIBLE_CANDIDATE`, `FAILED_VALIDATION`, `PARTIAL_INCOMPLETE`.

### 7.2 Independent Evaluation Engine Protection
When evaluating a layout via `EvaluationEngine`:
1. If a layout is incomplete, `complete_layout = False`, `is_comparable = False`, and `is_feasible = False`.
2. Evaluated metrics for incomplete layouts are stored as `diagnostic_partial_values` and prefixed with `partial_` (e.g., `partial_material_handling_cost`).
3. In `evaluate_many()`, incomplete layouts are **excluded from min-max normalization and composite scoring**. They cannot be ranked above complete solutions.

---

## 8. Dense Packing Diagnostics & Benchmark Problems

### 8.1 Industrial Benchmark 10 (`FLP_INDUSTRIAL_10`, 91.67% Utilization)
In `sample_plant.json`, 10 large industrial departments occupy 11,000 m² of a 12,000 m² plant (91.67% area density).
- CORELAP's greedy forward placement without backtracking positions the central hub departments first.
- In dense facilities, this can fragment the remaining free floor area into narrow perimeter corridors. When subsequent departments require larger continuous rectangles than the remaining corridors, the greedy solver halts with `FAILED_NO_FEASIBLE_CANDIDATE`.
- This is an honest diagnostic characteristic of forward construction heuristics in continuous space without shape deformation or backtracking.

### 8.2 Medium Benchmark 6 (`FLP_MEDIUM_6`, 58.57% Utilization)
To provide an academic, fully solvable construction benchmark:
- Facility: $100 \times 70\text{ m} = 7,000\text{ m}^2$.
- 6 discrete departments totaling $4,100\text{ m}^2$ (58.57% area density).
- CORELAP places all 6 departments with `SUCCESS_COMPLETE`, 0 overlaps, and 100% geometric feasibility.

---

## 9. References
1. **Lee, R. C., & Moore, J. M.** (1967). *CORELAP—COmputerized RElationship LAyout Planning*. Journal of Industrial Engineering, 18(3), 195–200.
2. **Muther, R.** (1973). *Systematic Layout Planning (SLP)*. Cahners Books, Boston.
3. **Tompkins, J. A., White, J. A., Bozer, Y. A., & Tanchoco, J. M. A.** (2010). *Facilities Planning* (4th ed.). John Wiley & Sons.
4. **Francis, R. L., McGinnis, L. F., & White, J. A.** (1992). *Facility Layout and Location: An Analytical Approach* (2nd ed.). Prentice Hall.
