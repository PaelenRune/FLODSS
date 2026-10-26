# Facility Layout Optimization & Decision Support System (FLODSS)

An industrial-grade Operations Research (OR) and Industrial Engineering (IE) platform for modular facility layout generation, multi-criteria evaluation, dynamic simulation, and decision support.

## Live Demo / Canlı Demo

[![Live Demo on Render](https://img.shields.io/badge/Render-Live%20Demo-46E3B7?logo=render&logoColor=white)](https://flodss.onrender.com)

**[Try FLODSS online](https://flodss.onrender.com)** — no downloads or local setup required.

**[FLODSS'u çevrimiçi deneyin](https://flodss.onrender.com)** — indirme veya yerel kurulum gerektirmez.

> **Current Phase Status:** **Phase 2: Problem Modeling & Data Ingestion Completed.**  
> *Note:* Optimization algorithms (CORELAP, ALDEP, CRAFT, GA, SA, etc.), simulation models, and AI assistants are slated for subsequent modular phases according to the roadmap below.

---

## 1. Project Purpose & Vision

The objective of this project is to develop a modular Decision Support System capable of:
1. Ingesting industrial factory parameters (departments, areas, flows, relationships, and geometric constraints).
2. Running multiple layout optimization algorithms (construction heuristics, improvement heuristics, metaheuristics, and exact solvers) across identical standardized problem representations.
3. Decoupling algorithm execution from objective multi-criteria evaluation.
4. Comparing alternative candidate layouts through Pareto trade-off analyses, discrete-event flow simulations, and AI-driven layout diagnosis.

### Target Decision Pipeline:
$$\text{Factory Problem} \longrightarrow \text{Problem Representation} \longrightarrow \text{Problem Fingerprint} \longrightarrow \text{Strategy Selection} \longrightarrow \text{Candidate Generation} \longrightarrow \text{Optimization} \longrightarrow \text{Evaluation} \longrightarrow \text{Simulation} \longrightarrow \text{Diagnosis} \longrightarrow \text{Strategy Adaptation} \longrightarrow \text{Re-optimization} \longrightarrow \text{Pareto Solutions} \longrightarrow \text{Decision Support}$$

---

## 2. Technology Stack

- **Backend:**
  - Python 3.12+
  - **FastAPI**: Asynchronous high-performance REST API
  - **Pydantic v2**: Type validation, domain schema enforcement, and serialization
  - **NumPy & SciPy**: Numerical linear algebra, distance matrix computations, and scientific optimization foundation
  - **pytest**: Test suite with automated schema and interface validation
  - Dependency management via standard `pyproject.toml`
- **Frontend:**
  - **React 18** + **TypeScript**
  - **Vite**: Modern rapid bundling and development server
  - Component-based architecture with telemetry polling and modular subsystem status cards
- **Architecture:**
  - Plug-and-play **Algorithm Registry** (`@register_algorithm`)
  - Decoupled **Evaluation Engine**
  - Independent **Constraint Engine**
  - Robust **Problem Loader & Matrix Converter** (JSON, CSV, From-To & REL Chart)
  - Structural **Problem Fingerprint & Analyzer**

---

## 3. Directory Structure

```text
Facility/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI route controllers (health, problems)
│   │   ├── core/            # Global configuration and settings
│   │   ├── models/          # Domain Pydantic schemas (Facility, Department, Flow, etc.)
│   │   ├── services/        # Business logic services (Health, ProblemLoader, MatrixParser, Analyzer)
│   │   ├── algorithms/      # BaseLayoutAlgorithm ABC & dynamic AlgorithmRegistry
│   │   ├── evaluation/      # Decoupled EvaluationEngine and metric evaluators
│   │   ├── constraints/     # ConstraintEngine and violation evaluators
│   │   ├── optimization/    # Multi-objective and Pareto solver foundations
│   │   ├── simulation/      # Discrete-event & traffic flow validation interfaces
│   │   ├── ai/              # AI Advisor and layout diagnosis interfaces
│   │   ├── visualization/   # 2D/3D layout rendering representations
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Pytest unit tests (30 passing tests)
│   └── pyproject.toml       # Backend dependency and project specification
│
├── frontend/
│   ├── src/
│   │   ├── components/      # Reusable React components (Header, Roadmap, ProblemCard, StatusCard)
│   │   ├── pages/           # Page views (Dashboard)
│   │   ├── services/        # API client services
│   │   ├── types/           # TypeScript API interfaces
│   │   ├── hooks/           # Custom React hooks (useHealthCheck)
│   │   ├── utils/           # Formatting and helper utilities
│   │   ├── App.tsx          # Root application component
│   │   └── main.tsx         # Frontend entrypoint
│   ├── index.html           # HTML5 document
│   ├── package.json         # Frontend dependencies and npm scripts
│   ├── tsconfig.json        # TypeScript configuration
│   └── vite.config.ts       # Vite bundler configuration
│
├── data/
│   ├── examples/            # Validated JSON benchmark cases (10-department sample_plant.json)
│   └── datasets/            # Standard literature benchmarks (Bazaraa, Nugent, Armour & Buffa)
│
├── experiments/             # Computational experiments, parameter sweeps, and convergence logs
├── docs/                    # Technical architecture specifications (ARCHITECTURE.md)
├── scripts/                 # Execution helper scripts (run_backend, run_frontend, run_tests)
└── README.md
```

---

## 4. Development Roadmap

The system follows a strict incremental development lifecycle:

1. **Phase 1: Core Architecture** :white_check_mark: *(Completed)*
   - Project directory scaffolding, type-safe Pydantic models, algorithm registry, evaluation engine interface, FastAPI health endpoint, React frontend foundation, and comprehensive unit tests.
2. **Phase 2: Problem Modeling & Data Ingestion** :white_check_mark: *(Completed)*
   - Validated JSON problem specification (`FacilityLayoutProblem`), From-To matrix parsers/inverters, Muther REL chart converters, granular multi-objective configurations, hard/soft constraint normalizers, realistic 10-department factory benchmark case, `ProblemLoader` (JSON & CSV), `ProblemService`, structural `ProblemFingerprint` analyzer, and REST API endpoints (`/api/problems/examples`, `/api/problems/validate`).
3. **Phase 3: Layout Representation** *(Upcoming)*
   - Discrete grid representations (unit block grids), continuous coordinate spaces, slicing trees, and flexible boundary models.
4. **Phase 4: Classical Construction & Improvement Algorithms**
   - CORELAP, ALDEP, MAT (construction heuristics), and CRAFT (pairwise exchange improvement).
5. **Phase 5: Metaheuristic Optimization**
   - Genetic Algorithm (GA), Simulated Annealing (SA), Particle Swarm Optimization (PSO), and Tabu Search.
6. **Phase 6: Multi-Objective & Exact Solvers**
   - NSGA-II, Pareto front generation, and Mixed-Integer Linear Programming (MILP / OR-Tools).
7. **Phase 7: Constraint Engine**
   - Hard geometric non-overlap enforcement, boundary compliance, clearance zones, and soft penalty functions.
8. **Phase 8: Dynamic Simulation**
   - Discrete-event simulation, aisle congestion analysis, and material handling vehicle flow validation.
9. **Phase 9: Adaptive Optimization Strategy**
   - Automated algorithm selection based on problem fingerprint, size, and constraint density.
10. **Phase 10: AI Assistant & Decision Support**
    - Gemini API integration for automated layout diagnosis, explanation of trade-offs, and design suggestions.
11. **Phase 11: Benchmarking Suite**
    - Automated comparative runs on literature benchmarks (Bazaraa, Nugent, Armour & Buffa).
12. **Phase 12: Advanced Interactive Visualization**
    - Interactive 2D plant canvas with manual drag-and-drop tweaking and 3D WebGL factory floor view.
13. **Phase 13: Research & Reproducibility**
    - Paper reproduction scripts, statistical hypothesis testing on results, and exportable technical reports.

---

## 5. Quick Start & Execution

### Prerequisites:
- Python 3.12+
- Node.js 18+ (Node 22 LTS verified)

### 1. Run Backend Server
```powershell
# From the project root:
.\backend\.venv\Scripts\Activate.ps1
uvicorn app.main:app --app-dir backend --reload --port 8000
```
*Backend Swagger Docs:* `http://127.0.0.1:8000/docs`  
*Health Endpoint:* `http://127.0.0.1:8000/api/health`

### 2. Run Frontend Development Server
```powershell
cd frontend
npm run dev
```
*Frontend UI:* `http://localhost:3000`

### 3. Run Backend Unit Tests
```powershell
.\backend\.venv\Scripts\pytest backend\tests -v
```

### 4. Build Frontend for Production
```powershell
cd frontend
npm run build
```
