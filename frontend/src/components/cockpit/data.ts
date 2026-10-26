export const departments = [
  { id: 'ST', name: 'Raw Material', color: '#f59e0b', dark: '#78350f', share: 24, area: 720, required: 680, x: 12, y: 12, w: 102, h: 92 },
  { id: 'MC', name: 'Machining', color: '#3b82f6', dark: '#1e3a8a', share: 32, area: 960, required: 900, x: 124, y: 12, w: 154, h: 92 },
  { id: 'AS', name: 'Assembly', color: '#8b5cf6', dark: '#4c1d95', share: 20, area: 600, required: 560, x: 124, y: 116, w: 154, h: 75 },
  { id: 'PK', name: 'Packaging', color: '#10b981', dark: '#064e3b', share: 12, area: 360, required: 340, x: 12, y: 116, w: 102, h: 75 },
  { id: 'LG', name: 'Logistics', color: '#f43f5e', dark: '#881337', share: 8, area: 240, required: 220, x: 12, y: 202, w: 266, h: 43 },
];
export const scenarios = [
  { name: 'Baseline Layout', score: 68, distance: '2,180', cost: '4,850' },
  { name: 'Optimized Layout #1', score: 94, distance: '1,420', cost: '3,928' },
  { name: 'Alternative Layout #2', score: 86, distance: '1,650', cost: '4,190' },
];
export const flows = [[0, 95, 12, 8, 4], [5, 0, 88, 20, 8], [0, 12, 0, 76, 16], [0, 0, 8, 0, 92], [4, 0, 0, 10, 0]];
