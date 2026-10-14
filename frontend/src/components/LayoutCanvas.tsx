import React, { useState, useRef, useMemo, useEffect, useCallback } from 'react';
import {
  ContinuousLayout,
  LayoutValidationResult,
  FacilityLayoutProblem,
  Flow,
} from '../types/api';
import { useLanguage } from '../context/LanguageContext';
import { formatCost } from '../utils/formatters';
import {
  Maximize2,
  ZoomIn,
  ZoomOut,
  X,
  Compass,
} from 'lucide-react';

export interface LayoutCanvasProps {
  layout: ContinuousLayout | null;
  problem?: FacilityLayoutProblem | null;
  validation?: LayoutValidationResult | null;
  selectedDeptId?: string | null;
  onSelectDept?: (deptId: string | null) => void;
  compact?: boolean;
}

// Distinct, high-contrast industrial palette (optimized for contrast and color-blind readability)
const DEPARTMENT_COLORS: string[] = [
  '#2563eb', // royal blue
  '#059669', // emerald green
  '#d97706', // amber
  '#7c3aed', // violet
  '#db2777', // deep pink
  '#0891b2', // cyan
  '#ea580c', // vivid orange
  '#0d9488', // teal
  '#4f46e5', // indigo
  '#65a30d', // lime green
  '#e11d48', // rose
  '#0284c7', // light blue
];

export interface FlowWithMetrics extends Flow {
  srcCx: number;
  srcCy: number;
  tgtCx: number;
  tgtCy: number;
  distance: number;
  unitCost: number;
  cost: number;
  isTop5: boolean;
  isTop10: boolean;
}

