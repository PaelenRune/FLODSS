# FLODSS Evaluation Contract & Canonical Benchmark Standard

**Version:** 1.0.0  
**Status:** Active Canonical Standard  
**Effective Date:** October 2026  
**Scope:** All algorithms, benchmarks, baseline evaluations, and reporting services across the Facility Layout Optimization & Decision Support System (FLODSS).

---

## 1. Purpose & Guiding Principles

The **Evaluation Contract** establishes an immutable, mathematically rigorous, and cryptographically verifiable evaluation standard for the FLODSS platform.

In past iterations (Phases 1 through 9.1), minor discrepancies emerged between benchmark reports due to:
- Disparate lookup keys (e.g. `"total_flow_distance"` vs. `"flow_distance"`),
- Disparate reporting conventions (raw objective values vs. normalized scores),
- Ad-hoc manual metric estimation (such as dividing Material Handling Cost by 2 to guess Flow-Distance),
- Unverified reporting of constraint penalties.

This contract defines the **canonical ground truth** for all layout evaluation in FLODSS. No benchmark metric may be reported unless it is produced by the canonical evaluation pipeline and linked to cryptographic provenance hashes of the problem instance and evaluation configuration.

---

## 2. Canonical Objective Metrics & Formulas

All evaluations are executed using the **Centroid-to-Centroid Manhattan Metric** ($L_1$) unless explicitly specified otherwise by an audited configuration.

### 2.1 Material Handling Cost (MHC)

$$\text{MHC} = \sum_{i=1}^{N} \sum_{j=1}^{N} F_{ij} \times D(c_i, c_j) \times C_{ij}$$

- **Definitions:**
  - $N$: Number of departments in the problem.
  - $F_{ij}$: Annual material flow volume between department $i$ and department $j$ ($\text{units} / \text{year}$).
  - $c_i = (x_i + \frac{w_i}{2}, y_i + \frac{h_i}{2})$: Geometric centroid of department $i$ ($\text{m}$).
  - $D(c_i, c_j) = |x_i - x_j| + |y_i - y_j|$: Centroid-to-centroid distance ($\text{m}$).
  - $C_{ij}$: Cost of material handling per unit flow per unit distance ($\$ / (\text{unit} \cdot \text{m})$).
- **Physical Unit:** **United States Dollars per year ($\$ / \text{year}$)**.
- **Reporting Key:** `material_handling_cost`
- **Precision:** Rounded to 2 decimal places ($0.01\$$).

---

### 2.2 Flow-Distance (FD)

$$\text{FD} = \sum_{i=1}^{N} \sum_{j=1}^{N} F_{ij} \times D(c_i, c_j)$$

- **Definitions:**
  - Pure physical movement volume independent of transportation unit costs.
- **Physical Unit:** **Material-moves ($\text{unit-m} / \text{year}$)**.
- **Reporting Key:** `flow_distance`
- **Precision:** Rounded to 2 decimal places ($0.01\,\text{m-moves}$).

> [!CRITICAL]
> **Flow-Distance is NOT Material Handling Cost divided by 2.**  
> When unit costs $C_{ij}$ vary across department pairs (e.g., in `FLP_INDUSTRIAL_10`, $C_{ij} \in [0.8, 2.0]\,\$/\text{m}$), $\text{MHC} \neq 2 \times \text{FD}$. Flow-Distance must always be calculated directly from the flow matrix and centroid distances.

---

### 2.3 Muther Closeness Relationship Score

FLODSS implements Muther's Systematic Layout Planning (SLP) proximity evaluation:

$$\text{RelScore} = \sum_{i=1}^{N-1} \sum_{j=i+1}^{N} \text{ProximityValue}(R_{ij}, D_{\text{edge}}(B_i, B_j))$$

- **Ratings & Numerical Weights:**
  - **A** (Absolutely Necessary): $+64$
  - **E** (Especially Important): $+16$
  - **I** (Important): $+4$
  - **O** (Ordinary Closeness): $+1$
  - **U** (Unimportant): $0$
  - **X** (Undesirable): $-64$
