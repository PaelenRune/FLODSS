import { localizeCockpitDeptName, useCockpitData } from './CockpitDataContext';
import { useLanguage } from '../../context/LanguageContext';

export function FromToMatrixHeatmap() {
  const { t } = useLanguage();
  const { departments, flows, live } = useCockpitData();
  const maxFlow = Math.max(1, ...flows.flat());
  return <section className="cockpit-panel"><div className="panel-heading"><h2>{t('Bölümler arası akış matrisi', 'From–to flow matrix')}</h2><span>fᵢⱼ</span></div>
    <div className="flow-table" style={{ overflow: 'auto', maxHeight: 290 }}><table><caption className="sr-only">{live ? t('Problem tarafından tanımlanan yönlü malzeme akış miktarları', 'Problem-defined directional material flow quantities') : t('Bölümler arası günlük malzeme transferleri', 'Daily material transfers between departments')}</caption><thead><tr><th>{t('Kaynak / Hedef', 'From / To')}</th>{departments.map(d => <th key={d.id}>{d.id}</th>)}</tr></thead><tbody>{flows.map((row, i) => <tr key={departments[i].id}><th>{departments[i].id}</th>{row.map((v, j) => <td key={departments[j].id}><span tabIndex={0} title={`${localizeCockpitDeptName(departments[i], live, t)} → ${localizeCockpitDeptName(departments[j], live, t)}: ${v}`} style={{ background: v ? `rgba(0, 190, 224, ${0.08 + v / maxFlow * .7})` : '#151c2a', color: v > maxFlow * .6 ? '#bdfaff' : '#72849b' }}>{v || (i === j ? '—' : 0)}</span></td>)}</tr>)}</tbody></table></div>
    <div className="heatmap-key"><span>{t('Düşük yoğunluk', 'Low intensity')}</span><i/><span>{t('Yüksek yoğunluk', 'High intensity')}</span></div></section>;
}
