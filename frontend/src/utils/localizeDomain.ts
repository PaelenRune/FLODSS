export type TranslateFn = (tr: string, en: string) => string;

const BENCHMARK_DEPT_NAME_TR: Record<string, string> = {
  // sample_academic_4.json
  'Milling': 'Frezeleme',
  'Drilling': 'Delme',
  'Welding': 'Kaynak',
  'Storage': 'Depolama',

  // sample_expansion_8.json
  'Raw Material Staging': 'Hammadde Hazırlık',
  'Machining Cell': 'Talaşlı İmalat Hücresi',
  'Heat Treatment': 'Isıl İşlem',
  'Quality Inspection': 'Kalite Kontrol',
  'Sub-Assembly': 'Alt Montaj',
  'Final Integration': 'Son Entegrasyon',
  'Packaging & Kitting': 'Paketleme ve Kit Hazırlama',
  'Finished Goods Warehouse': 'Mamul Deposu',

  // sample_logistics_5.json
  'Inbound Receiving Docks': 'Mal Kabul Rampaları',
  'Automated Parcel Sorting': 'Otomatik Koli Ayrıştırma',
  'High-Bay Racked Storage': 'Yüksek Raflı Depolama',
  'Order Consolidation & Packing': 'Sipariş Birleştirme ve Paketleme',
  'Outbound Shipping Staging': 'Sevkiyat Hazırlık Alanı',

  // sample_medium_plant.json
  'Receiving & Raw Inventory': 'Mal Kabul ve Hammadde Stoğu',
  'Machining & Fabrication': 'Talaşlı İmalat ve İmalat',
  'Mechanical Assembly': 'Mekanik Montaj',
  'Quality & Inspection': 'Kalite ve Muayene',
  'Packaging & Boxing': 'Paketleme ve Kutulama',
  'Warehousing & Shipping': 'Depolama ve Sevkiyat',

  // sample_plant.json
  'Raw Material Warehouse & Sheet Storage': 'Hammadde Deposu ve Sac Stoklama',
  'Laser Cutting & Sawing Cell': 'Lazer Kesim ve Testere Hücresi',
  'CNC Milling & Turning Center': 'CNC Freze ve Torna Merkezi',
  'Robotic & Manual Welding Shop': 'Robotik ve Manuel Kaynak Atölyesi',
  'Surface Treatment & Powder Coating': 'Yüzey İşlem ve Toz Boya',
  'Main Assembly Line & Subassembly': 'Ana Montaj Hattı ve Alt Montaj',
  'Quality Assurance & Metrology Lab': 'Kalite Güvence ve Metroloji Lab.',
  'Finished Goods Warehouse & Packaging': 'Mamul Deposu ve Paketleme',
  'Tooling & Maintenance Workshop': 'Kalıp ve Bakım Atölyesi',
  'Outbound Shipping & Staging Docks': 'Sevkiyat ve Yükleme Rampaları',

  // synthetic_constrained_factory_12.json
  'Main Logistics Intake Gate': 'Ana Lojistik Giriş Kapısı',
  'Heavy Stamping Press Cell': 'Ağır Pres ve Şekillendirme Hücresi',
  '5-Axis CNC Machining': '5 Eksenli CNC İşleme',
  'Automated Welding Cell': 'Otomatik Kaynak Hücresi',
  'Part Washing & Degreasing': 'Parça Yıkama ve Yağ Alma',
  'Powder Coating & Painting': 'Toz Boya ve Boyama',
  'Chassis Sub-Assembly': 'Şasi Alt Montajı',
  'Electrical Harness Line': 'Elektrik Kablo Demeti Hattı',
  'Final Conveyor Assembly': 'Konveyörlü Son Montaj',
  'Optical Metrology & QC': 'Optik Metroloji ve Kalite Kontrol',
  'Boxing & Wrapping Cell': 'Kutulama ve Sarma Hücresi',
  'Outbound Logistics Dock': 'Sevkiyat Lojistik Rampası',

  // synthetic_high_density_15.json
  'Receiving Dock': 'Mal Kabul Rampası',
  'Raw Material Warehouse': 'Hammadde Deposu',
  'Heavy Machining Cell 1': 'Ağır Talaşlı İmalat Hücresi 1',
  'Heavy Machining Cell 2': 'Ağır Talaşlı İmalat Hücresi 2',
  'Light Milling & Drilling': 'Hafif Freze ve Delme',
  'Sheet Metal Stamping': 'Sac Metal Presleme',
  'Robotic Welding Bay': 'Robotik Kaynak Bölümü',
  'Heat Treatment Furnaces': 'Isıl İşlem Fırınları',
  'Surface Finishing & Paint': 'Yüzey İşlem ve Boya',
  'Quality Control & CMM': 'Kalite Kontrol ve CMM',
  'Sub-Assembly Line A': 'Alt Montaj Hattı A',
  'Sub-Assembly Line B': 'Alt Montaj Hattı B',
  'Final System Assembly': 'Son Sistem Montajı',
  'Packaging & Crating': 'Paketleme ve Sandıklama',
  'Shipping & Logistics Dock': 'Sevkiyat ve Lojistik Rampası',

  // synthetic_high_density_20.json
  'Inbound Logistics Hub': 'Giriş Lojistik Merkezi',
  'Raw Steel Storage Bay A': 'Ham Çelik Depo Alanı A',
  'Raw Alloy Storage Bay B': 'Ham Alaşım Depo Alanı B',
  'Sawing & Blank Preparation': 'Kesim ve Taslak Hazırlık',
  'CNC Milling Cell': 'CNC Freze Hücresi',
  'CNC Turning Lathe Cell': 'CNC Torna Hücresi',
  'Precision Cylindrical Grinding': 'Hassas Silindirik Taşlama',
  'Heavy Hydraulic Stamping': 'Ağır Hidrolik Presleme',
  'Robotic Seam Welding': 'Robotik Dikiş Kaynağı',
  'Manual TIG/MIG Welding': 'Manuel TIG/MIG Kaynağı',
  'Industrial Degreasing & Wash': 'Endüstriyel Yağ Alma ve Yıkama',
  'Annealing & Heat Treatment': 'Tavlama ve Isıl İşlem',
  'Electroplating & Protective Coating': 'Elektrokaplama ve Koruyucu Kaplama',
  'Cleanroom Precision Assembly': 'Temiz Oda Hassas Montajı',
  'Sub-Assembly Module 1': 'Alt Montaj Modülü 1',
  'Sub-Assembly Module 2': 'Alt Montaj Modülü 2',
  'Final System Integration': 'Son Sistem Entegrasyonu',
  'Coordinate Metrology & Testing': 'Koordinat Metroloji ve Test',
  'Automated Packaging Cell': 'Otomatik Paketleme Hücresi',
  'Outbound Logistics Hub': 'Çıkış Lojistik Merkezi',

  // synthetic_logistics_factory_15.json
  'Primary Inbound Docks': 'Ana Mal Kabul Rampaları',
  'Bulk High-Bay Storage': 'Yüksek Raflı Yığın Depo',
  'De-Vanning & De-Palletizing': 'Boşaltma ve Palet Bozma',
  'Component Kitting & Sort': 'Bileşen Kitleme ve Ayrıştırma',
  'Surface Mount Line 1': 'Yüzey Montaj (SMT) Hattı 1',
  'Surface Mount Line 2': 'Yüzey Montaj (SMT) Hattı 2',
  'Robotic Insertion Cell': 'Robotik Dizgi Hücresi',
  'Selective Wave Soldering': 'Seçici Dalga Lehimleme',
  'Automated ICT & Burn-in': 'Otomatik ICT ve Burn-in Test',
  'Box-Build Final Assembly': 'Kasa İçi Son Montaj',
  'Retail Packaging Line': 'Perakende Paketleme Hattı',
  'Finished Goods Automated Bay': 'Otomatik Mamul Deposu',
  'Cross-Dock Dispatch Bays': 'Çapraz Sevkiyat Peronları',
  'Reverse Logistics & RMA': 'Tersine Lojistik ve İade (RMA)',
  'Facility Maintenance Central': 'Merkez Tesis Bakım',
};

