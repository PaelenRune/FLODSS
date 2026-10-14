# FLODSS Visual Design Guidelines & Engineering Standards

**Version:** 1.0.0-rc.1  
**Target:** Industrial Facility Layout Optimization & Decision Support System (FLODSS)  
**Audience:** Frontend Engineers, UX Designers, Optimization Scientists, Research Collaborators

---

## 1. Core Visual Principles

1. **Scientific Fidelity Above Aesthetics:** Every visual element must directly represent the underlying solver output. No geometry, coordinates, or flow metrics may be cosmetically fudged.
2. **Clean Blueprint by Default:** Default views present an uncluttered floor plan. Dense data layers (material flows, REL adjacency webs, pairwise contributor tables) must be opt-in toggles.
3. **Screen-Space Sizing Invariance:** Text and UI markers must remain readable regardless of zoom level. Never define text sizes purely in physical world meters without screen-space inversion.
4. **Guaranteed Bounded Containment:** No label or graphic element may spill outside its owner block. SVG `<clipPath>` containment is mandatory for all department entities.
5. **High-Contrast, Accessible Palette:** Palette choices must satisfy WCAG AA contrast (4.5:1) against dark backgrounds and remain distinguishable under common color-vision deficiencies.

---

## 2. Color System & Industrial Palette

FLODSS operates with a dark-mode industrial theme (`#0f172a` canvas background) that minimizes eye fatigue during extended research sessions and maximizes line contrast:

### 2.1. Department Color Palette
Departments are colored cyclically using distinct, high-contrast, saturated hues:
- `#2563eb` — Royal Blue
- `#059669` — Emerald Green
- `#d97706` — Warm Amber
- `#7c3aed` — Vivid Purple
- `#dc2626` — Crimson Red
- `#0891b2` — Deep Cyan
- `#4f46e5` — Indigo
- `#c026d3` — Fuchsia Magenta
- `#16a34a` — Forest Green
- `#ea580c` — Burnt Orange
- `#0284c7` — Sky Blue
- `#9333ea` — Violet

### 2.2. Semantic & Status Accents
- **Facility Envelope:** `#3b82f6` with `stroke-dasharray="6,3"`, `1.5px` stroke.
- **Facility Grid:** `#334155` fine dashed lines on $10\,\text{m}$ intervals.
- **Reserved Exclusion Zones:** `fill="url(#reserved-zone-hatch)"` (red diagonal stripes), stroke `#ef4444`, text `#fca5a5`.
- **Top 5 Flow Cost Drivers:** `#f59e0b` (amber) with `#d97706` arrowhead.
- **Selected Department Flows:** `#06b6d4` (cyan) with `#0891b2` arrowhead.
- **Normal Material Flows:** `#64748b` with `0.4` opacity.
- **Feasible Badge:** `#10b981` (emerald green text/bg).
- **Infeasible / Constraint Violation:** `#ef4444` (crimson red badge with `!`).

---

## 3. Viewport Scaling & SVG Canvas Architecture

### 3.1. Zero CSS Transform Scale Rule
Never apply CSS transforms (`transform: scale(zoom)`) to the outer canvas container. This creates compounding scale bugs where fonts, borders, and controls blow up.

### 3.2. Native SVG `viewBox` Pan/Zoom
Pan and zoom must be handled strictly inside the SVG's `viewBox` attribute:
```typescript
const viewBoxX = pan.x;
const viewBoxY = pan.y;
const viewBoxW = baseWorldW / zoom;
const viewBoxH = baseWorldH / zoom;
const viewBoxStr = `${viewBoxX} ${viewBoxY} ${viewBoxW} ${viewBoxH}`;
```
Set SVG element attributes to:
```xml
<svg width="100%" height="100%" viewBox={viewBoxStr} preserveAspectRatio="xMidYMid meet">
```

### 3.3. Dynamic Font Inversion
To keep text font sizes locked to ~11–13px on screen regardless of container size or zoom level:
```typescript
const effectivePixelsPerMeter = (containerWidth / (baseWorldW / zoom));
const targetScreenPx = isLarge ? 12.5 : isMedium ? 10.5 : 9.0;
const fontWorldUnits = targetScreenPx / Math.max(0.1, effectivePixelsPerMeter);
```

---

## 4. Label Hierarchy & Anti-Collision Classification

Every department block must dynamically classify its label based on its current screen-space pixel footprint ($W_{\text{px}} \times H_{\text{px}}$):

```
                        Screen-Space Footprint
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
Large (≥100×48px)        Medium (≥55×32px)        Small (≥28×20px)
         │                        │                        │
  Full Dept Name           Short Code/Name         2-4 Letter Abbrev
  + Dimensions (W×H)                               (RAW, MACH, HEAT)
  + Area (m²) if H≥95px
```

### SVG `<clipPath>` Containment
To guarantee that long department names never bleed into adjacent blocks:
```xml
<clipPath id={`clip-${p.department_id}`}>
  <rect x={rx + 1} y={ry + 1} width={Math.max(1, p.width - 2)} height={Math.max(1, p.height - 2)} rx="1" />
</clipPath>
```
All text nodes are enclosed within `<g clipPath={`url(#clip-${p.department_id})`}>`.

---

## 5. Material Flow Overlay Standards

1. **Clean Blueprint Default:** `showFlows` must default to `false`.
2. **Layer Order:** Flow paths must be rendered in `<g id="flow-overlay-layer">` situated *below* `<g id="departments-layer">`.
3. **Clamped Stroke Widths:** Stroke width in screen pixels must be clamped between $1.2\,\text{px}$ and $3.8\,\text{px}$:
   $$\text{strokeWidth}_{\text{px}} = 1.2 + \left(\frac{f_{ij}}{\max(f)}\right) \cdot 1.6$$
4. **Quadratic Offsets:** All directional arcs must implement quadratic Bezier curve curvature:
   $$\text{midX} = \frac{x_1 + x_2}{2} - dy \cdot 0.12, \quad \text{midY} = \frac{y_1 + y_2}{2} + dx \cdot 0.12$$
5. **Exact Reconciliation:** Any pairwise cost breakdown must reconcile exactly to the canonical Material Handling Cost:
   $$\sum_{k=1}^m \text{pair cost}_k \equiv \text{MHC}_{\text{canonical}}$$

---

## 6. Pareto Decision Support Standards

1. **Scientific Units:** All changes in Muther REL Satisfaction must be denoted in **percentage points (`%p`)**, never ambiguous relative percentages:
   $$\Delta\text{REL} = +1.09\,\%p$$
2. **Cryptographic Signatures:** Every layout candidate must display a compact SHA-256 Layout Signature.
3. **Composite Hash Validation:** Candidate comparisons must verify that both candidates originate from identical problem specifications. If hashes differ, a high-priority warning banner must be displayed.
4. **Dominance Explanations:** Non-dominated sorting layers must be accompanied by explicit natural language trade-off summaries explaining cost savings vs. relationship compromises.

---

## 7. Export Specifications

1. **Vector SVG:**
   - Must be self-contained with embedded `<defs>`, clip paths, grid patterns, and markers.
   - Scaled with explicit millimeter/meter coordinates suitable for CAD or publication import.
2. **High-DPI PNG:**
   - Rendered using HTML5 canvas at $3\times$ device pixel ratio ($300\,\text{DPI}$ equivalent).
   - High-contrast dark background (`#0f172a`), clean borders, and crisp typography suitable for IEEE/Springer journal figures.
