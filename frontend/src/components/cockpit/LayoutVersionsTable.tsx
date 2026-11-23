import { Download, Check } from 'lucide-react';
import { scenarios } from './data';
import { calculateFlowMetrics, percentageDelta, useCockpitData } from './CockpitDataContext';
import { useLanguage } from '../../context/LanguageContext';

export function LayoutVersionsTable({ selected, onSelect }: { selected: number; onSelect: (id: number) => void }) {
  const { t } = useLanguage();
  const { live, layout, problem, scenarios: liveScenarios = [], selectedScenario, selectScenario, baselineMetrics, metricConfig } = useCockpitData();
  const formatLiveScenarioName = (name: string) => {
    if (name === 'Baseline Layout') return t('İlk yerleşim', 'Baseline Layout');
    if (name.startsWith('Solver Layout · ')) {
      const suffix = name.slice('Solver Layout · '.length).trim();
      if (!suffix || /^continuous(_layout)?$/i.test(suffix)) {
        return t('Optimize edilmiş', 'Optimized layout');
      }
      return suffix;
    }
    if (name.startsWith('Solver Layout #')) {
      return `${t('Optimize edilmiş', 'Optimized')} #${name.slice('Solver Layout #'.length)}`;
    }
    if (name.startsWith('What-If Modified Layout · ')) return `${t('Senaryo Denemesi', 'What-If Modified Layout')} · ${name.slice('What-If Modified Layout · '.length)}`;
    return name;
  };
  const refScenarioNames: Record<string, string> = {
    'Baseline Layout': t('Temel Yerleşim', 'Baseline Layout'),
    'Optimized Layout #1': t('Optimize Edilmiş Yerleşim #1', 'Optimized Layout #1'),
    'Alternative Layout #2': t('Alternatif Yerleşim #2', 'Alternative Layout #2'),
  };
  if (live) {
    const exportLayout = () => {
      if (!layout) return;
      const url = URL.createObjectURL(new Blob([JSON.stringify(layout, null, 2)], { type: 'application/json' }));
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = 'flodss-active-layout.json'; anchor.click(); URL.revokeObjectURL(url);
    };
    const zeroLabel = t('yeni (sıfır taban)', 'new (zero baseline)');
    const baseStats = problem && liveScenarios[0] ? calculateFlowMetrics(problem, liveScenarios[0].layout, metricConfig) : null;
    const basePlaced = liveScenarios[0] ? Object.keys(liveScenarios[0].layout.placements).length : 0;
    const baselineComparable = Boolean(
      problem &&
      baseStats &&
      baseStats.missingFlows === 0 &&
      basePlaced >= problem.departments.length &&
      liveScenarios[0]?.evaluation?.is_feasible !== false
    );
    return <section className="cockpit-panel versions-panel"><div className="panel-heading"><h2>{t('Yerleşim senaryoları karşılaştırması', 'Layout scenarios comparison')}</h2><button className="icon-button" aria-label={t('Aktif kokpit yerleşimini dışa aktar', 'Export active cockpit layout')} disabled={!layout} onClick={exportLayout}><Download size={15}/></button></div><div className="scenario-columns"><span>{t('Senaryo', 'Scenario')}</span><span>{t('Maliyet farkı', 'Cost delta')}</span><span>{t('Mesafe / maliyet', 'Distance / cost')}</span></div>{problem && liveScenarios.map(s => {
      const metrics = calculateFlowMetrics(problem, s.layout, metricConfig);
      const placedCount = Object.keys(s.layout.placements).length;
      const isPartial = metrics.missingFlows > 0 || placedCount < problem.departments.length;
      const isInfeasible = s.evaluation ? !s.evaluation.is_feasible : false;
      const deltaLabel = isPartial
        ? t('Kısmi', 'Partial')
        : isInfeasible
          ? t('Uygun değil', 'Infeasible')
          : (s.id === 0 || baselineComparable)
            ? percentageDelta(metrics.handlingCost, baselineMetrics?.handlingCost ?? 0, zeroLabel)
            : t('Kıyas dışı', 'N/A');
      return <button className={`scenario-row ${selectedScenario === s.id ? 'selected' : ''}`} key={s.id} onClick={() => selectScenario?.(s.id)} aria-pressed={selectedScenario === s.id}><span><b>{formatLiveScenarioName(s.name)}</b><small>{s.id === 0 ? (s.name.startsWith('Solver Layout') ? t('Aktif ilk senaryo', 'Initial session layout') : t('İlk yüklenen yerleşim', 'First loaded layout')) : t('Uygulamak için tıklayın', 'Click to apply')} {selectedScenario === s.id && <Check size={12}/>}</small></span><strong>{deltaLabel}</strong><span>{metrics.flowDistance.toLocaleString(undefined, { maximumFractionDigits: 1 })}<small>{metrics.handlingCost.toLocaleString(undefined, { maximumFractionDigits: 1 })} {t('maliyet birimi', 'cost units')}{isPartial ? t(` · ${placedCount}/${problem.departments.length} bölüm · ${metrics.missingFlows} akış hesap dışı`, ` · ${placedCount}/${problem.departments.length} depts · ${metrics.missingFlows} flows excluded`) : isInfeasible ? t(' · uygun değil', ' · infeasible') : ''}</small></span></button>;
    })}<div className="panel-foot">{liveScenarios.length ? t('Oturum geçmişi · ağırlık merkezi tahminleri · düşük değer daha iyidir', 'Session history · centroid estimates · lower is better') : t('Başlamak için bir çözücü çalıştırın veya bir yerleşim içe aktarın.', 'Run a solver or import a layout to begin.')}</div></section>;
  }
  const download = () => { const blob = new Blob([JSON.stringify({ source: 'FLODSS reference scenario — not a live solver result', ...scenarios[selected] }, null, 2)], { type: 'application/json' }); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'flodss-reference-scenario.json'; a.click(); URL.revokeObjectURL(url); };
  return <section className="cockpit-panel versions-panel"><div className="panel-heading"><h2>{t('Yerleşim senaryoları karşılaştırması', 'Layout scenarios comparison')}</h2><button className="icon-button" aria-label={t('Seçili referans senaryoyu dışa aktar', 'Export selected reference scenario')} onClick={download}><Download size={15} /></button></div><div className="scenario-columns"><span>{t('Senaryo', 'Scenario')}</span><span>{t('Skor', 'Score')}</span><span>{t('Mesafe / maliyet', 'Distance / cost')}</span></div>{scenarios.map((s, i) => <button className={`scenario-row ${selected === i ? 'selected' : ''}`} key={s.name} onClick={() => onSelect(i)} aria-pressed={selected === i}><span><b>{refScenarioNames[s.name] ?? s.name}</b><small>{i === 1 ? t('Önerilen', 'Recommended') : i === 0 ? t('Orijinal yapılandırma', 'Original configuration') : t('Dengeli alternatif', 'Balanced alternative')} {selected === i && <Check size={12} />}</small></span><strong>{s.score}<small>/100</small></strong><span>{s.distance} m<small>${s.cost}/{t('ay', 'mo')}</small></span></button>)}<div className="panel-foot">{t('Referans senaryolar · karşılaştırmak için bir satıra tıklayın', 'Reference scenarios · click a row to compare')}</div></section>;
}
