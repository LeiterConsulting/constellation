import type { StudioDefinition } from './document';

export type LabelBindings = Partial<Record<'default' | 'eval', Record<string, unknown>>>;
export function elementLabel(definition: StudioDefinition, id: string, bindings?: LabelBindings): string {
  const item = definition.visualizations[id] || (definition.inputs as Record<string, Record<string, unknown>> | undefined)?.[id];
  if (!item) return 'Element';
  const options = item.options as Record<string, unknown> | undefined;
  const defaults = (definition.defaults as { tokens?: { default?: Record<string, { value?: unknown }> } } | undefined)?.tokens?.default;
  const readable = (value: unknown) => {
    if (typeof value !== 'string' || !value.trim()) return '';
    let unresolved = false;
    const text = value.replace(/\$(eval:)?([A-Za-z0-9_.:-]+)\$/g, (_all, evaluated: string, token: string) => {
      const replacement = evaluated ? bindings?.eval?.[token] : bindings?.default?.[token] ?? defaults?.[token]?.value;
      if (!['string', 'number', 'boolean'].includes(typeof replacement)) { unresolved = true; return ''; }
      return String(replacement);
    });
    return unresolved ? '' : text.trim().slice(0, 120);
  };
  const title = readable(item.title) || readable(options?.label);
  if (title) return title;
  if (item.type === 'splunk.markdown' && typeof options?.markdown === 'string') {
    const first = options.markdown.split('\n').find(line => line.trim()) || '';
    const label = readable(first.replace(/^\s*#{1,6}\s*/, '').replace(/[*_`]/g, '').replace(/<[^>]*>/g, '').replace(/\[([^\]]+)\]\([^)]*\)/g, '$1'));
    if (label) return label;
  }
  return item.type === 'input.button' ? 'Button' : String(item.type).startsWith('input.') ? 'Input' : 'Chart';
}
