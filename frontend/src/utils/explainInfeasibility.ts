import type {
  ContinuousLayout,
  EvaluationReport,
  FacilityLayoutProblem,
  LayoutValidationResult,
} from '../types/api';

export interface InfeasibilitySummary {
  status: 'feasible' | 'partial' | 'infeasible';
  headline: string;
  misleadingCostNote: string;
  reasons: string[];
  technicalDetails?: string;
}

export function summarizeLayoutInfeasibility(
  problem: FacilityLayoutProblem | null,
  layout: ContinuousLayout | null,
  validation: LayoutValidationResult | null | undefined,
  evaluation: EvaluationReport | null | undefined,
  missingFlows: number,
  t: (tr: string, en: string) => string
): InfeasibilitySummary {
  if (!problem || !layout) {
    return { status: 'feasible', headline: '', misleadingCostNote: '', reasons: [] };
  }

  const totalDepts = problem.departments.length;
  const placedDepts = Object.keys(layout.placements ?? {}).length;
  const unplacedCount = Math.max(0, totalDepts - placedDepts);
  const isPartial = placedDepts < totalDepts || missingFlows > 0;

  const rawErrors: string[] = [];
  if (validation?.errors) rawErrors.push(...validation.errors);
  if (evaluation?.hard_constraint_violations) rawErrors.push(...evaluation.hard_constraint_violations);
  if (evaluation?.constraint_violations) {
    for (const cv of evaluation.constraint_violations) {
      if (cv.classification === 'hard' && cv.description) {
        rawErrors.push(cv.description);
      }
    }
  }

  const overlapCount = rawErrors.filter((e) => /overlap/i.test(e)).length;
  const hasOverlapArea = (validation?.total_overlap_area ?? 0) > 0.01;
  const dimCount = rawErrors.filter((e) => /aspect ratio|minimum width|maximum width|minimum height|maximum height/i.test(e)).length;
  const boundaryCount = rawErrors.filter((e) => /boundary|exceeds facility|outside/i.test(e)).length;
  const zoneOrFixedCount = rawErrors.filter((e) => /reserved|fixed|exclusion|zone/i.test(e)).length;
  const missingMsgCount = rawErrors.filter((e) => /missing placement/i.test(e)).length;

  const hasHardInvalid =
    validation?.is_valid === false ||
    evaluation?.is_feasible === false ||
    (evaluation?.hard_violation_count ?? 0) > 0 ||
    hasOverlapArea ||
    rawErrors.length > 0;

  if (!isPartial && !hasHardInvalid) {
    return { status: 'feasible', headline: '', misleadingCostNote: '', reasons: [] };
  }

  const reasons: string[] = [];
  if (isPartial || missingMsgCount > 0) {
    reasons.push(
      t(
        `${Math.max(1, unplacedCount)} bölüm tesise sığdırılamadı (${placedDepts}/${totalDepts}); bu nedenle ${missingFlows} akış maliyet hesabına dahil edilmedi.`,
        `${Math.max(1, unplacedCount)} department(s) could not fit inside the facility (${placedDepts}/${totalDepts}); ${missingFlows} flows were excluded from cost.`
      )
    );
  }
  if (overlapCount > 0 || hasOverlapArea) {
    const countLabel = overlapCount > 0 ? `${overlapCount} ` : '';
    reasons.push(
      t(
        `${countLabel}adet bölüm çakışması tespit edildi (bölümler üst üste bindiği için mesafe yapay olarak küçülür).`,
        `${countLabel}department overlap(s) detected (distances become artificially small when blocks overlap).`
      )
    );
  }
  if (dimCount > 0) {
    reasons.push(
      t(
        `${dimCount} adet boyut veya en-boy oranı kısıtı ihlal edildi (aşırı ince/uzun veya sınır dışı dikdörtgenler oluştu).`,
        `${dimCount} dimension or aspect-ratio constraint(s) violated (excessively narrow/elongated blocks formed).`
      )
    );
  }
  if (boundaryCount > 0) {
    reasons.push(
      t(
        'Bazı bölümler tesis sınırlarının dışına taştı.',
        'One or more departments extend beyond the facility boundary.'
      )
    );
  }
  if (zoneOrFixedCount > 0) {
    reasons.push(
      t(
        'Sabit konum veya yasaklı bölge kısıtı ihlal edildi.',
        'Fixed position or reserved exclusion zone constraint violated.'
      )
    );
  }
  if (reasons.length === 0) {
    reasons.push(
      t(
        'Çözüm bir veya daha fazla kesin kısıtı sağlamadı.',
        'The layout failed to satisfy one or more hard constraints.'
      )
    );
  }

  const uniqueDetails = Array.from(new Set(rawErrors.map((s) => s.trim()).filter(Boolean)));
  const technicalDetails = uniqueDetails.length > 0 ? uniqueDetails.slice(0, 12).join('\n') : undefined;

  if (isPartial) {
    return {
      status: 'partial',
      headline: t('Eksik yerleşim — gerçek çözüm değildir', 'Incomplete layout — not a valid full solution'),
      misleadingCostNote: t(
        'Tüm bölümler yerleşmediği için gösterilen maliyet yanıltıcıdır; geçerli çözümlerle kıyaslanmamalıdır.',
        'Displayed cost is misleading because not all departments are placed; do not compare against valid layouts.'
      ),
      reasons,
      technicalDetails,
    };
  }

  return {
    status: 'infeasible',
    headline: t('Geçersiz çözüm — gerçekte uygulanamaz', 'Invalid solution — not physically buildable'),
    misleadingCostNote: t(
      'Çakışma veya kısıt ihlalleri nedeniyle gösterilen taşıma maliyeti yanıltıcıdır; gerçek bir çözüm değildir.',
      'Displayed handling cost is misleading due to overlaps or constraint violations; this is not a buildable layout.'
    ),
    reasons,
    technicalDetails,
  };
}

