# FLODSS — PHASE 15.2: VISUAL QA ITERATIONS & DEFECT ROOT CAUSE ANALYSIS

**Date:** October 13, 2026  
**Author:** FLODSS Principal Frontend Engineer & UX Researcher  
**Status:** **GATE 3, 7 PASSED — ALL REGRESSION DEFECTS ERADICATED**

---

## 1. Baseline Defect Identification & Root Cause Analysis

The baseline regression reference was captured on `FLP_EXPANSION_8` under 220% zoom. Inspection of that baseline revealed five severe visual, ergonomic, and scientific defects that rendered the tool unacceptable for academic and industrial decision support:

### Defect 1 (DEF-001): Catastrophic Text Explosion Under Zoom
- **Symptom:** When zooming to 220% or higher, department labels and dimension texts grew exponentially, expanding to hundreds of pixels across the screen, obliterating the floor plan.
- **Root Cause:**
  1. Font sizes were defined in physical facility world meters (e.g. `fontSize = 3.8m` to `6.2m`).
  2. The SVG element had a fixed width of `baseViewBoxW * 4.6` (e.g. 920px), and zoom was implemented by applying a CSS `transform: scale(zoom)` on the outer container.
  3. Consequently, at 220% zoom, the screen size in pixels was multiplied twice: once by the meter-to-pixel ratio and once by the CSS scale factor:
     $$\text{Screen Pixels} = \text{fontSize}_{\text{world}} \times \text{pixelsPerMeter} \times \text{scale}(2.2) \approx 140\text{px}$$
- **Architectural Solution:**
  1. Eliminated all CSS `transform: scale()` on outer containers.
  2. Transferred all pan and zoom logic into the native SVG `viewBox` coordinates via a responsive `ResizeObserver`.
  3. Dynamic Screen-Space Inversion: Text font sizes in SVG world meters are dynamically calculated to produce a constant, comfortable screen size of 11–13px:
     $$\text{fontSize}_{\text{world}} = \frac{\text{targetScreenPixels}}{\text{effectivePixelsPerMeter} \times \text{zoom}}$$
     At any zoom level (from 50% to 500%), text remains crisp, legible, and locked to human readability thresholds.

---

### Defect 2 (DEF-002): Visual Overload & Cluttered Material Flow Overlay
- **Symptom:** Factory floor plan was completely obscured by massive, overlapping, opaque arrow lines.
- **Root Cause:**
  1. Material flow overlay defaulted to `showFlows = true` on initial load.
  2. Flow line stroke widths were computed as raw volume divided by 50 (`strokeWidth = flow.quantity / 50`), yielding strokes up to 20m wide.
  3. Flow lines were rendered in front of department labels, obliterating department names.
- **Architectural Solution:**
  1. **Clean Layout by Default:** `showFlows` defaults strictly to `false`. The primary view presents a clean, architectural factory blueprint.
  2. **Normalized Clamping:** When enabled, stroke widths are normalized by maximum flow volume and clamped strictly between 1.2px and 3.8px in screen coordinates.
  3. **Z-Index Layering:** Flow lines are placed in a background SVG `<g id="flow-overlay-layer">` rendered *behind* department labels and centroid markers.
  4. **Quadratic Curvature:** Bidirectional flows between pairs $(i, j)$ and $(j, i)$ utilize quadratic Bezier offsets (`Q midX midY`) to prevent overlapping line collisions.

---

### Defect 3 (DEF-003): Text Collision & Label Overflow in Compact Departments
- **Symptom:** In departments with small dimensions or high aspect ratios, department names spilled out into neighboring departments, causing confusion about room boundaries.
- **Root Cause:** SVG `<text>` elements lacked bounding constraints, rendering unclipped beyond department rectangle borders.
- **Architectural Solution:**
  1. **Per-Department SVG ClipPaths:** Every department receives a unique `<clipPath id="clip-{deptId}">` matching its inner boundary rectangle (`x + 1, y + 1, width - 2, height - 2`).
  2. **Screen-Space Label Classification:**
     - **Large ($W_{\text{px}} \ge 100, H_{\text{px}} \ge 48$):** Full name (smartly truncated if needed) + dimensions ($W \times H$) + area ($m^2$).
     - **Medium ($W_{\text{px}} \ge 55, H_{\text{px}} \ge 32$):** Short department name.
     - **Small ($W_{\text{px}} \ge 28, H_{\text{px}} \ge 20$):** 2–4 character industry code (`RAW`, `MACH`, `HEAT`, `QC`, `SUB`, `FINAL`, `PACK`, `FG`).
     - **Extremely Small:** Centroid dot crosshair with hover tooltip.

---

### Defect 4 (DEF-004): Distorted Aspect Ratio & Unresponsive Viewport Containers
- **Symptom:** Plant dimensions appeared stretched when resizing the browser window, or layout did not center properly in compact previews.
- **Root Cause:** Hardcoded aspect ratio assumptions without dynamic `ResizeObserver` container measurements.
- **Architectural Solution:**
  1. Implemented a native `ResizeObserver` observing the container element.
  2. Mathematical Fit to View calculates scale based on `Math.min(containerW / facW, containerH / facH)` preserving exact facility proportions (e.g. 120m $\times$ 80m = 1.5 aspect ratio).

---

### Defect 5 (DEF-005): Omission of Reserved Exclusion Zones
- **Symptom:** The $20 \times 20\,\text{m}$ transformer room (`RZ_TRANSFORMER_ROOM`) specified in `FLP_EXPANSION_8` was invisible on the canvas.
- **Root Cause:** Canvas rendering loop only mapped `layout.placements`, completely ignoring `problem.facility.reserved_zones`.
- **Architectural Solution:**
  Added dedicated reserved exclusion layer rendering all defined zones with:
  - SVG diagonal crosshatch pattern (`url(#reserved-zone-hatch)`).
  - High-visibility red stroke (`#ef4444`, 1.2px).
  - Centered warning badge and title: `🚫 TRANSFORMER ROOM`.

---

## 2. Iteration & Verification Summary

| Defect ID | Description | Before (Phase 14.6 / Baseline) | After (Phase 15.2 Fix) | Verification Screenshot |
| :---: | :--- | :--- | :--- | :--- |
| **DEF-001** | Text explosion at 220% zoom | Text grew to 140px+, unreadable | Locked to 11–13px screen space | `15_zoom_220_zoomed.png` |
| **DEF-002** | Flow overlay clutter | Huge opaque arrows hiding plant | Clean default; clamped 1.2–3.8px | `03_expansion8_clean.png`, `04_expansion8_top5_flows.png` |
| **DEF-003** | Label collision & overflow | Text overflowing block boundaries | ClipPath per dept; responsive codes | `06_industrial10_clean.png`, `14_mobile_view_390x844.png` |
| **DEF-004** | Aspect ratio distortion | Stretched canvas | Preserved 1:1 scale; Fit to View | `01_academic4_clean.png`, `15_zoom_220_and_fit.png` |
| **DEF-005** | Missing exclusion zone | Transformer room invisible | Hatched red zone with clear label | `03_expansion8_clean.png`, `05_expansion8_inspector.png` |

---

## 3. Conclusion

All 5 baseline defects have been permanently eradicated at the root cause level. The visual quality of FLODSS now satisfies high academic and professional design standards across mobile, tablet, desktop, and extreme zoom contexts.
