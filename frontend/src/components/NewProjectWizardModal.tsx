import React, { useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  Factory,
  Layers,
  Plus,
  Sparkles,
  Trash2,
  Upload,
  Workflow,
  X,
} from 'lucide-react';
import { validateProblemPayload } from '../services/api';
import { useLanguage } from '../context/LanguageContext';
import type {
  Constraint,
  FacilityLayoutProblem,
  Flow,
  Relationship,
} from '../types/api';

interface NewProjectWizardModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreateProject: (problem: FacilityLayoutProblem, autoOptimize: boolean) => Promise<void> | void;
}

type PresetId = 'blank' | 'workshop' | 'factory' | 'warehouse';
type DistanceMetric = 'rectilinear' | 'euclidean';
type RelGrade = 'A' | 'E' | 'I' | 'O' | 'X';

interface DraftDepartment {
  uid: string;
  name: string;
  required_area: number;
  min_aspect_ratio: number;
  max_aspect_ratio: number;
  fixed_position?: { x: number; y: number };
}

interface DraftFlow {
  id: string;
  sourceUid: string;
  targetUid: string;
  quantity: number;
  cost_per_unit_distance: number;
}

interface DraftRelationship {
  id: string;
  deptAUid: string;
  deptBUid: string;
  grade: RelGrade;
}

const REL_SCORE_MAP: Record<RelGrade, number> = {
  A: 16,
  E: 8,
  I: 4,
  O: 2,
  X: -8,
};

const REL_COLOR_MAP: Record<RelGrade, { bg: string; border: string; text: string }> = {
  A: { bg: 'rgba(239, 68, 68, 0.16)', border: 'rgba(239, 68, 68, 0.45)', text: '#fca5a5' },
  E: { bg: 'rgba(249, 115, 22, 0.16)', border: 'rgba(249, 115, 22, 0.45)', text: '#fdba74' },
  I: { bg: 'rgba(16, 185, 129, 0.16)', border: 'rgba(16, 185, 129, 0.45)', text: '#6ee7b7' },
  O: { bg: 'rgba(59, 130, 246, 0.16)', border: 'rgba(59, 130, 246, 0.45)', text: '#93c5fd' },
  X: { bg: 'rgba(168, 85, 247, 0.16)', border: 'rgba(168, 85, 247, 0.45)', text: '#d8b4fe' },
};