export const LayoutCanvas: React.FC<LayoutCanvasProps> = ({
  layout,
  problem,
  validation,
  selectedDeptId,
  onSelectDept,
  compact = false,
}) => {
  const { t } = useLanguage();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);

  // Viewport Container Dimensions (tracked via ResizeObserver)
  const [containerSize, setContainerSize] = useState<{ width: number; height: number }>({
    width: compact ? 360 : 800,
    height: compact ? 260 : 500,
  });

  // Display toggles — Clean Layout by default (DEF-002 fix)
  const [showFlows, setShowFlows] = useState<boolean>(false);
  const [showDimensions, setShowDimensions] = useState<boolean>(!compact);
  const [showCentroids] = useState<boolean>(false);
  const [showGrid] = useState<boolean>(true);
  const [showCostPanel, setShowCostPanel] = useState<boolean>(false);
  const [flowFilter, setFlowFilter] = useState<'none' | 'top5' | 'top10' | 'all' | 'selected'>('top5');
  const [focusedFlowPair, setFocusedFlowPair] = useState<string | null>(null);

  // Hover states
  const [hoveredDeptId, setHoveredDeptId] = useState<string | null>(null);
  const [hoveredFlow, setHoveredFlow] = useState<FlowWithMetrics | null>(null);

  // Pan and Zoom states
  const [zoom, setZoom] = useState<number>(1.0);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState<boolean>(false);
  const panStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const didPanRef = useRef<boolean>(false);

  // ResizeObserver for Container
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
          setContainerSize({
            width: entry.contentRect.width,
            height: entry.contentRect.height,
          });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Geometry: Facility Dimensions
  const facW = layout?.facility_width || problem?.facility.width || 120.0;
  const facH = layout?.facility_height || problem?.facility.height || 80.0;
  const placements = useMemo(() => (layout?.placements ? Object.values(layout.placements) : []), [layout]);

  // World Bounding Box & Padding (6% padding around facility)
  const svgPadding = Math.max(8.0, Math.min(facW, facH) * 0.08);
  const baseWorldW = facW + svgPadding * 2;
  const baseWorldH = facH + svgPadding * 2;

  // Dynamic responsive container height: on small screens (<640px), scale container height to match facility aspect ratio snugly
  const isSmallViewport = containerSize.width < 640;
  const calculatedMobileHeight = Math.max(200, Math.min(360, Math.round((containerSize.width * baseWorldH) / baseWorldW) + 20));
  const dynamicContainerHeight = compact ? 260 : isSmallViewport ? calculatedMobileHeight : 480;

  // Pixels per meter at 100% zoom
  const baseScale = useMemo(() => {
    const activeH = compact ? 260 : containerSize.width < 640 ? calculatedMobileHeight : containerSize.height;
    const scaleX = containerSize.width / baseWorldW;
    const scaleY = activeH / baseWorldH;
    return Math.min(scaleX, scaleY);
  }, [containerSize, baseWorldW, baseWorldH, compact, calculatedMobileHeight]);

  const effectivePixelsPerMeter = baseScale * zoom;

  // ViewBox Calculations (SVG Hardware-Accelerated Pan and Zoom)
  const viewBoxW = baseWorldW / zoom;
  const viewBoxH = baseWorldH / zoom;
  const viewBoxX = -svgPadding + (baseWorldW - viewBoxW) / 2 - pan.x / Math.max(0.1, effectivePixelsPerMeter);
  const viewBoxY = -svgPadding + (baseWorldH - viewBoxH) / 2 + pan.y / Math.max(0.1, effectivePixelsPerMeter);

  // Coordinate Mapping: Continuous Cartesian (bottom-left) to SVG (top-left)
  const toSvgX = useCallback((x: number) => x, []);
  const toSvgY = useCallback((y: number, h: number = 0) => facH - y - h, [facH]);

  // Fit to View Callback
  const fitToView = useCallback(() => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  }, []);

  // Auto-fit on initial mount or when layout/problem dimensions change
  useEffect(() => {
    fitToView();
  }, [layout?.id, layout?.layout_signature, facW, facH, fitToView]);

  // Pan interaction handlers (drag-to-pan & touch-to-pan)
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Left click only
    setIsPanning(true);
    didPanRef.current = false;
    panStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isPanning) return;
    const dx = e.clientX - panStartRef.current.x - pan.x;
    const dy = e.clientY - panStartRef.current.y - pan.y;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      didPanRef.current = true;
    }
    setPan({
      x: e.clientX - panStartRef.current.x,
      y: e.clientY - panStartRef.current.y,
    });
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      const touch = e.touches[0];
      setIsPanning(true);
      didPanRef.current = false;
      panStartRef.current = { x: touch.clientX - pan.x, y: touch.clientY - pan.y };
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (!isPanning || e.touches.length !== 1) return;
    const touch = e.touches[0];
    const dx = touch.clientX - panStartRef.current.x - pan.x;
    const dy = touch.clientY - panStartRef.current.y - pan.y;
    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      didPanRef.current = true;
    }
    setPan({
      x: touch.clientX - panStartRef.current.x,
      y: touch.clientY - panStartRef.current.y,
    });
  };

  const handleTouchEnd = () => {
    setIsPanning(false);
  };

  // Mouse Wheel Zoom centered on pointer
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
    setZoom((prevZoom) => {
      const nextZoom = Math.min(4.0, Math.max(0.5, prevZoom * zoomFactor));
      return Number(nextZoom.toFixed(2));
    });
  };

  // Fixed Departments
  const fixedDeptIds = useMemo(() => {
    const fixed = new Set<string>();
    if (problem?.departments) {
      for (const d of problem.departments) {
        if (d.fixed_position) fixed.add(d.id);
      }
    }
    return fixed;
  }, [problem]);

  // Overlap Detection
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

  // Aspect Ratio Violations (checked against max allowed)
  const arViolations = useMemo(() => {
    const map = new Map<string, { current: number; max: number }>();
    if (!layout?.placements || !problem?.departments) return map;
    for (const d of problem.departments) {
      const p = layout.placements[d.id];
      if (!p) continue;
      const w = p.width;
      const h = p.height;
      const currentAR = Math.max(w, h) / Math.max(0.001, Math.min(w, h));
      const maxAR = d.max_aspect_ratio || 3.0;
      if (currentAR > maxAR + 1e-4) {
        map.set(d.id, { current: currentAR, max: maxAR });
      }
    }
    return map;
  }, [layout, problem]);

  // Material Flow Calculations with Centroid Rectilinear Distance
  const { allFlowsWithMetrics, visibleFlows, topCostFlows, totalComputedMHC } = useMemo(() => {
    if (!problem?.flows || !layout?.placements) {
      return { allFlowsWithMetrics: [], visibleFlows: [], topCostFlows: [], totalComputedMHC: 0 };
    }

    const calculated: FlowWithMetrics[] = [];
    let sumMHC = 0;

    for (const flow of problem.flows) {
      const src = layout.placements[flow.source_department];
      const tgt = layout.placements[flow.target_department];
      if (!src || !tgt || flow.quantity <= 0) continue;

      const srcCx = src.x + src.width / 2;
      const srcCy = src.y + src.height / 2;
      const tgtCx = tgt.x + tgt.width / 2;
      const tgtCy = tgt.y + tgt.height / 2;

      // Centroid Rectilinear (Manhattan) distance
      const distance = Math.abs(srcCx - tgtCx) + Math.abs(srcCy - tgtCy);
      const unitCost = flow.cost_per_unit_distance ?? 1.0;
      const cost = flow.quantity * distance * unitCost;
      sumMHC += cost;

      calculated.push({
        ...flow,
        srcCx,
        srcCy,
        tgtCx,
        tgtCy,
        distance,
        unitCost,
        cost,
        isTop5: false,
        isTop10: false,
      });
    }

    // Sort by transport cost contribution descending
    calculated.sort((a, b) => b.cost - a.cost);
    calculated.forEach((f, idx) => {
      f.isTop5 = idx < 5;
      f.isTop10 = idx < 10;
    });

    const top5 = calculated.slice(0, 5);

    // Filter flows based on active mode
    let filtered: FlowWithMetrics[] = [];
    if (!showFlows || flowFilter === 'none') {
      filtered = [];
    } else if (flowFilter === 'top5') {
      filtered = calculated.filter((f) => f.isTop5);
    } else if (flowFilter === 'top10') {
      filtered = calculated.filter((f) => f.isTop10);
    } else if (flowFilter === 'selected' && selectedDeptId) {
      filtered = calculated.filter(
        (f) => f.source_department === selectedDeptId || f.target_department === selectedDeptId
      );
    } else {
      filtered = calculated;
    }

    return {
      allFlowsWithMetrics: calculated,
      visibleFlows: filtered,
      topCostFlows: top5,
      totalComputedMHC: sumMHC,
    };
  }, [problem?.flows, layout?.placements, showFlows, flowFilter, selectedDeptId]);

  // Max flow quantity for stroke width normalization
  const maxFlowQuantity = useMemo(() => {
    if (allFlowsWithMetrics.length === 0) return 1;
    return Math.max(...allFlowsWithMetrics.map((f) => f.quantity), 1);
  }, [allFlowsWithMetrics]);

  // Selected Department Details for Inspector Drawer
  const selectedDeptDetails = useMemo(() => {
    if (!selectedDeptId || !layout?.placements) return null;
    const placement = layout.placements[selectedDeptId];
    if (!placement) return null;

    const probDept = problem?.departments?.find((d) => d.id === selectedDeptId);
    const aspect = Math.max(placement.width, placement.height) / Math.max(0.001, Math.min(placement.width, placement.height));
    const reqArea = probDept?.required_area ?? (placement.width * placement.height);
    const actArea = placement.width * placement.height;
    const areaDiffPct = reqArea > 0 ? ((actArea - reqArea) / reqArea) * 100 : 0;

    // Traffic summary
    let inflow = 0;
    let outflow = 0;
    allFlowsWithMetrics.forEach((f) => {
      if (f.target_department === selectedDeptId) inflow += f.quantity;
      if (f.source_department === selectedDeptId) outflow += f.quantity;
    });

    // Related Muther REL relationships
    const rels = (problem?.relationships || []).filter(
      (r) => r.department_a === selectedDeptId || r.department_b === selectedDeptId
    );

    return {
      id: selectedDeptId,
      name: probDept?.name || selectedDeptId,
      placement,
      probDept,
      aspect,
      maxAspect: probDept?.max_aspect_ratio || 3.0,
      reqArea,
      actArea,
      areaDiffPct,
      inflow,
      outflow,
      rels,
    };
  }, [selectedDeptId, layout, problem, allFlowsWithMetrics]);

  // High-Resolution SVG Export
  const handleExportSvg = () => {
    if (!svgRef.current) return;
    const svgClone = svgRef.current.cloneNode(true) as SVGSVGElement;
    svgClone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svgClone.setAttribute('viewBox', `0 0 ${baseWorldW} ${baseWorldH}`);
    svgClone.setAttribute('width', `${baseWorldW * 10}`);
    svgClone.setAttribute('height', `${baseWorldH * 10}`);

    const serializer = new XMLSerializer();
    const svgStr = serializer.serializeToString(svgClone);
    const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `flodss_layout_${layout?.problem_id || 'export'}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // High-DPI PNG Export (3x canvas scale with authentic 300 DPI pHYs metadata chunk)
  const handleExportPng = () => {
    if (!svgRef.current) return;
    const svgClone = svgRef.current.cloneNode(true) as SVGSVGElement;
    svgClone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    svgClone.setAttribute('viewBox', `0 0 ${baseWorldW} ${baseWorldH}`);
    svgClone.setAttribute('width', `${baseWorldW * 10}`);
    svgClone.setAttribute('height', `${baseWorldH * 10}`);

    const serializer = new XMLSerializer();
    const svgStr = serializer.serializeToString(svgClone);
    const img = new Image();
    const svgBlob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(svgBlob);

    img.onload = () => {
      const scaleFactor = 3;
      const canvas = document.createElement('canvas');
      canvas.width = baseWorldW * 10 * scaleFactor;
      canvas.height = baseWorldH * 10 * scaleFactor;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.scale(scaleFactor, scaleFactor);
        ctx.fillStyle = '#0f172a';
        ctx.fillRect(0, 0, baseWorldW * 10, baseWorldH * 10);
        ctx.drawImage(img, 0, 0, baseWorldW * 10, baseWorldH * 10);

        canvas.toBlob((blob) => {
          if (!blob) return;
          blob.arrayBuffer().then((buffer) => {
            // PNG signature (8 bytes) + IHDR chunk (25 bytes) = 33 bytes
            const u8 = new Uint8Array(buffer);
            // 300 DPI = 11,811 pixels per meter (0x00002E23)
            // pHYs chunk: length (4) + 'pHYs' (4) + x_ppm (4) + y_ppm (4) + unit (1) + crc (4) = 21 bytes
            const physChunk = new Uint8Array([
              0x00, 0x00, 0x00, 0x09, // Length: 9 bytes
              0x70, 0x48, 0x59, 0x73, // 'pHYs'
              0x00, 0x00, 0x2e, 0x23, // X pixels per meter (11811)
              0x00, 0x00, 0x2e, 0x23, // Y pixels per meter (11811)
              0x01,                   // Unit: meter
              0x78, 0xa5, 0x3f, 0x76, // CRC-32
            ]);
            // Insert physChunk right after IHDR at offset 33
            const withDpi = new Uint8Array(u8.length + physChunk.length);
            withDpi.set(u8.subarray(0, 33), 0);
            withDpi.set(physChunk, 33);
            withDpi.set(u8.subarray(33), 33 + physChunk.length);

            const finalBlob = new Blob([withDpi], { type: 'image/png' });
            const pngUrl = URL.createObjectURL(finalBlob);
            const link = document.createElement('a');
            link.href = pngUrl;
            link.download = `flodss_layout_${layout?.problem_id || 'export'}_300dpi.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(pngUrl);
          });
        }, 'image/png');
      }
      URL.revokeObjectURL(url);
    };
    img.onerror = (e) => {
      console.error('PNG export image loading failed:', e);
      URL.revokeObjectURL(url);
    };
    img.src = url;
  };

  // If no layout is selected, render clean placeholder
  if (!layout || placements.length === 0) {
    return (
      <div
        data-testid="no-layout-placeholder"
        style={{
          border: '2px dashed var(--border-color, #cbd5e1)',
          borderRadius: '8px',
          padding: '3rem 1.5rem',
          textAlign: 'center',
          backgroundColor: 'var(--bg-card, #ffffff)',
          color: 'var(--text-muted, #64748b)',
        }}
      >
        <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📐</div>
        <div style={{ fontWeight: 600, color: 'var(--text-primary, #0f172a)', fontSize: '1.1rem' }}>
          {t('Seçili Yerleşim Çözümü Yok', 'No Layout Solution Selected')}
        </div>
        <div style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
          {t(
            '2D fabrika yerleşim planını görüntülemek için bir optimizasyon algoritması çalıştırın veya Pareto sekmesinden bir adayı aktif yapın.',
            'Execute an optimization algorithm or set an active candidate from the Pareto tab to inspect the 2D layout.'
          )}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: '#0f172a',
        borderRadius: '8px',
        border: '1px solid #1e293b',
        overflow: 'hidden',
        boxShadow: '0 4px 20px rgba(0,0,0,0.25)',
      }}
    >
      {/* TOOLBAR */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '0.5rem',
          padding: compact ? '0.4rem 0.6rem' : '0.6rem 1rem',
          backgroundColor: '#1e293b',
          borderBottom: '1px solid #334155',
          color: '#f8fafc',
          fontSize: '0.8rem',
        }}
      >
        {/* Left: Info & Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 700, fontSize: compact ? '0.8rem' : '0.9rem', color: '#f1f5f9' }}>
            {layout.problem_id || problem?.name || t('2D Tesis Planı', '2D Layout')}
          </span>
          <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>
            {facW}m × {facH}m ({(facW * facH).toLocaleString()} m²)
          </span>

          {validation && (
            <span
              style={{
                padding: '2px 8px',
                borderRadius: '9999px',
                fontSize: '0.7rem',
                fontWeight: 700,
                backgroundColor: validation.is_valid ? '#064e3b' : '#7f1d1d',
                color: validation.is_valid ? '#6ee7b7' : '#fca5a5',
                border: `1px solid ${validation.is_valid ? '#059669' : '#dc2626'}`,
              }}
            >
              {validation.is_valid ? '✓ Feasible' : '⚠ Infeasible'}
            </span>
          )}

          {arViolations.size > 0 && (
            <span
              style={{
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '0.68rem',
                fontWeight: 600,
                backgroundColor: '#78350f',
                color: '#fcd34d',
                border: '1px solid #d97706',
              }}
              title={t('Aspect ratio sınırını aşan departmanlar var', 'Aspect ratio violations exist')}
            >
              ⚠ AR Sınırı ({arViolations.size})
            </span>
          )}

          {overlappingDeptIds.size > 0 && (
            <span
              style={{
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '0.68rem',
                fontWeight: 700,
                backgroundColor: '#7f1d1d',
                color: '#fca5a5',
                border: '1px solid #dc2626',
              }}
            >
              🚫 Çakışma ({overlappingDeptIds.size})
            </span>
          )}
        </div>

        {/* Right: Controls & Toggles */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          {/* Zoom Percentage */}
          <span
            style={{
              padding: '2px 6px',
              backgroundColor: '#0f172a',
              borderRadius: '4px',
              fontSize: '0.72rem',
              color: '#94a3b8',
              fontFamily: 'monospace',
            }}
          >
            {Math.round(zoom * 100)}%
          </span>

          {/* Zoom Buttons */}
          <button
            onClick={() => setZoom((z) => Math.min(4.0, Number((z * 1.2).toFixed(2))))}
            style={{ padding: '3px 6px', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            title={t('Yakınlaştır (+)', 'Zoom In (+)')}
          >
            <ZoomIn size={14} />
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(0.5, Number((z * 0.8).toFixed(2))))}
            style={{ padding: '3px 6px', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            title={t('Uzaklaştır (-)', 'Zoom Out (-)')}
          >
            <ZoomOut size={14} />
          </button>
          <button
            onClick={fitToView}
            style={{
              padding: '3px 8px',
              background: '#2563eb',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.72rem',
              display: 'flex',
              alignItems: 'center',
              gap: '3px',
            }}
            title={t('Tüm tesisi ekrana sığdır ve ortala', 'Fit entire facility to view')}
          >
            <Maximize2 size={13} />
            {t('Sığdır', 'Fit')}
          </button>

          <div style={{ width: 1, height: 16, backgroundColor: '#475569', margin: '0 2px' }} />

          {/* Flow Toggle (Clean Layout default) */}
          <button
            data-testid="toggle-flow-overlay-btn"
            onClick={() => setShowFlows(!showFlows)}
            style={{
              padding: '3px 8px',
              background: showFlows ? '#d97706' : '#334155',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.72rem',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title={t('Malzeme akış çizgilerini göster/gizle', 'Toggle material flow overlay')}
          >
            <Compass size={13} />
            {showFlows ? t('Akış Açık', 'Flows ON') : t('Akış Kapalı', 'Flows OFF')}
          </button>

          {showFlows && (
            <select
              value={flowFilter}
              onChange={(e) => setFlowFilter(e.target.value as any)}
              style={{
                padding: '2px 6px',
                backgroundColor: '#0f172a',
                color: '#f8fafc',
                border: '1px solid #475569',
                borderRadius: '4px',
                fontSize: '0.72rem',
                cursor: 'pointer',
              }}
              title={t('Akış filtresi', 'Flow filter')}
            >
              <option value="top5">⭐ {t('İlk 5 Maliyet', 'Top 5 Cost')}</option>
              <option value="top10">{t('İlk 10 Maliyet', 'Top 10 Cost')}</option>
              <option value="all">{t('Tüm Akışlar', 'All Flows')}</option>
              {selectedDeptId && <option value="selected">{t('Seçili Departman', 'Selected Dept')}</option>}
            </select>
          )}

          {!compact && (
            <>
              <button
                onClick={() => setShowCostPanel(!showCostPanel)}
                style={{
                  padding: '3px 8px',
                  background: showCostPanel ? '#7c3aed' : '#334155',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 600,
                  fontSize: '0.72rem',
                }}
                title={t('En yüksek taşıma maliyeti yaratan çiftler tablosu', 'Pairwise cost contributors table')}
              >
                📊 {t('Maliyet Dağılımı', 'Cost Drivers')}
              </button>

              <button
                onClick={() => setShowDimensions(!showDimensions)}
                style={{
                  padding: '3px 6px',
                  background: showDimensions ? '#475569' : '#334155',
                  color: '#f8fafc',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.72rem',
                }}
                title={t('Boyut metinlerini göster/gizle', 'Toggle dimension labels')}
              >
                {t('Boyutlar', 'Dims')}
              </button>
            </>
          )}

          {/* Export Buttons */}
          <button
            data-testid="export-layout-svg-btn"
            onClick={handleExportSvg}
            style={{ padding: '3px 6px', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.72rem', fontWeight: 600 }}
            title={t('SVG Vektör İndir', 'Export Vector SVG')}
          >
            SVG
          </button>
          <button
            data-testid="export-layout-png-btn"
            onClick={handleExportPng}
            style={{ padding: '3px 6px', background: '#334155', color: '#f8fafc', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.72rem', fontWeight: 600 }}
            title={t('300 DPI PNG İndir', 'Export High-Res PNG')}
          >
            PNG
          </button>
        </div>
      </div>

      {/* MAIN VIEWPORT CANVAS AREA */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onTouchCancel={handleTouchEnd}
        onWheel={handleWheel}
        style={{
          position: 'relative',
          width: '100%',
          height: `${dynamicContainerHeight}px`,
          backgroundColor: '#0a0f1d',
          overflow: 'hidden',
          cursor: isPanning ? 'grabbing' : 'grab',
          userSelect: 'none',
          touchAction: 'none',
        }}
      >
        <svg
          ref={svgRef}
          aria-label="2D Facility Layout Canvas"
          data-testid="layout-canvas-svg"
          xmlns="http://www.w3.org/2000/svg"
          width="100%"
          height="100%"
          viewBox={`${viewBoxX} ${viewBoxY} ${viewBoxW} ${viewBoxH}`}
          style={{ display: 'block', width: '100%', height: '100%' }}
        >
          <defs>
            {/* Grid Pattern */}
            <pattern id="facility-grid" width="10" height="10" patternUnits="userSpaceOnUse">
              <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#1e293b" strokeWidth="0.3" />
            </pattern>

            {/* Reserved Zone Diagonal Hatching */}
            <pattern id="reserved-zone-hatch" width="6" height="6" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
              <line x1="0" y1="0" x2="0" y2="6" stroke="#ef4444" strokeWidth="1.2" strokeOpacity="0.45" />
            </pattern>

            {/* Arrowhead Markers for Flow Overlay */}
            <marker
              id="marker-arrow-normal"
              viewBox="0 0 10 10"
              refX="7"
              refY="5"
              markerWidth="4.5"
              markerHeight="4.5"
              orient="auto-start-reverse"
            >
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#64748b" fillOpacity="0.85" />
            </marker>

            <marker
              id="marker-arrow-top5"
              viewBox="0 0 10 10"
              refX="7"
              refY="5"
              markerWidth="5.5"
              markerHeight="5.5"
              orient="auto-start-reverse"
            >
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#f59e0b" />
            </marker>

            <marker
              id="marker-arrow-selected"
              viewBox="0 0 10 10"
              refX="7"
              refY="5"
              markerWidth="5.5"
              markerHeight="5.5"
              orient="auto-start-reverse"
            >
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#06b6d4" />
            </marker>

            {/* Department Label Clip Paths (Guarantees zero text overflow outside block) */}
            {placements.map((p) => {
              const rx = toSvgX(p.x);
              const ry = toSvgY(p.y, p.height);
              return (
                <clipPath key={`clip-${p.department_id}`} id={`clip-${p.department_id}`}>
                  <rect x={rx + 1} y={ry + 1} width={Math.max(1, p.width - 2)} height={Math.max(1, p.height - 2)} rx="1" />
                </clipPath>
              );
            })}
          </defs>

          {/* 1. Facility Envelope & Grid */}
          <rect
            x={0}
            y={0}
            width={facW}
            height={facH}
            fill="#0f172a"
            stroke="#3b82f6"
            strokeWidth="1.5"
            strokeDasharray="6,3"
            style={{ cursor: 'default' }}
            onClick={() => {
              if (!didPanRef.current) {
                onSelectDept?.(null);
                setFocusedFlowPair(null);
                setHoveredFlow(null);
              }
            }}
          />
          {showGrid && (
            <rect x={0} y={0} width={facW} height={facH} fill="url(#facility-grid)" pointerEvents="none" />
          )}

          {/* 2. Reserved Exclusion Zones (DEF-005 fix) */}
          {problem?.facility?.reserved_zones?.map((rz) => {
            const rx = toSvgX(rz.bounding_box.x_min);
            const rw = rz.bounding_box.x_max - rz.bounding_box.x_min;
            const rh = rz.bounding_box.y_max - rz.bounding_box.y_min;
            const ry = toSvgY(rz.bounding_box.y_min, rh);
            const rzName = rz.id.replace('RZ_', '').replace('_', ' ');

            return (
              <g key={rz.id}>
                <rect
                  x={rx}
                  y={ry}
                  width={rw}
                  height={rh}
                  fill="url(#reserved-zone-hatch)"
                  stroke="#ef4444"
                  strokeWidth="1.2"
                />
                <text
                  x={rx + rw / 2}
                  y={ry + rh / 2}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fill="#fca5a5"
                  fontSize={Math.max(2.5, Math.min(4.5, rw / 5))}
                  fontWeight="700"
                  style={{ pointerEvents: 'none', userSelect: 'none' }}
                >
                  🚫 {rzName}
                </text>
              </g>
            );
          })}

          {/* 3. MATERIAL FLOW OVERLAY LAYER (Behind department labels, DEF-002 fix) */}
          {showFlows && visibleFlows.length > 0 && (
            <g id="flow-overlay-layer">
              {visibleFlows.map((flow, idx) => {
                const isTop5 = flow.isTop5;
                const isSelectedDeptFlow =
                  selectedDeptId &&
                  (flow.source_department === selectedDeptId || flow.target_department === selectedDeptId);
                const isFocusedPair = focusedFlowPair === `${flow.source_department}->${flow.target_department}`;

                // Normalized stroke width (1.2px to 3.8px screen-space converted to world coordinates)
                const flowRatio = flow.quantity / Math.max(1, maxFlowQuantity);
                const strokeWidthPx = isFocusedPair
                  ? 4.0
                  : isTop5
                  ? 2.2 + flowRatio * 1.6
                  : 1.2 + flowRatio * 1.2;
                const strokeWidthWorld = strokeWidthPx / Math.max(0.1, effectivePixelsPerMeter);

                // Coordinates
                const x1 = toSvgX(flow.srcCx);
                const y1 = toSvgY(flow.srcCy);
                const x2 = toSvgX(flow.tgtCx);
                const y2 = toSvgY(flow.tgtCy);

                // Slight quadratic curvature to avoid bidirectional arrow overlap
                const dx = x2 - x1;
                const dy = y2 - y1;
                const midX = (x1 + x2) / 2 - dy * 0.12;
                const midY = (y1 + y2) / 2 + dx * 0.12;
                const pathD = `M ${x1} ${y1} Q ${midX} ${midY} ${x2} ${y2}`;

                const strokeColor = isFocusedPair ? '#ec4899' : isSelectedDeptFlow ? '#06b6d4' : isTop5 ? '#f59e0b' : '#64748b';
                const strokeOpacity = isFocusedPair ? 1.0 : isSelectedDeptFlow ? 0.95 : isTop5 ? 0.85 : 0.4;
                const markerId = isFocusedPair
                  ? 'marker-arrow-selected'
                  : isSelectedDeptFlow
                  ? 'marker-arrow-selected'
                  : isTop5
                  ? 'marker-arrow-top5'
                  : 'marker-arrow-normal';

                return (
                  <path
                    key={`flow-${idx}`}
                    d={pathD}
                    fill="none"
                    stroke={strokeColor}
                    strokeWidth={strokeWidthWorld}
                    strokeOpacity={strokeOpacity}
                    markerEnd={`url(#${markerId})`}
                    style={{ transition: 'stroke-width 0.2s, stroke-opacity 0.2s', cursor: 'pointer' }}
                    onMouseEnter={() => setHoveredFlow(flow)}
                    onMouseLeave={() => setHoveredFlow(null)}
                    onClick={(e) => {
                      e.stopPropagation();
                      const pair = `${flow.source_department}->${flow.target_department}`;
                      setFocusedFlowPair((prev) => (prev === pair ? null : pair));
                      setHoveredFlow((prev) => (prev?.source_department === flow.source_department && prev?.target_department === flow.target_department ? null : flow));
                    }}
                  />
                );
              })}
            </g>
          )}

          {/* 4. DEPARTMENT RECTANGLES & RESPONSIVE LABELS (DEF-003 fix) */}
          <g id="departments-layer">
            {placements.map((p, idx) => {
              const color = DEPARTMENT_COLORS[idx % DEPARTMENT_COLORS.length];
              const isSelected = selectedDeptId === p.department_id;
              const isHovered = hoveredDeptId === p.department_id;
              const isFixed = fixedDeptIds.has(p.department_id);
              const isOverlapping = overlappingDeptIds.has(p.department_id);
              const arViolation = arViolations.get(p.department_id);

              const rx = toSvgX(p.x);
              const ry = toSvgY(p.y, p.height);
              const cx = rx + p.width / 2;
              const cy = ry + p.height / 2;
              const area = p.width * p.height;
              const probDept = problem?.departments?.find((d) => d.id === p.department_id);

              // Responsive Screen Dimensions in Pixels
              const screenW = p.width * effectivePixelsPerMeter;
              const screenH = p.height * effectivePixelsPerMeter;

              // Text formatting based on screen space
              const cleanId = p.department_id.replace(/^DEP_/, '');
              const fullName = probDept?.name || cleanId;

              // Screen size classification:
              const isLarge = screenW >= 100 && screenH >= 48;
              const isMedium = screenW >= 55 && screenH >= 32;
              const isSmall = screenW >= 28 && screenH >= 20;

              // Font scaling in world units to produce exact ~11-13px screen text
              const targetTitlePx = isLarge ? 12.5 : isMedium ? 10.5 : 9.0;
              const fontTitleWorld = targetTitlePx / Math.max(0.1, effectivePixelsPerMeter);
              const fontSubWorld = 9.0 / Math.max(0.1, effectivePixelsPerMeter);

              // Smart label truncation
              let labelText = cleanId;
              if (isLarge) {
                const maxChars = Math.max(8, Math.floor(screenW / 7.5));
                labelText = fullName.length > maxChars ? fullName.slice(0, maxChars - 1) + '…' : fullName;
              } else if (isMedium) {
                labelText = cleanId.slice(0, 8);
              } else if (isSmall) {
                labelText = cleanId.slice(0, 4);
              } else {
                labelText = cleanId.slice(0, 2);
              }

              return (
                <g
                  key={p.department_id}
                  data-department-id={p.department_id}
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={() => setHoveredDeptId(p.department_id)}
                  onMouseLeave={() => setHoveredDeptId(null)}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (!didPanRef.current) {
                      onSelectDept?.(isSelected ? null : p.department_id);
                    }
                  }}
                >
                  {/* Department Fill Rectangle */}
                  <rect
                    x={rx}
                    y={ry}
                    width={p.width}
                    height={p.height}
                    fill={color}
                    fillOpacity={isSelected ? 0.92 : isHovered ? 0.8 : 0.55}
                    stroke={
                      isSelected
                        ? '#ffffff'
                        : isOverlapping || arViolation
                        ? '#ef4444'
                        : isFixed
                        ? '#fbbf24'
                        : color
                    }
                    strokeWidth={isSelected ? 2.5 / Math.max(0.1, zoom) : (isOverlapping || arViolation ? 2.0 : 1.2) / Math.max(0.1, zoom)}
                    strokeDasharray={isFixed ? '4,2' : undefined}
                    rx="1.2"
                    style={{ transition: 'fill-opacity 0.15s, stroke-width 0.15s' }}
                  />

                  {/* Centroid Crosshair */}
                  {showCentroids && (
                    <g opacity={0.65}>
                      <line x1={cx - 1.5} y1={cy} x2={cx + 1.5} y2={cy} stroke="#ffffff" strokeWidth="0.5" />
                      <line x1={cx} y1={cy - 1.5} x2={cx} y2={cy + 1.5} stroke="#ffffff" strokeWidth="0.5" />
                    </g>
                  )}

                  {/* Department Label (Strictly clipped inside department bounds) */}
                  <g clipPath={`url(#clip-${p.department_id})`} style={{ pointerEvents: 'none', userSelect: 'none' }}>
                    {/* Line 1: Name / ID */}
                    <text
                      x={cx}
                      y={isLarge && showDimensions && screenH >= 70 ? cy - fontTitleWorld * 0.9 : cy}
                      textAnchor="middle"
                      dominantBaseline="central"
                      fill="#ffffff"
                      fontSize={fontTitleWorld}
                      fontWeight="700"
                    >
                      {labelText}
                    </text>

                    {/* Line 2: Dimensions (Rendered only when vertical room exists) */}
                    {isLarge && showDimensions && screenH >= 70 && (
                      <text
                        x={cx}
                        y={cy + fontSubWorld * 0.7}
                        textAnchor="middle"
                        dominantBaseline="central"
                        fill="#e2e8f0"
                        fontSize={fontSubWorld}
                        fontWeight="500"
                      >
                        {p.width.toFixed(1)}m × {p.height.toFixed(1)}m
                      </text>
                    )}

                    {/* Line 3: Area (Rendered only on large blocks with sufficient height) */}
                    {isLarge && showDimensions && screenH >= 95 && (
                      <text
                        x={cx}
                        y={cy + fontSubWorld * 2.2}
                        textAnchor="middle"
                        dominantBaseline="central"
                        fill="#cbd5e1"
                        fontSize={fontSubWorld * 0.9}
                      >
                        {area.toFixed(0)} m²
                      </text>
                    )}
                  </g>

                  {/* Status Badges on corner */}
                  {arViolation && (
                    <g transform={`translate(${rx + p.width - 4.5}, ${ry + 4.5})`}>
                      <circle cx="0" cy="0" r="2.2" fill="#ef4444" />
                      <text x="0" y="0.8" textAnchor="middle" dominantBaseline="central" fill="#ffffff" fontSize="2.2" fontWeight="700">!</text>
                    </g>
                  )}
                </g>
              );
            })}
          </g>
        </svg>

        {/* FLOATING FLOW TOOLTIP */}
        {hoveredFlow && (
          <div
            style={{
              position: 'absolute',
              bottom: 12,
              left: 12,
              backgroundColor: 'rgba(15, 23, 42, 0.92)',
              border: '1px solid #3b82f6',
              borderRadius: '6px',
              padding: '0.5rem 0.8rem',
              color: '#ffffff',
              fontSize: '0.75rem',
              pointerEvents: 'none',
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              zIndex: 20,
            }}
          >
            <div style={{ fontWeight: 700, color: '#60a5fa', marginBottom: '2px' }}>
              {hoveredFlow.source_department} ➔ {hoveredFlow.target_department}
            </div>
            <div>
              {t('Akış Miktarı:', 'Flow:')} <strong>{hoveredFlow.quantity.toLocaleString()}</strong> {hoveredFlow.unit}
            </div>
            <div>
              {t('Manhattan Mesafesi:', 'Distance:')} <strong>{hoveredFlow.distance.toFixed(1)} m</strong>
            </div>
            <div>
              {t('Taşıma Maliyeti:', 'Pair Cost:')}{' '}
              <strong style={{ color: '#fbbf24' }}>
                {formatCost(hoveredFlow.cost, problem?.metadata?.currency)}
              </strong>{' '}
              ({totalComputedMHC > 0 ? ((hoveredFlow.cost / totalComputedMHC) * 100).toFixed(1) : 0}% MHC)
            </div>
          </div>
        )}

        {/* SCIENTIFIC METRIC DISCLOSURE BADGE */}
        {showFlows && (
          <div
            style={{
              position: 'absolute',
              bottom: 8,
              right: 8,
              backgroundColor: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid #334155',
              borderRadius: '4px',
              padding: '2px 8px',
              color: '#94a3b8',
              fontSize: '0.68rem',
              pointerEvents: 'none',
            }}
          >
            Centroid Rectilinear Distance (Manhattan) • Conceptual Flow Arcs
          </div>
        )}
      </div>

      {/* PAIRWISE COST DRIVERS PANEL (DEF-002 / Part 4.5) */}
      {showCostPanel && (
        <div
          style={{
            backgroundColor: '#1e293b',
            borderTop: '1px solid #334155',
            padding: '0.75rem 1rem',
            color: '#f8fafc',
            maxHeight: '220px',
            overflowY: 'auto',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#f1f5f9' }}>
              📊 {t('En Yüksek Taşıma Maliyeti Yaratan Akışlar (Top Cost Contributors)', 'Top Material Handling Cost Drivers')}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
              {t('Toplam Kanonik MHC:', 'Canonical MHC:')}{' '}
              <strong style={{ color: '#34d399' }}>
                {formatCost(totalComputedMHC, problem?.metadata?.currency)}
              </strong>
            </div>
          </div>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.75rem', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #475569', color: '#94a3b8' }}>
                <th style={{ padding: '4px 6px' }}>{t('Hat', 'Pair')}</th>
                <th style={{ padding: '4px 6px' }}>{t('Akış (f_ij)', 'Flow')}</th>
                <th style={{ padding: '4px 6px' }}>{t('Mesafe (d_ij)', 'Dist')}</th>
                <th style={{ padding: '4px 6px' }}>{t('Birim Maliyet (c_ij)', 'Unit Cost')}</th>
                <th style={{ padding: '4px 6px' }}>{t('Maliyet Katkısı', 'Pair Cost')}</th>
                <th style={{ padding: '4px 6px' }}>MHC %</th>
                <th style={{ padding: '4px 6px' }}>{t('İşlem', 'Action')}</th>
              </tr>
            </thead>
            <tbody>
              {topCostFlows.map((f, i) => {
                const isFocused = focusedFlowPair === `${f.source_department}->${f.target_department}`;
                const pct = totalComputedMHC > 0 ? (f.cost / totalComputedMHC) * 100 : 0;
                return (
                  <tr
                    key={i}
                    onClick={() => setFocusedFlowPair(isFocused ? null : `${f.source_department}->${f.target_department}`)}
                    style={{
                      borderBottom: '1px solid #334155',
                      backgroundColor: isFocused ? '#3730a3' : 'transparent',
                      cursor: 'pointer',
                    }}
                  >
                    <td style={{ padding: '4px 6px', fontWeight: 600, color: '#60a5fa' }}>
                      {f.source_department} ➔ {f.target_department}
                    </td>
                    <td style={{ padding: '4px 6px' }}>{f.quantity.toLocaleString()}</td>
                    <td style={{ padding: '4px 6px' }}>{f.distance.toFixed(1)} m</td>
                    <td style={{ padding: '4px 6px' }}>{formatCost(f.unitCost, problem?.metadata?.currency)}</td>
                    <td style={{ padding: '4px 6px', fontWeight: 700, color: '#fbbf24' }}>
                      {formatCost(f.cost, problem?.metadata?.currency)}
                    </td>
                    <td style={{ padding: '4px 6px', color: '#34d399' }}>{pct.toFixed(1)}%</td>
                    <td style={{ padding: '4px 6px' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setFocusedFlowPair(isFocused ? null : `${f.source_department}->${f.target_department}`);
                        }}
                        style={{
                          padding: '2px 6px',
                          fontSize: '0.68rem',
                          background: isFocused ? '#ec4899' : '#334155',
                          color: '#ffffff',
                          border: 'none',
                          borderRadius: '3px',
                          cursor: 'pointer',
                        }}
                      >
                        {isFocused ? t('Bırak', 'Clear') : t('Odakla', 'Focus')}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* DEPARTMENT INSPECTION DRAWER (Part 5) */}
      {selectedDeptDetails && (
        <div
          data-testid="department-inspection-drawer"
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
            width: compact ? '260px' : '340px',
            height: '100%',
            backgroundColor: '#1e293b',
            borderLeft: '1px solid #334155',
            boxShadow: '-4px 0 16px rgba(0,0,0,0.4)',
            zIndex: 30,
            display: 'flex',
            flexDirection: 'column',
            overflowY: 'auto',
            padding: '1rem',
            color: '#f8fafc',
          }}
        >
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                {t('Departman İnceleme Paneli', 'Department Inspection')}
              </div>
              <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: '#f1f5f9' }}>
                {selectedDeptDetails.name}
              </h3>
              <div style={{ fontSize: '0.75rem', color: '#60a5fa' }}>ID: {selectedDeptDetails.id}</div>
            </div>
            <button
              data-testid="close-drawer-btn"
              title={t('Kapat', 'Close')}
              aria-label="close-drawer"
              onClick={() => onSelectDept?.(null)}
              style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
            >
              <X size={18} />
            </button>
          </div>

          {/* Geometry Details */}
          <div style={{ backgroundColor: '#0f172a', borderRadius: '6px', padding: '0.75rem', marginBottom: '0.75rem', border: '1px solid #334155' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#38bdf8', marginBottom: '0.5rem' }}>
              📐 {t('Fiziksel Geometri & Boyutlar', 'Physical Geometry')}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.75rem' }}>
              <div>
                <span style={{ color: '#94a3b8' }}>{t('Genişlik (W):', 'Width:')}</span>{' '}
                <strong>{selectedDeptDetails.placement.width.toFixed(1)} m</strong>
              </div>
              <div>
                <span style={{ color: '#94a3b8' }}>{t('Yükseklik (H):', 'Height:')}</span>{' '}
                <strong>{selectedDeptDetails.placement.height.toFixed(1)} m</strong>
              </div>
              <div>
                <span style={{ color: '#94a3b8' }}>{t('Gerçekleşen Alan:', 'Actual Area:')}</span>{' '}
                <strong>{selectedDeptDetails.actArea.toFixed(1)} m²</strong>
              </div>
              <div>
                <span style={{ color: '#94a3b8' }}>{t('İstenen Alan:', 'Required:')}</span>{' '}
                <strong>{selectedDeptDetails.reqArea.toFixed(1)} m²</strong>
              </div>
              <div>
                <span style={{ color: '#94a3b8' }}>{t('Orjin (X, Y):', 'Origin:')}</span>{' '}
                <strong>({selectedDeptDetails.placement.x.toFixed(1)}, {selectedDeptDetails.placement.y.toFixed(1)})</strong>
              </div>
              <div>
                <span style={{ color: '#94a3b8' }}>{t('Centroid:', 'Centroid:')}</span>{' '}
                <strong>
                  ({(selectedDeptDetails.placement.x + selectedDeptDetails.placement.width / 2).toFixed(1)},{' '}
                  {(selectedDeptDetails.placement.y + selectedDeptDetails.placement.height / 2).toFixed(1)})
                </strong>
              </div>
            </div>

            {/* Aspect Ratio Check */}
            <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid #1e293b', fontSize: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#94a3b8' }}>Aspect Ratio:</span>
                <span
                  style={{
                    padding: '1px 6px',
                    borderRadius: '4px',
                    fontWeight: 700,
                    backgroundColor: selectedDeptDetails.aspect <= selectedDeptDetails.maxAspect ? '#064e3b' : '#7f1d1d',
                    color: selectedDeptDetails.aspect <= selectedDeptDetails.maxAspect ? '#6ee7b7' : '#fca5a5',
                  }}
                >
                  {selectedDeptDetails.aspect.toFixed(2)} (max {selectedDeptDetails.maxAspect})
                </span>
              </div>
            </div>
          </div>

          {/* Traffic Summary */}
          <div style={{ backgroundColor: '#0f172a', borderRadius: '6px', padding: '0.75rem', marginBottom: '0.75rem', border: '1px solid #334155' }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#fbbf24', marginBottom: '0.5rem' }}>
              📦 {t('Malzeme Trafiği Özeti', 'Material Traffic')}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.5rem' }}>
              <div>
                <div style={{ color: '#94a3b8' }}>{t('Gelen Akış:', 'Inflow:')}</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#34d399' }}>
                  {selectedDeptDetails.inflow.toLocaleString()}
                </div>
              </div>
              <div>
                <div style={{ color: '#94a3b8' }}>{t('Giden Akış:', 'Outflow:')}</div>
                <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f59e0b' }}>
                  {selectedDeptDetails.outflow.toLocaleString()}
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                setShowFlows(true);
                setFlowFilter('selected');
              }}
              style={{
                width: '100%',
                padding: '4px 8px',
                backgroundColor: '#2563eb',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                fontSize: '0.72rem',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              🎯 {t('Yalnızca Bu Bölümün Akışlarını Göster', 'Focus Department Flows')}
            </button>
          </div>

          {/* Muther REL Adjacencies */}
          {selectedDeptDetails.rels.length > 0 && (
            <div style={{ backgroundColor: '#0f172a', borderRadius: '6px', padding: '0.75rem', border: '1px solid #334155' }}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#c084fc', marginBottom: '0.5rem' }}>
                🤝 {t('Muther REL İlişkileri', 'Muther REL Ratings')}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.72rem' }}>
                {selectedDeptDetails.rels.map((r, i) => {
                  const partner = r.department_a === selectedDeptId ? r.department_b : r.department_a;
                  const typeColors: Record<string, string> = {
                    A: '#ef4444',
                    E: '#f59e0b',
                    I: '#10b981',
                    O: '#3b82f6',
                    U: '#64748b',
                    X: '#dc2626',
                  };
                  return (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ color: '#cbd5e1' }}>➔ {partner}</span>
                      <span
                        style={{
                          padding: '1px 5px',
                          borderRadius: '3px',
                          fontWeight: 700,
                          backgroundColor: typeColors[r.relationship_type] || '#334155',
                          color: '#ffffff',
                        }}
                      >
                        {r.relationship_type} ({r.score})
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
