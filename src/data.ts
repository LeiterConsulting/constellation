export type PreviewRange = '-15m' | '-1h' | '-24h' | '-7d';
export interface DataScope { index?: string; sourcetype?: string; query?: string; language?: 'spl' | 'spl2'; earliest: PreviewRange; }
export interface DataDiscovery { indexes: Array<{ name: string; kind: string }>; status: string; activity: Array<{ index: string; sourcetype: string; events: string }>; warning: string; note: string; }
export interface DataProfile { scope: DataScope; baseQuery: string; fields: Array<{ name: string; numeric: boolean; present: number }>; sampledRows: number; bounded: boolean; note: string; }
export const previewRanges: Array<{ value: PreviewRange; label: string }> = [
  { value: '-15m', label: 'Last 15 minutes' }, { value: '-1h', label: 'Last hour' },
  { value: '-24h', label: 'Last 24 hours' }, { value: '-7d', label: 'Last 7 days' },
];
