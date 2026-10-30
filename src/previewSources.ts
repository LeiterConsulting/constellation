import type { StudioDefinition } from './document';

const executable = new Set(['ds.search', 'ds.spl2', 'ds.chain', 'ds.savedSearch']);
export const PREVIEW_SOURCE_LIMIT = 8;

/** Select consumers, not the document's declaration order. Chain ancestors are
 * resolved by searchRequest/server resolution; an unconsumed parent does not
 * need a second job. Never evaluate native expressions to discover authority.
 */
export function previewSourceSchedule(definition: StudioDefinition, activeTab?: string) {
  const layout = definition.layout;
  const layouts = layout.layoutDefinitions as Record<string, { structure?: Array<{ item?: string }> }> | undefined;
  const tabs = layout.tabs as { items?: Array<{ layoutId: string }> } | undefined;
  const page = layouts ? (activeTab && layouts[activeTab] ? activeTab
    : tabs?.items?.find(tab => layouts[tab.layoutId])?.layoutId || Object.keys(layouts)[0]) : undefined;
  const structure = (layouts ? layouts[page || '']?.structure : layout.structure) as Array<{ item?: string }> | undefined;
  const placed = (structure || []).flatMap(item => typeof item.item === 'string' ? [item.item] : []);
  const inputs = (definition.inputs || {}) as Record<string, { title?: string; dataSources?: Record<string, string> }>;
  const globals = (Array.isArray(layout.globalInputs) ? layout.globalInputs : []).filter((id): id is string => typeof id === 'string');
  const consumers = [...new Set([...globals, ...placed.filter(id => Object.hasOwn(inputs, id)), ...placed])];
  const sources = new Set<string>();
  const titles: Record<string, string> = {};
  for (const id of consumers) {
    const consumer = definition.visualizations[id] || inputs[id] as { title?: string; dataSources?: Record<string, string> } | undefined;
    for (const sourceId of Object.values(consumer?.dataSources || {})) {
      if (typeof sourceId !== 'string' || !executable.has(definition.dataSources?.[sourceId]?.type || '')) continue;
      sources.add(sourceId);
      titles[sourceId] ||= consumer?.title || id;
    }
  }
  const ids = [...sources];
  return { page, ids, scheduled: ids.slice(0, PREVIEW_SOURCE_LIMIT), deferred: ids.slice(PREVIEW_SOURCE_LIMIT), titles };
}

/** Dependency metadata only. Snapshots cannot use extend: the Framework would
 * treat them as executable chain sources. Flatten the literal query instead.
 * Opaque reports keep their separate native qualification boundary.
 */
export function previewDependencyQuery(definition: StudioDefinition, id: string, seen = new Set<string>()): string {
  if (seen.has(id) || seen.size >= 24) return '';
  seen.add(id);
  const source = definition.dataSources?.[id];
  const query = typeof source?.options?.query === 'string' ? source.options.query : '';
  const parent = source?.type === 'ds.chain' ? source.options?.extend || source.extend : undefined;
  return typeof parent === 'string' ? `${previewDependencyQuery(definition,parent,seen)} | ${query.replace(/^\s*\|/,'')}` : query;
}
