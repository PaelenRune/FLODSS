# FLODSS User Guide: End-to-End Operational Manual
## Facility Layout Optimization & Decision Support System (`v1.0.0-rc.1`)

This manual guides researchers, operations analysts, and industrial engineers through the end-to-end workflow of facility layout optimization using FLODSS. No advanced software programming knowledge is required; all interactions are accessible through the web workspace.

---

## Table of Contents
1. [Workflow Overview](#1-workflow-overview)
2. [Step 1: Problem Definition & Department Modeling](#step-1-problem-definition--department-modeling)
3. [Step 2: From-To Flow & REL Closeness Matrices](#step-2-from-to-flow--rel-closeness-matrices)
4. [Step 3: Spatial Constraints & Reserved Exclusion Zones](#step-3-spatial-constraints--reserved-exclusion-zones)
5. [Step 4: Algorithm Selection & Optimization Execution](#step-4-algorithm-selection--optimization-execution)
6. [Step 5: Interactive 2D Layout Canvas & Spatial Inspection](#step-5-interactive-2d-layout-canvas--spatial-inspection)
7. [Step 6: Multi-Objective Trade-Off & Pareto Frontier Analysis](#step-6-multi-objective-trade-off--pareto-frontier-analysis)
8. [Step 7: Explainable Decision Support (Offline-First)](#step-7-explainable-decision-support-offline-first)
9. [Step 8: Research Export Center & Academic Thesis Provenance](#step-8-research-export-center--academic-thesis-provenance)

---

## 1. Workflow Overview

FLODSS organizes facility design into eight sequential engineering tabs located in the top navigation bar:

```
[1. Problem Editor] ➔ [2. Flow & REL] ➔ [3. Constraints] ➔ [4. Optimization]
          ➔ [5. 2D Layout Viewer] ➔ [6. Pareto & Trade-offs] ➔ [7. AI Decision Support] ➔ [8. Export Center]
```

At any point, changes made in one tab are immediately propagated throughout the entire platform.

---

## Step 1: Problem Definition & Department Modeling

Navigate to **Tab 1: Problem Editor**.

### 1.1 Facility Boundaries
- **Width ($W$) and Height ($H$):** Enter the outer Cartesian dimensions of your factory floor in meters (e.g., $100.0\,\text{m} \times 60.0\,\text{m}$).
- **Total Area & Utilization:** The system computes gross floor space ($6000.0\,\text{m}^2$) and displays live area utilization percentage.

### 1.2 Department Inventory Table
- **Department ID:** Unique alphanumeric tag (e.g., `DEP_01`, `RECEIVING`, `MILLING`).
- **Required Area ($A_i$):** Target physical footprint in square meters.
- **Aspect Ratio Bounds ($\alpha_{\min}, \alpha_{\max}$):** Permissible elongation factor ($\max(w, h) / \min(w, h)$). Standard industrial practice restricts aspect ratios to $[1.0, 3.0]$ to prevent narrow or unconstructible slivers.
- **Fixed Locations (Optional):** Check "Fixed Location" if equipment or dock doors are immovable, specifying continuous coordinate anchors $(X_0, Y_0)$.

### 1.3 Preloaded Benchmark Templates
To load classic industrial benchmarks, open the **"Load Benchmark Problem"** dropdown:
- `FLP_INDUSTRIAL_10`: 10-department manufacturing plant ($100 \times 60\,\text{m}$, 84.7% area utilization).
- `FLP_MANUFACTURING_8`: 8-department fabrication cell ($80 \times 50\,\text{m}$).
- `FLP_HEALTHCARE_12`: 12-department hospital clinical block ($120 \times 80\,\text{m}$).
- `FLP_LOGISTICS_15`: 15-department distribution hub ($150 \times 100\,\text{m}$).

Clicking **"Validate Problem Specification"** runs a real-time schema and geometric check against the backend `/api/problems/validate` endpoint, verifying unique IDs, utilization limits, and aspect feasibility.

---

## Step 2: From-To Flow & REL Closeness Matrices

Navigate to **Tab 2: Flow & REL**.

### 2.1 From-To Flow Matrix
- Represents directed material transfer volume per time period (e.g., pallets/day, fork-truck moves/week).
- In the grid table, rows represent source departments ($i$) and columns represent destination departments ($j$).
- Input numerical values directly into cells. Row totals (Total Outflow) and column totals (Total Inflow) update automatically.
- Click **"Export Flow Matrix CSV"** to save or inspect data in Microsoft Excel or R.

### 2.2 Systematic Layout Planning (SLP) REL Matrix
- Implements Richard Muther’s qualitative closeness chart:
  - **A (Score 16):** Absolutely Necessary (direct adjacency required, e.g., Melt Shop to Casting).
  - **E (Score 8):** Especially Important (close proximity strongly preferred).
  - **I (Score 4):** Important (standard functional relationship).
  - **O (Score 2):** Ordinary Closeness OK.
  - **U (Score 0):** Unimportant (no physical or functional interaction).
  - **X (Score -8):** Undesirable / Prohibited (must be separated, e.g., Paint Booth and Welding).
- Selecting a rating from the dropdown automatically updates the symmetric cell across the diagonal.
- Click **"Export REL Matrix CSV"** to archive the closeness chart.

---

## Step 3: Spatial Constraints & Reserved Exclusion Zones

Navigate to **Tab 3: Constraints**.

### 3.1 Reserved Exclusion Zones
Used to model fixed architectural obstacles where departments cannot be placed:
- Central logistics corridors / spine aisles
- Structural building columns
- Emergency fire exits and egress paths
- Utility shafts and HVAC risers

**How to add a reserved zone:**
1. Enter an identifier (e.g., `RZ_MAIN_AISLE`).
2. Choose zone type (`aisle_corridor`, `building_column`, `emergency_exit`, `utility_chase`).
3. Enter bounding box coordinates: $X_{\min}, X_{\max}, Y_{\min}, Y_{\max}$.
4. Check **"Strict Exclusion"** (enforced as a hard constraint with zero tolerance).
5. Click **"Add Reserved Zone"**.

### 3.2 Fixed Position Equipment
Review all pinned equipment anchors. Fixed departments display a 📌 badge and will be treated as stationary landmarks by the solvers.

---

## Step 4: Algorithm Selection & Optimization Execution

Navigate to **Tab 4: Optimization**.

### 4.1 Solver Selection
FLODSS features six distinct algorithmic solvers:
1. **Adaptive Strategy Engine v1 (Recommended):** Evaluates problem characteristics (density, aspect ratios, obstacles) and autonomously executes the best solver pipeline with automatic fallbacks.
2. **Genetic Algorithm v1:** Slicing-tree chromosome representation with flexible bay decoding, order crossover (OX), and multi-operator mutation.
3. **Feasible Rectangular Generator (Guillotine):** Constructive row packing algorithm guaranteeing complete area conservation and zero overlap.
4. **CRAFT Heuristic:** Pairwise 2-way and 3-way continuous centroid swap local search.
5. **CORELAP:** Classical constructive heuristic based on Total Closeness Rating (TCR).
6. **ALDEP:** Stochastic strip-sweep construction with Muther REL thresholding.

### 4.2 Search Hyperparameters
- **Random Seed:** Set an integer (default `42`) to guarantee 100% deterministic reproducibility across experiment runs.
- **Time Budget (Seconds):** Maximum wall-clock time allocated for metaheuristic search.
- **Population Size / Generations:** Genetic algorithm exploration depth.

### 4.3 Execution & Infeasibility Handling
Click **"Execute Optimization Solver"**:
- FLODSS displays **true wall-clock elapsed time in milliseconds** upon completion.
- If a method encounters geometrical dead-ends (e.g., Guillotine packing unable to fit high-aspect departments into a dense boundary), the system renders an explicit **Infeasibility Warning Banner** detailing:
  - Exact termination reason.
  - Partial placement status.
  - Recommended fallback action (e.g., "Switch to Genetic Algorithm or Adaptive Engine").
- When a feasible solution is found, the **Result Metrics Panel** displays:
  - Material Handling Cost (MHC)
  - Relationship (REL) Satisfaction Percentage
  - Soft Constraint Penalty
  - Total Evaluations / Generations

Click **"View 2D Layout"** to inspect the geometry, or **"Compare on Pareto Frontier"** to evaluate trade-offs.

---

## Step 5: Interactive 2D Layout Canvas & Spatial Inspection

Navigate to **Tab 5: 2D Layout Viewer**.

### 5.1 Real-Time Canvas Controls
- **True Cartesian 1:1 Scale:** Layout is plotted in continuous solver coordinates with origin $(0, 0)$ at the bottom-left corner.
- **Zoom In / Out:** Click `+` and `-` buttons or use the mouse wheel.
- **Pan:** Click and drag anywhere on the canvas to inspect large facilities.
- **Fit to Screen:** Instantly centers and scales the entire facility boundary to your display window.
- **Grid Toggle:** Display or hide 5-meter background coordinate grid lines.
- **Color Legend:** Toggle the department palette overlay panel.

### 5.2 Visual Verification Badges
- **Reserved Exclusion Zones:** Rendered with diagonal warning hatch patterns and boundary labels.
- **Fixed Position Anchors:** Tagged with a gold 📌 pin indicator.
- **Pairwise Overlap Alert:** If any two departments intersect ($[x_1, x_1+w_1] \cap [x_2, x_2+w_2] > 0$), intersecting regions highlight in vivid red with an immediate violation notice banner.
- **Department Inspector Drawer:** Clicking on any department rectangle opens a side inspection drawer showing:
  - Exact Origin $(X, Y)$ and Center Centroid $(X_c, Y_c)$
  - Width $\times$ Height ($W \times H$) in meters
  - Measured Area vs. Required Area ($m^2$)
  - Aspect Ratio and Orientation Angle

### 5.3 Vector & Raster Export
Directly on the canvas toolbar:
- Click **"Export SVG"** to download crisp, publication-grade vector graphics for thesis figures.
- Click **"Export PNG"** to download 300 DPI raster renders.

---

## Step 6: Multi-Objective Trade-Off & Pareto Frontier Analysis

Navigate to **Tab 6: Pareto & Trade-offs**.

In industrial layout planning, single-objective optimization often yields skewed results. FLODSS simultaneously optimizes three orthogonal criteria:
1. **Material Handling Cost (MHC):** Rectilinear flow cost $\sum_{i < j} f_{ij} c_{ij} (|x_i - x_j| + |y_i - y_j|)$ ➔ **MINIMIZE**
2. **Relationship Satisfaction:** SLP affinity score $\sum_{i < j} r_{ij} \cdot \text{Adj}(i, j)$ ➔ **MAXIMIZE**
3. **Soft Constraint Penalty:** Cumulative penalty for minor aspect ratio stretching or corridor buffering ➔ **MINIMIZE**

### 6.1 Pareto Dominance & Frontier Plot
- Displays interactive 2D and 3D scatter plots of candidate solutions generated by different algorithms.
- **Non-dominated points (Pareto frontier):** Highlighted with star badges.
- **Knee-point detection:** Highlights the optimal compromise solution exhibiting maximum gain across all objectives without extreme sacrifices.

---

## Step 7: Explainable Decision Support (Offline-First)

Navigate to **Tab 7: AI Decision Support**.

### 7.1 Local Deterministic Explainer (100% Offline)
- Runs completely on your local computer without external API calls or internet access.
- Produces rigorous engineering explanations answering:
  - *Why was a specific algorithm selected by the Adaptive Engine?*
  - *Which department pairs contribute most to Material Handling Cost?*
  - *What trade-offs exist between the top Pareto candidate layouts?*
- All metrics cited in explanations are mathematically verified against `CanonicalEvaluationService`.

### 7.2 Gemini AI Mode (Strictly Disabled by Default)
- External AI cloud integration is **disabled by default** to safeguard confidential layout geometries and plant layouts.
- Can only be activated if the researcher explicitly provides a Gemini API key and grants cryptographically signed consent for sanitized statistical summaries.

---

## Step 8: Research Export Center & Academic Thesis Provenance

Navigate to **Tab 8: Export Center**.

For doctoral dissertations, master’s theses, and peer-reviewed conference publications, scientific reproducibility is paramount. The Export Center bundles complete provenance metadata:

### 8.1 Thesis Provenance Card
Displays live cryptographic verification parameters:
- **FLODSS Version:** `v1.0.0-rc.1`
- **Problem ID / Hash:** Deterministic SHA-256 fingerprint of facility dimensions, departments, flows, and constraints.
- **Layout Signature:** Canonical SHA-256 geometric hash (invariant under department ordering).
- **Evaluation Config Hash:** Identifies exact distance metrics (Rectilinear Manhattan) and penalty parameters.
- **Source Algorithm:** Method name and version.
- **Random Seed & Duration:** Base pseudo-random seed and true execution duration in milliseconds.

### 8.2 One-Click Academic Deliverables
- **Layout Geometry JSON:** Complete continuous coordinate bounding boxes and placements (`flodss_layout_<id>_<sig>.json`).
- **Experiment Config JSON:** Full problem definition, hyperparameters, random seeds, and environment settings for reproducibility (`flodss_experiment_config_<id>.json`).
- **Evaluation Metrics CSV:** Canonical table of MHC, Flow-Distance, REL Satisfaction, Adjacency, and Feasibility flags (`flodss_metrics_<id>.csv`).
- **Algorithm Comparison CSV:** Side-by-side benchmark comparison table ready for import into LaTeX tables or statistical software (`flodss_algorithm_comparison_<id>.csv`).
- **Pareto Portfolio JSON:** Array of all non-dominated candidate layouts with full objective vectors (`flodss_pareto_portfolio_<id>.json`).
