import { TrendingUp, Scan, Route, Wallet } from 'lucide-react';

export function KpiMetricsCard({ scenario }: { scenario: number }) {
  const metrics = [
    { title: 'Flow efficiency', value: ['0%', '+42%', '+27%'][scenario], sub: 'vs Baseline', color: '#00f0ff', icon: TrendingUp },
    { title: 'Area utilization', value: ['0%', '+28%', '+18%'][scenario], sub: scenario === 1 ? '94% occupied' : 'Reference comparison', color: '#8b5cf6', icon: Scan },
    { title: 'Material flow distance', value: ['0%', '-35%', '-24%'][scenario], sub: ['2,180 m/day', '1,420 m/day', '1,650 m/day'][scenario], color: '#10b981', icon: Route },
    { title: 'Handling cost', value: ['0%', '-19%', '-14%'][scenario], sub: scenario === 1 ? '$3,210/month saved*' : 'vs Baseline', color: '#f59e0b', icon: Wallet },
  ];
  return <div className="cockpit-kpis">{metrics.map(({ title, value, sub, color, icon: Icon }) => <article className="cockpit-kpi" key={title} style={{ '--metric-color': color } as React.CSSProperties}>
    <div className="kpi-label"><span>{title}</span><Icon size={16} /></div><strong>{value}</strong><span className="cockpit-muted">{sub}</span><svg viewBox="0 0 130 25" aria-hidden="true"><path d="M0 23 L15 20 L28 22 L40 13 L54 17 L67 10 L80 12 L94 5 L108 8 L130 1" /></svg>
  </article>)}</div>;
}