const BENCHMARK_TEXT_TR: Record<string, string> = {
  // Problem names
  'Academic Hand-Calculated Problem (4 Departments)': 'Akademik El Hesabı Problemi (4 Bölüm)',
  'Industrial Facility Expansion (8 Departments)': 'Endüstriyel Tesis Genişletme (8 Bölüm)',
  'E-Commerce Fulfillment & Logistics Hub (5 Departments)': 'E-Ticaret Sipariş Karşılama ve Lojistik Merkezi (5 Bölüm)',
  'Medium Manufacturing & Assembly Facility (6 Departments)': 'Orta Ölçekli Üretim ve Montaj Tesisi (6 Bölüm)',
  'Precision Machinery Manufacturing Plant (10 Departments)': 'Hassas Makine Üretim Tesisi (10 Bölüm)',
  'Precision Machinery Manufacturing Plant': 'Hassas Makine Üretim Tesisi',
  'Synthetic Constrained Plant with Spine Corridor & Fixed Dock (12 Departments)': 'Ana Koridor ve Sabit Rampalı Kısıtlı Tesis (12 Bölüm)',
  'Synthetic High-Density Heavy Machinery Plant (15 Departments)': 'Yüksek Yoğunluklu Ağır Makine Tesisi (15 Bölüm)',
  'Synthetic High-Density Advanced Manufacturing Complex (20 Departments)': 'Yüksek Yoğunluklu İleri Üretim Kompleksi (20 Bölüm)',
  'Synthetic High-Throughput Electronics Logistics & Assembly Plant (15 Departments)': 'Yüksek Kapasiteli Elektronik Lojistik ve Montaj Tesisi (15 Bölüm)',

  // Facility names
  'Test Plant': 'Test Tesisi',
  'Phase 2 Expansion Plant': '2. Aşama Genişleme Tesisi',
  'Rapid Fulfillment Center': 'Hızlı Sipariş Karşılama Merkezi',
  'Medium Discrete Assembly Hall': 'Orta Ölçekli Kesikli Montaj Holü',
  'Heavy Equipment Advanced Production Hall': 'Ağır Makine İleri Üretim Holü',
  'Constrained Industrial Facility': 'Kısıtlı Endüstriyel Tesis',
  'Heavy Machinery Plant': 'Ağır Makine Tesisi',
  'Advanced Manufacturing Complex': 'İleri Üretim Kompleksi',
  'Electronics Contract Assembly Facility': 'Elektronik Sözleşmeli Montaj Tesisi',
};