- **Scoring Function:**
  - If $R_{ij} \in \{A, E, I, O\}$: Full positive score if departments are adjacent or within threshold distance; decreases linearly or steps down with distance.
  - If $R_{ij} = X$: Severe penalty if departments are adjacent ($D_{\text{edge}} = 0$).
- **Reporting Keys:**
  - `relationship_raw_score`: Net raw score (points).
  - `relationship_satisfaction_percentage`: Normalized satisfaction in $[0.0, 100.0]\%$, computed as:
    $$\text{RelSat} = \frac{\text{Actual Earned Positive Score}}{\text{Maximum Possible Positive Score}} \times 100\%$$

---

### 2.4 Area Utilization

$$\text{Utilization} = \frac{\sum_{i=1}^{N} w_i \times h_i}{W_{\text{facility}} \times H_{\text{facility}}} \times 100\%$$

- **Physical Unit:** Percentage ($\%$) in $[0.0, 100.0]\%$.
- **Reporting Key:** `area_utilization`

---

## 3. Constraint Evaluation & Feasibility Classification

FLODSS strictly bifurcates constraints into **Hard** and **Soft** categories:

### 3.1 Hard Constraints (Feasibility Gate)

A layout is classified as **feasible** (`is_feasible == True`) if and only if **100%** of hard constraints are satisfied:
1. **Facility Boundary Containment:** $x_i \ge 0$, $y_i \ge 0$, $x_i + w_i \le W_{\text{facility}}$, $y_i + h_i \le H_{\text{facility}}$.
2. **Zero Overlap:** Pairwise intersection area between all department pairs is identically $0.00\,\text{m}^2$.
3. **Exact Area Conservation:** $|w_i \times h_i - A_{\text{required}, i}| / A_{\text{required}, i} \le 0.0001$ ($0.01\%$).
4. **Aspect Ratio Boundaries:** $\max(w/h, h/w) \le \text{AR}_{\max}$.
5. **Dimensional Bounds:** $w_{\min} \le w_i \le w_{\max}$ and $h_{\min} \le h_i \le h_{\max}$.
6. **Hard Proximity / Separation Rules:** Specific hazard buffers (e.g. paint vs. welding fire separation).

### 3.2 Soft Constraints & Penalty Formulation

Soft constraints represent engineering preferences or non-fatal operational restrictions (e.g., acoustic or vibration isolation). Violating a soft constraint **does not invalidate feasibility**, but incurs an annualized penalty cost:

$$P_{\text{soft}} = \sum_{k \in \text{Violations}} \Delta_k \times r_k$$

- $\Delta_k$: Deficit or excess distance violation ($\text{m}$).
- $r_k$: Penalty rate ($\$ / \text{m}$).
- **Physical Unit:** **United States Dollars per year ($\$ / \text{year}$)**.
- **Reporting Keys:**
  - `soft_violations_count`: Number of violated soft rules.
  - `soft_penalty`: Total financial penalty in USD ($).

---

## 4. Cryptographic Provenance Architecture

To prevent ambiguity, every `CanonicalEvaluationReport` is permanently bound to SHA-256 hashes of the underlying problem data and hyperparameters:

```
+-----------------------------------------------------------------------+
|                     CanonicalEvaluationReport                         |
|-----------------------------------------------------------------------|
|  * problem_composite_hash: SHA-256(problem_id + components)           |
|    - department_geometry_hash                                         |
|    - flow_matrix_hash                                                 |
|    - rel_matrix_hash                                                  |
|    - constraint_definitions_hash                                      |
|  * evaluation_config_hash: SHA-256(JSON(config))                      |
|  * layout_signature:       SHA-256(canonical sorted placements)       |
|-----------------------------------------------------------------------|
|  * material_handling_cost: $93,876.54                                 |
|  * flow_distance:          78,675.22 m-moves                          |
|  * rel_satisfaction:       63.70%                                     |
|  * soft_penalty:           $0.00                                      |
|  * is_feasible:            True                                       |
+-----------------------------------------------------------------------+
```

