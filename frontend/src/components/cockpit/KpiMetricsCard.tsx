import { TrendingUp, Scan, Route, Wallet } from 'lucide-react';
import { percentageDelta, useCockpitData } from './CockpitDataContext';
import { useLanguage } from '../../context/LanguageContext';

export function KpiMetricsCard({ scenario }: { scenario: number }) {
  const { t } = useLanguage();
  const { live, departments, evaluation, metrics, baselineMetrics } = useCockpitData();
  const format = (value: number | undefined) => (value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
  const distance = evaluation?.flow_distance ?? metrics?.flowDistance ?? 0;
  const cost = evaluation?.material_handling_cost ?? metrics?.handlingCost ?? 0;
  const metricLabel = metrics?.metric === 'euclidean'
    ? t('Öklid', 'euclidean')
    : metrics?.metric === 'manhattan' || !metrics?.metric
      ? t('Manhattan', 'manhattan')
      : metrics.metric;
  const source = `${evaluation ? t('Değerlendirildi', 'Evaluated') : t('İstemci tahmini', 'Client estimate')} · ${metricLabel}${metrics?.missingFlows ? t(` · kısmi: ${metrics.missingFlows} yerleşmemiş akış hariç`, ` · partial: ${metrics.missingFlows} unplaced flows excluded`) : ''}`;
  const zeroLabel = t('yeni (sıfır taban)', 'new (zero baseline)');
  const vsBaseline = t('Temel Yerleşime göre', 'vs Baseline');
  const cards = live ? [
    { title: t('Yerleşim uygunluğu', 'Layout feasibility'), value: evaluation ? (evaluation.is_feasible ? t('Uygun', 'Feasible') : t('Uygun Değil', 'Infeasible')) : t('Bekliyor', 'Pending'), sub: t('Sunucu değerlendirmesi', 'Backend evaluation'), color: '#00f0ff', icon: TrendingUp },
    { title: t('Alan kullanımı', 'Area utilization'), value: `${format(departments.reduce((sum, d) => sum + d.share, 0))}%`, sub: t('Tahsis edilen / tesis alanı (brüt)', 'Allocated / facility area (gross)'), color: '#8b5cf6', icon: Scan },
    { title: t('Akış ağırlıklı mesafe', 'Flow-weighted distance'), value: format(distance), sub: `${percentageDelta(metrics?.flowDistance ?? 0, baselineMetrics?.flowDistance ?? 0, zeroLabel)} ${vsBaseline} · ${source}`, color: '#10b981', icon: Route },
    { title: t('Taşıma maliyeti', 'Handling cost'), value: format(cost), sub: `${percentageDelta(metrics?.handlingCost ?? 0, baselineMetrics?.handlingCost ?? 0, zeroLabel)} ${vsBaseline} · ${source}`, color: '#f59e0b', icon: Wallet },
  ] : [
    { title: t('Akış verimliliği', 'Flow efficiency'), value: ['0%', '+42%', '+27%'][scenario], sub: vsBaseline, color: '#00f0ff', icon: TrendingUp },
    { title: t('Alan kullanımı', 'Area utilization'), value: ['0%', '+28%', '+18%'][scenario], sub: scenario === 1 ? t('%94 dolu', '94% occupied') : t('Referans karşılaştırma', 'Reference comparison'), color: '#8b5cf6', icon: Scan },
    { title: t('Malzeme akış mesafesi', 'Material flow distance'), value: ['0%', '-35%', '-24%'][scenario], sub: [t('2.180 m/gün', '2,180 m/day'), t('1.420 m/gün', '1,420 m/day'), t('1.650 m/gün', '1,650 m/day')][scenario], color: '#10b981', icon: Route },
    { title: t('Taşıma maliyeti', 'Handling cost'), value: ['0%', '-19%', '-14%'][scenario], sub: scenario === 1 ? t('$3,210/ay tasarruf*', '$3,210/month saved*') : vsBaseline, color: '#f59e0b', icon: Wallet },
  ];
  return <div className="cockpit-kpis">{cards.map(({ title, value, sub, color, icon: Icon }) => <article className="cockpit-kpi" key={title} style={{ '--metric-color': color } as React.CSSProperties}>
    <div className="kpi-label"><span>{title}</span><Icon size={16} /></div><strong>{value}</strong><span className="cockpit-muted">{sub}</span><svg viewBox="0 0 130 25" aria-hidden="true"><path d="M0 23 L15 20 L28 22 L40 13 L54 17 L67 10 L80 12 L94 5 L108 8 L130 1" /></svg>
  </article>)}</div>;
}
