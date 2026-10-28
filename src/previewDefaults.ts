import type { JsonObject, StudioDefinition } from './document';
import type { TokenState } from '@splunk/dashboard-types';
export type InputDefaults = Record<string, Record<string, unknown>>;

/** Keep reset semantics while avoiding an input's display fallback after unset. */
export function resetDefaults(definition: StudioDefinition, inputDefaults: InputDefaults = {}): JsonObject {
  const defaults = structuredClone(definition.defaults || {}) as JsonObject;
  const namespaces = (defaults.tokens ||= {}) as Record<string, Record<string, JsonObject>>;
  for (const [namespace, values] of Object.entries(inputDefaults)) {
    namespaces[namespace] ||= {};
    for (const [name, value] of Object.entries(values)) namespaces[namespace][name] = { ...namespaces[namespace][name], value };
  }
  return defaults;
}

/** Framework static-default extraction accepts only strings; unset must also
 * be explicit in initialTokenBinding, where null has native unset semantics.
 */
export function previewTokenSnapshot(definition: StudioDefinition, tokens: TokenState | undefined, inputDefaults: InputDefaults = {}): TokenState | undefined {
  if (!tokens?.default) return tokens;
  const values = { ...tokens.default };
  const defaults = resetDefaults(definition, inputDefaults).tokens as Record<string, Record<string, JsonObject>>;
  for (const name of Object.keys(defaults.default || {})) if (!Object.hasOwn(values, name)) values[name] = null;
  return { ...tokens, default: values };
}

export function initializePreviewDefaults(preview: StudioDefinition, original: StudioDefinition, tokens?: { default?: Record<string, unknown> }, inputDefaults: InputDefaults = {}) {
  if (!tokens?.default) return;
  const defaults = resetDefaults(original, inputDefaults);
  const namespaces = (defaults.tokens ||= {}) as Record<string, Record<string, JsonObject>>;
  const values = (namespaces.default ||= {});
  // The Framework may omit an empty namespace and then reapply native defaults.
  // Its unset sentinel keeps absent restored tokens explicit during initialization.
  for (const key of Object.keys(values)) if (!Object.hasOwn(tokens.default, key)) values[key] = { ...values[key], value: null };
  for (const [key, value] of Object.entries(tokens.default)) values[key] = { ...values[key], value };
  preview.defaults = defaults;
  for (const input of Object.values((preview.inputs || {}) as Record<string, { type?: string; options?: JsonObject }>)) {
    if (['input.dropdown', 'input.multiselect', 'input.text', 'input.number', 'input.timerange'].includes(input.type || '')
        && input.options && (!input.options.tokenNamespace || input.options.tokenNamespace === 'default')
        && Object.hasOwn(input.options, 'defaultValue')) delete input.options.defaultValue;
  }
}
