import { TrendingUp, Scan, Route, Wallet } from 'lucide-react';
import { percentageDelta, useCockpitData } from './CockpitDataContext';

export function KpiMetricsCard({ scenario }: { scenario: number }) {
  const { live, departments, evaluation, metrics, baselineMetrics } = useCockpitData();
  const format = (value: number | undefined) => (value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 });
  const distance = evaluation?.flow_distance ?? metrics?.flowDistance ?? 0;
  const cost = evaluation?.material_handling_cost ?? metrics?.handlingCost ?? 0;
  const source = `${evaluation ? 'Evaluated' : 'Client estimate'} · ${metrics?.metric ?? 'manhattan'}${metrics?.missingFlows ? ` · partial: ${metrics.missingFlows} unplaced flows excluded` : ''}`;
  const cards = live ? [
    { title: 'Layout feasibility', value: evaluation ? (evaluation.is_feasible ? 'Feasible' : 'Infeasible') : 'Pending', sub: 'Backend evaluation', color: '#00f0ff', icon: TrendingUp },
    { title: 'Area utilization', value: `${format(departments.reduce((sum, d) => sum + d.share, 0))}%`, sub: 'Allocated / facility area (gross)', color: '#8b5cf6', icon: Scan },
    { title: 'Flow-weighted distance', value: format(distance), sub: `${percentageDelta(metrics?.flowDistance ?? 0, baselineMetrics?.flowDistance ?? 0)} vs Baseline · ${source}`, color: '#10b981', icon: Route },
    { title: 'Handling cost', value: format(cost), sub: `${percentageDelta(metrics?.handlingCost ?? 0, baselineMetrics?.handlingCost ?? 0)} vs Baseline · ${source}`, color: '#f59e0b', icon: Wallet },
  ] : [
    { title: 'Flow efficiency', value: ['0%', '+42%', '+27%'][scenario], sub: 'vs Baseline', color: '#00f0ff', icon: TrendingUp },
    { title: 'Area utilization', value: ['0%', '+28%', '+18%'][scenario], sub: scenario === 1 ? '94% occupied' : 'Reference comparison', color: '#8b5cf6', icon: Scan },
    { title: 'Material flow distance', value: ['0%', '-35%', '-24%'][scenario], sub: ['2,180 m/day', '1,420 m/day', '1,650 m/day'][scenario], color: '#10b981', icon: Route },
    { title: 'Handling cost', value: ['0%', '-19%', '-14%'][scenario], sub: scenario === 1 ? '$3,210/month saved*' : 'vs Baseline', color: '#f59e0b', icon: Wallet },
  ];
  return <div className="cockpit-kpis">{cards.map(({ title, value, sub, color, icon: Icon }) => <article className="cockpit-kpi" key={title} style={{ '--metric-color': color } as React.CSSProperties}>
    <div className="kpi-label"><span>{title}</span><Icon size={16} /></div><strong>{value}</strong><span className="cockpit-muted">{sub}</span><svg viewBox="0 0 130 25" aria-hidden="true"><path d="M0 23 L15 20 L28 22 L40 13 L54 17 L67 10 L80 12 L94 5 L108 8 L130 1" /></svg>
  </article>)}</div>;
}
