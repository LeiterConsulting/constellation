import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Button from '@splunk/react-ui/Button';
import Link from '@splunk/react-ui/Link';
import ControlGroup from '@splunk/react-ui/ControlGroup';
import TextArea from '@splunk/react-ui/TextArea';
import Select from '@splunk/react-ui/Select';
import Modal from '@splunk/react-ui/Modal';
import MessageBar from '@splunk/react-ui/Message';
import SplunkThemeProvider from '@splunk/themes/SplunkThemeProvider';
import type { DashboardContextProviderProps } from '@splunk/dashboard-context';
import Preview from './Preview';
import { applyEdit, cleanDashboardUrl, createBlank, createStarter, validateDefinition, fromStudioXml, type Edit, type Revision, type StudioDefinition } from './document';
import { isSplunk, saveCopy, providerRequest, providerLabel, type ProviderSettings } from './api';
import Settings from './Settings';
import { applyStudioChanges, readAttachment, type AgentReply, type Attachment, type Environment } from './agent';
import { useSearchPreview } from './useSearchPreview';
import { instanceIdeas, contextualPrompts, promptContextKey, type PromptSuggestion } from './prompts';
import { newDraftId, readDraft, openDraft, type ChatMessage as Chat, type DraftList, type DraftRecord, type DraftSnapshot } from './drafts';
import { useDraftPersistence } from './useDraftPersistence';
import { previewRanges, type DataDiscovery, type DataScope } from './data';
import DashboardLibrary from './DashboardLibrary';
import DataChooser from './DataChooser';
import PageManager from './PageManager';
import { changePage, elementsOf, pagesOf, readWorkspaceRoute, validFocus, workspaceLink, type PagePurpose } from './pages';
import { Actions, Canvas, CanvasHeading, Composer, Conversation, ConversationScroll, EmptyCanvas, IdeaGrid, IdeaText, IdeaButton, PromptChoices, FloatingLauncher, GlobalStyle, Header, Message, Muted, PanelHeading, Shell, Source, Transcript, Workspace } from './styles';

const LAYOUT_KEY = 'constellation.layout.v1';
const readLayout = () => { try { return localStorage.getItem(LAYOUT_KEY) === 'floating'; } catch { return false; } };
type Proposals = { key: string; items: PromptSuggestion[] } | null;
const welcome = (definition: StudioDefinition): Chat[] => [{ id: 0, user: false, text: Object.keys(definition.visualizations).length
  ? 'What would you like to understand or change in this dashboard?'
  : 'What should this dashboard help you understand? Choose data from this Splunk instance, bring an existing search, or describe the question you want to answer.' }];

