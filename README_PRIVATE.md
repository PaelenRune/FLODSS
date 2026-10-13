# FLODSS: Facility Layout Optimization & Decision Support System
## Confidential Private Research Prototype — Release Candidate `v1.0.0-rc.1`

> [!CAUTION]
> **STRICTLY CONFIDENTIAL / PROPRIETARY RESEARCH RELEASE CANDIDATE**  
> This software is a private research platform undergoing academic evaluation and intellectual property / patent assessment.  
> **Do not distribute, deploy to public servers, publish source code to open repositories (e.g., GitHub, GitLab), or upload proprietary factory datasets.**

---

## 1. System Overview

**FLODSS (Facility Layout Optimization & Decision Support System)** is an integrated Operations Research and Industrial Engineering platform engineered for modular facility layout generation, multi-criteria algorithmic evaluation, and explainable decision support.

The system addresses the classical Unequal-Area Facility Layout Problem (UA-FLP) in continuous two-dimensional Cartesian space, enforcing hard geometric feasibility (zero overlap, exact area conservation, boundary constraints, reserved spine/corridor exclusion zones, and fixed equipment anchors) while optimizing multiple quantitative and qualitative objectives.

### Key Architectural Pillars
- **Strict Geometric Correctness:** Continuous Cartesian space $[0, W] \times [0, H]$ with origin at bottom-left $(0,0)$. Real-time pairwise rectangle intersection testing ($\max(0, \min(x_1+w_1, x_2+w_2) - \max(x_1, x_2)) \times \dots$) guarantees $0.00\,\text{m}^2$ total overlap.
- **Canonical Evaluation Engine:** Deterministic, reproducible scoring across Material Handling Cost (MHC, rectilinear Manhattan centroid distance), Flow-Distance Metric, Muther Systematic Layout Planning (SLP) Relationship (REL) chart affinity score, boundary adjacency percentage, and soft penalty functions.
- **Multi-Method Solver Portfolio:**
  1. *CORELAP:* Constructive heuristic via Total Closeness Rating (TCR) and 8-neighbor placement.
  2. *ALDEP:* Stochastic strip-sweep construction with Muther REL affinity thresholding.
  3. *CRAFT:* Continuous steepest-descent 2-way and 3-way pairwise department centroid swap improvement.
  4. *Feasible Rectangular Generator:* Guillotine row packing with exact continuous dimension solving.
  5. *Genetic Algorithm v1:* Slicing-tree chromosome representation with area-preserving bay decoding, Order Crossover (OX), and multi-operator mutation.
  6. *Adaptive Strategy Engine v1:* Autonomous decision pipeline analyzing problem fingerprint (density, aspect bounds, fixed zones) to schedule primary heuristics, metaheuristics, and automatic fallback pathways.
- **Multi-Objective Pareto Analysis:** Computes non-dominated candidate sets across 3 orthogonal objectives (Minimize MHC, Maximize REL Satisfaction, Minimize Soft Penalties) with hypervolume indicators, knee-point detection, and compromise ranking.
- **Confidentiality-First Explainability:** Local-first, deterministic rule-based explainer running 100% offline. Optional Google Gemini API integration is **disabled by default**, protected behind explicit multi-step user consent and SHA-256 payload whitelisting.
- **Academic Thesis Export Center:** One-click bundles containing Layout Geometry JSON, Experiment Config JSON, Canonical Metrics CSV, Benchmark Comparison CSV, Pareto Portfolio JSON, and 2D Vector Visualizations (SVG/PNG) with full cryptographic provenance (FLODSS version `v1.0.0-rc.1`, problem hash, evaluation config hash, layout SHA-256 signature, random seed, and wall-clock execution time).

---

## 2. Directory Structure

```
Facility/
├── backend/                         # Python 3.12+ FastAPI backend
│   ├── app/
│   │   ├── algorithms/              # CORELAP, ALDEP, CRAFT, Generator, GA
│   │   ├── api/                     # REST API route controllers
│   │   ├── evaluation/              # CanonicalEvaluationService & metrics
│   │   ├── feasibility/             # Guillotine & Slicing decoders
│   │   ├── models/                  # Pydantic schemas (Facility, Dept, Flow, REL)
│   │   ├── optimization/            # Adaptive Strategy Engine & Pareto Frontier
│   │   ├── ai/                      # Local Explainer & Gemini Client (disabled)
│   │   └── services/                # Geometry engine, normalizer, problem service
│   ├── tests/                       # Pytest test suite (377 passing tests)
│   └── pyproject.toml               # v1.0.0-rc.1 backend specification
├── frontend/                        # React 18 + TypeScript + Vite workspace
│   ├── src/
│   │   ├── components/              # Canvas, ProblemEditor, MatrixEditor, Solvers...
│   │   ├── pages/                   # Tabbed Engineering Workspace (Dashboard)
│   │   ├── services/                # API client bindings
│   │   └── types/                   # Type declarations
│   └── package.json                 # v1.0.0-rc.1 frontend specification
├── data/examples/                   # Verified benchmark problems & canonical layouts
├── docs/                            # Architectural & User Documentation
└── README_PRIVATE.md                # This confidential prototype brief
```

---

## 3. Quick Start (Local Development)

### Prerequisites
- Python $\ge 3.12$
- Node.js $\ge 18.0$ and npm

### Backend Launch
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend Launch
```powershell
cd frontend
npm install
npm run dev
```

Access the engineering workspace at `http://localhost:5173`. Backend interactive API docs are available locally at `http://127.0.0.1:8000/docs`.

---

## 4. Academic Citation & Intellectual Property Notice

If referencing this software platform in thesis manuscripts, internal research memoranda, or defense presentations:

> *FLODSS (Facility Layout Optimization & Decision Support System), Version 1.0.0-rc.1, Private Research Prototype, Operations Research & Industrial Engineering Laboratory, 2026.*

**Notice:** All algorithmic formulations, adaptive strategy switching heuristics, slicing decoders, and user interface workflows are proprietary and confidential. Commercial distribution or unauthorized transmission is strictly prohibited.
