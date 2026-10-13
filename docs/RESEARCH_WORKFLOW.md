# Academic Research & Thesis Experimentation Workflow
## FLODSS: Facility Layout Optimization & Decision Support System (`v1.0.0-rc.1`)

This document outlines the standard research methodology and experimental protocol for conducting reproducible academic research, thesis evaluations, and benchmarking studies using FLODSS.

---

## 1. Experimental Methodology Overview

Rigorous evaluation of Unequal-Area Facility Layout Problems (UA-FLP) requires controlling for stochastic variation, enforcing geometric constraints, and establishing a single canonical evaluation protocol.

```
+-------------------------------------------------------------------------+
|                          RESEARCH PROTOCOL                              |
|                                                                         |
|  1. Problem Formulation ──> 2. Deterministic Seeding                    |
|  3. Multi-Algorithm Execution ──> 4. Geometric Feasibility Verification |
|  5. Canonical Objective Evaluation ──> 6. Pareto Frontier Discovery     |
|  7. Statistical Aggregation ──> 8. Thesis Provenance Export             |
+-------------------------------------------------------------------------+
```

---

## 2. Experimental Setup & Benchmarks

### 2.1 Benchmark Selection
For academic publications and thesis comparative chapters, report evaluations on standard benchmark suites:
- **Baseline Industrial Case (`FLP_INDUSTRIAL_10`):** 10 departments, $100 \times 60\,\text{m}$ facility ($6000\,\text{m}^2$), 84.7% area utilization, dense material flow network, tight aspect constraints.
- **Moderate Manufacturing Facility (`FLP_MANUFACTURING_8`):** 8 departments, $80 \times 50\,\text{m}$.
- **Constrained Healthcare Clinic (`FLP_HEALTHCARE_12`):** 12 departments, $120 \times 80\,\text{m}$, fixed emergency triage anchors.
- **Large Synthetic Logistics Hub (`FLP_LOGISTICS_15`):** 15 departments, high throughput, reserved central spine corridor.

### 2.2 Seeding & Deterministic Multi-Run Protocol
Heuristics (CRAFT, ALDEP) and metaheuristics (Genetic Algorithm, Adaptive Strategy Engine) rely on pseudo-random generators:
- **Rule of Determinism:** Never run experiments without setting an explicit random seed.
- **Multi-Trial Evaluation:** For stochastic algorithms (ALDEP, GA), execute across a fixed set of at least 10 or 30 seeds:
  $$\text{Seeds} = \{42, 101, 202, 303, 404, 505, 606, 707, 808, 909\}$$
- Report:
  - Best solution found ($\text{MHC}_{\min}$)
  - Mean ($\mu_{\text{MHC}}$) and Standard Deviation ($\sigma_{\text{MHC}}$)
  - Feasibility rate ($\% \text{ Feasible Runs}$)
  - Wall-clock runtime ($\mu_{\text{time}}$ in seconds or milliseconds)

---

## 3. Strict Geometric Feasibility Standards

In published literature, layout solutions that contain overlapping departments or violate outer building perimeters are mathematically invalid. FLODSS guarantees:

1. **Zero Overlap Tolerance:**
   $$\forall i \ne j, \quad \text{Area}(\text{Box}_i \cap \text{Box}_j) = 0.00\,\text{m}^2$$
2. **Exact Area Conservation:**
   $$\forall i, \quad w_i \times h_i = A_i^{\text{required}} \pm 10^{-4}$$
3. **Boundary Containment:**
   $$\forall i, \quad 0 \le x_i \quad \text{and} \quad x_i + w_i \le W, \quad 0 \le y_i \quad \text{and} \quad y_i + h_i \le H$$
4. **Aspect Ratio Compliance:**
   $$\forall i, \quad \alpha_i = \frac{\max(w_i, h_i)}{\min(w_i, h_i)} \le \alpha_{\max}$$
5. **Reserved Exclusion Compliance:**
   $$\forall i, \forall k, \quad \text{Area}(\text{Box}_i \cap \text{ReservedZone}_k) = 0.00\,\text{m}^2$$

Any candidate violating conditions 1–3 or 5 is strictly flagged as **Infeasible** and disqualified from the final Pareto frontier.

---

## 4. Canonical Evaluation Contract

