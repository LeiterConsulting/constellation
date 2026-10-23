import { Component, useMemo, useRef, type ErrorInfo, type ReactNode } from 'react';
import DashboardCore from '@splunk/dashboard-core';
import { DashboardContextProvider, type DashboardContextProviderProps } from '@splunk/dashboard-context';
import EnterprisePreset from '@splunk/dashboard-presets/EnterprisePreset';
import type { DashboardJSON } from '@splunk/dashboard-types';
import { previewDefinition, type StudioDefinition } from './document';
import { isSplunk } from './api';
import { RendererFrame, Muted } from './styles';
import type { PreviewRows } from './agent';
import ElementFocus from './ElementFocus';
import { navigationTarget } from './pages';

class RendererBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(_error: Error, _info: ErrorInfo) { /* Keep user document content out of logs. */ }
  render() { return this.state.failed ? <Muted role="alert">The renderer could not display this definition. Your document is preserved; export it or undo the last change.</Muted> : this.props.children; }
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
  selected: string; selecting: boolean;
}
export default function Preview({ definition, revision, tokens, activeTab, onTokens, onTab, onSelect, searchResults, searchVersion, selected, selecting }: Props) {
  const frame=useRef<HTMLDivElement>(null);
  const preview = useMemo(() => {
    const result = previewDefinition(definition, searchResults, tokens);
    for (const [id, visualization] of Object.entries(result.visualizations)) {
      if (!Object.hasOwn(EnterprisePreset.visualizations || {}, visualization.type)) {
        result.visualizations[id] = { type: 'splunk.markdown', title: visualization.title,
          options: { markdown: `**Open in native Studio**\n\nThe embedded renderer does not include ${visualization.type}. Its original configuration is preserved.`, backgroundColor: 'transparent' } };
      }
    }
    if (!isSplunk() && result.inputs && typeof result.inputs === 'object') {
      const inputs = result.inputs as Record<string, { type?: string }>;
      const removed = new Set(Object.entries(inputs).filter(([, input]) => input.type === 'input.timerange').map(([id]) => id));
      for (const id of removed) delete inputs[id];
      if (Array.isArray(result.layout.globalInputs)) result.layout.globalInputs = result.layout.globalInputs.filter(id => !removed.has(String(id)));
    }
    return result as unknown as DashboardJSON;
  }, [definition, searchResults, tokens]);
  const plugin = useMemo(() => ({ onEventTrigger: (event: { [key: string]: unknown }) => {
    if (typeof event.type === 'string' && /click$/.test(event.type) && typeof event.targetId === 'string') {
      const source = definition.visualizations[event.targetId] || (definition.inputs as Record<string, {eventHandlers?: unknown}> | undefined)?.[event.targetId];
      if (!source) return;
      onSelect(navigationTarget(definition,event.targetId,(event.payload as {name?:unknown}|undefined)?.name) || event.targetId);
    }
  } }), [definition, onSelect]);
  return <RendererFrame ref={frame}><RendererBoundary key={revision + ':' + searchVersion}>
    <DashboardContextProvider key={revision + ':' + searchVersion} preset={EnterprisePreset} initialDefinition={preview}
      initialTokenBinding={tokens} initialTab={activeTab} onTokenBindingChange={onTokens}
      onActiveTabChange={onTab} dashboardPlugin={plugin}>
      <><DashboardCore width="100%" height={700} />
      <ElementFocus definition={definition} activeTab={activeTab} selected={selected} selecting={selecting} frame={frame} onSelect={onSelect}/>
      </>
    </DashboardContextProvider>
  </RendererBoundary></RendererFrame>;
}
