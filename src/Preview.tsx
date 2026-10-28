import { Component, memo, useLayoutEffect, useMemo, useRef, type ErrorInfo, type ReactNode } from 'react';
import DashboardCore from '@splunk/dashboard-core';
import { DashboardContextProvider, Preset, type DashboardContextProviderProps } from '@splunk/dashboard-context';
import EnterprisePreset from '@splunk/dashboard-presets/EnterprisePreset';
import type { DashboardJSON } from '@splunk/dashboard-types';
import { updateDefinition, useStore } from '@splunk/dashboard-state';
import { getInputDefaultTokens } from '@splunk/dashboard-definition';
import { previewDefinition, type StudioDefinition } from './document';
import { isSplunk } from './api';
import { RendererFrame, Muted } from './styles';
import type { PreviewRows } from './agent';
import ElementFocus from './ElementFocus';
import { navigationTarget } from './pages';
import { usePreviewHeight } from './usePreviewHeight';
import { previewTokenSnapshot, resetDefaults } from './previewDefaults';
import { nativeSupportMessage } from './previewCompatibility';

// Metadata lookup only. This utility never constructs or runs a data source.
const inputPreset = new Preset({ presetDefinition: EnterprisePreset, SnapshotDataSource: undefined });

class RendererBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(_error: Error, _info: ErrorInfo) { /* Keep user document content out of logs. */ }
  render() { return this.state.failed ? <Muted role="alert">The renderer could not display this definition. Your document is preserved; export it or undo the last change.</Muted> : this.props.children; }
}

/** Initialization needs the current snapshot; native reset needs original defaults.
 * Restore only the renderer definition after its store has initialized. Tokens,
 * input state (including dynamic first choices), sources and the user draft stay intact.
 */
function RestorePreviewDefaults({ defaults }: { defaults: DashboardJSON['defaults'] }) {
  const store = useStore();
  useLayoutEffect(() => {
    const definition = { ...store.getState().definition };
    if (JSON.stringify(definition.defaults) === JSON.stringify(defaults)) return;
    if (defaults === undefined) delete definition.defaults;
    else definition.defaults = structuredClone(defaults);
    store.dispatch(updateDefinition(definition));
  }, [store, defaults]);
  return null;
}

interface Props {
  definition: StudioDefinition; revision: number;
  tokens: DashboardContextProviderProps['initialTokenBinding'];
  activeTab?: string;
  onTokens: NonNullable<DashboardContextProviderProps['onTokenBindingChange']>;
  onTab: NonNullable<DashboardContextProviderProps['onActiveTabChange']>;
  onSelect: (id: string) => void;
  searchResults: Record<string, PreviewRows>;
  searchVersion: number;
  searchMessages?: Record<string, string>;
  selected: string; selecting: boolean;
  nativeTypes?: string[];
}
export default memo(function Preview({ definition, revision, tokens, activeTab, onTokens, onTab, onSelect, searchResults, searchVersion, searchMessages, selected, selecting, nativeTypes }: Props) {
  const frame=useRef<HTMLDivElement>(null);
  const height=usePreviewHeight(frame);
  const inputDefaults = useMemo(() => getInputDefaultTokens({ definition: definition as unknown as DashboardJSON, preset: inputPreset }), [definition]);
  const initialTokens = useMemo(() => previewTokenSnapshot(definition, tokens, inputDefaults), [definition, tokens, inputDefaults]);
  const originalDefaults = useMemo(() => resetDefaults(definition, inputDefaults), [definition, inputDefaults]);
  const preview = useMemo(() => {
    const result = previewDefinition(definition, searchResults, tokens, searchMessages, inputDefaults);
    for (const [id, visualization] of Object.entries(result.visualizations)) {
      const unsupported = nativeSupportMessage(visualization.type, nativeTypes);
      if (!Object.hasOwn(EnterprisePreset.visualizations || {}, visualization.type)) {
        result.visualizations[id] = { type: 'splunk.markdown', title: visualization.title,
          options: { markdown: `**Open in native Studio**\n\nThe embedded renderer does not include ${visualization.type}. Its original configuration is preserved.`, backgroundColor: 'transparent' } };
      } else if (unsupported) {
        result.visualizations[id] = { type: 'splunk.markdown', title: visualization.title,
          options: { markdown: unsupported, backgroundColor: 'transparent' } };
      }
    }
    if (!isSplunk() && result.inputs && typeof result.inputs === 'object') {
      const inputs = result.inputs as Record<string, { type?: string }>;
      const removed = new Set(Object.entries(inputs).filter(([, input]) => input.type === 'input.timerange').map(([id]) => id));
      for (const id of removed) delete inputs[id];
      if (Array.isArray(result.layout.globalInputs)) result.layout.globalInputs = result.layout.globalInputs.filter(id => !removed.has(String(id)));
    }
    return result as unknown as DashboardJSON;
  }, [definition, searchResults, tokens, searchMessages, inputDefaults, nativeTypes]);
  const plugin = useMemo(() => ({ onEventTrigger: (event: { [key: string]: unknown }) => {
    if (selecting) return;
    if (typeof event.type === 'string' && /click$/.test(event.type) && typeof event.targetId === 'string') {
      const source = definition.visualizations[event.targetId] || (definition.inputs as Record<string, {eventHandlers?: unknown}> | undefined)?.[event.targetId];
      if (!source) return;
      onSelect(navigationTarget(definition,event.targetId,(event.payload as {name?:unknown}|undefined)?.name) || event.targetId);
    }
  } }), [definition, onSelect, selecting]);
  const renderKey = revision + ':' + searchVersion + ':' + JSON.stringify(searchMessages);
  return <RendererFrame ref={frame} style={{ height }} role="region" aria-label="Dashboard preview"><RendererBoundary key={renderKey}>
    <DashboardContextProvider key={renderKey} preset={EnterprisePreset} initialDefinition={preview}
      initialTokenBinding={initialTokens} initialTab={activeTab} onTokenBindingChange={onTokens}
      onActiveTabChange={onTab} dashboardPlugin={plugin}>
      <><RestorePreviewDefaults defaults={originalDefaults as DashboardJSON['defaults']} /><DashboardCore width="100%" height="100%" />
      <ElementFocus definition={definition} activeTab={activeTab} selected={selected} selecting={selecting} frame={frame} onSelect={onSelect} bindings={tokens}/>
      </>
    </DashboardContextProvider>
  </RendererBoundary></RendererFrame>;
});