export default function App({ initialColorScheme }: { initialColorScheme: 'light' | 'dark' }) {
  const [theme, setTheme] = useState(initialColorScheme);
  const [floating, setFloating] = useState(readLayout);
  const [collapsed, setCollapsed] = useState(false);
  const [revision, setRevision] = useState<Revision>(() => ({ number: 0, definition: createBlank() }));
  const [history, setHistory] = useState<Revision[]>([]);
  const [future, setFuture] = useState<Revision[]>([]);
  const [selected, setSelected] = useState('');
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<Chat[]>(() => welcome(createBlank()));
  const messageId = useRef(0);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [modal, setModal] = useState<'source' | 'open' | 'link' | null>(null);
  const [tokens, setTokens] = useState<DashboardContextProviderProps['initialTokenBinding']>();
  const navigationFocus=useRef<unknown>();
  const [activeTab, setActiveTab] = useState<string>();
  const [pagePurposes,setPagePurposes]=useState<PagePurpose>({});
  const [copiedLink,setCopiedLink]=useState('');
  const [pagesOpen,setPagesOpen]=useState(false);
  const [selecting,setSelecting]=useState(false);
  const initialRoute=useRef(readWorkspaceRoute(window.location.href));
  const [saved, setSaved] = useState<{ name: string; url: string } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const modalReturnFocus = useRef<HTMLElement | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [connection, setConnection] = useState<ProviderSettings | null>(null);
  const [thinking, setThinking] = useState(false);
  const generation = useRef<AbortController | null>(null);
  const revisionRef = useRef(revision);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const attachmentInput = useRef<HTMLInputElement>(null);
  const [proposals, setProposals] = useState<Proposals>(null);
  const [draftId, setDraftId] = useState(newDraftId);
  const [storageReady, setStorageReady] = useState(!isSplunk());
  const [dataContext, setDataContext] = useState<DataScope | null>(null);
  const [discovery, setDiscovery] = useState<DataDiscovery | null>(null);
  const [dataChooser, setDataChooser] = useState<{ scope?: DataScope | null; goal?: string } | null>(null);
  const composerInput = useRef<HTMLTextAreaElement>(null);
  const conversationElement = useRef<HTMLElement>(null);
  const conversationScroll = useRef<HTMLDivElement>(null);
  const [panelHeight, setPanelHeight] = useState(560);
  const [activity, setActivity] = useState<string[]>([]);
  const [environment, setEnvironment] = useState<Environment | null>(null);
  const [environmentOpen, setEnvironmentOpen] = useState(false);
  const searches = useSearchPreview(revision.definition, tokens, dataContext?.earliest || '-15m');
  revisionRef.current = revision;
  const empty = Object.keys(revision.definition.visualizations).length === 0 && Object.keys(revision.definition.inputs || {}).length === 0;
  const hasConversation = messages.some(message => message.user);
  const contextKey = promptContextKey(revision.number, revision.definition, selected, activeTab, dataContext);
  const suggestions = attachments.length ? contextualPrompts(revision.definition, selected, attachments.length, dataContext, pagePurposes)
    : proposals?.key === contextKey ? proposals.items : contextualPrompts(revision.definition, selected, 0, dataContext, pagePurposes);
  const snapshot = useMemo<DraftSnapshot>(() => ({ definition: revision.definition, messages, prompt, attachments, tokens, activeTab, selected,
    suggestions: proposals?.key === contextKey ? proposals.items : null, activity, saved, dataContext,
    searchesEnabled: searches.enabled, pagePurposes, pendingRequest: thinking ? [...messages].reverse().find(message => message.user)?.text || '' : '' }),
  [revision.definition, messages, prompt, attachments, tokens, activeTab, selected, proposals, contextKey, activity, saved, dataContext, searches.enabled, pagePurposes, thinking]);
  const persistence = useDraftPersistence(draftId, snapshot, storageReady);
  const activate = (definition: StudioDefinition, restored?: DraftRecord, keepLibrary = false) => {
    window.history.replaceState(window.history.state, '', cleanDashboardUrl(window.location.href));
    generation.current?.abort(); generation.current = null; setThinking(false); searches.reset();
    setHistory([]); setFuture([]); setCollapsed(false);setSelecting(false);
    const number = revisionRef.current.number + 1;
    const state = restored?.state;
    if (restored) persistence.adopt(restored);
    setDraftId(restored?.id || newDraftId());
    setRevision({ number, definition }); setSelected(validFocus(definition,state?.selected || '')?state?.selected || '':'');
    setPagePurposes(state?.pagePurposes||{});
    navigationFocus.current=state?.tokens?.default?.constellation_focus;
    setTokens(state?.tokens); setActiveTab(state?.activeTab); setSaved(state?.saved || null);
    setDataContext(state?.dataContext || null);
    const conversation = state?.messages.length ? state.messages : welcome(definition);
    setMessages(conversation); messageId.current = Math.max(0, ...conversation.map(message => message.id));
    setPrompt(state?.prompt || state?.pendingRequest || '');
    setAttachments(state?.attachments || []); setActivity(state?.activity || []);
    setProposals(state?.suggestions != null ? { key: promptContextKey(number, definition, state.selected, state.activeTab, state.dataContext), items: state.suggestions } : null);
    if (!keepLibrary) setModal(null);
    if (state?.searchesEnabled) searches.run();
    setStatus(state?.pendingRequest ? 'The previous request was interrupted. Your request is ready to send again; it has not been rerun.'
      : restored ? 'Draft and conversation restored.' : '');
  };
  const choosePrompt = (suggestion: PromptSuggestion) => {
    setPrompt(suggestion.prompt); setCollapsed(false);
    requestAnimationFrame(() => composerInput.current?.focus());
  };
  useEffect(() => {
    window.history.replaceState(window.history.state, '', cleanDashboardUrl(window.location.href));
    if (!isSplunk()) return;
    const controller = new AbortController();
    void providerRequest<ProviderSettings>('settings', undefined, controller.signal).then(setConnection).catch(() => { /* Settings explains connection errors on request. */ });
    void providerRequest<DataDiscovery>('discovery', undefined, controller.signal).then(setDiscovery).catch(() => { /* An existing search remains available in the data chooser. */ });
    void (async () => {
      try {
        const list = await providerRequest<DraftList>('drafts', undefined, controller.signal);
        const requested=initialRoute.current.draft||list.activeId;
        if (requested && list.drafts.some(item => item.id === requested)) {
          const record = await (initialRoute.current.draft ? openDraft(requested) : readDraft(requested));
          if (!controller.signal.aborted) {
            const route=initialRoute.current;
            activate(record.state.definition, record);
            if(route.page&&pagesOf(record.state.definition).some(page=>page.id===route.page))setActiveTab(route.page);
            if(route.focus&&validFocus(record.state.definition,route.focus))setSelected(route.focus);
          }
        } else if(initialRoute.current.draft) {
          setStatus('This draft link is unavailable to your Splunk user. Choose a draft from Dashboards.');
        }
      } catch (failure) { if (!controller.signal.aborted) setStatus(failure instanceof Error ? failure.message : 'Drafts could not be restored.'); }
      finally { if (!controller.signal.aborted) setStorageReady(true); }
    })();
    return () => { controller.abort(); generation.current?.abort(); };
  }, []);
  useEffect(() => {
    const node = conversationElement.current;
    if (!node || collapsed) return;
    let frame = 0;
    const measure = () => setPanelHeight(floating ? Math.max(320, Math.min(680, window.innerHeight * 0.72))
      : Math.max(320, window.innerHeight - Math.max(16, node.getBoundingClientRect().top) - 16));
    const schedule = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(measure); };
    measure(); window.addEventListener('resize', schedule); window.addEventListener('scroll', schedule, { passive: true });
    return () => { cancelAnimationFrame(frame); window.removeEventListener('resize', schedule); window.removeEventListener('scroll', schedule); };
  }, [floating, collapsed]);
  useEffect(() => { const node = conversationScroll.current; if (node) node.scrollTop = node.scrollHeight; }, [messages, proposals, selected, activeTab]);
  const onSelect = useCallback((id: string) => {
    const pages=pagesOf(revisionRef.current.definition);
    const page=id.startsWith('page:') ? pages.find(page=>page.id===id.slice(5)) : pages.find(page=>page.items.includes(id));
    if(page)setActiveTab(page.id);
    setSelected(id);setSelecting(false);setCollapsed(false);requestAnimationFrame(()=>composerInput.current?.focus({preventScroll:true}));}, []);
  const onTab = useCallback((id: string | undefined) => {setActiveTab(id);setSelecting(false);setSelected(value=>{
    const page=pagesOf(revisionRef.current.definition).find(page=>page.id===id);
    return value.startsWith('page:') ? (id ? `page:${id}` : '') : page?.items.includes(value) ? value : '';
  });}, []);
  const onTokens = useCallback<NonNullable<DashboardContextProviderProps['onTokenBindingChange']>>(value => {
    setTokens(previous => JSON.stringify(previous) === JSON.stringify(value) ? previous : value);
  }, []);
  useEffect(()=>{
    const target=tokens?.default?.constellation_focus;
    if(target===navigationFocus.current)return;navigationFocus.current=target;
    if(typeof target==='string'&&target&&validFocus(revision.definition,target))setSelected(target);
  },[tokens,activeTab,revision.definition]);
  useEffect(()=>{if(!selecting)return;const escape=(event:KeyboardEvent)=>{if(event.key==='Escape')setSelecting(false);};window.addEventListener('keydown',escape);return()=>window.removeEventListener('keydown',escape);},[selecting]);
  useEffect(()=>{
    const layouts=revision.definition.layout.layoutDefinitions as Record<string,unknown> | undefined;
    setPagePurposes(previous=>{const next=Object.fromEntries(Object.entries(previous).filter(([id])=>layouts&&Object.hasOwn(layouts,id)));return Object.keys(next).length===Object.keys(previous).length?previous:next;});
    setSelected(previous=>validFocus(revision.definition,previous)?previous:'');
    if(activeTab&&!pagesOf(revision.definition).some(page=>page.id===activeTab))setActiveTab(pagesOf(revision.definition)[0]?.id);
  },[revision.definition,activeTab]);
  const addMessage = (text: string, user = false) => setMessages(previous => [...previous.slice(-99), { id: ++messageId.current, user, text }]);

  const toggleDock = () => {
    setFloating(previous => { const next = !previous; try { localStorage.setItem(LAYOUT_KEY, next ? 'floating' : 'docked'); } catch { /* Layout still works without storage. */ } return next; });
  };
  const commit = (edit: Edit, message: string) => {
    try {
      const next = applyEdit(revision, revision.number, edit);
      setHistory(previous => [...previous.slice(-19), revision]); setFuture([]); setRevision(next); setSaved(null);
      addMessage(message); setStatus(`Draft updated · revision ${next.number}`);
    } catch (error) { setStatus(error instanceof Error ? error.message : 'The edit could not be applied.'); }
  };
  const load = async (definition: StudioDefinition) => {
    generation.current?.abort(); generation.current = null; setThinking(false);
    setBusy(true);
    try { if (await persistence.flush()) activate(definition); } finally { setBusy(false); }
  };
  const submit = async (request?: string, scopeOverride?: DataScope) => {
    const text = (request || prompt).trim(); if (!text || !storageReady) return;
    if (attachments.some(file => !connection?.capabilities?.[file.data.startsWith('data:application/pdf;') ? 'pdf' : 'images'])) { setStatus('Attachments were not sent. Choose a provider and model that support these file types in Settings.'); return; }
    setPrompt(''); addMessage(text, true);
    if ((connection?.configured || connection?.keyConfigured) && connection.model) {
      const controller = new AbortController(); generation.current = controller; setThinking(true); setStatus(`${empty ? 'Building' : 'Working'} with ${providerLabel(connection.provider)}…`);
      setActivity([empty ? 'Shaping your first dashboard…' : 'Reading the current dashboard…']); setProposals(null);
      const base = revisionRef.current;
      try {
        if (!environment) {
          setActivity(['Checking Splunk and SPL2 support…']);
          const detected = await providerRequest<Environment>('environment', { probe: true }, controller.signal);
          setEnvironment(detected);
        }
        if (controller.signal.aborted) return;
        setActivity([`Planning Studio changes with ${providerLabel(connection.provider)}…`]);
        const result = await providerRequest<AgentReply>('author', {
          prompt: text, revision: base.number, definition: base.definition, selected, activeTab, suggestionFormat: 'cards',
          dataContext: scopeOverride || dataContext, pagePurposes, tokens,
          attachments, history: messages.filter(message => message.id !== 0).slice(-12).map(message => ({ role: message.user ? 'user' : 'assistant', text: message.text })),
        }, controller.signal);
        if (controller.signal.aborted) return;
        if (result.dataContext) setDataContext(result.dataContext);
        if(result.pagePurposes)setPagePurposes(result.pagePurposes);
        let updated = base;
        if (result.changes.length) {
          const previousRevision = revisionRef.current;
          const next = applyStudioChanges(previousRevision, result);
          setHistory(previous => [...previous.slice(-19), previousRevision]); setFuture([]); setRevision(next); setSaved(null);
          updated = next;
          setSelected(value => validFocus(next.definition,value) ? value : '');
          setStatus(result.recovery&&result.recovery.modelCalls>1?'Dashboard updated after automatic recovery.':'Dashboard updated.');
        } else setStatus('The agent replied. The document is unchanged.');
        setActivity([...result.activity, ...(result.validationNotes || []).map(note => `Corrected during validation: ${note}`)]); setProposals({ key: promptContextKey(updated.number, updated.definition, selected, activeTab, result.dataContext || scopeOverride || dataContext), items: result.suggestions }); setAttachments([]); addMessage(result.message);
        if (result.dataContext && result.changes.length && !searches.enabled) searches.run();
      } catch (error) {
        if (!controller.signal.aborted) {
          if (error instanceof Error && 'validationError' in error && typeof error.validationError === 'string') setActivity([error.validationError]);
          setProposals({ key: promptContextKey(base.number, base.definition, selected, activeTab, scopeOverride || dataContext), items: [{ label: 'Retry your request', prompt: text, reason: 'Retry the original goal against the current verified data. Your draft is retained.', kind: 'refine' }] });
          const message = error instanceof Error ? error.message : 'The request failed. Your draft is unchanged.'; setStatus(message); addMessage(message); }
      } finally { if (generation.current === controller) { generation.current = null; setThinking(false); } }
      return;
    }
    if (empty) { addMessage('Connect a model in Settings and I can turn this idea into a first dashboard. Your prompt is kept in this conversation.'); return; }
    if (/^rename (?:it |this |the dashboard )?to /i.test(text)) {
      const title = text.replace(/^rename (?:it |this |the dashboard )?to /i, '');
      commit(selected ? { type: 'tile-title', id: selected, title } : { type: 'rename', title }, selected ? 'Updated the selected chart title.' : 'Updated the dashboard title.');
    } else addMessage('Connect a model in Settings to build or change this dashboard using its actual Splunk data. Your draft and conversation are saved.');
  };
  const exportJson = () => {
    const url = URL.createObjectURL(new Blob([JSON.stringify(revision.definition, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = 'constellation-dashboard.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const openPicker = async () => {
    modalReturnFocus.current = document.activeElement as HTMLElement;
    if (await persistence.flush()) setModal('open');
  };
  const save = async () => {
    setBusy(true); setStatus('Saving a private copy to Splunk…');
    try { const result = await saveCopy(revision.definition, theme); setSaved(result); setStatus('Saved a copy and verified its definition by reading it back.'); }
    catch (error) { setStatus(error instanceof Error ? error.message : 'The save could not be completed.'); }
    finally { setBusy(false); }
  };

  return <SplunkThemeProvider family="enterprise" colorScheme={theme} density="comfortable"><GlobalStyle/><Shell>
    <Header><h1>Constellation</h1><Muted>Dashboard workspace</Muted><Actions style={{ marginLeft: 'auto' }}>
      <Button onClick={() => { modalReturnFocus.current = document.activeElement as HTMLElement; setSettingsOpen(true); }} disabled={!isSplunk()}>Settings</Button>
      <Button onClick={() => void load(createBlank())} disabled={busy || !storageReady}>New dashboard</Button>
      <Button onClick={() => void openPicker()} disabled={busy || thinking || !storageReady}>Dashboards</Button>
      <Button onClick={exportJson}>Export JSON</Button>
      <Button disabled={!isSplunk() || thinking} onClick={() => {
        modalReturnFocus.current = document.activeElement as HTMLElement; setEnvironmentOpen(true);
        void providerRequest<Environment>('environment', { probe: true }).then(setEnvironment).catch(error => setStatus(error instanceof Error ? error.message : 'Environment discovery failed.'));
      }}>Environment</Button>
      <Button appearance="primary" onClick={() => void save()} disabled={busy || !isSplunk() || empty || thinking}>Save a copy to Splunk</Button>
      <Button appearance="subtle" onClick={() => setTheme(previous => previous === 'light' ? 'dark' : 'light')}>{theme === 'light' ? 'Dark' : 'Light'} theme</Button>
    </Actions></Header>
    <Workspace $floating={floating || collapsed}>
      <Canvas><CanvasHeading><div><h2>{revision.definition.title || 'Untitled dashboard'}</h2><Muted role="status">{persistence.status}</Muted>{revision.definition.description ? <Muted>{String(revision.definition.description)}</Muted> : null}</div><Actions>
        <Button disabled={thinking||!storageReady} onClick={()=>{modalReturnFocus.current=document.activeElement as HTMLElement;setPagesOpen(true);}}>Pages</Button>
        {!empty?<Button aria-pressed={selecting} disabled={thinking} onClick={()=>setSelecting(value=>!value)}>{selecting?'Cancel selection':'Select element'}</Button>:null}
        {!empty?<Button disabled={!isSplunk()||thinking} onClick={()=>void (async()=>{if(!await persistence.flush())return;try{await navigator.clipboard.writeText(workspaceLink(window.location.href,draftId,activeTab,selected||undefined));setStatus('Copied a private draft link to this page and focus. The link requires Splunk access.');}catch{setCopiedLink(workspaceLink(window.location.href,draftId,activeTab,selected||undefined));modalReturnFocus.current=document.activeElement as HTMLElement;setModal('link');}})()}>Copy link</Button>:null}
        {!empty || hasConversation ? <Button disabled={thinking || !storageReady || !isSplunk()} onClick={() => { modalReturnFocus.current = document.activeElement as HTMLElement; setDataChooser({ scope: dataContext }); }}>{dataContext ? `Data: ${dataContext.index || 'existing search'}` : 'Choose Splunk data'}</Button> : null}
        <Button disabled={!history.length || thinking} onClick={() => { const previous = history[history.length - 1]; setFuture(items => [...items, revision]); setHistory(items => items.slice(0, -1)); setRevision({ ...previous, number: revision.number + 1 }); setSaved(null); setStatus('Last document change undone.'); }}>Undo</Button>
        <Button disabled={!future.length || thinking} onClick={() => { const next = future[future.length - 1]; setHistory(items => [...items, revision]); setFuture(items => items.slice(0, -1)); setRevision({ ...next, number: revision.number + 1 }); setSaved(null); setStatus('Document change restored.'); }}>Redo</Button>
        <Button onClick={() => { modalReturnFocus.current = document.activeElement as HTMLElement; setModal('source'); }}>Show source</Button>
        {!empty ? <Button disabled={!isSplunk() || searches.running} onClick={searches.run}>{searches.enabled ? 'Refresh searches' : 'Run searches'}</Button> : null}
        {searches.enabled ? <Button onClick={searches.pause}>Pause searches</Button> : null}
      </Actions></CanvasHeading>
      {persistence.error ? <MessageBar type="error">{persistence.error}<Actions><Button onClick={() => void persistence.flush()}>Retry save</Button><Button disabled={thinking} onClick={() => void (async () => {
        const id = newDraftId();
        try { const record = await persistence.sync.save(id, { ...snapshot, definition: { ...snapshot.definition, title: `${snapshot.definition.title || 'Dashboard'} · copy` } }); activate(record.state.definition, record); }
        catch (failure) { setStatus(failure instanceof Error ? failure.message : 'A new draft could not be saved.'); }
      })()}>Save as new draft</Button></Actions></MessageBar> : null}
      {dataContext ? <Actions><Muted>{dataContext.sourcetype ? `Sourcetype: ${dataContext.sourcetype}` : dataContext.query ? 'Using your existing search' : 'All sourcetypes in the selected index'}</Muted>
        <ControlGroup label="Preview range"><Select value={dataContext.earliest} disabled={thinking} onChange={(_event, { value }) => setDataContext({ ...dataContext, earliest: value as DataScope['earliest'] })}>
          {previewRanges.map(range => <Select.Option key={range.value} {...range}/>)}</Select></ControlGroup></Actions> : null}
      {selecting?<Muted role="status">Select an element on the canvas to focus the conversation. Escape cancels; the focus list also supports keyboard selection.</Muted>:null}
      {pagesOf(revision.definition,pagePurposes).find(page=>page.id===(activeTab||pagesOf(revision.definition)[0]?.id))?.purpose?<Muted>{pagesOf(revision.definition,pagePurposes).find(page=>page.id===(activeTab||pagesOf(revision.definition)[0]?.id))?.purpose}</Muted>:null}
      {empty ? <EmptyCanvas $floating={floating && !collapsed} aria-label="New dashboard canvas">
        <h2>{thinking ? 'Building from your data…' : hasConversation ? 'Let’s answer your question.' : 'Start with your Splunk data.'}</h2>
        <Muted>{hasConversation ? 'The canvas will update as we inspect the data and build your dashboard.' : 'Choose an index, bring an existing search, or describe the question this dashboard should answer.'}</Muted>
        {!hasConversation ? <><Actions><Button appearance="primary" disabled={!storageReady || !isSplunk()} onClick={() => { modalReturnFocus.current = document.activeElement as HTMLElement; setDataChooser({}); }}>Choose Splunk data</Button>
          <Button disabled={!storageReady || !isSplunk()} onClick={() => { modalReturnFocus.current = document.activeElement as HTMLElement; setDataChooser({ scope: { query: '', language: 'spl', earliest: '-24h' } }); }}>Use an existing search</Button></Actions>
          <IdeaGrid>{instanceIdeas(discovery).map(idea => <IdeaButton key={idea.prompt} disabled={!storageReady} onClick={() => { modalReturnFocus.current = document.activeElement as HTMLElement; setDataChooser({ scope: idea.scope, goal: idea.prompt }); }}>
          <IdeaText><strong>{idea.label}</strong><span>{idea.reason}</span></IdeaText>
        </IdeaButton>)}</IdeaGrid><Muted>{discovery ? discovery.warning || 'Suggested from this instance’s recent activity and visible catalog. We inspect fields before building.' : isSplunk() ? 'Checking the data available in this Splunk instance…' : 'Open the installed Splunk app to discover real data.'}</Muted></> : null}
        {connection?.capabilities?.images ? <Actions><Button onClick={() => { setCollapsed(false); attachmentInput.current?.click(); }} disabled={thinking}>{connection.capabilities.pdf ? 'Start from a sketch or PDF' : 'Start from a sketch'}</Button></Actions> : null}
      </EmptyCanvas> : <Preview definition={revision.definition} revision={revision.number} tokens={tokens} activeTab={activeTab} onTokens={onTokens} onTab={onTab} onSelect={onSelect} searchResults={searches.results} searchVersion={searches.version} selected={selected} selecting={selecting}/> }
      {searches.status ? <Muted role="status">{searches.status}</Muted> : null}
      {status ? <Muted role="status">{status}</Muted> : null}{saved ? <Link to={saved.url} openInNewContext appearance="standalone">Open saved dashboard in native Studio</Link> : null}
      </Canvas>
      <Conversation ref={conversationElement} style={{ height: panelHeight }} $floating={floating} $collapsed={collapsed} aria-label="Dashboard conversation">
        <PanelHeading><h3>Let’s build</h3><Actions><Button onClick={toggleDock}>{floating ? 'Dock' : 'Float'}</Button><Button onClick={() => setCollapsed(true)} aria-label="Collapse conversation">Hide</Button></Actions></PanelHeading>
        <Muted>{(connection?.configured || connection?.keyConfigured) && connection.model ? `${providerLabel(connection.provider)} · ${connection.model}${connection.capabilities?.pdf ? ' · images and PDFs' : connection.capabilities?.images ? ' · images' : ''}` : 'Preview commands · connect a provider in Settings'}</Muted>
        <ConversationScroll ref={conversationScroll}><Transcript aria-live="polite">{messages.map(message => <Message key={message.id} $user={message.user}>{message.text}</Message>)}</Transcript>
        {activity.length ? <details><summary>{thinking ? activity.at(-1) : 'Activity'}</summary><ul>{activity.map(item => <li key={item}>{item}</li>)}</ul></details> : null}
        {!empty ? <ControlGroup label="Conversation focus"><Select value={selected} filter onChange={(_event, { value }) => onSelect(String(value || ''))}>
          <Select.Option label="Whole dashboard" value=""/>{pagesOf(revision.definition).map(page=><Select.Option key={page.id} label={`Page: ${page.name}`} value={`page:${page.id}`}/>)}
          {elementsOf(revision.definition).map(item => <Select.Option key={item.id} label={`${item.kind==='input'?'Input: ':''}${item.label}`} value={item.id}/>)}
        </Select></ControlGroup> : null}
        {!thinking && suggestions.length && (!empty || hasConversation || attachments.length) ? <PromptChoices aria-label="Suggested next steps">
          <p>Suggested next</p>{suggestions.map((suggestion, index) => <Button key={suggestion.prompt} appearance={index === 0 ? 'secondary' : 'subtle'}
            style={{ whiteSpace: 'normal', height: 'auto', textAlign: 'left' }} title={suggestion.reason} onClick={() => choosePrompt(suggestion)}>
            {index === 0 ? <IdeaText><strong>{suggestion.label}</strong><span>{suggestion.reason}</span></IdeaText> : suggestion.label}
          </Button>)}
        </PromptChoices> : null}
        </ConversationScroll><Composer onSubmit={event => { event.preventDefault(); if (!thinking) void submit(); }}><ControlGroup label={empty ? 'Describe your dashboard' : 'Ask for a change'}><TextArea inputRef={composerInput} value={prompt} disabled={!storageReady} onChange={(_event, { value }) => setPrompt(value)} rowsMin={2} rowsMax={5}/></ControlGroup><Actions><Button type="submit" appearance="primary" disabled={!prompt.trim() || thinking || !storageReady}>Send</Button>{thinking ? <Button onClick={() => { generation.current?.abort(); generation.current = null; setThinking(false); setStatus('Stopped waiting. Late results will not change the draft; an upstream request may finish.'); }}>Stop</Button> : null}<Button disabled={!storageReady || thinking || !connection?.capabilities?.images || attachments.length >= 2} onClick={() => attachmentInput.current?.click()}>{connection?.capabilities?.pdf ? 'Attach sketch or PDF' : 'Attach sketch'}</Button></Actions>
        <input ref={attachmentInput} type="file" hidden accept={connection?.capabilities?.pdf ? 'image/png,image/jpeg,image/webp,application/pdf' : 'image/png,image/jpeg,image/webp'} aria-label="Attach dashboard reference" onChange={async event => {
          const file = event.target.files?.[0]; event.target.value = ''; if (!file) return;
          try { const attachment = await readAttachment(file); setAttachments(previous => previous.length < 2 ? [...previous, attachment] : previous); }
          catch (error) { setStatus(error instanceof Error ? error.message : 'The attachment could not be read.'); }
        }}/>
        {attachments.map((attachment, index) => <Actions key={index}><Muted>{attachment.name} · ready to send</Muted><Button onClick={() => setAttachments(previous => previous.filter((_, i) => i !== index))} disabled={thinking}>Remove</Button></Actions>)}
        <Muted>{connection?.capabilities?.images ? `${connection.capabilities.pdf ? 'Images or PDF' : 'Images'} · 4 MB each · sent with your message.` : 'Files require a model with verified input support.'}</Muted></Composer>
      </Conversation>
      {collapsed ? <FloatingLauncher><Button appearance="primary" onClick={() => setCollapsed(false)}>Show conversation</Button></FloatingLauncher> : null}
    </Workspace>
    <Modal open={modal === 'source'} onRequestClose={() => setModal(null)} returnFocus={modalReturnFocus} style={{ width: 'min(720px, calc(100vw - 32px))' }}>
      <Modal.Header title="Dashboard source"/><Modal.Body><Source>{JSON.stringify(revision.definition, null, 2)}</Source></Modal.Body>
      <Modal.Footer><Button onClick={() => setModal(null)}>Close</Button></Modal.Footer>
    </Modal>
    <Modal open={modal==='link'} onRequestClose={()=>setModal(null)} returnFocus={modalReturnFocus}>
      <Modal.Header title="Private draft link"/><Modal.Body><Muted>Copy this link to reopen this page and conversation focus. It requires access as the draft owner in Splunk.</Muted><ControlGroup label="Link"><TextArea value={copiedLink} onChange={()=>{}} rowsMin={3}/></ControlGroup></Modal.Body><Modal.Footer><Button onClick={()=>setModal(null)}>Close</Button></Modal.Footer>
    </Modal>
    {modal === 'open' ? <DashboardLibrary onClose={() => setModal(null)} returnFocus={modalReturnFocus}
      onOpen={record => activate(record.state.definition, record)}
      onUpdated={record => { if (record.id === draftId) activate(record.state.definition, record, true); }}
      onDeleted={id => { if (id === draftId) activate(createBlank(), undefined, true); }}
      onNative={item => { try { activate(fromStudioXml(item.xml)); } catch (failure) { setStatus(failure instanceof Error ? failure.message : 'Dashboard could not be opened.'); } }}
      onImport={() => fileInput.current?.click()} onExample={() => activate(createStarter())}/> : null}
    <input ref={fileInput} type="file" accept=".json,application/json" hidden aria-label="Choose a Studio JSON file" onChange={async event => {
      const file = event.target.files?.[0]; event.target.value = ''; if (!file) return;
      try { if (file.size > 1_000_000) throw new Error('Choose a definition under 1 MB.'); await load(validateDefinition(JSON.parse(await file.text()))); }
      catch (failure) { setStatus(failure instanceof Error ? failure.message : 'The file could not be opened.'); }
    }}/>
    {dataChooser ? <DataChooser discovery={discovery} initial={dataChooser.scope} initialGoal={dataChooser.goal} returnFocus={modalReturnFocus}
      onClose={() => setDataChooser(null)} onBuild={async (scope, request) => { setDataContext(scope); void submit(request, scope); }}/> : null}
    {pagesOpen?<PageManager definition={revision.definition} purposes={pagePurposes} activeTab={activeTab} returnFocus={modalReturnFocus} onClose={()=>setPagesOpen(false)} onSave={(id,name,purpose)=>{
      const before=revisionRef.current,next={number:before.number+1,definition:changePage(before.definition,id,name)};
      setHistory(items=>[...items.slice(-19),before]);setFuture([]);setRevision(next);setPagePurposes(values=>({...values,[id]:purpose}));setActiveTab(id);setSelected(`page:${id}`);setSaved(null);setStatus('Page updated. Describe what you want on this page in the conversation.');
    }}/>:null}
    {settingsOpen ? <Settings onClose={() => setSettingsOpen(false)} onSaved={setConnection} returnFocus={modalReturnFocus}/> : null}
    <Modal open={environmentOpen} onRequestClose={() => setEnvironmentOpen(false)} returnFocus={modalReturnFocus}>
      <Modal.Header title="Splunk environment"/><Modal.Body>
        {environment ? <><p>Splunk {environment.version} · Dashboard Studio {environment.studioVersion}</p><p>SPL: {environment.spl} · SPL2 ad hoc: {environment.spl2.adhoc.replaceAll('_', ' ')} · SPL2 modules: {environment.spl2.modules.replaceAll('_', ' ')}</p><p>Tabs, absolute and grid layouts, inputs, tokens, drilldowns, and conditional visibility are available. {environment.features.networkGraph ? 'Network graphs and the newer custom visualization framework are available in native Studio.' : 'Network graphs and the newer custom visualization framework require Splunk 10.4.'}</p><p>Search previews use the selected bounded time range, up to 200 rows and 5 seconds per query. Result rows stay in Splunk and your browser. Custom visualizations and external navigation require native Studio.</p></> : <p>Checking the current environment and a synthetic SPL2 query…</p>}
      </Modal.Body><Modal.Footer><Button onClick={() => setEnvironmentOpen(false)}>Close</Button></Modal.Footer>
    </Modal>
  </Shell></SplunkThemeProvider>;
}
