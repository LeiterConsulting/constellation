import type { DashboardContextProviderProps } from '@splunk/dashboard-context';
import type { Attachment } from './agent';
import type { DataScope } from './data';
import type { StudioDefinition } from './document';
import type { PromptSuggestion } from './prompts';
import { providerRequest } from './api';

export interface ChatMessage { id: number; user: boolean; text: string; }
export interface DraftSnapshot {
  definition: StudioDefinition; messages: ChatMessage[]; prompt: string; attachments: Attachment[];
  tokens?: DashboardContextProviderProps['initialTokenBinding']; activeTab?: string; selected: string;
  suggestions: PromptSuggestion[] | null; activity: string[]; saved: { name: string; url: string } | null;
  dataContext?: DataScope | null; searchesEnabled: boolean; pendingRequest?: string;
  pagePurposes?: Record<string, string>;
}
export interface DraftSummary { id: string; title: string; version: number; updatedAt: string; deletedAt: string | null; kind: 'draft' | 'native_backup'; }
export interface DraftRecord extends DraftSummary { state: DraftSnapshot; }
export interface DraftList { drafts: DraftSummary[]; trash: DraftSummary[]; activeId: string | null; }
export const newDraftId = () => Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, '0')).join('');
export const openDraft = (id: string) => providerRequest<DraftRecord>('drafts', { action: 'open', id });
export const readDraft = (id: string) => providerRequest<DraftRecord>('drafts', { action: 'read', id });

type Writer = (id: string, version: number, state: DraftSnapshot) => Promise<DraftRecord>;
/** Serializes saves per document; concurrent tabs still use server revision checks. */
export class DraftSync {
  private saved = new Map<string, { version: number; signature: string }>();
  private queues = new Map<string, Promise<DraftRecord>>();
  constructor(private writer: Writer = (id, version, state) => providerRequest<DraftRecord>('drafts', { action: 'save', id, version, schemaVersion: 2, state })) {}
  adopt(record: DraftRecord) { this.saved.set(record.id, { version: record.version, signature: JSON.stringify(record.state) }); }
  matches(id: string, state: DraftSnapshot) { return this.saved.get(id)?.signature === JSON.stringify(state); }
  save(id: string, state: DraftSnapshot): Promise<DraftRecord> {
    const captured = structuredClone(state);
    const signature = JSON.stringify(captured);
    const previous = this.queues.get(id) || Promise.resolve();
    const task = previous.catch(() => undefined).then(async () => {
      const saved = this.saved.get(id);
      if (saved?.signature === signature) return { id, version: saved.version, state: captured } as DraftRecord;
      const record = await this.writer(id, saved?.version || 0, captured);
      this.adopt(record); return record;
    });
    this.queues.set(id, task);
    void task.finally(() => { if (this.queues.get(id) === task) this.queues.delete(id); }).catch(() => undefined);
    return task;
  }
}
