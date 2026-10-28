import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Dropdown from '@splunk/react-ui/Dropdown';
import Menu from '@splunk/react-ui/Menu';
import DraftDetails from './DraftDetails';
import SaveDashboard from './SaveDashboard';
import AgentProgress from './AgentProgress';
import { authoringRun, progressLabel, type RunProgress } from './authoringRun';
import ConversationText from './ConversationText';
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
import Brand from './Brand';
import DashboardImages from './DashboardImages';
import PortableDashboard from './PortableDashboard';
import { readPortable, type PortableDashboard as PortableFile } from './portableAssets';
import { placeDashboardImage } from './dashboardAssets';
import { applyEdit, cleanDashboardUrl, createBlank, createStarter, validateDefinition, fromStudioXml, type Edit, type Revision, type StudioDefinition } from './document';
import { isSplunk, providerRequest, providerLabel, failureActivity, type ProviderSettings } from './api';
import Settings from './Settings';
import { applyStudioChanges, readAttachment, type AgentReply, type Attachment, type Environment } from './agent';
import { useSearchPreview } from './useSearchPreview';
import { contextualPrompts, nextSuggestions, promptContextKey, suggestionFocus, type PromptSuggestion, type PromptContext } from './prompts';
import { useStarterIdeas } from './useStarterIdeas';
import { newDraftId, readDraft, openDraft, type ChatMessage as Chat, type DraftList, type DraftRecord, type DraftSnapshot, type DashboardBrief } from './drafts';
import { useDraftPersistence } from './useDraftPersistence';
import { dataScopeKey, fieldDefinitionKey, previewRanges, nativePreviewRange, type DataDiscovery, type DataProfile, type DataScope } from './data';
import DashboardLibrary from './DashboardLibrary';
import DataChooser from './DataChooser';
import PageManager from './PageManager';
import { changePage, elementsOf, pagesOf, readWorkspaceRoute, validFocus, workspaceLink, type PagePurpose } from './pages';
import { Actions, CanvasTools, ControlPopover, Canvas, CanvasHeading, Composer, Conversation, ConversationScroll, EmptyCanvas, IdeaGrid, IdeaText, IdeaButton, PromptChoices, FloatingLauncher, GlobalStyle, Header, Message, Muted, PanelHeading, Shell, Source, Transcript, Workspace } from './styles';

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
  const [brief, setBrief] = useState<DashboardBrief>({ purpose: '', requirements: '' });
  const [portable,setPortable] = useState<false | 'export' | PortableFile>(false);
  const [imagesOpen, setImagesOpen] = useState(false);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const moreFocus = useRef<HTMLButtonElement>(null);
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
  const [saveOpen, setSaveOpen] = useState(false);
  const [connection, setConnection] = useState<ProviderSettings | null>(null);
  const [connectionLoading, setConnectionLoading] = useState(isSplunk);
  const [thinking, setThinking] = useState(false);
  const generation = useRef<AbortController | null>(null);
  const [runProgress, setRunProgress] = useState<RunProgress | null>(null);
  const stop = () => { generation.current?.abort(); generation.current = null; setThinking(false); setStatus('Stopped waiting. Late results will not change this draft. A provider request may still finish upstream.'); addMessage('Stopped. No dashboard changes were applied.'); requestAnimationFrame(() => composerInput.current?.focus({ preventScroll: true })); };
  const revisionRef = useRef(revision);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [inputError, setInputError] = useState(''), [importError, setImportError] = useState('');
  const attachmentInput = useRef<HTMLInputElement>(null);
  const [proposals, setProposals] = useState<Proposals>(null);
  const [draftId, setDraftId] = useState(newDraftId);
  const [storageReady, setStorageReady] = useState(!isSplunk());
  const [unavailableDraft, setUnavailableDraft] = useState(false);
  const [storageError, setStorageError] = useState('');
  const [storageAttempt, setStorageAttempt] = useState(0);
  const [dataContext, setDataContext] = useState<DataScope | null>(null);
  const lastDataScope = useRef<DataScope | null>(null);
  const [dataProfile, setDataProfile] = useState<DataProfile | null>(null);
  const [discovery, setDiscovery] = useState<DataDiscovery | null>(null);
  const [dataChooser, setDataChooser] = useState<{ scope?: DataScope | null; goal?: string } | null>(null);
  const composerInput = useRef<HTMLTextAreaElement>(null);
  const selectionToggle = useRef<HTMLButtonElement>(null);
  const conversationLauncher = useRef<HTMLButtonElement>(null);
  const closeDialog = (close: () => void) => {
    close();
    requestAnimationFrame(() => {
      const target = modalReturnFocus.current;
      (target?.isConnected ? target : composerInput.current)?.focus({ preventScroll: true });
    });
  };
  const conversationElement = useRef<HTMLElement>(null);
  const conversationScroll = useRef<HTMLDivElement>(null);
  const [panelHeight, setPanelHeight] = useState(560);
  const [activity, setActivity] = useState<string[]>([]);
  const [environment, setEnvironment] = useState<Environment | null>(null);
  const [environmentOpen, setEnvironmentOpen] = useState(false);
  const [environmentError, setEnvironmentError] = useState('');
  const dialogOpen = !!(imagesOpen || modal || pagesOpen || settingsOpen || saveOpen || detailsOpen || environmentOpen || dataChooser);
  const previewEarliest = dataContext?.earliest || nativePreviewRange(revision.definition);
  const searches = useSearchPreview(revision.definition, tokens, previewEarliest);
  revisionRef.current = revision;
  const empty = Object.keys(revision.definition.visualizations).length === 0 && Object.keys(revision.definition.inputs || {}).length === 0;
  const hasConversation = messages.some(message => message.user);
  useEffect(() => { if (dataContext) lastDataScope.current = dataContext; }, [dataContext]);
  const starters = useStarterIdeas(discovery, isSplunk() && storageReady && empty && !hasConversation && !thinking, dataContext || lastDataScope.current);
  const sameScope = Boolean(dataContext && dataProfile && dataScopeKey(dataContext) === dataScopeKey(dataProfile.scope));
  const promptContext = useMemo<PromptContext>(() => ({ brief, messages, profile: sameScope ? dataProfile : null, results: searches.results, activeTab }), [brief,messages,sameScope,dataProfile,searches.results,activeTab]);
  const contextKey = promptContextKey(revision.number, revision.definition, selected, activeTab, dataContext, promptContext);
  const suggestions = useMemo(() => nextSuggestions(proposals?.key === contextKey ? proposals.items : [],
    contextualPrompts(revision.definition, selected, attachments.length, dataContext, pagePurposes, promptContext), promptContext), [proposals,contextKey,revision.definition,selected,attachments.length,dataContext,pagePurposes,promptContext]);
  const snapshot = useMemo<DraftSnapshot>(() => ({ definition: revision.definition, brief, messages, prompt, attachments, tokens, activeTab, selected,
    suggestions: suggestions.filter(item => item.prompt.length <= 1200), activity, saved, dataContext,
    searchesEnabled: searches.enabled, pagePurposes, pendingRequest: thinking ? [...messages].reverse().find(message => message.user)?.text || '' : '' }),
  [revision.definition, brief, messages, prompt, attachments, tokens, activeTab, selected, suggestions, activity, saved, dataContext, searches.enabled, pagePurposes, thinking]);
  const persistence = useDraftPersistence(draftId, snapshot, storageReady);
  const activate = (definition: StudioDefinition, restored?: DraftRecord, keepLibrary = false, pending = false) => {
    const nextDraftId = restored?.id || newDraftId();
    window.history.replaceState(window.history.state, '', workspaceLink(window.location.href, nextDraftId));
    generation.current?.abort(); generation.current = null; setThinking(false); searches.reset();
    setInputError(''); setImportError('');
    setHistory([]); setFuture([]); setCollapsed(false);setSelecting(false);
    const number = revisionRef.current.number + 1;
    const state = restored?.state;
    if (restored) persistence.adopt(restored, pending);
    setDraftId(nextDraftId);
    setUnavailableDraft(false); setStorageReady(true);
    setRevision({ number, definition }); setSelected(validFocus(definition,state?.selected || '')?state?.selected || '':'');
    setPagePurposes(state?.pagePurposes||{}); setBrief(state?.brief || { purpose: '', requirements: '' }); setDetailsOpen(false);
    navigationFocus.current=state?.tokens?.default?.constellation_focus;
    setTokens(state?.tokens); setActiveTab(state?.activeTab); setSaved(state?.saved || null);
    setDataContext(state?.dataContext || null); setDataProfile(null);
    const conversation = state?.messages.length ? state.messages : welcome(definition);
    setMessages(conversation); messageId.current = Math.max(0, ...conversation.map(message => message.id));
    setPrompt(state?.prompt || state?.pendingRequest || '');
    setAttachments(state?.attachments || []); setActivity(state?.activity || []);
    setProposals(state?.suggestions != null ? { key: promptContextKey(number, definition, state.selected, state.activeTab, state.dataContext, {brief:state.brief,messages:state.messages}), items: state.suggestions } : null);
    if (!keepLibrary) setModal(null);
    if (state?.searchesEnabled) searches.run();
    setStatus(state?.pendingRequest ? 'The previous request was interrupted. Your request is ready to send again; it has not been rerun.'
      : pending ? 'Recovered unsaved changes from this tab.' : restored ? 'Draft and conversation restored.' : '');
  };
  const choosePrompt = (suggestion: PromptSuggestion) => {
    const target=suggestionFocus(suggestion,revisionRef.current.definition);
    if(target)onSelect(target);
    setPrompt(suggestion.prompt); setCollapsed(false);
    requestAnimationFrame(() => composerInput.current?.focus());
  };
  useEffect(() => {
    window.history.replaceState(window.history.state, '', initialRoute.current.draft
      ? workspaceLink(window.location.href, initialRoute.current.draft) : cleanDashboardUrl(window.location.href));
    if (!isSplunk()) return;
    const controller = new AbortController();
    void providerRequest<ProviderSettings>('settings', undefined, controller.signal).then(setConnection).catch(() => { /* Settings explains connection errors on request. */ })
      .finally(() => { if (!controller.signal.aborted) setConnectionLoading(false); });
    void providerRequest<DataDiscovery>('discovery', undefined, controller.signal).then(setDiscovery).catch(() => { /* An existing search remains available in the data chooser. */ });
    void providerRequest<Environment>('environment', undefined, controller.signal).then(setEnvironment).catch(() => { /* Explicit Environment checks can retry and explain access errors. */ });
    void (async () => {
      try {
        setStorageError('');
        const list = await providerRequest<DraftList>('drafts', undefined, controller.signal);
        const requested=initialRoute.current.draft||list.activeId||draftId;
        const server = list.drafts.some(item => item.id === requested)
          ? await (initialRoute.current.draft ? openDraft(requested) : readDraft(requested)) : null;
        if (controller.signal.aborted) return;
        const restored = persistence.restore(list.owner || '', requested, server, list.trash.some(item => item.id === requested));
        if (restored) {
          const { record, pending } = restored;
          if (!controller.signal.aborted) {
            const route=initialRoute.current;
            activate(record.state.definition, record, false, pending);
            if(route.page&&pagesOf(record.state.definition).some(page=>page.id===route.page))setActiveTab(route.page);
            if(route.focus&&validFocus(record.state.definition,route.focus))setSelected(route.focus);
          }
        } else if(initialRoute.current.draft) {
          setUnavailableDraft(true);
          return;
        }
        setStorageReady(true);
      } catch (failure) { if (!controller.signal.aborted) setStorageError(failure instanceof Error ? failure.message : 'Drafts could not be restored.'); }
    })();
    return () => { controller.abort(); generation.current?.abort(); };
  }, [storageAttempt]);
  useEffect(() => {
    if (storageReady && isSplunk()) window.history.replaceState(window.history.state, '', workspaceLink(window.location.href, draftId));
  }, [draftId, storageReady]);
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
  useEffect(()=>{if(!selecting || dialogOpen)return;const escape=(event:KeyboardEvent)=>{if(event.key==='Escape'){setSelecting(false);requestAnimationFrame(()=>selectionToggle.current?.focus({preventScroll:true}));}};window.addEventListener('keydown',escape);return()=>window.removeEventListener('keydown',escape);},[selecting,dialogOpen]);
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
    try { if (!unavailableDraft && !await persistence.flush()) return false; activate(definition); return true; } finally { setBusy(false); }
  };
  const submit = async (request?: string, scopeOverride?: DataScope) => {
    const text = (request || prompt).trim(); if (!text || !storageReady || connectionLoading) return;
    if (text.length > 8000) { setInputError('Keep each message within 8,000 characters.'); return; }
    if (attachments.some(file => !connection?.capabilities?.[file.data.startsWith('data:application/pdf;') ? 'pdf' : 'images'])) { setInputError('Attachments were not sent. Choose a provider and model that support these file types in Settings, or remove them.'); return; }
    setInputError('');
    setPrompt(''); addMessage(text, true);
    if (!brief.purpose) setBrief(previous => ({ ...previous, purpose: text }));
    if ((connection?.configured || connection?.keyConfigured) && connection.model) {
      const controller = new AbortController(); generation.current = controller; setThinking(true); setStatus(`${empty ? 'Building' : 'Working'} with ${providerLabel(connection.provider)}…`);
      setActivity([empty ? 'Shaping your first dashboard…' : 'Reading the current dashboard…']); setProposals(null);
      const base = revisionRef.current;
      try {
        setRunProgress(null);
        const result = await authoringRun({
          prompt: text, revision: base.number, definition: base.definition, selected, activeTab, suggestionFormat: 'cards',
          dataContext: scopeOverride || dataContext, pagePurposes, brief, tokens,
          attachments, history: messages.filter(message => message.id !== 0).slice(-12).map(message => ({ role: message.user ? 'user' : 'assistant', text: message.text })),
        }, controller.signal, value => { if (!controller.signal.aborted) { setRunProgress(previous => previous?.stage === value.stage && JSON.stringify(previous.events) === JSON.stringify(value.events) ? previous : value); setActivity(previous => { const next = value.events.map(event => `${Math.round(event.seconds)}s · ${progressLabel({ ...value, stage: event.stage, events: [event] })}`); return previous.join("\n") === next.join("\n") ? previous : next; }); } });
        if (controller.signal.aborted) return;
        if (result.brief) setBrief(result.brief);
        if (result.dataContext) setDataContext(result.dataContext);
        if (result.dataProfile) setDataProfile(result.dataProfile);
        if(result.pagePurposes)setPagePurposes(result.pagePurposes);
        let updated = base;
        if (result.changes.length) {
          const previousRevision = revisionRef.current;
          const next = applyStudioChanges(previousRevision, result);
          setHistory(previous => [...previous.slice(-19), previousRevision]); setFuture([]); setRevision(next); setSaved(null);
          updated = next;
          setSelected(value => validFocus(next.definition,value) ? value : '');
          setStatus(result.recovery&&result.recovery.modelCalls>1?'Dashboard updated after automatic recovery.':'Dashboard updated.');
        } else setStatus(result.dataContext && fieldDefinitionKey(result.dataContext) !== fieldDefinitionKey(scopeOverride || dataContext) ? 'Field definitions updated.' : 'The agent replied. The document is unchanged.');
        setActivity([...result.activity, ...(result.validationNotes || []).map(note => `Corrected during validation: ${note}`),
          ...(result.recovery ? [`${result.recovery.modelCalls} model requests · ${result.recovery.queryChecks} search checks${typeof result.recovery.seconds==='number'?` · ${Math.round(result.recovery.seconds)} seconds`:''}.`] : [])]); setProposals({ key: promptContextKey(updated.number, updated.definition, selected, activeTab, result.dataContext || scopeOverride || dataContext, {brief:result.brief || brief,messages:[...messages,{user:true,text}]}), items: result.suggestions }); setAttachments([]); addMessage(result.message);
        if (result.dataContext && result.changes.length && !searches.enabled) searches.run();
      } catch (error) {
        if (!controller.signal.aborted) {
          setPrompt(value => value || text);
          const details = failureActivity(error); if (details.length) setActivity(details);
          setProposals({ key: promptContextKey(base.number, base.definition, selected, activeTab, scopeOverride || dataContext, {brief:brief.purpose ? brief : {...brief,purpose:text},messages:[...messages,{user:true,text}]}), items: [{ label: 'Retry your request', prompt: text, reason: 'Retry the original goal against the current verified data. Your draft is retained.', kind: 'refine' }] });
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
  const openPicker = async (target: HTMLElement) => {
    modalReturnFocus.current = target;
    if (unavailableDraft || await persistence.flush()) setModal('open');
  };
  return <SplunkThemeProvider family="enterprise" colorScheme={theme} density="compact"><GlobalStyle/><Shell>
    <Header><Brand/><Actions style={{ marginLeft: 'auto' }}>
      <Button onClick={event => { modalReturnFocus.current = event.currentTarget; setSettingsOpen(true); }} disabled={!isSplunk()}>Settings</Button>
      <Button onClick={() => void load(createBlank())} disabled={busy || (!storageReady && !unavailableDraft)}>New dashboard</Button>
      <Button onClick={event => void openPicker(event.currentTarget)} disabled={busy || thinking || (!storageReady && !unavailableDraft)}>Dashboards</Button>
      <Button appearance="primary" onClick={event => { modalReturnFocus.current = event.currentTarget; void persistence.flush().then(ok => { if (ok) setSaveOpen(true); }); }} disabled={busy || !isSplunk() || empty || thinking || !storageReady}>Save to Splunk</Button>
      <Dropdown focusToggleReasons={['escapeKey', 'tabKey', 'toggleClick']} toggle={<Button elementRef={moreFocus} isMenu>More</Button>}><Menu style={{ width: 220 }}>
        <Menu.Item disabled={thinking || !storageReady || !isSplunk()} onClick={() => { modalReturnFocus.current = moreFocus.current; setImagesOpen(true); }}>Images and icons</Menu.Item>
        <Menu.Item disabled={thinking || !storageReady} onClick={() => { modalReturnFocus.current = moreFocus.current; void persistence.flush().then(ok => { if (ok) setDetailsOpen(true); }); }}>Draft details and history</Menu.Item>
        <Menu.Item disabled={empty || !isSplunk() || thinking} onClick={() => void (async () => { if (!await persistence.flush()) return; const link = workspaceLink(window.location.href, draftId, activeTab, selected || undefined); try { await navigator.clipboard.writeText(link); setStatus('Copied a private draft link. Splunk access is required.'); } catch { setCopiedLink(link); modalReturnFocus.current = moreFocus.current; setModal('link'); } })()}>Copy draft link</Menu.Item>
        <Menu.Item onClick={exportJson}>Export JSON</Menu.Item>
        <Menu.Item disabled={!isSplunk() || thinking || !storageReady} onClick={()=>{modalReturnFocus.current=moreFocus.current;setPortable('export');}}>Export with assets</Menu.Item>
        <Menu.Item onClick={() => { modalReturnFocus.current = moreFocus.current; setModal('source'); }}>Show source</Menu.Item>
        <Menu.Item disabled={!isSplunk() || thinking} onClick={() => { modalReturnFocus.current = moreFocus.current; setEnvironmentOpen(true); setEnvironmentError(''); void providerRequest<Environment>('environment', { probe: true }).then(setEnvironment).catch(error => setEnvironmentError(error instanceof Error ? error.message : 'Environment discovery failed.')); }}>Environment</Menu.Item>
        <Menu.Item onClick={() => setTheme(previous => previous === 'light' ? 'dark' : 'light')}>{theme === 'light' ? 'Dark' : 'Light'} theme</Menu.Item>
      </Menu></Dropdown>
    </Actions></Header>
    {storageError ? <MessageBar type="error">{storageError}<Button onClick={() => setStorageAttempt(value => value + 1)}>Retry loading drafts</Button></MessageBar> : null}
    <Workspace $floating={floating || collapsed}>
      <Canvas><CanvasHeading><div><h2>{unavailableDraft ? 'No draft opened' : revision.definition.title || 'Untitled dashboard'}</h2><Muted role="status">{unavailableDraft ? 'Nothing has been saved.' : persistence.status}{searches.status ? ` · ${searches.status}` : ''}</Muted>{revision.definition.description ? <details><summary>About this dashboard</summary><Muted>{String(revision.definition.description)}</Muted></details> : null}</div><Actions>
        <Button disabled={thinking||!storageReady} onClick={event=>{modalReturnFocus.current=event.currentTarget;setPagesOpen(true);}}>Pages</Button>
        {!empty?<Button elementRef={selectionToggle} aria-pressed={selecting} disabled={thinking} onClick={()=>setSelecting(value=>!value)}>{selecting?'Cancel selection':'Select element'}</Button>:null}
        <Button disabled={!history.length || thinking} onClick={() => { const previous = history[history.length - 1]; setFuture(items => [...items, revision]); setHistory(items => items.slice(0, -1)); setRevision({ ...previous, number: revision.number + 1 }); setSaved(null); setStatus('Last document change undone.'); }}>Undo</Button>
        {future.length ? <Button disabled={thinking} onClick={() => { const next = future[future.length - 1]; setHistory(items => [...items, revision]); setFuture(items => items.slice(0, -1)); setRevision({ ...next, number: revision.number + 1 }); setSaved(null); setStatus('Document change restored.'); }}>Redo</Button> : null}
      </Actions></CanvasHeading>
      {!empty || hasConversation || dataContext ? <CanvasTools aria-label="Dashboard controls"><Dropdown focusToggleReasons={['escapeKey', 'tabKey', 'toggleClick']} toggle={<Button isMenu>{dataContext?.index || (dataContext ? 'Existing search' : 'Searches')} · {previewRanges.find(range => range.value === previewEarliest)?.label}</Button>}><ControlPopover aria-label="Data and preview controls">
        {!empty || hasConversation ? <Button disabled={thinking || !storageReady || !isSplunk()} onClick={event => { modalReturnFocus.current = event.currentTarget; setDataChooser({ scope: dataContext }); }}>{dataContext ? `Data: ${dataContext.index || 'existing search'}` : 'Choose Splunk data'}</Button> : null}
      {dataContext ? <><Muted>{dataContext.sourcetype ? `Sourcetype: ${dataContext.sourcetype}` : dataContext.query ? 'Using your existing search' : 'All sourcetypes in the selected index'}</Muted>
        <ControlGroup label="Preview range"><Select value={dataContext.earliest} disabled={thinking} onChange={(_event, { value }) => setDataContext({ ...dataContext, earliest: value as DataScope['earliest'] })}>
          {previewRanges.map(range => <Select.Option key={range.value} {...range}/>)}</Select></ControlGroup></> : null}
      {!dataContext && Object.values(revision.definition.dataSources || {}).some(source => ['ds.search', 'ds.spl2', 'ds.chain'].includes(source.type)) ? <Muted>Preview: {previewRanges.find(range => range.value === previewEarliest)?.label}. Native Studio keeps each saved search’s configured range.</Muted> : null}
      {searches.evidence.length ? <details><summary>Search details</summary><Muted>Complete means the query finished and its result rows fit this preview. Partial results may omit events or rows. Snapshots become stale after one minute; refresh for current data.</Muted><ul>{searches.evidence.map(item => <li key={item.id}><strong>{item.title}: {item.state}</strong><Muted>{item.detail}</Muted></li>)}</ul></details> : null}
        <Actions>        {!empty ? <Button disabled={!isSplunk() || searches.running} onClick={searches.run}>{searches.enabled ? 'Refresh searches' : 'Run searches'}</Button> : null}
        {searches.enabled ? <Button onClick={searches.pause}>Pause searches</Button> : null}
</Actions>
      </ControlPopover></Dropdown><Muted>{selecting ? 'Select an element to refine it in chat.' : pagesOf(revision.definition,pagePurposes).find(page => page.id === (activeTab || pagesOf(revision.definition)[0]?.id))?.purpose || 'Select an element to refine it in chat.'}</Muted></CanvasTools> : null}
      {importError ? <MessageBar type="error">{importError}</MessageBar> : null}
      {persistence.error ? <MessageBar type="error">{persistence.error}<Actions><Button onClick={() => void persistence.flush()}>Retry save</Button><Button disabled={thinking} onClick={() => void (async () => {
        const id = newDraftId();
        try { const record = await persistence.sync.save(id, { ...snapshot, definition: { ...snapshot.definition, title: `${snapshot.definition.title || 'Dashboard'} · copy` } }); activate(record.state.definition, record); }
        catch (failure) { setStatus(failure instanceof Error ? failure.message : 'A new draft could not be saved.'); }
      })()}>Save as new draft</Button></Actions></MessageBar> : null}
      {selecting?<Muted role="status">Select an element on the canvas to focus the conversation. Escape cancels; the focus list also supports keyboard selection.</Muted>:null}
      {unavailableDraft ? <EmptyCanvas $floating={floating && !collapsed} aria-label="Unavailable draft">
        <h2>This draft isn’t available.</h2>
        <Muted>Draft links require the original owner’s Splunk account. Open Dashboards to choose your work, or New dashboard to start.</Muted>
      </EmptyCanvas> : empty ? <EmptyCanvas $floating={floating && !collapsed} aria-label="New dashboard canvas">
        <h2>{thinking ? 'Building your dashboard…' : hasConversation ? 'Let’s answer your question.' : 'Start with your Splunk data.'}</h2>
        <Muted>{hasConversation ? 'Your dashboard will appear here as we build. Follow the conversation for progress.' : 'Choose a question your data can answer, or describe what you want to understand in the conversation.'}</Muted>
        {!hasConversation ? <><Actions><Button appearance="primary" disabled={!storageReady || !isSplunk()} onClick={event => { modalReturnFocus.current = event.currentTarget; setDataChooser({}); }}>Choose Splunk data</Button>
          <Button disabled={!storageReady || !isSplunk()} onClick={event => { modalReturnFocus.current = event.currentTarget; setDataChooser({ scope: { query: '', language: 'spl', earliest: '-24h' } }); }}>Use an existing search</Button></Actions>
          <IdeaGrid aria-label="Questions from your Splunk data">{starters.ideas.map(idea => <IdeaButton key={dataScopeKey(idea.scope)+':'+idea.prompt} title={`Based on fields: ${idea.fields?.join(', ')}`} disabled={!storageReady} onClick={() => { setDataContext(idea.scope || null); setDataProfile(idea.profile || null); setProposals(null); choosePrompt(idea); setStatus('Your question is ready in the conversation. Edit it or send to build.'); }}>
          <IdeaText><strong>{idea.label}</strong><span>{idea.reason}</span></IdeaText>
        </IdeaButton>)}</IdeaGrid><Muted role="status">{starters.loading ? 'Finding useful questions in your recent data…' : starters.ideas.length ? 'Based on inspected fields in recent data. Choose a question to edit before building.' : discovery ? discovery.warning || 'Choose data or bring an existing search to find a useful starting question.' : isSplunk() ? 'Checking the data available in this Splunk instance…' : 'Open the installed Splunk app to discover real data.'}</Muted></> : null}
        {connection?.capabilities?.images ? <Actions><Button onClick={() => { setCollapsed(false); attachmentInput.current?.click(); }} disabled={thinking}>{connection.capabilities.pdf ? 'Start from a sketch or PDF' : 'Start from a sketch'}</Button></Actions> : null}
      </EmptyCanvas> : <Preview definition={revision.definition} revision={revision.number} documentId={draftId} tokens={tokens} activeTab={activeTab} onTokens={onTokens} onTab={onTab} onSelect={onSelect} searchResults={searches.results} searchMessages={searches.messages} selected={selected} selecting={selecting} nativeTypes={environment?.visualizations} cascadingInputs={environment?.features.cascadingInputs}/> }
      {status ? <Muted role="status">{status}</Muted> : null}{saved ? <Link to={saved.url} openInNewContext appearance="standalone">Open saved dashboard in native Studio</Link> : null}
      </Canvas>
      <Conversation ref={conversationElement} style={{ height: panelHeight }} $floating={floating} $collapsed={collapsed} aria-label="Dashboard conversation">
        <PanelHeading><h3>Let’s build</h3><Actions><Button onClick={toggleDock}>{floating ? 'Dock' : 'Float'}</Button><Button onClick={() => { setCollapsed(true); requestAnimationFrame(() => conversationLauncher.current?.focus({preventScroll:true})); }} aria-label="Collapse conversation">Hide</Button></Actions></PanelHeading>
        <Muted>{connectionLoading ? 'Loading your AI connection…' : (connection?.configured || connection?.keyConfigured) && connection.model ? `${providerLabel(connection.provider)} · ${connection.model}${connection.capabilities?.pdf ? ' · images and PDFs' : connection.capabilities?.images ? ' · images' : ''}` : 'Connect a model in Settings to start building.'}</Muted>
        {!empty ? <details><summary>Focus: {elementsOf(revision.definition,tokens).find(item => item.id === selected)?.label || pagesOf(revision.definition).find(page => `page:${page.id}` === selected)?.name || "Whole dashboard"}</summary><ControlGroup label="Conversation focus"><Select value={selected} filter disabled={thinking} onChange={(_event, { value }) => onSelect(String(value || ''))}>
          <Select.Option label="Whole dashboard" value=""/>{pagesOf(revision.definition).map(page=><Select.Option key={page.id} label={`Page: ${page.name}`} value={`page:${page.id}`}/>)}
          {elementsOf(revision.definition,tokens).map(item => <Select.Option key={item.id} label={`${item.kind==='input'?'Input: ':''}${item.label}`} value={item.id}/>)}
        </Select></ControlGroup></details> : null}
        <ConversationScroll ref={conversationScroll}><Transcript aria-live="polite">{messages.map(message => <Message key={message.id} $user={message.user}>{message.user ? message.text : <ConversationText text={message.text}/>}</Message>)}</Transcript>
        {activity.length ? <details><summary>{thinking ? activity.at(-1) : 'Activity'}</summary><ul>{activity.map(item => <li key={item}>{item}</li>)}</ul></details> : null}
        {!thinking && suggestions.length && (!empty || hasConversation || attachments.length) ? <PromptChoices aria-label="Suggested next steps">
          <p>Keep exploring</p>{suggestions.map((suggestion, index) => <Button key={suggestion.prompt} appearance={index === 0 ? 'secondary' : 'subtle'}
            style={{ whiteSpace: 'normal', height: 'auto', textAlign: 'left' }} title={suggestion.reason} onClick={() => choosePrompt(suggestion)}>
            {index === 0 ? <IdeaText><strong>{suggestion.label}</strong><span>{suggestion.reason}</span></IdeaText> : suggestion.label}
          </Button>)}
        </PromptChoices> : null}
        </ConversationScroll>{thinking ? <AgentProgress progress={runProgress} onStop={stop}/> : null}<Composer onSubmit={event => { event.preventDefault(); if (!thinking) void submit(); }}><ControlGroup label={empty ? 'Describe your dashboard' : 'Ask for a change'}><TextArea inputRef={composerInput} value={prompt} disabled={!storageReady} onChange={(_event, { value }) => setPrompt(value)} rowsMin={2} rowsMax={5}/></ControlGroup><Actions><Button type="submit" appearance="primary" disabled={!prompt.trim() || thinking || !storageReady || connectionLoading}>Send</Button><Button disabled={!storageReady || thinking || !connection?.capabilities?.images || attachments.length >= 2} onClick={() => attachmentInput.current?.click()}>{connection?.capabilities?.pdf ? 'Attach sketch or PDF' : 'Attach sketch'}</Button></Actions>
        <input ref={attachmentInput} type="file" hidden accept={connection?.capabilities?.pdf ? 'image/png,image/jpeg,image/webp,application/pdf' : 'image/png,image/jpeg,image/webp'} aria-label="Attach dashboard reference" onChange={async event => {
          const file = event.target.files?.[0]; event.target.value = ''; if (!file) return;
          try { const attachment = await readAttachment(file); setProposals(null); setInputError(''); setAttachments(previous => previous.length < 2 ? [...previous, attachment] : previous); }
          catch (error) { setInputError(error instanceof Error ? error.message : 'The attachment could not be read.'); }
        }}/>
        {attachments.map((attachment, index) => <Actions key={index}><Muted>{attachment.name} · ready to send</Muted><Button onClick={() => { setAttachments(previous => previous.filter((_, i) => i !== index)); setProposals(null); setInputError(''); }} disabled={thinking}>Remove</Button></Actions>)}
        {inputError || prompt.length > 8000 ? <MessageBar type="error">{prompt.length > 8000 ? 'Keep each message within 8,000 characters.' : inputError}</MessageBar> : null}
        <Muted>{connection?.capabilities?.images ? `${connection.capabilities.pdf ? 'Images or PDF' : 'Images'} · 4 MB each · sent with your message.` : 'Files require a model with verified input support.'}</Muted></Composer>
      </Conversation>
      {collapsed ? <FloatingLauncher><Button elementRef={conversationLauncher} appearance="primary" onClick={() => { setCollapsed(false); requestAnimationFrame(() => composerInput.current?.focus({preventScroll:true})); }}>Show conversation</Button></FloatingLauncher> : null}
    </Workspace>
    <Modal open={modal === 'source'} onRequestClose={() => setModal(null)} returnFocus={modalReturnFocus} style={{ width: 'min(720px, calc(100vw - 32px))' }}>
      <Modal.Header title="Dashboard source"/><Modal.Body><Source>{JSON.stringify(revision.definition, null, 2)}</Source></Modal.Body>
      <Modal.Footer><Button onClick={() => setModal(null)}>Close</Button></Modal.Footer>
    </Modal>
    <Modal open={modal==='link'} onRequestClose={()=>setModal(null)} returnFocus={modalReturnFocus}>
      <Modal.Header title="Private draft link"/><Modal.Body><Muted>Copy this link to reopen this page and conversation focus. It requires access as the draft owner in Splunk.</Muted><ControlGroup label="Link"><TextArea value={copiedLink} onChange={()=>{}} rowsMin={3}/></ControlGroup></Modal.Body><Modal.Footer><Button onClick={()=>setModal(null)}>Close</Button></Modal.Footer>
    </Modal>
    {modal === 'open' ? <DashboardLibrary onClose={() => closeDialog(() => setModal(null))} returnFocus={modalReturnFocus}
      onOpen={record => { activate(record.state.definition, record); requestAnimationFrame(() => composerInput.current?.focus({preventScroll:true})); }}
      onUpdated={record => { if (record.id === draftId) activate(record.state.definition, record, true); }}
      onDeleted={id => { if (id === draftId) activate(createBlank(), undefined, true); }}
      onNative={item => activate(fromStudioXml(item.xml))}
      onImport={() => { setImportError(''); setModal(null); fileInput.current?.click(); }} onExample={() => activate(createStarter())}/> : null}
    <input ref={fileInput} type="file" accept=".json,application/json" hidden aria-label="Choose a dashboard file" onChange={async event => {
      const file = event.target.files?.[0]; event.target.value = ''; if (!file) return;
      try { if (file.size > 18_000_000) throw new Error('Choose a portable file under 18 MB.'); const value=JSON.parse(await file.text()); if(value?.format==='constellation-dashboard')setPortable(await readPortable(value)); else await load(validateDefinition(value)); }
      catch (failure) { setImportError(failure instanceof SyntaxError ? 'This file is not valid Studio JSON. Check the file and try again.' : failure instanceof Error ? failure.message : 'The file could not be opened.'); }
    }}/>
    {dataChooser ? <DataChooser discovery={discovery} initial={dataChooser.scope} initialGoal={dataChooser.goal ?? prompt} returnFocus={modalReturnFocus}
      onClose={() => closeDialog(() => setDataChooser(null))} onBuild={async (scope, request) => { setDataContext(scope); void submit(request, scope); }}/> : null}
    {pagesOpen?<PageManager definition={revision.definition} purposes={pagePurposes} activeTab={activeTab} returnFocus={modalReturnFocus} onClose={()=>closeDialog(()=>setPagesOpen(false))} onSave={(id,name,purpose)=>{
      const before=revisionRef.current,next={number:before.number+1,definition:changePage(before.definition,id,name)};
      setHistory(items=>[...items.slice(-19),before]);setFuture([]);setRevision(next);setPagePurposes(values=>({...values,[id]:purpose}));setActiveTab(id);setSelected(`page:${id}`);setSaved(null);setStatus('Page updated. Describe what you want on this page in the conversation.');
    }}/>:null}
    {portable ? <PortableDashboard definition={revision.definition} file={portable==='export'?undefined:portable} onImport={load} returnFocus={modalReturnFocus} onClose={()=>closeDialog(()=>setPortable(false))}/> : null}
    {imagesOpen ? <DashboardImages returnFocus={modalReturnFocus} onClose={() => closeDialog(() => setImagesOpen(false))} onChoose={asset => {
      const next=placeDashboardImage(revision.definition,asset,activeTab,selected);
        setHistory(items=>[...items.slice(-19),revision]);setFuture([]);setRevision({number:revision.number+1,definition:next.definition});setSaved(null);setImagesOpen(false);onSelect(next.id);addMessage('Updated the dashboard asset. Select it and ask for a change to refine its size or placement.');
    }}/> : null}
    {detailsOpen ? <DraftDetails id={draftId} brief={brief} scope={dataContext ? `${dataContext.index || 'Existing search'} · ${previewRanges.find(range => range.value === dataContext.earliest)?.label}` : ''} returnFocus={modalReturnFocus}
      onClose={() => { setDetailsOpen(false); requestAnimationFrame(() => modalReturnFocus.current?.focus()); }} onSave={value => { setBrief(value); setProposals(null); setStatus('Dashboard brief updated.'); }}
      onRestore={async version => { if (!await persistence.flush()) throw new Error('Save the current draft before restoring a version.'); const current = await readDraft(draftId); const record = await providerRequest<DraftRecord>('drafts', { action: 'restore_revision', id: draftId, version: current.version, revision: version }); activate(record.state.definition, record); setStatus('Earlier dashboard restored. Your conversation and the previous version are retained.'); }}/>:null}
    {settingsOpen ? <Settings onClose={() => closeDialog(() => setSettingsOpen(false))} onSaved={setConnection} returnFocus={modalReturnFocus}/> : null}
    {saveOpen ? <SaveDashboard definition={revision.definition} theme={theme} returnFocus={modalReturnFocus} onClose={() => closeDialog(() => setSaveOpen(false))} onSaved={result => { setSaved(result); setStatus('Private Studio copy saved. Open it in Studio to edit, share or use Splunk’s dashboard actions.'); }}/>:null}
    <Modal open={environmentOpen} onRequestClose={() => setEnvironmentOpen(false)} returnFocus={modalReturnFocus}>
      <Modal.Header title="Splunk environment"/><Modal.Body>
        {environmentError ? <MessageBar type="error">{environmentError} Close and reopen Environment to retry.</MessageBar> : null}
        {environment ? <><p>Splunk {environment.version} · Dashboard Studio {environment.studioVersion}</p><p>SPL: {environment.spl} · SPL2 ad hoc: {environment.spl2.adhoc.replaceAll('_', ' ')} · SPL2 modules: {environment.spl2.modules.replaceAll('_', ' ')}</p><p>Tabs, absolute and grid layouts, inputs, tokens and drilldowns are available. {environment.features.conditionalVisibility ? 'Conditional visibility is supported.' : 'Conditional visibility requires Splunk 10.2.'} {environment.features.networkGraph ? 'Network graphs and the newer custom visualization framework are available in native Studio.' : 'Network graphs and the newer custom visualization framework require Splunk 10.4.'}</p>{environment.customVisualizations ? <p>{environment.customVisualizations.status === 'available' ? `${environment.customVisualizations.items.length} accessible custom visualization definitions found${environment.customVisualizations.partial ? ' in a limited catalog' : ''}. Rendering still requires native Studio.` : 'Custom visualization discovery is unavailable to this user. Imported definitions are preserved.'}</p> : null}<p>Search previews use the selected bounded time range, up to 200 rows and 5 seconds per query. Result rows stay in Splunk and your browser. Custom visualizations and external navigation require native Studio.</p></> : !environmentError ? <p>Checking the current environment and a synthetic SPL2 query…</p> : null}
      </Modal.Body><Modal.Footer><Button onClick={() => setEnvironmentOpen(false)}>Close</Button></Modal.Footer>
    </Modal>
  </Shell></SplunkThemeProvider>;
}