### 4.1 Problem Provenance Hashes

1. **`department_geometry_hash`:**
   $$\text{SHA-256}\left(W_{\text{fac}} \times H_{\text{fac}} \,\Big|\, \prod_{d} \left(d.\text{id}:d.A_{\text{req}}:d.w_{\min}:d.w_{\max}:d.h_{\min}:d.h_{\max}:d.\text{AR}_{\min}:d.\text{AR}_{\max}\right)\right)$$
2. **`flow_matrix_hash`:**
   $$\text{SHA-256}\left(\prod_{(i,j)} \left(i \to j : F_{ij} : C_{ij}\right)\right)$$
3. **`rel_matrix_hash`:**
   $$\text{SHA-256}\left(\prod_{(i,j)} \left(i \leftrightarrow j : R_{ij} : \text{Score}\right)\right)$$
4. **`constraint_definitions_hash`:**
   $$\text{SHA-256}\left(\prod_{c} \left(c.\text{id} : c.\text{type} : c.\text{depts} : c.\text{params} : c.\text{class} : c.\text{penalty}\right)\right)$$
5. **`composite_data_hash`:**
   $$\text{SHA-256}\left(\text{problem\_id} \,|\, \text{geom\_hash} \,|\, \text{flow\_hash} \,|\, \text{rel\_hash} \,|\, \text{const\_hash}\right)$$

### 4.2 Standard Configuration Fingerprint

Standard `EvaluationConfig()` parameters:
- `distance_metric`: `"manhattan"`
- `coordinate_origin`: `"bottom_left"`
- `area_tolerance_percent`: `0.01`
- `aspect_ratio_tolerance`: `0.01`
- `engine_version`: `"1.0.0"`
- `evaluation_config_hash`: `eb0c6a65de43d685de8a995638289a9189876cb4d43b40d175072d6409cf7811`

---

## 5. Standardized Canonical Benchmark Table (FLP_INDUSTRIAL_10)

Under this contract, the canonical ground truth for the three primary baseline layouts of `FLP_INDUSTRIAL_10` is:

| Metric | A. Manual Baseline | B. Guillotine Generated | C. GA Best (Seed 2024) |
| :--- | :---: | :---: | :---: |
| **Source File** | `sample_layout.json` | `generated_industrial_10.json` | `ga_optimized_industrial_10.json` |
| **Layout Signature** | `b6459286bc1fb50b...` | `61c4bf8899651778...` | `fa36b29c4fa43e85...` |
| **MHC ($)** | **\$139,498.75** | **\$180,263.99** | **\$93,876.54** |
| **Flow-Distance** | **117,893.75 m-moves** | **153,551.19 m-moves** | **78,675.22 m-moves** |
| **Relationship Score** | 66.56 | 53.00 | 76.43 |
| **Rel Satisfaction (%)**| **55.47%** | **44.17%** | **63.70%** |
| **Area Utilization (%)**| 91.67% | 91.67% | 91.67% |
| **Hard Violations** | 0 | 0 | 0 |
| **Soft Violations** | 0 | 1 (`CST_SOFT_VIBRATION_SEP`) | 0 |
| **Soft Penalty ($)** | **\$0.00** | **\$62,500.00** | **\$0.00** |
| **Feasibility Status** | **Feasible** | **Feasible** | **Feasible** |

---

## 6. Implementation & Compliance Requirements

1. **Centralized Service:**
   All production code, API endpoints, and experimental benchmark scripts MUST call `CanonicalEvaluationService.evaluate(problem, layout)` from `backend/app/evaluation/canonical.py`.
2. **Zero Heuristic Extrapolation:**
   Dividing or multiplying metrics by arbitrary constants (such as dividing MHC by 2 to guess Flow-Distance) is strictly prohibited.
3. **Automated Regression Testing:**
   Any change to `EvaluationEngine`, `DistanceEvaluator`, or `ConstraintEngine` must be verified against `backend/tests/test_phase9_2_evaluation_audit.py` to ensure bitwise reproducibility.
