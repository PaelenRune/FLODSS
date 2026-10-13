import React, { useState, useRef, useMemo } from 'react';
import { ContinuousLayout, LayoutValidationResult, FacilityLayoutProblem } from '../types/api';
import { useLanguage } from '../context/LanguageContext';

interface LayoutCanvasProps {
  layout: ContinuousLayout | null;
  problem?: FacilityLayoutProblem | null;
  validation?: LayoutValidationResult | null;
  selectedDeptId?: string | null;
  onSelectDept?: (deptId: string | null) => void;
}

// Distinct, high-contrast industrial palette
const DEPARTMENT_COLORS: string[] = [
  '#3b82f6', // blue
  '#10b981', // emerald
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#14b8a6', // teal
  '#6366f1', // indigo
  '#84cc16', // lime
  '#e11d48', // rose
  '#0ea5e9', // sky
];

export const LayoutCanvas: React.FC<LayoutCanvasProps> = ({
  layout,
  problem,
  validation,
  selectedDeptId,
  onSelectDept,
}) => {
  const { t } = useLanguage();
  const [showCentroids, setShowCentroids] = useState(true);
  const [showGrid, setShowGrid] = useState(true);
  const [showDimensions, setShowDimensions] = useState(true);
  const [showLegend, setShowLegend] = useState(false);
  const [hoveredDeptId, setHoveredDeptId] = useState<string | null>(null);

  // Zoom and Pan state
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const svgRef = useRef<SVGSVGElement | null>(null);

  // Map of fixed departments from problem definition
  const fixedDeptIds = useMemo(() => {
    const fixed = new Set<string>();
    if (problem?.departments) {
      for (const d of problem.departments) {
        if (d.fixed_position) {
          fixed.add(d.id);
        }
      }
    }
    return fixed;
  }, [problem]);

  // Check for pairwise overlaps directly from continuous layout coordinates
  const overlappingDeptIds = useMemo(() => {
    const overlaps = new Set<string>();
    if (!layout?.placements) return overlaps;
    const items = Object.values(layout.placements);
    for (let i = 0; i < items.length; i++) {
      for (let j = i + 1; j < items.length; j++) {
        const a = items[i];
        const b = items[j];
        const xOverlap = Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x));
        const yOverlap = Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));
        if (xOverlap > 0.01 && yOverlap > 0.01) {
          overlaps.add(a.department_id);
          overlaps.add(b.department_id);
        }
      }
    }
    return overlaps;
  }, [layout]);

  if (!layout) {
    return (
      <div style={{
        padding: '3rem 2rem',
        textAlign: 'center',
        background: 'var(--bg-secondary)',
        borderRadius: '0.75rem',
        border: '1px dashed var(--border-color)',
        color: 'var(--text-muted)',
      }}>
        <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📐</div>
        <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '1.1rem' }}>
          {t('Seçili Yerleşim Çözümü Yok', 'No Layout Solution Selected')}
        </div>
        <div style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
          {t(
            '2D fabrika yerleşim planını (Continuous 2D Floor Plan) görüntülemek için bir optimizasyon algoritması çalıştırın veya Benchmark yükleyin.',
            'Execute an optimization algorithm or load a benchmark layout to view the 2D factory floor plan.'
          )}
        </div>
      </div>
    );
  }

  const facW = layout.facility_width || problem?.facility.width || 150.0;
  const facH = layout.facility_height || problem?.facility.height || 80.0;
  const placements = Object.values(layout.placements);

  // SVG base viewbox dimensions
  const svgPadding = 40; // margin for axes and labels
  const baseViewBoxW = facW + svgPadding * 2;
  const baseViewBoxH = facH + svgPadding * 2;

  // Coordinate mapping: Continuous bottom-left (x, y) to SVG (origin at top-left)
  const toSvgX = (x: number) => svgPadding + x;
  const toSvgY = (y: number, h: number = 0) => svgPadding + (facH - y - h);

  const activeDept = hoveredDeptId || selectedDeptId;
  const activePlacement = activeDept ? layout.placements[activeDept] : null;
  const activeProblemDept = activeDept && problem?.departments ? problem.departments.find(d => d.id === activeDept) : null;

  // Zoom controls
  const handleZoomIn = () => setZoom(prev => Math.min(prev * 1.25, 4.0));
  const handleZoomOut = () => setZoom(prev => Math.max(prev / 1.25, 0.4));
  const handleFitToScreen = () => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };

  // Pan mouse interactions
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 0) { // left mouse
      setIsPanning(true);
      panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPan({
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      });
    }
  };

  const handleMouseUp = () => setIsPanning(false);

  // Export 2D layout as SVG file
  const handleExportSvg = () => {
    if (!svgRef.current) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `layout_${layout.id || 'export'}_2d.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Export 2D layout as PNG image
  const handleExportPng = () => {
    if (!svgRef.current) return;
    const svgData = new XMLSerializer().serializeToString(svgRef.current);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    img.onload = () => {
      canvas.width = baseViewBoxW * 2;
      canvas.height = baseViewBoxH * 2;
      if (ctx) {
        ctx.fillStyle = '#0d1117';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        const pngUrl = canvas.toDataURL('image/png');
        const link = document.createElement('a');
        link.href = pngUrl;
        link.download = `layout_${layout.id || 'export'}_2d.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '0.75rem',
      overflow: 'hidden',
      marginBottom: '2rem',
      boxShadow: '0 4px 16px rgba(0,0,0,0.15)',
    }}>
      {/* Top toolbar */}
      <div style={{
        padding: '0.85rem 1.25rem',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        background: 'var(--bg-card)',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>🏭</span>
            <span style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--text-primary)' }}>
              {layout.name || layout.id || t('2D Fabrika Yerleşim Planı (Continuous Layout)', '2D Factory Layout Plan')}
            </span>
            <span style={{
              fontSize: '0.75rem',
              padding: '0.15rem 0.55rem',
              borderRadius: '9999px',
              fontWeight: 600,
              backgroundColor: validation?.is_valid ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              color: validation?.is_valid ? '#10b981' : '#ef4444',
              border: `1px solid ${validation?.is_valid ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            }}>
              {validation?.is_valid ? t('✓ Tam & Feasible', '✓ Complete & Feasible') : t('⚠ Feasibility Uyarısı', '⚠ Feasibility Notice')}
            </span>
            {overlappingDeptIds.size > 0 && (
              <span style={{
                fontSize: '0.7rem',
                padding: '0.15rem 0.45rem',
                borderRadius: '4px',
                backgroundColor: 'rgba(239, 68, 68, 0.2)',
                color: '#ef4444',
                fontWeight: 700,
              }}>
                Overlap Alert ({overlappingDeptIds.size} Depts)
              </span>
            )}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            {t('Tesis:', 'Facility:')} {facW}m × {facH}m ({(facW * facH).toLocaleString()} m²) &bull; {placements.length} {t('Yerleşen Departman', 'Placed Departments')} &bull; Zoom: {Math.round(zoom * 100)}%
          </div>
        </div>

        {/* View & Navigation Toggles */}
        <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Zoom controls */}
          <div style={{ display: 'flex', border: '1px solid var(--border-color)', borderRadius: '0.375rem', overflow: 'hidden' }}>
            <button
              onClick={handleZoomIn}
              title="Zoom In"
              style={{
                padding: '0.3rem 0.6rem',
                fontSize: '0.85rem',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              +
            </button>
            <button
              onClick={handleZoomOut}
              title="Zoom Out"
              style={{
                padding: '0.3rem 0.6rem',
                fontSize: '0.85rem',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                border: 'none',
                borderLeft: '1px solid var(--border-color)',
                cursor: 'pointer',
              }}
            >
              &minus;
            </button>
            <button
              onClick={handleFitToScreen}
              title="Reset Zoom & Pan"
              style={{
                padding: '0.3rem 0.65rem',
                fontSize: '0.75rem',
                background: 'var(--bg-secondary)',
                color: 'var(--text-secondary)',
                border: 'none',
                borderLeft: '1px solid var(--border-color)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              {t('Sığdır', 'Fit')}
            </button>
          </div>

          <button
            onClick={() => setShowGrid(!showGrid)}
            style={{
              padding: '0.3rem 0.65rem',
              fontSize: '0.75rem',
              borderRadius: '0.375rem',
              border: '1px solid var(--border-color)',
              background: showGrid ? 'var(--accent-blue)' : 'var(--bg-secondary)',
              color: showGrid ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            {t('Izgara (Grid)', 'Grid')}
          </button>
          <button
            onClick={() => setShowCentroids(!showCentroids)}
            style={{
              padding: '0.3rem 0.65rem',
              fontSize: '0.75rem',
              borderRadius: '0.375rem',
              border: '1px solid var(--border-color)',
              background: showCentroids ? 'var(--accent-blue)' : 'var(--bg-secondary)',
              color: showCentroids ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            Centroids
          </button>
          <button
            onClick={() => setShowDimensions(!showDimensions)}
            style={{
              padding: '0.3rem 0.65rem',
              fontSize: '0.75rem',
              borderRadius: '0.375rem',
              border: '1px solid var(--border-color)',
              background: showDimensions ? 'var(--accent-blue)' : 'var(--bg-secondary)',
              color: showDimensions ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            {t('Boyutlar', 'Dimensions')}
          </button>
          <button
            onClick={() => setShowLegend(!showLegend)}
            style={{
              padding: '0.3rem 0.65rem',
              fontSize: '0.75rem',
              borderRadius: '0.375rem',
              border: '1px solid var(--border-color)',
              background: showLegend ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
              color: showLegend ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            {t('Lejant', 'Legend')}
          </button>

          {/* Export buttons */}
          <div style={{ display: 'flex', gap: '0.25rem', marginLeft: '0.25rem' }}>
            <button
              onClick={handleExportSvg}
              title="Download Layout SVG"
              style={{
                padding: '0.3rem 0.55rem',
                fontSize: '0.72rem',
                borderRadius: '0.375rem',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              SVG
            </button>
            <button
              onClick={handleExportPng}
              title="Download Layout PNG"
              style={{
                padding: '0.3rem 0.55rem',
                fontSize: '0.72rem',
                borderRadius: '0.375rem',
                border: '1px solid var(--border-color)',
                background: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              PNG
            </button>
          </div>
        </div>
      </div>

      {/* Main Interactive Canvas Area */}
      <div
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          padding: '1rem',
          background: '#090d16',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          overflow: 'hidden',
          cursor: isPanning ? 'grabbing' : 'grab',
          position: 'relative',
          minHeight: '440px',
        }}
      >
        <div style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          transformOrigin: 'center center',
          transition: isPanning ? 'none' : 'transform 0.15s ease-out',
        }}>
          <svg
            ref={svgRef}
            viewBox={`0 0 ${baseViewBoxW} ${baseViewBoxH}`}
            width={baseViewBoxW * 4.5}
            height={baseViewBoxH * 4.5}
            style={{
              maxWidth: '1000px',
              height: 'auto',
              backgroundColor: '#111827',
              borderRadius: '0.5rem',
              boxShadow: '0 8px 30px rgba(0, 0, 0, 0.5)',
              border: '1px solid #1f2937',
            }}
          >
            <defs>
              <pattern id="grid-pattern" width="10" height="10" patternUnits="userSpaceOnUse">
                <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#ffffff0d" strokeWidth="0.5" />
              </pattern>
              <pattern id="reserved-zone-stripes" width="6" height="6" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
                <line x1="0" y1="0" x2="0" y2="6" stroke="#f59e0b" strokeWidth="1.5" strokeOpacity="0.4" />
              </pattern>
              <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#6e7681" />
              </marker>
            </defs>

            {/* Plant Outer Boundary */}
            <rect
              x={svgPadding}
              y={svgPadding}
              width={facW}
              height={facH}
              fill="#0b0f19"
              stroke="#374151"
              strokeWidth="1.5"
            />

            {/* Optional Grid Overlay */}
            {showGrid && (
              <rect
                x={svgPadding}
                y={svgPadding}
                width={facW}
                height={facH}
                fill="url(#grid-pattern)"
              />
            )}

            {/* Reserved Exclusion Zones */}
            {problem?.facility?.reserved_zones?.map((rz) => {
              const rx = toSvgX(rz.bounding_box.x_min);
              const rw = rz.bounding_box.x_max - rz.bounding_box.x_min;
              const rh = rz.bounding_box.y_max - rz.bounding_box.y_min;
              const ry = toSvgY(rz.bounding_box.y_min, rh);
              return (
                <g key={rz.id}>
                  <rect
                    x={rx}
                    y={ry}
                    width={rw}
                    height={rh}
                    fill="url(#reserved-zone-stripes)"
                    stroke="#f59e0b"
                    strokeWidth="1"
                    strokeDasharray="2,2"
                  />
                  <text
                    x={rx + rw / 2}
                    y={ry + rh / 2 + 1.5}
                    fill="#f59e0b"
                    fontSize="4"
                    fontWeight="700"
                    textAnchor="middle"
                    style={{ pointerEvents: 'none', userSelect: 'none' }}
                  >
                    🚧 {rz.id}
                  </text>
                </g>
              );
            })}

            {/* Coordinate Axes */}
            {/* X-axis along bottom */}
            <line
              x1={svgPadding}
              y1={svgPadding + facH}
              x2={svgPadding + facW + 15}
              y2={svgPadding + facH}
              stroke="#6b7280"
              strokeWidth="1"
              markerEnd="url(#arrow)"
            />
            <text
              x={svgPadding + facW + 18}
              y={svgPadding + facH + 4}
              fill="#9ca3af"
              fontSize="7"
              fontWeight="600"
            >
              +X ({facW}m)
            </text>

            {/* Y-axis along left */}
            <line
              x1={svgPadding}
              y1={svgPadding + facH}
              x2={svgPadding}
              y2={svgPadding - 15}
              stroke="#6b7280"
              strokeWidth="1"
              markerEnd="url(#arrow)"
            />
            <text
              x={svgPadding - 4}
              y={svgPadding - 18}
              fill="#9ca3af"
              fontSize="7"
              fontWeight="600"
              textAnchor="middle"
            >
              +Y ({facH}m)
            </text>

            {/* Origin Label (0,0) */}
            <text
              x={svgPadding - 6}
              y={svgPadding + facH + 12}
              fill="#6b7280"
              fontSize="6"
              textAnchor="end"
            >
              (0,0)
            </text>

            {/* Department Placements */}
            {placements.map((p, idx) => {
              const color = DEPARTMENT_COLORS[idx % DEPARTMENT_COLORS.length];
              const isHovered = hoveredDeptId === p.department_id;
              const isSelected = selectedDeptId === p.department_id;
              const isFixed = fixedDeptIds.has(p.department_id);
              const isOverlapping = overlappingDeptIds.has(p.department_id);

              const rx = toSvgX(p.x);
              const ry = toSvgY(p.y, p.height);
              const cx = rx + p.width / 2;
              const cy = ry + p.height / 2;
              const area = p.width * p.height;

              return (
                <g
                  key={p.department_id}
                  onMouseEnter={() => setHoveredDeptId(p.department_id)}
                  onMouseLeave={() => setHoveredDeptId(null)}
                  onClick={() => onSelectDept?.(p.department_id === selectedDeptId ? null : p.department_id)}
                  style={{ cursor: 'pointer' }}
                >
                  {/* Department Rectangle */}
                  <rect
                    x={rx}
                    y={ry}
                    width={p.width}
                    height={p.height}
                    fill={color}
                    fillOpacity={isSelected ? 0.90 : isHovered ? 0.80 : 0.50}
                    stroke={isSelected ? '#ffffff' : isOverlapping ? '#ef4444' : isFixed ? '#fbbf24' : color}
                    strokeWidth={isSelected ? 2.5 : isOverlapping ? 2.0 : isFixed ? 1.8 : 1.0}
                    strokeDasharray={isFixed ? '3,1' : undefined}
                    rx="1.5"
                    style={{ transition: 'all 0.15s ease' }}
                  />

                  {/* Fixed Department Pin Marker */}
                  {isFixed && (
                    <text
                      x={rx + 3}
                      y={ry + 5}
                      fontSize="4"
                      fill="#fbbf24"
                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                    >
                      📌
                    </text>
                  )}

                  {/* Centroid Crosshair */}
                  {showCentroids && (
                    <g opacity={isHovered || isSelected ? 1 : 0.6}>
                      <line x1={cx - 3} y1={cy} x2={cx + 3} y2={cy} stroke="#ffffff" strokeWidth="0.75" />
                      <line x1={cx} y1={cy - 3} x2={cx} y2={cy + 3} stroke="#ffffff" strokeWidth="0.75" />
                      <circle cx={cx} cy={cy} r="0.9" fill="#ffffff" />
                    </g>
                  )}

                  {/* Department Label */}
                  <text
                    x={cx}
                    y={cy - (showDimensions ? 3 : 0)}
                    fill="#ffffff"
                    fontSize={Math.max(3.5, Math.min(6.5, p.width / 3))}
                    fontWeight="700"
                    textAnchor="middle"
                    style={{ pointerEvents: 'none', userSelect: 'none' }}
                  >
                    {p.department_id.replace(/^DEP_/, '')}
                  </text>

                  {/* Dimension Annotations */}
                  {showDimensions && (
                    <>
                      <text
                        x={cx}
                        y={cy + 4}
                        fill="#e5e7eb"
                        fontSize="3.6"
                        textAnchor="middle"
                        style={{ pointerEvents: 'none', userSelect: 'none' }}
                      >
                        {p.width.toFixed(1)}m × {p.height.toFixed(1)}m
                      </text>
                      <text
                        x={cx}
                        y={cy + 9}
                        fill="#9ca3af"
                        fontSize="3.2"
                        textAnchor="middle"
                        style={{ pointerEvents: 'none', userSelect: 'none' }}
                      >
                        ({Math.round(area)} m²)
                      </text>
                    </>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* Legend Overlay */}
        {showLegend && (
          <div style={{
            position: 'absolute',
            top: '1rem',
            right: '1rem',
            backgroundColor: 'rgba(17, 24, 39, 0.95)',
            border: '1px solid var(--border-color)',
            borderRadius: '0.5rem',
            padding: '0.75rem',
            maxHeight: '260px',
            overflowY: 'auto',
            width: '200px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            zIndex: 10,
          }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#f3f4f6', marginBottom: '0.5rem' }}>
              {t('Departman Lejantı', 'Department Legend')}
            </div>
            {placements.map((p, idx) => {
              const color = DEPARTMENT_COLORS[idx % DEPARTMENT_COLORS.length];
              const probDept = problem?.departments?.find(d => d.id === p.department_id);
              return (
                <div
                  key={p.department_id}
                  onClick={() => onSelectDept?.(p.department_id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    fontSize: '0.7rem',
                    padding: '0.2rem 0',
                    cursor: 'pointer',
                    color: selectedDeptId === p.department_id ? '#60a5fa' : '#d1d5db',
                  }}
                >
                  <span style={{ width: '10px', height: '10px', backgroundColor: color, borderRadius: '2px', flexShrink: 0 }} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {probDept?.name || p.department_id}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Selected Department Detailed Property Inspector Drawer */}
      {activePlacement && (
        <div style={{
          padding: '0.85rem 1.25rem',
          background: 'var(--bg-card)',
          borderTop: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          fontSize: '0.825rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 700, color: 'var(--accent-blue)', fontSize: '0.9rem' }}>
              {activeProblemDept?.name || activePlacement.department_id} ({activePlacement.department_id})
            </span>
            {fixedDeptIds.has(activePlacement.department_id) && (
              <span style={{ backgroundColor: '#fbbf2420', color: '#fbbf24', padding: '0.1rem 0.4rem', borderRadius: '4px', fontSize: '0.7rem', fontWeight: 600 }}>
                📌 Fixed Position
              </span>
            )}
            <span style={{ color: 'var(--text-secondary)' }}>
              Origin: (x={activePlacement.x.toFixed(1)}m, y={activePlacement.y.toFixed(1)}m)
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              {t('Boyut:', 'Size:')} {activePlacement.width.toFixed(1)}m × {activePlacement.height.toFixed(1)}m
            </span>
            <span style={{ color: 'var(--text-secondary)' }}>
              {t('Alan:', 'Area:')} {(activePlacement.width * activePlacement.height).toLocaleString()} m²
              {activeProblemDept ? ` (Req: ${activeProblemDept.required_area} m²)` : ''}
            </span>
          </div>

          <div style={{ display: 'flex', gap: '1rem', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
            <span>
              Centroid: ({(activePlacement.x + activePlacement.width / 2).toFixed(1)}, {(activePlacement.y + activePlacement.height / 2).toFixed(1)})
            </span>
            <span>
              Aspect Ratio: {(Math.max(activePlacement.width, activePlacement.height) / Math.min(activePlacement.width, activePlacement.height)).toFixed(2)}
            </span>
          </div>
        </div>
      )}

      {/* Bottom Metrics Bar */}
      <div style={{
        padding: '0.75rem 1.25rem',
        background: 'var(--bg-primary)',
        borderTop: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '0.75rem',
        fontSize: '0.8rem',
      }}>
        <div style={{ display: 'flex', gap: '1.25rem', flexWrap: 'wrap' }}>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>{t('Kullanılan Alan (Occupied): ', 'Occupied: ')}</span>
            <span style={{ fontWeight: 600 }}>
              {validation?.metrics.occupied_area ? `${validation.metrics.occupied_area.toLocaleString()} m²` : `${placements.reduce((acc, p) => acc + p.width * p.height, 0).toLocaleString()} m²`}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Floor Utilization: </span>
            <span style={{ fontWeight: 600, color: '#10b981' }}>
              {validation?.metrics.utilization_ratio ? `${(validation.metrics.utilization_ratio * 100).toFixed(1)}%` : `${((placements.reduce((acc, p) => acc + p.width * p.height, 0) / (facW * facH)) * 100).toFixed(1)}%`}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text-muted)' }}>Pairwise Overlap: </span>
            <span style={{ fontWeight: 600, color: (validation?.total_overlap_area || 0) > 0 ? '#ef4444' : '#10b981' }}>
              {validation?.total_overlap_area ? `${validation.total_overlap_area} m²` : '0.00 m²'}
            </span>
          </div>
        </div>

        {validation?.signature && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontFamily: 'monospace', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>Signature:</span>
            <span style={{ color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '0.1rem 0.4rem', borderRadius: '4px', border: '1px solid var(--border-color)' }}>
              {validation.signature.substring(0, 16)}...
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
