# FLODSS Benchmark Methodology & Reproducibility Protocol

*Facility Layout Optimization Decision Support System (FLODSS)*  
*Document Version: 1.0.0 (Phase 13)*  
*Target Environment: Python 3.12, Node.js v20+, Windows / Linux*  

---

## 1. Overview and Purpose

This document provides complete instructions to independently replicate and audit the benchmark evaluations of FLODSS across standard academic instances and synthetic industrial-scale problems.

All benchmark results cited in the Phase 13 reports (`experiments/reports/INDUSTRIAL_VALIDATION.md`) are generated using deterministic execution rules, fixed pseudo-random number seeds, and strict canonical evaluation contracts.

---

## 2. Benchmark Dataset Suite

The benchmark datasets reside under `data/examples/` and conform to the `FacilityLayoutProblem` JSON schema:

1. **`sample_plant.json` (`FLP_INDUSTRIAL_10`)**: 10 departments, $150 \times 80\,$m, 91.67% area utilization, strict aspect ratio bounds $[1.0, 3.0]$.
2. **`synthetic_high_density_15.json` (`HIGH_DENSITY_15`)**: 15 departments, $180 \times 100\,$m, 90.00% utilization, realistic process flow volumes.
3. **`synthetic_high_density_20.json` (`HIGH_DENSITY_20`)**: 20 departments, $200 \times 120\,$m, 95.83% utilization, tight aspect ratio bounds $[1.0, 2.0]$.
4. **`synthetic_constrained_factory_12.json` (`CONSTRAINED_FACTORY_12`)**: 12 departments, $160 \times 100\,$m, 81.25% utilization, fixed receiving dock (`DEP_01_GATE` at origin $0,0$), reserved central spine corridor ($x \in [75, 85]$).
5. **`synthetic_logistics_factory_15.json` (`LOGISTICS_FACTORY_15`)**: 15 departments, $200 \times 90\,$m, 85.00% utilization, asymmetric tote flows.

To regenerate or verify synthetic instances:
```powershell
backend\.venv\Scripts\python.exe backend\scripts\generate_synthetic_benchmarks.py
```

---

## 3. Solver Configurations & Budget Contracts

Benchmarking tests three core algorithmic configurations across 5 fixed random seeds: `[42, 101, 202, 303, 404]`.

### 3.1 Feasible Layout Generator (`FeasibleGenerator_Guillotine`)
- **Strategy**: `GeneratorStrategy.GUILLOTINE_ROW_PACKING`
- **Time Budget**: 10.0 seconds
- **Evaluations Count**: 1 (constructive, single-pass)

### 3.2 Fixed Genetic Algorithm (`Fixed_GA_v1`)
- **Representation**: Slicing Tree with Area-Preserving Decoder
- **Population Size**: 20 individuals
- **Max Generations**: 20
- **Time Budget**: 10.0 seconds
- **Selection**: Tournament selection ($k=3$)
- **Operators**: Order crossover (OX), bay size crossover, swap mutation, inversion mutation

### 3.3 Adaptive Strategy Engine (`Adaptive Pipeline`)
- **Strategy Selection**: Rule-based problem fingerprinting and archetype classification
- **Primary Constructor**: Feasible Layout Generator
- **Fallback Trigger**: Detected constructive failure, aspect bound breach, or geometric dead-end
- **Secondary Engine**: Genetic Layout Algorithm with dynamic budget allocation
- **Pareto Frontier**: Multi-objective non-dominated ranking across MHC, REL%, and Soft Penalty

---

## 4. Reproducible Execution Command

To execute the multi-seed benchmark across all 5 problems and log performance metrics (runtime, peak memory, feasibility, MHC, REL%, signatures):

```powershell
backend\.venv\Scripts\python.exe backend\scripts\run_phase13_benchmarks.py
```

Output records are written to `data/examples/phase13_benchmark_results.json`.

---

## 5. Canonical Evaluation Contracts

To prevent discrepancies between optimization phases, all metrics are computed through `CanonicalEvaluationService`:
- **Material Handling Cost (MHC)**:
  $$\text{MHC} = \sum_{i < j} f_{ij} \cdot c_{ij} \cdot d(c_i, c_j)$$
  where $d(c_i, c_j) = |x_i - x_j| + |y_i - y_j|$ is the rectilinear Manhattan distance between department centroids.
- **Relationship Satisfaction (REL%)**:
  Percentage of positive closeness preferences (A, E, I) satisfied based on adjacent perimeter contact or proximity threshold ($d_{ij} \le 1.25 \cdot (r_i + r_j)$).
- **Soft Constraint Penalty**:
  Monetary penalties incurred from violating soft separation requirements (e.g. vibration-sensitive placement).
- **Hard Feasibility Verification**:
  Complete verification of zero pairwise overlap ($\text{area} = 0.00$), exact area conservation ($\Delta \text{area} = 0.00$), aspect ratio limits $[\text{min\_ar}, \text{max\_ar}]$, fixed department coordinates, and reserved zone exclusion.

---

## 6. Assumptions and Known Boundaries

1. **Planar 2D Modeling**: Layouts model 2D floor surfaces; vertical multi-floor layouts and 3D rack elevations are outside the current scope.
2. **Rectilinear Movement**: Material handling distance uses Manhattan routing aligned with standard facility aisle grids.
3. **Constructive Guillotine Limits**: Single-pass guillotine row packing is deterministic and fast, but cannot guarantee feasibility when area utilization exceeds 90% or when internal exclusion zones bisect the facility floor.
4. **No Global Optimality**: The Facility Layout Problem is strongly NP-hard. FLODSS uses heuristic and metaheuristic approaches; no mathematical claim of global optimality is made.
