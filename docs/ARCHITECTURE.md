# Facility Layout Optimization & Decision Support System (FLODSS)
## Architecture & Technical Design Specification

### 1. Vision & Purpose
FLODSS is designed as an industrial-grade Operations Research and Facility Logistics decision support platform. Rather than a monolithic layout generator, it implements a decoupled, modular architecture capable of running multiple construction heuristics, improvement methods, metaheuristics, and exact solvers, followed by rigorous multi-criteria evaluation, discrete-event simulation, and AI-assisted layout diagnosis.

---

### 2. Architectural Principles

1. **Decoupled Optimization & Evaluation**:
   Algorithms do not evaluate their own fitness or subjective quality.
   $$\text{Algorithm} \longrightarrow \text{LayoutSolution} \longrightarrow \text{Evaluation Engine}$$
   This guarantees objective, reproducible comparison across completely different algorithmic paradigms (e.g. comparing CORELAP with CRAFT or Genetic Algorithms).

2. **Open-Closed Principle (Plug-and-Play)**:
   New algorithms inherit from `BaseLayoutAlgorithm` and register via `@register_algorithm`. Adding a new solver requires zero modifications to existing services, API routers, or frontend modules.

3. **Strict Domain Typing & Validation**:
   All entities (Facility, Department, Flow, Relationship, Constraint, Problem, Solution) are governed by Pydantic v2 schemas with automated validation of geometry, area utilization, and graph consistency.

4. **Long-Term Decision Support Pipeline**:
   ```mermaid
   flowchart TD
       A["Factory Problem Specification"] --> B["Problem Representation (FLP)"]
       B --> C["Problem Fingerprint & Characteristic Analysis"]
       C --> D["Strategy & Algorithm Selection"]
       D --> E["Candidate Generation (Construction)"]
       E --> F["Iterative Optimization (Improvement / Metaheuristic / MILP)"]
       F --> G["Multi-Criteria Evaluation Engine"]
       G --> H["Dynamic Simulation (Congestion & AGV Flow)"]
       H --> I["AI Diagnosis (Gemini Advisor)"]
       I --> J["Strategy Adaptation & Parameter Tuning"]
       J --> F
       I --> K["Pareto Front & Solution Ranking"]
       K --> L["Executive Decision Support & 2D/3D Blueprint"]
   ```

---

### 3. Subsystem Breakdown

#### 3.1 Core Data Models (`app.models`)
- **Facility**: Global footprint, bounds, total area, and structural metadata.
- **Department**: Target area, aspect ratio boundaries, optional fixed coordinates and orientations.
- **Flow**: Quantitative material flow volumes ($f_{ij}$), unit costs ($c_{ij}$), routing identifiers.
- **Relationship**: Muther's SLP qualitative closeness ratings ($r_{ij} \in \{A, E, I, O, U, X\}$) with configurable affinity weights.
- **Constraint**: Hard and soft constraints (non-overlapping, perimeter boundary, minimum separation, forbidden zones, aspect ratio limits).
- **FacilityLayoutProblem**: Validated aggregate case container.
- **LayoutSolution**: Placements, centroid coordinates, bounding boxes, recorded violations, and feasibility flags.

#### 3.2 Algorithm Interface & Registry (`app.algorithms`)
- `BaseLayoutAlgorithm`: Abstract Base Class defining standard lifecycle methods:
  - `name: str`
  - `version: str`
  - `category: AlgorithmCategory`
  - `parameters: Dict[str, Any]`
  - `supported_problem_types: List[str]`
  - `validate(problem) -> ValidationResult`
  - `solve(problem, **kwargs) -> LayoutSolution`
- `AlgorithmRegistry`: Dynamic registry providing factory creation, introspection, and registration decorators.

#### 3.3 Evaluation Engine (`app.evaluation`)
- `BaseMetricEvaluator`: Abstract evaluator contract.
- Standard metrics supported by architecture:
  - Material Handling Cost (MHC)
  - Total Flow-Distance Cost ($\sum f_{ij} \cdot d_{ij} \cdot c_{ij}$)
  - Relationship Satisfaction ($\sum r_{ij} \cdot s_{ij}$)
  - Floor Area Utilization
  - Constraint Penalty Violations
  - Aisle Congestion & Bottlenecks
  - Safety & Hazard Separation Score
  - Layout Compactness & Perimeter Efficiency
  - Reconfiguration / Relocation Transition Cost
- `EvaluationEngine`: Evaluates single solutions and produces multi-solution comparative rankings.

#### 3.4 Constraint Validation Engine (`app.constraints`)
- Manages hard feasibility (strict validity) and soft feasibility (penalties applied in multi-objective scoring).

#### 3.5 Optimization & Multi-Objective Layer (`app.optimization`)
- Data structures for Pareto fronts and multi-objective trade-off analysis.

#### 3.6 Dynamic Simulation (`app.simulation`)
- Contracts for discrete-event traffic simulation and stochastic material handling validation.

#### 3.7 Cognitive Layer (`app.ai`)
- Contracts for automated layout diagnosis, weakness identification, and heuristic improvement suggestions (designed for Gemini API integration).

#### 3.8 Visualization Subsystem (`app.visualization`)
- Normalized coordinate translation for 2D canvas blueprints and future 3D representations.

---

### 4. REST API Architecture (`app.api`)
- Built on **FastAPI**.
- Standardized CORS middleware configured for frontend origins.
- Health & readiness endpoint: `GET /api/health`.
- OpenAPI documentation automatically available at `/docs` and `/redoc`.
