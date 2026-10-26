import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { CockpitOverview } from '../src/components/cockpit/CockpitOverview';
import { useCockpitScenarios } from '../src/components/cockpit/liveScenarios';
import type { ContinuousLayout, FacilityLayoutProblem } from '../src/types/api';

const initialProblem: FacilityLayoutProblem = {
  id: 'interaction', name: 'Interaction test',
  facility: { id: 'f', name: 'Fixture facility', width: 100, height: 50, area: 5000 },
  departments: ['A', 'B', 'C'].map(id => ({ id, name: `Department ${id}`, required_area: 100 })),
  flows: [{ source_department: 'A', target_department: 'C', quantity: 10, unit: 'units' }],
  relationships: [], constraints: [],
};
const initialLayout: ContinuousLayout = {
  problem_id: initialProblem.id, representation_type: 'continuous', facility_width: 100, facility_height: 50,
  placements: Object.fromEntries(['A', 'B', 'C'].map((id, i) => [id, { department_id: id, x: i * 20, y: 0, width: 10, height: 10 }])),
};
function Fixture() {
  const [problem, setProblem] = useState(initialProblem);
  const [layout, setLayout] = useState(initialLayout);
  const [visible, setVisible] = useState(true);
  const history = useCockpitScenarios(problem, layout, null);
  return <><button onClick={() => setVisible(v => !v)}>Toggle cockpit</button><button onClick={() => setLayout({ ...initialLayout, name: 'GA', placements: { ...initialLayout.placements, A: { ...initialLayout.placements.A, x: 10 } } })}>Receive solver</button><button onClick={() => setProblem({ ...initialProblem, id: 'another-problem' })}>Change problem</button>{visible && <CockpitOverview problem={problem} layout={layout} evaluation={null} liveScenarios={history} onOpenWorkspace={() => {}}/>}</>;
}
createRoot(document.getElementById('root')!).render(<Fixture/>);
