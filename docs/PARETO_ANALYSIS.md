# FLODSS Multi-Objective Evaluation & Pareto Frontier Architecture (Phase 10)

**Version:** 1.0.0  
**Status:** Active Standard  
**Target Problems:** `FLP_INDUSTRIAL_10`, `FLP_ACADEMIC_4`, General Facility Layout Problems  
**Module:** `backend/app/optimization/pareto.py`  
**API Endpoint:** `POST /api/pareto/analyze`, `POST /api/pareto/compare`, `GET /api/pareto/objectives`

---

## 1. Executive Summary & Purpose

In classical Facility Layout Problem (FLP) formulations, algorithms frequently collapse multi-attribute objectives into an arbitrary scalar cost or penalization function. However, practical industrial facility engineering inherently balances competing criteria:
- **Material Handling Cost (MHC):** Annualized financial expense of intralogistics movements.
- **Muther Relationship Closeness Satisfaction (%):** Subjective qualitative adjacency preferences (e.g. communication proximity, safety, workflow logic).
- **Engineering Soft Constraint Penalties ($):** Vibration isolation, acoustic buffers, and environmental clearances.

The **Phase 10 Pareto Frontier Engine** introduces a rigorous multi-objective evaluation and decision support framework that compares multiple complete and feasible layout designs without forcing an arbitrary single-objective aggregation upon the designer.

---

## 2. Mathematical Definition of Pareto Dominance

Let $\Omega$ represent the set of all evaluated, complete, and feasible layout candidates for a problem instance. Each candidate $x \in \Omega$ is evaluated across $M$ objective functions $f_1(x), f_2(x), \dots, f_M(x)$.

### 2.1 Optimization Directions
In FLODSS Phase 10:
1. $f_{\text{MHC}}(x) \to \mathbf{\min}$ (Material Handling Cost in USD/year)
2. $f_{\text{REL}}(x) \to \mathbf{\max}$ (Muther Relationship Satisfaction in $[0.0, 100.0]\%$)
3. $f_{\text{SOFT}}(x) \to \mathbf{\min}$ (Soft Constraint Penalty Cost in USD/year)

> [!NOTE]
> **Flow-Distance Exclusion:** While Flow-Distance ($m$-moves) is computed and reported in auxiliary metrics, it is deliberately excluded from default Pareto dominance sorting due to its high mathematical collinearity with MHC, preventing redundant dimensionality distortion.

### 2.2 Formal Dominance Criterion with Tolerance $\epsilon$
For two candidate layouts $A, B \in \Omega$, candidate $A$ **dominates** candidate $B$ (denoted $A \succ B$) if and only if:

$$\forall m \in \{1, \dots, M\}: \begin{cases} f_m(A) \le f_m(B) + \epsilon_m & \text{if } f_m \text{ is minimized} \\ f_m(A) \ge f_m(B) - \epsilon_m & \text{if } f_m \text{ is maximized} \end{cases}$$

$$\mathbf{AND}$$

$$\exists m \in \{1, \dots, M\}: \begin{cases} f_m(A) < f_m(B) - \epsilon_m & \text{if } f_m \text{ is minimized} \\ f_m(A) > f_m(B) + \epsilon_m & \text{if } f_m \text{ is maximized} \end{cases}$$

Where $\epsilon_m$ is an objective-specific floating-point tolerance (default $10^{-4}$, $0.01\$$ for financial metrics, and $0.01\%$ for percentages).

---

## 3. Fast Non-Dominated Sorting Algorithm

FLODSS implements the standard $O(K^2 \cdot M)$ non-dominated sorting algorithm (Deb et al.):

1. **Domination Bookkeeping:**
   - For every candidate $p \in \Omega$, determine:
     - $S_p$: The set of solutions that $p$ dominates ($p \succ q$).
     - $n_p$: The domination counter (number of solutions that dominate $p$).
2. **Frontier Extraction (Rank 1):**
   - All candidates with $n_p = 0$ constitute the **Pareto Frontier (Rank 1)**.
3. **Iterative Peeling (Ranks 2, 3, ...):**
   - For each candidate $p$ in Front $i$, visit each $q \in S_p$ and decrement $n_q \leftarrow n_q - 1$.
   - Any solution whose counter drops to $0$ enters Front $i + 1$.
4. **Deterministic Tie-Breaking:**
   - Within each rank, candidates are sorted deterministically by primary objective ($f_{\text{MHC}}$ ascending), then by $f_{\text{REL}}$ descending, then by `candidate_id`.

---

## 4. Candidate Validation & Filtering Protocol

Before candidates enter the non-dominated sorting pipeline, `ParetoFrontierService` enforces strict integrity gates:

