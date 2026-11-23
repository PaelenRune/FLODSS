import { useState } from 'react';
import { getShortDepartmentLabel, localizeCockpitDeptName, useCockpitData } from './CockpitDataContext';
import { useLanguage } from '../../context/LanguageContext';

export function FromToMatrixHeatmap() {
  const { t } = useLanguage();
  const { departments, flows, live } = useCockpitData();
  const [nonZeroOnly, setNonZeroOnly] = useState(false);
  const maxFlow = Math.max(1, ...flows.flat());
  const nonZeroPairs = flows.flatMap((row, i) =>
    row.flatMap((v, j) => (v > 0 && i !== j ? [{ from: departments[i], to: departments[j], value: v }] : []))
  ).sort((a, b) => b.value - a.value);

  return <section className="cockpit-panel">
    <div className="panel-heading">
      <h2>{t('Bölümler arası akış matrisi', 'From–to flow matrix')}</h2>
      <button
        type="button"
        className={`matrix-filter-btn ${nonZeroOnly ? 'active' : ''}`}
        aria-pressed={nonZeroOnly}
        onClick={() => setNonZeroOnly(v => !v)}
      >
        {t('Yalnızca akış olan çiftler', 'Non-zero flows only')} ({nonZeroPairs.length})
      </button>
    </div>
    {nonZeroOnly ? (
      <div className="nonzero-flow-list" style={{ overflow: 'auto', maxHeight: 290 }}>
        {nonZeroPairs.length === 0 ? (
          <div className="nonzero-empty">{t('Tanımlı malzeme akışı yok.', 'No active material flows defined.')}</div>
        ) : nonZeroPairs.map(pair => {
          const fromFull = localizeCockpitDeptName(pair.from, live, t);
          const toFull = localizeCockpitDeptName(pair.to, live, t);
          const ratio = pair.value / maxFlow;
          return (
            <div key={`${pair.from.id}-${pair.to.id}`} className="nonzero-flow-row" title={`${fromFull} → ${toFull}: ${pair.value}`}>
              <div className="nonzero-pair">
                <strong>{getShortDepartmentLabel(pair.from, t)} → {getShortDepartmentLabel(pair.to, t)}</strong>
                <small>{fromFull} → {toFull}</small>
              </div>
              <div className="nonzero-bar"><span style={{ width: `${Math.max(8, ratio * 100)}%` }}/></div>
              <b>{pair.value.toLocaleString()}</b>
            </div>
          );
        })}
      </div>
    ) : (
      <div className="flow-table" style={{ overflow: 'auto', maxHeight: 290 }}><table><caption className="sr-only">{live ? t('Problem tarafından tanımlanan yönlü malzeme akış miktarları', 'Problem-defined directional material flow quantities') : t('Bölümler arası günlük malzeme transferleri', 'Daily material transfers between departments')}</caption><thead><tr><th>{t('Kaynak / Hedef', 'From / To')}</th>{departments.map(d => <th key={d.id} title={localizeCockpitDeptName(d, live, t)}>{getShortDepartmentLabel(d, t)}</th>)}</tr></thead><tbody>{flows.map((row, i) => <tr key={departments[i].id}><th title={localizeCockpitDeptName(departments[i], live, t)}>{getShortDepartmentLabel(departments[i], t)}</th>{row.map((v, j) => <td key={departments[j].id}><span tabIndex={0} title={`${localizeCockpitDeptName(departments[i], live, t)} → ${localizeCockpitDeptName(departments[j], live, t)}: ${v}`} style={{ background: v ? `rgba(0, 190, 224, ${0.08 + v / maxFlow * .7})` : '#151c2a', color: v > maxFlow * .6 ? '#bdfaff' : '#72849b' }}>{v || (i === j ? '—' : 0)}</span></td>)}</tr>)}</tbody></table></div>
    )}
    <div className="heatmap-key"><span>{t('Düşük yoğunluk', 'Low intensity')}</span><i/><span>{t('Yüksek yoğunluk', 'High intensity')}</span></div></section>;
}
