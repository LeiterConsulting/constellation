import { providerRequest } from './api';
import type { StudioDefinition } from './document';
export interface DashboardDependency { kind: string; name: string; app: string; status: 'available'|'review'|'missing'; detail: string; fingerprint?: string; }
export interface PortableLookup { kind: 'lookup'; name: string; app: 'constellation'; fields: string[]; rows: string[][]; fingerprint: string; }
export interface DependencyCheck { definition: StudioDefinition; dependencies: DashboardDependency[]; notes: string[]; blocked: boolean; lookups?: PortableLookup[]; }
export const prepareDependencies = (definition: StudioDefinition, includeReports: boolean, includeKnowledge = false) => providerRequest<DependencyCheck>('dependencies',{action:'export',definition,includeReports,includeKnowledge});
export const checkDependencies = (definition: StudioDefinition, dependencies: DashboardDependency[] = [], lookups: PortableLookup[] = []) => providerRequest<DependencyCheck>('dependencies',{action:'check',definition,dependencies,lookups});
export const importDependencies = (definition: StudioDefinition, dependencies: DashboardDependency[] = [], lookups: PortableLookup[] = []) => providerRequest<DependencyCheck>('dependencies',{action:'import',definition,dependencies,lookups});