| Gate | Criterion | Action on Violation |
| :--- | :--- | :--- |
| **Problem Provenance** | `candidate.problem_id == problem.id` AND `composite_hash` match | Excluded: `"Cross-problem mismatch"` |
| **Config Provenance** | `evaluation_config_hash` match | Excluded: `"EvaluationConfig hash mismatch"` |
| **Completeness** | All $N$ problem departments placed | Excluded: `"Incomplete layout: missing departments"` |
| **Feasibility** | Zero hard constraint violations & zero geometric overlaps | Excluded: `"Infeasible layout: hard violations"` |
| **Deduplication** | Distinct SHA-256 layout signature | Excluded: `"Duplicate layout signature (already represented)"` |

---

## 5. Verification on Hand-Calculated Canonical Example

To mathematically prove the correctness of `ParetoFrontierService.dominates` and sorting, a 3-solution benchmark was hand-verified:

- **Solution A:** $\text{MHC} = 100$, $\text{REL} = 80$, $\text{Soft} = 0$
- **Solution B:** $\text{MHC} = 120$, $\text{REL} = 70$, $\text{Soft} = 10$
- **Solution C:** $\text{MHC} = 90$,  $\text{REL} = 60$, $\text{Soft} = 0$

### Mathematical Analysis:
1. **$A$ vs $B$:**
   - $\text{MHC}$: $100 < 120$ (A is better)
   - $\text{REL}$: $80 > 70$ (A is better)
   - $\text{Soft}$: $0 < 10$ (A is better)
   - $\implies A \succ B$ ($A$ dominates $B$).
2. **$A$ vs $C$:**
   - $\text{MHC}$: $100 > 90$ ($C$ is better)
   - $\text{REL}$: $80 > 60$ ($A$ is better)
   - $\text{Soft}$: $0 == 0$ (Equal)
   - $\implies A \not\succ C$ and $C \not\succ A$ (Non-dominating trade-off).
3. **$B$ vs $C$:**
   - $B$ has higher REL ($70 > 60$), while $C$ has lower MHC ($90 < 120$) and lower Soft ($0 < 10$).
   - $\implies B \not\succ C$ and $C \not\succ B$.

### Output:
- **Pareto Frontier (Rank 1):** $\{A, C\}$
- **Dominated Layer (Rank 2):** $\{B\}$

Unit test `test_hand_calculated_three_solution_example` confirms 100% agreement.

---

## 6. Baseline Precision Audit: 180,263.94 vs 180,263.99

Phase 9.2 identified a 5-cent difference in reported Guillotine baseline MHC ($180,263.94$ vs $180,263.99$).

### Root Cause:
1. In Phase 8, when `FeasibleLayoutGenerator` solved in-memory, heights were 64-bit IEEE-754 floats ($h = 24.2857142857\dots$), yielding $\text{MHC} = \$180,263.94$.
2. When serialized to `generated_industrial_10.json`, placement dimensions were truncated to 4 decimal places ($h = 24.2857$).
3. Because centroids are $c_y = y + h/2$, rounding altered centroid coordinates by $\sim 10^{-5}\,\text{m}$, altering the weighted distance sum by $\$0.05$ ($0.000028\%$).
4. The SHA-256 layout signature (`61c4bf8899651778...`) is bitwise identical in both cases.

### Resolution:
`ParetoFrontierService` applies objective tolerance $\epsilon_{\text{MHC}} = 0.10\$$. Under this tolerance, two representations within 5 cents cannot produce false dominance artifacts.

---

## 7. Multi-Criteria Decision Support & Weighting

To assist facility designers who desire a single recommendation based on organizational priorities, FLODSS implements **Min-Max Normalized Utility Scoring**:

For each objective $m$, normalize value $v_m$ into $[0.0, 1.0]$ across all valid candidates:
$$u_m = \begin{cases} \frac{\max(V_m) - v_m}{\max(V_m) - \min(V_m)} & \text{if } m \text{ is minimized} \\ \frac{v_m - \min(V_m)}{\max(V_m) - \min(V_m)} & \text{if } m \text{ is maximized} \end{cases}$$

Composite utility:
$$U(x) = \frac{\sum_{m=1}^M w_m \cdot u_m(x)}{\sum_{m=1}^M w_m}$$

### Preference Profiles:
- **Cost Priority:** $w_{\text{MHC}} = 0.70, w_{\text{REL}} = 0.15, w_{\text{SOFT}} = 0.15$
- **Relationship Priority:** $w_{\text{MHC}} = 0.15, w_{\text{REL}} = 0.70, w_{\text{SOFT}} = 0.15$
- **Soft Constraint Priority:** $w_{\text{MHC}} = 0.15, w_{\text{REL}} = 0.15, w_{\text{SOFT}} = 0.70$
- **Balanced Utility:** $w_{\text{MHC}} = 0.34, w_{\text{REL}} = 0.33, w_{\text{SOFT}} = 0.33$

