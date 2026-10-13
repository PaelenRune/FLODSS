# FLODSS Changelog & Evolution History
All notable changes to the **Facility Layout Optimization & Decision Support System (FLODSS)** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-rc.1] - Phase 14: V1.0 Product Experience & Private Research Release Candidate

### Added
- **Tabbed Engineering Workspace (`Dashboard.tsx`):** Unified, responsive 8-tab operational workflow replacing vertical card stack:
  1. *Problem Editor:* Plant dimensions, utilization ratio, live department table with inline add/edit/delete, and benchmark template loading.
  2. *Flow & REL Matrix Editor:* Dual From-To flow table with row/column totals and Muther SLP closeness chart (A, E, I, O, U, X) with symmetric auto-mirroring and CSV export.
  3. *Constraint Editor:* Reserved exclusion zones manager (aisle corridors, structural columns, exits) and fixed position inspector.
  4. *Optimization Workspace:* Central solver selector for all 6 algorithmic engines, operating condition summaries, parameter controls (seed, budget, population, generations), true wall-clock elapsed time in milliseconds, and failure/infeasibility fallback notice banner.
  5. *Interactive 2D Layout Viewer:* 1:1 true continuous Cartesian canvas with smooth Zoom, Pan, Fit-to-screen, color legend overlay, fixed anchor badges, reserved zone hatching, pairwise overlap red-highlighting, interactive department property inspector drawer, and direct SVG/PNG export buttons.
  6. *Multi-Objective Pareto Analysis:* 3-objective non-dominated frontier discovery and knee-point compromise visualization.
  7. *Explainable Decision Support:* Local offline deterministic explainer with optional consent-gated Gemini AI module.
  8. *Research Export Center:* One-click downloads for Layout JSON, Experiment Config JSON, Canonical Metrics CSV, Comparison CSV, Pareto Portfolio JSON, and 2D vector graphics.
- **Thesis Reproducibility Provenance Card (`ExportCenterCard.tsx`):** Cryptographic experiment metadata recording version `v1.0.0-rc.1`, Problem Hash, EvaluationConfig Hash, Layout SHA-256 signature, Source Algorithm, Random Seed, and Run Duration.
- **Phase 14 End-to-End Test Suite (`test_phase14_release_candidate.py`):** Comprehensive integration tests covering custom problem validation roundtrips, area utilization limits, inline problem solving, and layout signature reproducibility (bringing total backend tests to 377).
- **Comprehensive Documentation Suite:** `README_PRIVATE.md`, `docs/USER_GUIDE.md`, `docs/INSTALLATION_GUIDE.md`, `docs/RESEARCH_WORKFLOW.md`, and `docs/PRIVATE_DEPLOYMENT_PLAN.md`.

### Changed
- Explicitly bumped platform version across `backend/app/core/config.py`, `backend/pyproject.toml`, and `frontend/package.json` to `1.0.0-rc.1`.
- Enhanced `Header.tsx` with release candidate tag and local-first security indicator.
- Strengthened type safety in `frontend/src/types/api.ts` with clean `ReservedZone`, `ContinuousLayout`, and `EvaluationReport` structures.

---

## [0.13.0] - Phase 13: Industrial Validation, Security Hardening & Performance
### Added
- Synthetic stress test suites (`HIGH_DENSITY_15`, `HIGH_DENSITY_20`, `CONSTRAINED_FACTORY_12`, `LOGISTICS_FACTORY_15`).
- Boundary fuzzing tests and edge-case validation for extreme aspect ratios.
- Total backend test count reached 354 tests.

---

## [0.12.0] - Phase 12: Confidentiality-First Gemini AI Decision Explanation
### Added
- `LocalDeterministicExplainer` providing 100% offline, mathematically grounded decision summaries.
- Optional Google Gemini API integration with `AI_ENABLED=false` default.
- Cryptographic consent signing (`ServerConsentStore`) and payload sanitization excluding proprietary geometries.

---

## [0.11.1] - Phase 11.1: Adaptive Pipeline Consistency Audit
### Fixed
- Reconciled metric discrepancies between standalone Guillotine generator and Adaptive Strategy Engine runs.
- Enforced strict routing through `CanonicalEvaluationService` for all portfolio candidate evaluations.