export function summarizeSolverError(
  rawMessage: string,
  t: (tr: string, en: string) => string
): string {
  const msg = (rawMessage || '').trim();
  if (!msg) {
    return t(
      'Çözücü bu problem üzerinde geçerli bir yerleşim üretemeden durdu.',
      'The solver stopped before finding a valid layout for this problem.'
    );
  }
  if (/overlap/i.test(msg)) {
    return t(
      'Başlangıç veya ara planda çakışan bölümler bulunduğu için algoritma iyileştirmeye geçemedi.',
      'The algorithm could not proceed because departments overlap in the input or intermediate layout.'
    );
  }
  if (/missing|incomplete|placed/i.test(msg)) {
    return t(
      'Yüksek doluluk veya boyut kısıtları nedeniyle tüm bölümler tesise yerleştirilemedi.',
      'Not all departments could be placed due to high density or dimension constraints.'
    );
  }
  if (/aspect ratio|min_width|max_width|min_height|max_height/i.test(msg)) {
    return t(
      'Bölümler için belirlenen en-boy oranı veya genişlik/yükseklik sınırları içinde çözüm bulunamadı.',
      'No placement could satisfy all department aspect-ratio or width/height bounds.'
    );
  }
  if (/timeout|time limit|runtime/i.test(msg)) {
    return t(
      'Ayrılan zaman bütçesi dolduğu için arama erken durduruldu; bütçeyi artırmayı deneyin.',
      'The search stopped when the time budget expired; try increasing the time limit.'
    );
  }
  if (/density|capacity|exceeds/i.test(msg)) {
    return t(
      'Tesis alanı veya doluluk oranı seçilen algoritmanın sığdırabileceği sınırı aşıyor.',
      'Facility area density exceeds what this solver can pack cleanly.'
    );
  }
  if (/failed to fetch|network|econnrefused/i.test(msg)) {
    return t(
      'Çözücü sunucusuna (backend API) bağlanılamadı; yerel sunucunun çalıştığından emin olun.',
      'Could not reach the backend solver API; verify the local server is running.'
    );
  }
  if (/422|validation/i.test(msg)) {
    return t(
      'Problem veya başlangıç yerleşimi verisi sunucu kısıt doğrulamasını geçemedi.',
      'Problem or initial layout payload failed server constraint validation.'
    );
  }
  if (/infeasible/i.test(msg)) {
    return t(
      'Algoritma tüm kesin kısıtları aynı anda sağlayan uygulanabilir bir plan üretemedi.',
      'The algorithm could not produce a feasible plan satisfying all hard constraints.'
    );
  }
  return msg.length <= 160
    ? msg
    : t(
        'Çözücü beklenmeyen bir kısıt veya geometri hatası nedeniyle durdu (ayrıntılar aşağıda).',
        'The solver stopped due to a constraint or geometry error (details below).'
      );
}
