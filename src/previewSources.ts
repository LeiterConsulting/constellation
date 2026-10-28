import type { StudioDefinition } from './document';

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