export function localizeDepartmentName(
  name: string | undefined,
  t: TranslateFn
): string {
  if (!name) return '';
  const trimmed = name.trim();
  const trName = BENCHMARK_DEPT_NAME_TR[trimmed];
  return trName ? t(trName, name) : name;
}

export function localizeBenchmarkText(
  text: string | undefined,
  t: TranslateFn
): string {
  if (!text) return '';
  const trimmed = text.trim();
  const trText = BENCHMARK_TEXT_TR[trimmed];
  return trText ? t(trText, text) : text;
}

const SHORT_DEPT_LABEL_TR: Record<string, [string, string]> = {
  DEP_RAW_MATERIAL: ['Hammadde', 'Raw Mat.'],
  DEP_CUTTING: ['Kesim', 'Cutting'],
  DEP_MACHINING: ['CNC', 'CNC'],
  DEP_WELDING: ['Kaynak', 'Welding'],
  DEP_SURFACE_TREAT: ['Boya', 'Coating'],
  DEP_ASSEMBLY: ['Montaj', 'Assembly'],
  DEP_QUALITY: ['Kalite', 'Quality'],
  DEP_FINISHED_GOODS: ['Mamul', 'Finished'],
  DEP_MAINTENANCE: ['Bakım', 'Maint.'],
  DEP_SHIPPING: ['Sevkiyat', 'Shipping'],
  ST: ['Hammadde', 'Storage'],
  MC: ['İmalat', 'Machining'],
  AS: ['Montaj', 'Assembly'],
  PK: ['Paketleme', 'Packing'],
  LG: ['Sevkiyat', 'Logistics'],
};

export function getShortDepartmentLabel(
  dept: { id: string; name: string },
  t: TranslateFn
): string {
  const mapped = SHORT_DEPT_LABEL_TR[dept.id];
  if (mapped) return t(mapped[0], mapped[1]);
  const full = localizeDepartmentName(dept.name, t).trim();
  if (!full) return dept.id.replace(/^DEP_/, '');
  const words = full.replace(/&/g, ' ').trim().split(/\s+/);
  if (words.length >= 2 && words[0].length <= 3) {
    return `${words[0]} ${words[1]}`.slice(0, 12);
  }
  return words[0].slice(0, 11);
}