To prevent metric discrepancies across different optimization phases, all metrics reported in thesis tables must be computed through FLODSS’s central `CanonicalEvaluationService`:

### 4.1 Objective Formulations
- **Material Handling Cost (MHC):**
  $$\text{MHC} = \sum_{i < j} f_{ij} \cdot c_{ij} \cdot (|x_{c, i} - x_{c, j}| + |y_{c, i} - y_{c, j}|)$$
  where $(x_{c, i}, y_{c, i})$ is the continuous centroid: $x_{c, i} = x_i + \frac{w_i}{2}$, $y_{c, i} = y_i + \frac{h_i}{2}$.
- **Muther SLP Relationship Satisfaction ($\%$):**
  $$\text{REL} = \frac{\sum_{i < j} r_{ij} \cdot \text{Adjacency}(i, j)}{\sum_{i < j, r_{ij} > 0} r_{ij}} \times 100\%$$
- **Soft Penalty Cost:**
  $$\text{Penalty}_{\text{soft}} = \sum_i \max(0, \alpha_i - \alpha_{\max}) \cdot \omega_{\alpha}$$

### 4.2 Cryptographic Hash Verification
Every evaluation report contains:
- `layout_signature`: Canonical SHA-256 hash invariant to department ordering.
- `evaluation_config_hash`: SHA-256 digest of objective weights, distance metrics, and penalty constants.

---

## 5. Multi-Objective Pareto Frontier Protocol

When evaluating multi-method results:
1. Run CORELAP, ALDEP, CRAFT, Feasible Generator, Genetic Algorithm, and Adaptive Strategy Engine on the same benchmark problem.
2. Pool all feasible solutions into the **Candidate Portfolio**.
3. Compute Pareto dominance: Solution $A$ dominates solution $B$ ($A \succ B$) if and only if $A$ is no worse than $B$ across all objectives and strictly better in at least one:
   $$\text{MHC}(A) \le \text{MHC}(B) \quad \land \quad \text{REL}(A) \ge \text{REL}(B) \quad \land \quad \text{Soft}(A) \le \text{Soft}(B)$$
4. Identify non-dominated solutions forming the **Pareto Frontier**.
5. Calculate the **Knee Point**: the candidate exhibiting the maximum marginal rate of substitution (best compromise between flow efficiency and functional affinity).

---

## 6. Academic Thesis Deliverables & Data Bundling

In **Tab 8: Export Center**, generate standard thesis deliverables:

| File Name | Format | Academic Purpose |
| :--- | :--- | :--- |
| `flodss_layout_<id>_<sig>.json` | JSON | Complete numerical layout coordinates for appendices or supplementary data repositories. |
| `flodss_experiment_config_<id>.json` | JSON | Exact machine-readable experiment specification enabling replication by external examiners. |
| `flodss_metrics_<id>.csv` | CSV | Formatted data table of all canonical objective scores ready for LaTeX `pgfplotstable` or Excel import. |
| `flodss_algorithm_comparison_<id>.csv` | CSV | Comparative table summarizing MHC, REL %, runtime, and feasibility across all benchmarked methods. |
| `flodss_pareto_portfolio_<id>.json` | JSON | Complete set of non-dominated candidates and objective vectors for Pareto trade-off plotting. |
| `flodss_layout_canvas.svg` | SVG | Publication-quality 2D vector graphic showing department boundaries, labels, centroids, and reserved corridors. |

---

## 7. Sample Citation & Text for Thesis Methodology Chapter

```latex
\section{Experimental Facility Layout Methodology}
Facility layout optimization was conducted using the FLODSS decision support platform (Version 1.0.0-rc.1) \cite{flodss2026}. Continuous Cartesian coordinates were decoded using area-preserving flexible bay slicing trees, guaranteeing zero overlap ($\text{Overlap} = 0.00\,\text{m}^2$) and exact area conservation. 

Material Handling Costs (MHC) were computed using rectilinear Manhattan centroid distances:
\begin{equation}
\text{MHC} = \sum_{i < j} f_{ij} c_{ij} \left( |x_{c, i} - x_{c, j}| + |y_{c, i} - y_{c, j}| \right)
\end{equation}

All algorithmic runs were evaluated under deterministic pseudo-random seeds ($S=42$) and verified via SHA-256 layout signatures to guarantee 100\% experimental reproducibility.
```