function makeUid(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}`;
}

function slugifyId(text: string): string {
  const normalized = text
    .replace(/[çÇ]/g, 'c')
    .replace(/[ğĞ]/g, 'g')
    .replace(/[ıİ]/g, 'i')
    .replace(/[öÖ]/g, 'o')
    .replace(/[şŞ]/g, 's')
    .replace(/[üÜ]/g, 'u')
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
  return (normalized || 'TESIS').slice(0, 14);
}

function buildPresetState(
  presetId: PresetId,
  t: (tr: string, en: string) => string
): {
  projectName: string;
  width: number;
  height: number;
  distanceMetric: DistanceMetric;
  defaultCost: number;
  departments: DraftDepartment[];
  flows: DraftFlow[];
  relationships: DraftRelationship[];
  constraints: Constraint[];
} {
  if (presetId === 'workshop') {
    const depts: DraftDepartment[] = [
      { uid: 'd1', name: t('Hammadde Deposu', 'Raw Material Storage'), required_area: 450, min_aspect_ratio: 1.0, max_aspect_ratio: 2.8 },
      { uid: 'd2', name: t('Kesim ve Hazırlık', 'Cutting & Prep'), required_area: 400, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd3', name: t('Montaj Hattı', 'Assembly Line'), required_area: 550, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd4', name: t('Sevkiyat Alanı', 'Shipping Dock'), required_area: 300, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
    ];
    return {
      projectName: t('Küçük Üretim Atölyesi', 'Small Manufacturing Workshop'),
      width: 50,
      height: 40,
      distanceMetric: 'rectilinear',
      defaultCost: 1.0,
      departments: depts,
      flows: [
        { id: 'f1', sourceUid: 'd1', targetUid: 'd2', quantity: 60, cost_per_unit_distance: 1.0 },
        { id: 'f2', sourceUid: 'd2', targetUid: 'd3', quantity: 55, cost_per_unit_distance: 1.0 },
        { id: 'f3', sourceUid: 'd3', targetUid: 'd4', quantity: 50, cost_per_unit_distance: 1.0 },
      ],
      relationships: [
        { id: 'r1', deptAUid: 'd1', deptBUid: 'd2', grade: 'A' },
        { id: 'r2', deptAUid: 'd2', deptBUid: 'd3', grade: 'E' },
        { id: 'r3', deptAUid: 'd3', deptBUid: 'd4', grade: 'A' },
        { id: 'r4', deptAUid: 'd1', deptBUid: 'd4', grade: 'O' },
      ],
      constraints: [],
    };
  }

  if (presetId === 'factory') {
    const depts: DraftDepartment[] = [
      { uid: 'd1', name: t('Hammadde Kabul', 'Raw Material Intake'), required_area: 900, min_aspect_ratio: 1.0, max_aspect_ratio: 2.8 },
      { uid: 'd2', name: t('CNC İşleme', 'CNC Machining'), required_area: 1100, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd3', name: t('Kaynak Atölyesi', 'Welding Shop'), required_area: 850, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd4', name: t('Yüzey İşlem ve Boya', 'Surface & Coating'), required_area: 750, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd5', name: t('Ana Montaj', 'Main Assembly'), required_area: 1000, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd6', name: t('Kalite ve Sevkiyat', 'QA & Shipping'), required_area: 600, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
    ];
    return {
      projectName: t('Orta Ölçekli İmalat Fabrikası', 'Medium Manufacturing Plant'),
      width: 100,
      height: 60,
      distanceMetric: 'rectilinear',
      defaultCost: 1.0,
      departments: depts,
      flows: [
        { id: 'f1', sourceUid: 'd1', targetUid: 'd2', quantity: 80, cost_per_unit_distance: 1.0 },
        { id: 'f2', sourceUid: 'd2', targetUid: 'd3', quantity: 70, cost_per_unit_distance: 1.0 },
        { id: 'f3', sourceUid: 'd3', targetUid: 'd4', quantity: 65, cost_per_unit_distance: 1.2 },
        { id: 'f4', sourceUid: 'd4', targetUid: 'd5', quantity: 60, cost_per_unit_distance: 1.0 },
        { id: 'f5', sourceUid: 'd5', targetUid: 'd6', quantity: 55, cost_per_unit_distance: 1.0 },
      ],
      relationships: [
        { id: 'r1', deptAUid: 'd1', deptBUid: 'd2', grade: 'A' },
        { id: 'r2', deptAUid: 'd2', deptBUid: 'd3', grade: 'E' },
        { id: 'r3', deptAUid: 'd4', deptBUid: 'd5', grade: 'E' },
        { id: 'r4', deptAUid: 'd5', deptBUid: 'd6', grade: 'A' },
        { id: 'r5', deptAUid: 'd3', deptBUid: 'd4', grade: 'I' },
        { id: 'r6', deptAUid: 'd3', deptBUid: 'd1', grade: 'X' },
      ],
      constraints: [],
    };
  }

  if (presetId === 'warehouse') {
    const depts: DraftDepartment[] = [
      { uid: 'd1', name: t('Mal Kabul Rampası', 'Receiving Dock'), required_area: 650, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd2', name: t('Yüksek Raf Depolama', 'Pallet Racking'), required_area: 1200, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd3', name: t('Sipariş Toplama', 'Order Picking'), required_area: 750, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd4', name: t('Paketleme ve Etiketleme', 'Packing & Labeling'), required_area: 450, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
      { uid: 'd5', name: t('Sevkiyat Rampası', 'Outbound Dispatch'), required_area: 450, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
    ];
    return {
      projectName: t('Lojistik Dağıtım Merkezi', 'Logistics Distribution Hub'),
      width: 80,
      height: 50,
      distanceMetric: 'rectilinear',
      defaultCost: 1.0,
      departments: depts,
      flows: [
        { id: 'f1', sourceUid: 'd1', targetUid: 'd2', quantity: 95, cost_per_unit_distance: 1.0 },
        { id: 'f2', sourceUid: 'd2', targetUid: 'd3', quantity: 90, cost_per_unit_distance: 1.0 },
        { id: 'f3', sourceUid: 'd3', targetUid: 'd4', quantity: 85, cost_per_unit_distance: 1.0 },
        { id: 'f4', sourceUid: 'd4', targetUid: 'd5', quantity: 85, cost_per_unit_distance: 1.0 },
      ],
      relationships: [
        { id: 'r1', deptAUid: 'd1', deptBUid: 'd2', grade: 'A' },
        { id: 'r2', deptAUid: 'd2', deptBUid: 'd3', grade: 'A' },
        { id: 'r3', deptAUid: 'd3', deptBUid: 'd4', grade: 'E' },
        { id: 'r4', deptAUid: 'd4', deptBUid: 'd5', grade: 'A' },
      ],
      constraints: [],
    };
  }

  // Blank facility preset
  const depts: DraftDepartment[] = [
    { uid: 'd1', name: t('Bölüm 1 (Giriş)', 'Department 1 (Intake)'), required_area: 600, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
    { uid: 'd2', name: t('Bölüm 2 (Üretim)', 'Department 2 (Production)'), required_area: 800, min_aspect_ratio: 1.0, max_aspect_ratio: 3.0 },
  ];
  return {
    projectName: t('Özel Tesis Projesi', 'Custom Facility Project'),
    width: 60,
    height: 40,
    distanceMetric: 'rectilinear',
    defaultCost: 1.0,
    departments: depts,
    flows: [
      { id: 'f1', sourceUid: 'd1', targetUid: 'd2', quantity: 25, cost_per_unit_distance: 1.0 },
    ],
    relationships: [],
    constraints: [],
  };
}

export const NewProjectWizardModal: React.FC<NewProjectWizardModalProps> = ({
  isOpen,
  onClose,
  onCreateProject,
}) => {
  const { t } = useLanguage();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [selectedPreset, setSelectedPreset] = useState<PresetId>('workshop');
  const [projectName, setProjectName] = useState<string>('');
  const [width, setWidth] = useState<number>(50);
  const [height, setHeight] = useState<number>(40);
  const [distanceMetric, setDistanceMetric] = useState<DistanceMetric>('rectilinear');
  const [defaultCost, setDefaultCost] = useState<number>(1.0);
  const [departments, setDepartments] = useState<DraftDepartment[]>([]);
  const [flows, setFlows] = useState<DraftFlow[]>([]);
  const [relationships, setRelationships] = useState<DraftRelationship[]>([]);
  const [importedConstraints, setImportedConstraints] = useState<Constraint[]>([]);

  // Inline Step 3 add controls
  const [flowSourceUid, setFlowSourceUid] = useState<string>('');
  const [flowTargetUid, setFlowTargetUid] = useState<string>('');
  const [flowQuantity, setFlowQuantity] = useState<number>(40);
  const [flowCost, setFlowCost] = useState<number>(1.0);

  const [relAUid, setRelAUid] = useState<string>('');
  const [relBUid, setRelBUid] = useState<string>('');
  const [relGrade, setRelGrade] = useState<RelGrade>('A');

  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorMessages, setErrorMessages] = useState<string[]>([]);

  const applyPreset = (presetId: PresetId) => {
    const preset = buildPresetState(presetId, t);
    setSelectedPreset(presetId);
    setProjectName(preset.projectName);
    setWidth(preset.width);
    setHeight(preset.height);
    setDistanceMetric(preset.distanceMetric);
    setDefaultCost(preset.defaultCost);
    setDepartments(preset.departments);
    setFlows(preset.flows);
    setRelationships(preset.relationships);
    setImportedConstraints(preset.constraints);
    setFlowSourceUid(preset.departments[0]?.uid ?? '');
    setFlowTargetUid(preset.departments[1]?.uid ?? '');
    setFlowCost(preset.defaultCost);
    setRelAUid(preset.departments[0]?.uid ?? '');
    setRelBUid(preset.departments[1]?.uid ?? '');
    setErrorMessages([]);
  };

  useEffect(() => {
    if (isOpen) {
      setStep(1);
      setSubmitting(false);
      setErrorMessages([]);
      applyPreset('workshop');
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) {
        onClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isOpen, submitting, onClose]);

  if (!isOpen) return null;

  const facilityArea = Math.max(0, (Number.isFinite(width) ? width : 0) * (Number.isFinite(height) ? height : 0));
  const totalDeptArea = departments.reduce((sum, d) => sum + (Number.isFinite(d.required_area) ? d.required_area : 0), 0);
  const utilizationPct = facilityArea > 0 ? (totalDeptArea / facilityArea) * 100 : 0;
  const isOverCapacity = facilityArea <= 0 || totalDeptArea > facilityArea;

  const deptByUid = new Map(departments.map((d) => [d.uid, d]));

  const validateStep1 = (): string[] => {
    const errs: string[] = [];
    if (!projectName.trim()) {
      errs.push(t('Lütfen bir proje veya tesis adı girin.', 'Please enter a project or facility name.'));
    }
    if (!Number.isFinite(width) || width < 10 || width > 1000) {
      errs.push(t('Tesis genişliği 10 ile 1000 metre arasında olmalıdır.', 'Facility width must be between 10 and 1000 meters.'));
    }
    if (!Number.isFinite(height) || height < 10 || height > 1000) {
      errs.push(t('Tesis derinliği 10 ile 1000 metre arasında olmalıdır.', 'Facility depth must be between 10 and 1000 meters.'));
    }
    if (!Number.isFinite(defaultCost) || defaultCost < 0) {
      errs.push(t('Birim taşıma maliyeti negatif olamaz.', 'Default cost per unit distance cannot be negative.'));
    }
    return errs;
  };

  const validateStep2 = (): string[] => {
    const errs: string[] = [];
    if (departments.length < 2) {
      errs.push(t('En az 2 bölüm tanımlamanız gerekir.', 'At least 2 departments are required.'));
    }
    departments.forEach((d, idx) => {
      const label = d.name.trim() || `#${idx + 1}`;
      if (!d.name.trim()) {
        errs.push(t(`${idx + 1}. sıradaki bölüm için bir ad girin.`, `Please enter a name for department #${idx + 1}.`));
      }
      if (!Number.isFinite(d.required_area) || d.required_area <= 0) {
        errs.push(t(`"${label}" bölümünün alanı 0'dan büyük olmalıdır.`, `Required area for "${label}" must be greater than 0.`));
      }
      if (!Number.isFinite(d.min_aspect_ratio) || d.min_aspect_ratio < 1) {
        errs.push(t(`"${label}" için Min. En-Boy oranı en az 1.0 olmalıdır.`, `Min aspect ratio for "${label}" must be at least 1.0.`));
      }
      if (!Number.isFinite(d.max_aspect_ratio) || d.max_aspect_ratio < d.min_aspect_ratio) {
        errs.push(t(`"${label}" için Maks. En-Boy oranı Min. orandan küçük olamaz.`, `Max aspect ratio for "${label}" must be >= Min aspect ratio.`));
      }
    });
    if (isOverCapacity) {
      errs.push(
        t(
          `Toplam bölüm alanı (${totalDeptArea.toLocaleString()} m²), tesis brüt alanını (${facilityArea.toLocaleString()} m²) aşıyor. Bölüm alanlarını küçültün veya tesis boyutunu büyütün.`,
          `Total department area (${totalDeptArea.toLocaleString()} m²) exceeds gross facility area (${facilityArea.toLocaleString()} m²). Reduce department areas or enlarge facility dimensions.`
        )
      );
    }
    return errs;
  };

  const goNextStep = () => {
    setErrorMessages([]);
    if (step === 1) {
      const errs = validateStep1();
      if (errs.length > 0) {
        setErrorMessages(errs);
        return;
      }
      // Ensure step 3 selectors point to valid uids
      if (!deptByUid.has(flowSourceUid) && departments[0]) setFlowSourceUid(departments[0].uid);
      if (!deptByUid.has(flowTargetUid) && departments[1]) setFlowTargetUid(departments[1].uid);
      if (!deptByUid.has(relAUid) && departments[0]) setRelAUid(departments[0].uid);
      if (!deptByUid.has(relBUid) && departments[1]) setRelBUid(departments[1].uid);
      setStep(2);
      return;
    }
    if (step === 2) {
      const errs = validateStep2();
      if (errs.length > 0) {
        setErrorMessages(errs);
        return;
      }
      if (!deptByUid.has(flowSourceUid) && departments[0]) setFlowSourceUid(departments[0].uid);
      if (!deptByUid.has(flowTargetUid) && (departments[1] || departments[0])) {
        setFlowTargetUid((departments[1] ?? departments[0]).uid);
      }
      if (!deptByUid.has(relAUid) && departments[0]) setRelAUid(departments[0].uid);
      if (!deptByUid.has(relBUid) && (departments[1] || departments[0])) {
        setRelBUid((departments[1] ?? departments[0]).uid);
      }
      setStep(3);
    }
  };

  const handleAddDepartment = () => {
    const nextIndex = departments.length + 1;
    const suggestedArea = Math.max(100, Math.round((facilityArea * 0.1) / 10) * 10);
    setDepartments((prev) => [
      ...prev,
      {
        uid: makeUid('dept'),
        name: t(`Bölüm ${nextIndex}`, `Department ${nextIndex}`),
        required_area: suggestedArea,
        min_aspect_ratio: 1.0,
        max_aspect_ratio: 3.0,
      },
    ]);
  };

  const handleUpdateDepartment = (uid: string, patch: Partial<DraftDepartment>) => {
    setDepartments((prev) => prev.map((d) => (d.uid === uid ? { ...d, ...patch } : d)));
  };

  const handleDeleteDepartment = (uid: string) => {
    if (departments.length <= 2) return;
    setDepartments((prev) => prev.filter((d) => d.uid !== uid));
    setFlows((prev) => prev.filter((f) => f.sourceUid !== uid && f.targetUid !== uid));
    setRelationships((prev) => prev.filter((r) => r.deptAUid !== uid && r.deptBUid !== uid));
  };

  const handleAddFlow = () => {
    setErrorMessages([]);
    if (!flowSourceUid || !flowTargetUid) return;
    if (flowSourceUid === flowTargetUid) {
      setErrorMessages([t('Kaynak ve hedef bölüm aynı olamaz.', 'Source and target department cannot be the same.')]);
      return;
    }
    if (!Number.isFinite(flowQuantity) || flowQuantity <= 0) {
      setErrorMessages([t('Taşıma miktarı 0\'dan büyük olmalıdır.', 'Flow quantity must be greater than 0.')]);
      return;
    }
    const cost = Number.isFinite(flowCost) && flowCost >= 0 ? flowCost : defaultCost;
    setFlows((prev) => {
      const existing = prev.find((f) => f.sourceUid === flowSourceUid && f.targetUid === flowTargetUid);
      if (existing) {
        return prev.map((f) =>
          f.id === existing.id
            ? { ...f, quantity: flowQuantity, cost_per_unit_distance: cost }
            : f
        );
      }
      return [
        ...prev,
        {
          id: makeUid('flow'),
          sourceUid: flowSourceUid,
          targetUid: flowTargetUid,
          quantity: flowQuantity,
          cost_per_unit_distance: cost,
        },
      ];
    });
  };

  const handleGenerateSequentialFlows = () => {
    setErrorMessages([]);
    setFlows((prev) => {
      const next = [...prev];
      for (let i = 0; i < departments.length - 1; i++) {
        const src = departments[i].uid;
        const dst = departments[i + 1].uid;
        if (!next.some((f) => f.sourceUid === src && f.targetUid === dst)) {
          next.push({
            id: makeUid('flow'),
            sourceUid: src,
            targetUid: dst,
            quantity: 35,
            cost_per_unit_distance: Number.isFinite(defaultCost) ? defaultCost : 1.0,
          });
        }
      }
      return next;
    });
  };

  const handleAddRelationship = () => {
    setErrorMessages([]);
    if (!relAUid || !relBUid) return;
    if (relAUid === relBUid) {
      setErrorMessages([t('Yakınlık ilişkisi için iki farklı bölüm seçin.', 'Please select two different departments for a relationship.')]);
      return;
    }
    setRelationships((prev) => {
      const existing = prev.find(
        (r) =>
          (r.deptAUid === relAUid && r.deptBUid === relBUid) ||
          (r.deptAUid === relBUid && r.deptBUid === relAUid)
      );
      if (existing) {
        return prev.map((r) => (r.id === existing.id ? { ...r, grade: relGrade } : r));
      }
      return [
        ...prev,
        {
          id: makeUid('rel'),
          deptAUid: relAUid,
          deptBUid: relBUid,
          grade: relGrade,
        },
      ];
    });
  };

  const handleImportJsonFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setErrorMessages([]);
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as Partial<FacilityLayoutProblem>;
      if (!parsed || !parsed.facility || !Array.isArray(parsed.departments) || parsed.departments.length < 2) {
        setErrorMessages([
          t(
            'JSON dosyası geçerli bir FLODSS problemi değil (facility ve en az 2 department içermelidir).',
            'JSON file is not a valid FLODSS problem (must include facility and at least 2 departments).'
          ),
        ]);
        return;
      }

      const uidMap = new Map<string, string>();
      const importedDepts: DraftDepartment[] = parsed.departments.map((d, idx) => {
        const uid = makeUid(`imp_${idx}`);
        uidMap.set(d.id, uid);
        return {
          uid,
          name: d.name || d.id || `Department ${idx + 1}`,
          required_area: Number(d.required_area) || 100,
          min_aspect_ratio: Number(d.min_aspect_ratio) || 1.0,
          max_aspect_ratio: Number(d.max_aspect_ratio) || 3.0,
          fixed_position: d.fixed_position,
        };
      });

      const importedFlows: DraftFlow[] = Array.isArray(parsed.flows)
        ? parsed.flows
            .filter((f) => uidMap.has(f.source_department) && uidMap.has(f.target_department))
            .map((f) => ({
              id: makeUid('flow'),
              sourceUid: uidMap.get(f.source_department)!,
              targetUid: uidMap.get(f.target_department)!,
              quantity: Number(f.quantity) || 10,
              cost_per_unit_distance: Number(f.cost_per_unit_distance ?? parsed.objective_config?.default_cost_per_unit_distance ?? 1.0),
            }))
        : [];

      const validGrades = new Set<RelGrade>(['A', 'E', 'I', 'O', 'X']);
      const importedRels: DraftRelationship[] = Array.isArray(parsed.relationships)
        ? parsed.relationships
            .filter((r) => uidMap.has(r.department_a) && uidMap.has(r.department_b))
            .map((r) => {
              const rawGrade = String(r.relationship_type || 'O').toUpperCase() as RelGrade;
              return {
                id: makeUid('rel'),
                deptAUid: uidMap.get(r.department_a)!,
                deptBUid: uidMap.get(r.department_b)!,
                grade: validGrades.has(rawGrade) ? rawGrade : 'O',
              };
            })
        : [];

      setProjectName(parsed.name || parsed.facility.name || file.name.replace(/\.json$/i, ''));
      setWidth(Number(parsed.facility.width) || 60);
      setHeight(Number(parsed.facility.height) || 40);
      setDistanceMetric(parsed.objective_config?.distance_metric === 'euclidean' ? 'euclidean' : 'rectilinear');
      setDefaultCost(Number(parsed.objective_config?.default_cost_per_unit_distance ?? parsed.objective_config?.custom_weights?.default_cost_per_unit_distance ?? 1.0));
      setDepartments(importedDepts);
      setFlows(importedFlows);
      setRelationships(importedRels);
      setImportedConstraints(Array.isArray(parsed.constraints) ? parsed.constraints : []);
      setFlowSourceUid(importedDepts[0]?.uid ?? '');
      setFlowTargetUid(importedDepts[1]?.uid ?? '');
      setRelAUid(importedDepts[0]?.uid ?? '');
      setRelBUid(importedDepts[1]?.uid ?? '');
    } catch (err: any) {
      setErrorMessages([
        t(`JSON dosyası okunamadı: ${err?.message || 'Bilinmeyen hata'}`, `Failed to parse JSON file: ${err?.message || 'Unknown error'}`),
      ]);
    } finally {
      e.target.value = '';
    }
  };

  const buildProblemPayload = (): FacilityLayoutProblem => {
    const suffix = Date.now().toString(36).toUpperCase().slice(-4);
    const problemId = `CUSTOM_${slugifyId(projectName)}_${suffix}`;

    const idByUid = new Map<string, string>();
    departments.forEach((d, idx) => {
      idByUid.set(d.uid, `DEP_${(idx + 1).toString().padStart(2, '0')}`);
    });

    const finalDepts = departments.map((d) => ({
      id: idByUid.get(d.uid)!,
      name: d.name.trim(),
      required_area: Number(d.required_area),
      min_aspect_ratio: Number(d.min_aspect_ratio) || 1.0,
      max_aspect_ratio: Number(d.max_aspect_ratio) || 3.0,
      ...(d.fixed_position ? { fixed_position: d.fixed_position } : {}),
    }));

    const finalFlows: Flow[] = flows
      .filter((f) => idByUid.has(f.sourceUid) && idByUid.has(f.targetUid) && f.sourceUid !== f.targetUid)
      .map((f) => ({
        source_department: idByUid.get(f.sourceUid)!,
        target_department: idByUid.get(f.targetUid)!,
        quantity: Number(f.quantity),
        cost_per_unit_distance: Number.isFinite(f.cost_per_unit_distance) ? f.cost_per_unit_distance : defaultCost,
        unit: 'loads/day',
      }));

    const finalRels: Relationship[] = relationships
      .filter((r) => idByUid.has(r.deptAUid) && idByUid.has(r.deptBUid) && r.deptAUid !== r.deptBUid)
      .map((r) => ({
        department_a: idByUid.get(r.deptAUid)!,
        department_b: idByUid.get(r.deptBUid)!,
        relationship_type: r.grade,
        score: REL_SCORE_MAP[r.grade],
      }));

    const w = Number(width);
    const h = Number(height);

    return {
      id: problemId,
      name: projectName.trim(),
      facility: {
        id: `FAC_${problemId}`,
        name: projectName.trim(),
        width: w,
        height: h,
        area: Number((w * h).toFixed(2)),
        reserved_zones: [],
      },
      departments: finalDepts,
      flows: finalFlows,
      relationships: finalRels,
      constraints: importedConstraints.filter((c) => c && Array.isArray(c.involved_departments) && c.involved_departments.every((did) => finalDepts.some((fd) => fd.id === did))),
      objective_config: {
        distance_metric: distanceMetric,
        primary_objective: 'minimize_flow_distance',
        flow_weight: 1.0,
        relationship_weight: 0.5,
        default_cost_per_unit_distance: Number(defaultCost) || 1.0,
      },
      metadata: {
        custom_project: true,
        created_at: new Date().toISOString(),
      },
    };
  };

  const handleFinish = async (autoOptimize: boolean) => {
    const allErrors = [...validateStep1(), ...validateStep2()];
    if (allErrors.length > 0) {
      setErrorMessages(allErrors);
      return;
    }

    const builtProblem = buildProblemPayload();
    setSubmitting(true);
    setErrorMessages([]);
    try {
      const report = await validateProblemPayload(builtProblem);
      if (!report.is_valid) {
        setErrorMessages(
          report.errors && report.errors.length > 0
            ? report.errors
            : [t('Problem sunucu doğrulamasından geçemedi.', 'Problem failed server schema validation.')]
        );
        setSubmitting(false);
        return;
      }
      await onCreateProject(builtProblem, autoOptimize);
      setSubmitting(false);
      onClose();
    } catch (err: any) {
      setErrorMessages([
        err?.message || t('Proje doğrulanırken beklenmeyen bir hata oluştu.', 'Unexpected error while validating project.'),
      ]);
      setSubmitting(false);
    }
  };

  const presets: Array<{ id: PresetId; title: string; meta: string }> = [
    { id: 'blank', title: t('Sıfırdan Boş Tesis', 'Blank Facility'), meta: t('60×40 m · 2 bölüm', '60×40 m · 2 depts') },
    { id: 'workshop', title: t('Küçük Atölye', 'Small Workshop'), meta: t('50×40 m · 4 bölüm', '50×40 m · 4 depts') },
    { id: 'factory', title: t('Orta Fabrika', 'Medium Factory'), meta: t('100×60 m · 6 bölüm', '100×60 m · 6 depts') },
    { id: 'warehouse', title: t('Lojistik Depo', 'Logistics Warehouse'), meta: t('80×50 m · 5 bölüm', '80×50 m · 5 depts') },
  ];

  const stepsMeta = [
    { num: 1 as const, label: t('1. Tesis Bilgileri', '1. Facility Setup'), icon: Factory },
    { num: 2 as const, label: t('2. Bölümler', '2. Departments'), icon: Layers },
    { num: 3 as const, label: t('3. Akışlar ve Yakınlık', '3. Flows & REL'), icon: Workflow },
  ];

  return (
    <div
      className="wizard-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget && !submitting) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-project-wizard-title"
    >
      <div className="wizard-modal">
        {/* Header */}
        <div className="wizard-header">
          <div className="wizard-title-wrap">
            <span className="wizard-icon-badge">
              <Factory size={18} />
            </span>
            <div>
              <h2 id="new-project-wizard-title">
                {t('Yeni Tesis Projesi Oluştur', 'Create New Facility Project')}
              </h2>
              <p>
                {t(
                  'Kendi tesis boyutlarınızı, bölümlerinizi ve malzeme akışlarınızı girin; mevcut tüm algoritmalarla optimize edin.',
                  'Enter your own plant dimensions, departments, and material flows; optimize with all built-in solvers.'
                )}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="wizard-close-btn"
            onClick={() => !submitting && onClose()}
            aria-label={t('Kapat', 'Close')}
          >
            <X size={16} />
          </button>
        </div>

        {/* Stepper */}
        <div className="wizard-stepper">
          {stepsMeta.map((item) => {
            const Icon = item.icon;
            const isCurrent = step === item.num;
            const isDone = step > item.num;
            return (
              <button
                key={item.num}
                type="button"
                className={`wizard-step-tab ${isCurrent ? 'current' : ''} ${isDone ? 'done' : ''}`}
                onClick={() => {
                  if (item.num < step) {
                    setErrorMessages([]);
                    setStep(item.num);
                  } else if (item.num > step && item.num === 2 && validateStep1().length === 0) {
                    setErrorMessages([]);
                    setStep(2);
                  } else if (item.num > step && item.num === 3 && validateStep1().length === 0 && validateStep2().length === 0) {
                    setErrorMessages([]);
                    setStep(3);
                  }
                }}
              >
                <span className="step-dot">{isDone ? <Check size={12} /> : <Icon size={12} />}</span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>

        {/* Error Box */}
        {errorMessages.length > 0 && (
          <div className="wizard-error-box" role="alert">
            <AlertTriangle size={15} />
            <div>
              <strong>{t('Lütfen aşağıdaki alanları kontrol edin:', 'Please review the following issues:')}</strong>
              <ul>
                {errorMessages.map((msg, idx) => (
                  <li key={idx}>{msg}</li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Body */}
        <div className="wizard-body">
          {step === 1 && (
            <div className="wizard-step-panel">
              <div className="wizard-section-top">
                <div>
                  <h3>{t('Hızlı Başlangıç Şablonu (Opsiyonel)', 'Starter Preset (Optional)')}</h3>
                  <p>{t('Hazır bir yapıyı temel alıp üzerine düzenleme yapabilir veya sıfırdan başlayabilirsiniz.', 'Start from an editable preset or from a blank floorplan.')}</p>
                </div>
                <div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".json,application/json"
                    style={{ display: 'none' }}
                    onChange={handleImportJsonFile}
                  />
                  <button
                    type="button"
                    className="wizard-btn-secondary"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    <Upload size={13} />
                    {t('JSON Dosyasından Yükle', 'Import from JSON')}
                  </button>
                </div>
              </div>

              <div className="wizard-preset-grid">
                {presets.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className={`wizard-preset-card ${selectedPreset === p.id ? 'active' : ''}`}
                    onClick={() => applyPreset(p.id)}
                  >
                    <strong>{p.title}</strong>
                    <span>{p.meta}</span>
                  </button>
                ))}
              </div>

              <div className="wizard-form-grid">
                <label className="wizard-field span-2">
                  <span>{t('Proje / Tesis Adı *', 'Project / Facility Name *')}</span>
                  <input
                    type="text"
                    value={projectName}
                    onChange={(e) => setProjectName(e.target.value)}
                    placeholder={t('Örn: Yeni İmalat Holü - Faz 1', 'e.g. New Production Hall - Phase 1')}
                  />
                </label>

                <label className="wizard-field">
                  <span>{t('Tesis Genişliği W (metre) *', 'Facility Width W (m) *')}</span>
                  <input
                    type="number"
                    min={10}
                    max={1000}
                    step={1}
                    value={width}
                    onChange={(e) => setWidth(parseFloat(e.target.value) || 0)}
                  />
                </label>

                <label className="wizard-field">
                  <span>{t('Tesis Derinliği H (metre) *', 'Facility Depth H (m) *')}</span>
                  <input
                    type="number"
                    min={10}
                    max={1000}
                    step={1}
                    value={height}
                    onChange={(e) => setHeight(parseFloat(e.target.value) || 0)}
                  />
                </label>

                <label className="wizard-field">
                  <span>{t('Mesafe Metriği', 'Distance Metric')}</span>
                  <select
                    value={distanceMetric}
                    onChange={(e) => setDistanceMetric(e.target.value as DistanceMetric)}
                  >
                    <option value="rectilinear">{t('Manhattan / Dikdörtgen Koridor (Rectilinear)', 'Rectilinear (Manhattan Corridor)')}</option>
                    <option value="euclidean">{t('Öklid (Kuş Uçuşu Mesafe)', 'Euclidean (Straight-line)')}</option>
                  </select>
                </label>

                <label className="wizard-field">
                  <span>{t('Varsayılan Birim Taşıma Maliyeti', 'Default Unit Transport Cost')}</span>
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    value={defaultCost}
                    onChange={(e) => setDefaultCost(parseFloat(e.target.value) || 0)}
                  />
                </label>
              </div>

              <div className="wizard-area-banner">
                <div>
                  <small>{t('Hesaplanan Brüt Tesis Alanı', 'Computed Gross Facility Area')}</small>
                  <strong>{facilityArea.toLocaleString()} m²</strong>
                  <span>({width || 0} m × {height || 0} m)</span>
                </div>
                <div>
                  <small>{t('Mevcut Şablon Bölüm Sayısı', 'Current Department Count')}</small>
                  <strong>{departments.length} {t('bölüm', 'depts')}</strong>
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="wizard-step-panel">
              <div className="wizard-section-top">
                <div>
                  <h3>{t('Üretim ve Lojistik Bölümleri', 'Production & Logistics Departments')}</h3>
                  <p>
                    {t(
                      'Her bölümün adını, gerekli taban alanını (m²) ve kabul edilebilir en-boy oranlarını belirleyin.',
                      'Specify each department name, required floor area (m²), and allowable aspect ratio limits.'
                    )}
                  </p>
                </div>
                <button
                  type="button"
                  className="wizard-btn-accent"
                  onClick={handleAddDepartment}
                >
                  <Plus size={14} />
                  {t('Bölüm Ekle', 'Add Department')}
                </button>
              </div>

              {/* Capacity Progress Bar */}
              <div className={`wizard-capacity-box ${isOverCapacity ? 'over' : utilizationPct > 92 ? 'tight' : ''}`}>
                <div className="wizard-capacity-head">
                  <span>
                    {t('Alan Kullanım Oranı:', 'Area Utilization:')}{' '}
                    <strong>
                      {totalDeptArea.toLocaleString()} / {facilityArea.toLocaleString()} m² ({utilizationPct.toFixed(1)}%)
                    </strong>
                  </span>
                  <small>
                    {isOverCapacity
                      ? t('Tesis alanı aşıldı!', 'Facility area exceeded!')
                      : utilizationPct > 92
                        ? t('Optimizasyon için %8–%15 boşluk bırakmanız önerilir', 'Recommended to leave 8–15% buffer space')
                        : t('Optimizasyon için uygun boşluk mevcut', 'Healthy headroom for optimization')}
                  </small>
                </div>
                <div className="wizard-capacity-track">
                  <div
                    className="wizard-capacity-fill"
                    style={{ width: `${Math.min(100, Math.max(0, utilizationPct))}%` }}
                  />
                </div>
              </div>

              <div className="wizard-dept-table-wrap">
                <table className="wizard-dept-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>{t('Bölüm Adı', 'Department Name')}</th>
                      <th>{t('Alan (m²)', 'Area (m²)')}</th>
                      <th>{t('Min En-Boy', 'Min Aspect')}</th>
                      <th>{t('Maks En-Boy', 'Max Aspect')}</th>
                      <th aria-label={t('Sil', 'Delete')} />
                    </tr>
                  </thead>
                  <tbody>
                    {departments.map((dept, index) => (
                      <tr key={dept.uid}>
                        <td className="col-idx">DEP_{(index + 1).toString().padStart(2, '0')}</td>
                        <td>
                          <input
                            type="text"
                            value={dept.name}
                            onChange={(e) => handleUpdateDepartment(dept.uid, { name: e.target.value })}
                            placeholder={t('Bölüm adı', 'Department name')}
                          />
                        </td>
                        <td className="col-num">
                          <input
                            type="number"
                            min={1}
                            step={10}
                            value={dept.required_area}
                            onChange={(e) => handleUpdateDepartment(dept.uid, { required_area: parseFloat(e.target.value) || 0 })}
                          />
                        </td>
                        <td className="col-num-sm">
                          <input
                            type="number"
                            min={1}
                            max={10}
                            step={0.1}
                            value={dept.min_aspect_ratio}
                            onChange={(e) => handleUpdateDepartment(dept.uid, { min_aspect_ratio: parseFloat(e.target.value) || 1 })}
                          />
                        </td>
                        <td className="col-num-sm">
                          <input
                            type="number"
                            min={1}
                            max={20}
                            step={0.1}
                            value={dept.max_aspect_ratio}
                            onChange={(e) => handleUpdateDepartment(dept.uid, { max_aspect_ratio: parseFloat(e.target.value) || 1 })}
                          />
                        </td>
                        <td className="col-del">
                          <button
                            type="button"
                            className="wizard-row-del"
                            disabled={departments.length <= 2}
                            title={departments.length <= 2 ? t('En az 2 bölüm gereklidir', 'Minimum 2 departments required') : t('Bölümü sil', 'Remove department')}
                            onClick={() => handleDeleteDepartment(dept.uid)}
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="wizard-step-panel">
              {/* Summary Strip */}
              <div className="wizard-summary-strip">
                <span><strong>{projectName || t('Yeni Tesis', 'New Facility')}</strong></span>
                <span>{width}×{height} m ({facilityArea.toLocaleString()} m²)</span>
                <span>{departments.length} {t('bölüm', 'depts')} · %{utilizationPct.toFixed(1)} {t('doluluk', 'used')}</span>
                <span>{flows.length} {t('akış', 'flows')} · {relationships.length} REL</span>
              </div>

              <div className="wizard-step3-grid">
                {/* Material Flows Column */}
                <div className="wizard-subpanel">
                  <div className="wizard-subpanel-head">
                    <div>
                      <h4>{t('Malzeme Akışları (From-To)', 'Material Flows (From-To)')}</h4>
                      <small>{t('Bölümler arası günlük yük / parça taşıma miktarları', 'Daily load / unit transfers between departments')}</small>
                    </div>
                    <button
                      type="button"
                      className="wizard-btn-secondary"
                      onClick={handleGenerateSequentialFlows}
                    >
                      {t('Sıralı Akış Oluştur (1→2→3...)', 'Auto Sequential Flow (1→2→3...)')}
                    </button>
                  </div>

                  <div className="wizard-inline-adder">
                    <select value={flowSourceUid} onChange={(e) => setFlowSourceUid(e.target.value)} aria-label={t('Kaynak bölüm', 'Source department')}>
                      {departments.map((d, idx) => (
                        <option key={d.uid} value={d.uid}>{idx + 1}. {d.name}</option>
                      ))}
                    </select>
                    <span className="arrow-sep">→</span>
                    <select value={flowTargetUid} onChange={(e) => setFlowTargetUid(e.target.value)} aria-label={t('Hedef bölüm', 'Target department')}>
                      {departments.map((d, idx) => (
                        <option key={d.uid} value={d.uid}>{idx + 1}. {d.name}</option>
                      ))}
                    </select>
                    <input
                      type="number"
                      min={1}
                      value={flowQuantity}
                      onChange={(e) => setFlowQuantity(parseFloat(e.target.value) || 0)}
                      title={t('Miktar (yük/gün)', 'Quantity (loads/day)')}
                      placeholder={t('Miktar', 'Qty')}
                    />
                    <input
                      type="number"
                      min={0}
                      step={0.1}
                      value={flowCost}
                      onChange={(e) => setFlowCost(parseFloat(e.target.value) || 0)}
                      title={t('Birim Maliyet', 'Unit Cost')}
                      placeholder={t('Maliyet', 'Cost')}
                    />
                    <button type="button" className="wizard-btn-accent" onClick={handleAddFlow}>
                      <Plus size={13} />
                      {t('Akış Ekle', 'Add Flow')}
                    </button>
                  </div>

                  <div className="wizard-item-list">
                    {flows.length === 0 ? (
                      <div className="wizard-empty-hint">
                        {t('Henüz malzeme akışı eklenmedi. Yukarıdan ekleyin veya "Sıralı Akış Oluştur" düğmesini kullanın.', 'No flows added yet. Add pairs above or click "Auto Sequential Flow".')}
                      </div>
                    ) : (
                      flows.map((f) => {
                        const src = deptByUid.get(f.sourceUid);
                        const dst = deptByUid.get(f.targetUid);
                        return (
                          <div key={f.id} className="wizard-list-row">
                            <span className="pair-text">
                              <strong>{src?.name || f.sourceUid}</strong> → <strong>{dst?.name || f.targetUid}</strong>
                            </span>
                            <span className="pair-meta">
                              {f.quantity} {t('yük/gün', 'loads/day')} · c={f.cost_per_unit_distance}
                            </span>
                            <button
                              type="button"
                              className="wizard-row-del"
                              onClick={() => setFlows((prev) => prev.filter((item) => item.id !== f.id))}
                              aria-label={t('Akışı sil', 'Remove flow')}
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>

                {/* Closeness Relationships Column */}
                <div className="wizard-subpanel">
                  <div className="wizard-subpanel-head">
                    <div>
                      <h4>{t('Yakınlık İlişkileri (REL)', 'Closeness Relationships (REL)')}</h4>
                      <small>{t('A: Mutlaka Yakın (+16) · E: Çok Önemli (+8) · I: Önemli (+4) · O: Olağan (+2) · X: Uzak Tutulmalı (-8)', 'A: +16 · E: +8 · I: +4 · O: +2 · X: Undesirable (-8)')}</small>
                    </div>
                  </div>

                  <div className="wizard-inline-adder rel">
                    <select value={relAUid} onChange={(e) => setRelAUid(e.target.value)} aria-label={t('Bölüm A', 'Department A')}>
                      {departments.map((d, idx) => (
                        <option key={d.uid} value={d.uid}>{idx + 1}. {d.name}</option>
                      ))}
                    </select>
                    <span className="arrow-sep">↔</span>
                    <select value={relBUid} onChange={(e) => setRelBUid(e.target.value)} aria-label={t('Bölüm B', 'Department B')}>
                      {departments.map((d, idx) => (
                        <option key={d.uid} value={d.uid}>{idx + 1}. {d.name}</option>
                      ))}
                    </select>
                    <select value={relGrade} onChange={(e) => setRelGrade(e.target.value as RelGrade)} aria-label={t('İlişki Derecesi', 'REL Grade')}>
                      <option value="A">A (+16 · {t('Kesinlikle Yakın', 'Abs. Necessary')})</option>
                      <option value="E">E (+8 · {t('Çok Önemli', 'Esp. Important')})</option>
                      <option value="I">I (+4 · {t('Önemli', 'Important')})</option>
                      <option value="O">O (+2 · {t('Olağan', 'Ordinary')})</option>
                      <option value="X">X (-8 · {t('Uzak Tutulmalı', 'Undesirable')})</option>
                    </select>
                    <button type="button" className="wizard-btn-accent" onClick={handleAddRelationship}>
                      <Plus size={13} />
                      {t('İlişki Ekle', 'Add REL')}
                    </button>
                  </div>

                  <div className="wizard-item-list">
                    {relationships.length === 0 ? (
                      <div className="wizard-empty-hint">
                        {t('Opsiyonel: Birlikte olması gereken (A/E) veya ayrılması gereken (X) bölümleri tanımlayabilirsiniz.', 'Optional: Define departments that must stay close (A/E) or separated (X).')}
                      </div>
                    ) : (
                      relationships.map((r) => {
                        const a = deptByUid.get(r.deptAUid);
                        const b = deptByUid.get(r.deptBUid);
                        const badgeStyle = REL_COLOR_MAP[r.grade];
                        return (
                          <div key={r.id} className="wizard-list-row">
                            <span
                              className="rel-grade-badge"
                              style={{
                                background: badgeStyle.bg,
                                borderColor: badgeStyle.border,
                                color: badgeStyle.text,
                              }}
                            >
                              {r.grade} ({REL_SCORE_MAP[r.grade] > 0 ? `+${REL_SCORE_MAP[r.grade]}` : REL_SCORE_MAP[r.grade]})
                            </span>
                            <span className="pair-text">
                              <strong>{a?.name || r.deptAUid}</strong> ↔ <strong>{b?.name || r.deptBUid}</strong>
                            </span>
                            <button
                              type="button"
                              className="wizard-row-del"
                              onClick={() => setRelationships((prev) => prev.filter((item) => item.id !== r.id))}
                              aria-label={t('İlişkiyi sil', 'Remove relationship')}
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="wizard-footer">
          <button
            type="button"
            className="wizard-btn-secondary"
            disabled={submitting}
            onClick={() => {
              if (step === 1) onClose();
              else {
                setErrorMessages([]);
                setStep((s) => (s === 3 ? 2 : 1));
              }
            }}
          >
            {step === 1 ? (
              t('İptal', 'Cancel')
            ) : (
              <>
                <ArrowLeft size={13} />
                {t('Geri', 'Back')}
              </>
            )}
          </button>

          <div className="wizard-footer-right">
            {step < 3 ? (
              <button
                type="button"
                className="cockpit-btn-primary"
                onClick={goNextStep}
              >
                {t('Devam Et', 'Continue')}
                <ArrowRight size={13} />
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="wizard-btn-secondary"
                  disabled={submitting}
                  onClick={() => void handleFinish(false)}
                >
                  {submitting ? t('Doğrulanıyor...', 'Validating...') : t('Projeyi Oluştur', 'Create Project')}
                </button>
                <button
                  type="button"
                  className="cockpit-btn-primary"
                  disabled={submitting}
                  onClick={() => void handleFinish(true)}
                >
                  <Sparkles size={13} />
                  {submitting
                    ? t('Oluşturuluyor...', 'Creating...')
                    : t('Oluştur ve Hemen Optimize Et', 'Create & Optimize Now')}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
