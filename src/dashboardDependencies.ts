import { providerRequest } from './api';
import type { StudioDefinition } from './document';
export interface DashboardDependency { kind: string; name: string; app: string; status: 'available'|'review'|'missing'; detail: string; fingerprint?: string; }
export interface DependencyCheck { definition: StudioDefinition; dependencies: DashboardDependency[]; notes: string[]; blocked: boolean; }
export const prepareDependencies = (definition: StudioDefinition, includeReports: boolean) => providerRequest<DependencyCheck>('dependencies',{action:'export',definition,includeReports});
export const checkDependencies = (definition: StudioDefinition, dependencies: DashboardDependency[] = []) => providerRequest<DependencyCheck>('dependencies',{action:'check',definition,dependencies});