> [!IMPORTANT]
> **Dominance Independence:** Decision support recommendations are calculated across the entire candidate set, but explicitly flag whether the selected candidate resides on the Pareto Frontier (`is_on_pareto_frontier`). If a user's extreme weights ever pick a dominated solution, an explicit warning is provided.

---

## 8. Empirical Benchmark Results on FLP_INDUSTRIAL_10

Evaluating the standardized baseline and multi-seed candidate portfolio on `FLP_INDUSTRIAL_10`:

| Candidate ID | Algorithm / Seed | MHC ($) | Rel Sat (%) | Soft Penalty ($) | Pareto Rank | Status | Dominance Notes |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **GA Best (Seed 2024)** | Metaheuristic (S-2024) | **\$93,876.54** | 63.70% | **\$0.00** | **Rank 1 (Frontier)** | Non-Dominated | Lowest MHC overall |
| **GA Seed 101** | Metaheuristic (S-101) | \$107,487.83 | **64.79%** | **\$0.00** | **Rank 1 (Frontier)** | Non-Dominated | Highest Rel Sat overall |
| **GA Seed 999** | Metaheuristic (S-999) | \$114,717.87 | 63.17% | \$0.00 | **Rank 2** | Sub-Optimal | Dominated by Seed 2024 & Seed 101 |
| **GA Seed 777** | Metaheuristic (S-777) | \$107,922.59 | 59.11% | \$12,195.00 | **Rank 2** | Sub-Optimal | Incurs vibration separation penalty |
| **GA Seed 42** | Metaheuristic (S-42) | \$121,190.46 | 54.08% | \$0.00 | **Rank 3** | Dominated | Dominated by Seed 2024 & Seed 101 |
| **Manual Baseline** | Human Expert Design | \$139,498.75 | 55.47% | \$0.00 | **Rank 3** | Dominated | Dominated by GA Seed 2024 & Seed 101 |
| **Guillotine Baseline** | Row Constructive | \$180,263.99 | 44.17% | \$62,500.00 | **Rank 4** | Dominated | High cost, low Rel, high soft penalty |

### Key Engineering Findings:
1. **The Pareto Frontier contains 2 distinct solutions:**
   - `GA Best (Seed 2024)` offers the lowest material handling cost ($\$93,876.54$).
   - `GA Seed 101` offers the highest relationship satisfaction ($64.79\%$).
2. **There is a genuine trade-off:** Saving $\$13,611.29$ in annual material handling cost (Seed 2024 vs Seed 101) requires accepting a $1.09\%$ decrease in Muther closeness satisfaction.
3. **Manual Baseline is dominated:** Both frontier solutions achieve lower MHC and higher relationship satisfaction while maintaining zero constraint violations.
4. **Guillotine Baseline is dominated at Rank 4:** Exhibits the highest handling cost ($\$180,263.99$) and incurs a $\$62,500.00$ acoustic/vibration deficit.

---

## 9. API Reference

### `POST /api/pareto/analyze`
**Request:**
```json
{
  "problem_id": "FLP_INDUSTRIAL_10",
  "include_saved_baselines": true,
  "priority_weights": {
    "material_handling_cost": 0.50,
    "relationship_satisfaction": 0.50
  }
}
```

**Response (Summary):**
```json
{
  "problem_id": "FLP_INDUSTRIAL_10",
  "frontier_count": 2,
  "frontier_candidate_ids": ["GA Best Solution (Seed 2024)", "GA_SEED_101"],
  "ranks": {
    "1": ["GA Best Solution (Seed 2024)", "GA_SEED_101"],
    "2": ["GA_SEED_777", "GA_SEED_999"],
    "3": ["GA_SEED_42", "Manual Baseline"],
    "4": ["Guillotine Baseline"]
  },
  "recommendations": {
    "cost_priority": { "recommended_candidate_id": "GA Best Solution (Seed 2024)" },
    "relationship_priority": { "recommended_candidate_id": "GA_SEED_101" }
  }
}
```

---

## 10. Scope Boundaries

In accordance with Phase 10 guidelines:
- **No out-of-scope algorithms were developed:** NSGA-II, Simulated Annealing, MILP, Gemini API, Machine Layout, or Adaptive Strategy Engine were strictly excluded.
- The next development milestone will proceed based on these verified multi-objective foundations.