---

## [0.11.0] - Phase 11: Adaptive Strategy Engine v1
### Added
- Autonomous problem fingerprinting (`ProblemAnalyzer`) evaluating density, flow connectivity, and aspect constraints.
- Strategy decision tree selecting between constructive heuristics, slicing tree GA, and multi-stage fallbacks.
- Candidate portfolio aggregation and automated Pareto frontier generation.

---

## [0.10.0] - Phase 10: Multi-Objective Evaluation & Pareto Frontier v1
### Added
- 3-objective Pareto dominance engine:
  - Material Handling Cost (MHC) ➔ Minimize
  - Relationship (REL) Satisfaction ➔ Maximize
  - Soft Constraint Penalty ➔ Minimize
- Hypervolume indicator and knee-point compromise detection.

---

## [0.9.2] - Phase 9.2: Evaluation Integrity & Reproducibility Audit
### Fixed
- Addressed Flow-Distance vs. Material Handling Cost calculation discrepancies.
- Established canonical evaluation contract and SHA-256 evaluation configuration hashing.

---

## [0.9.1] - Phase 9.1: Genetic Algorithm Verification & Benchmark
### Verified
- Validated GA optimization performance on `FLP_INDUSTRIAL_10` benchmark.
- Confirmed baseline independence from manual layout coordinates.

---

## [0.9.0] - Phase 9: Genetic Algorithm v1
### Added
- Slicing-tree chromosome representation with flexible bay structure decoding.
- Area-preserving continuous bay dimension calculation.
- Order Crossover (OX) and multi-operator mutation pipeline.

---

## [0.8.1] - Phase 8.1: Generated Layout Verification & Improvement Baseline
### Verified
- Guillotine row packing determinism and exact area conservation across 10 independent verification runs.

---

## [0.8.0] - Phase 8: Feasible Rectangular Layout Generator
### Added
- Guillotine row packing algorithm for unequal-area facility layout generation.
- Exact dimension generator respecting aspect ratio bounds and building envelope constraints.

---

## [0.7.1] - Phase 7.1: Algorithm Comparison & Empirical Benchmarks
### Added
- Benchmark runner comparing CORELAP, ALDEP, and CRAFT.
- Automated comparison reporting table and relative improvement metrics.

---

## [0.7.0] - Phase 7: CRAFT Heuristic
### Added
- Continuous CRAFT pairwise department centroid exchange local improvement heuristic.
- Support for 2-way and 3-way department swaps with steepest-descent termination.

---

## [0.6.0] - Phase 6: ALDEP Heuristic
### Added
- Automated Layout Design Program (ALDEP) stochastic construction algorithm.
- Strip-sweep placement across horizontal and vertical bands with Muther REL thresholding.

---

## [0.5.0] - Phase 5: CORELAP Heuristic
### Added
- Computerized Relationship Layout Planning (CORELAP) constructive heuristic.
- Total Closeness Rating (TCR) prioritization and 8-neighbor adjacency placement.

---

## [0.4.0] - Phase 4: Layout Evaluation & Multi-Metric Decision Engine
### Added
- Material Handling Cost calculation with rectilinear (Manhattan) centroid distance.
- Muther SLP relationship satisfaction and boundary adjacency measurement.
- Soft constraint penalty evaluation.

---

## [0.3.0] - Phase 3: Layout Representation & Geometry Engine
### Added
- Continuous 2D Cartesian spatial representation ($[0, W] \times [0, H]$) with origin at bottom-left.
- Pairwise rectangular overlap detection ($O(n^2)$).
- Canonical layout normalization and SHA-256 geometric layout signature generator.

---

## [0.2.0] - Phase 2: Problem Ingestion & Data Validation
### Added
- Facility, Department, Material Flow, and Relationship data models.
- Problem JSON schema validation and area utilization verification.

---

## [0.1.0] - Phase 1: Core Foundation & Architectural Scaffolding
### Added
- Initial FastAPI backend and React frontend application structure.
- Health diagnostics and modular architectural roadmap.
