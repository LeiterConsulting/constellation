import type { DataProfile } from './data';
export type ProfileField = DataProfile['fields'][number];
export const isMeasurement = (field: ProfileField) => field.numeric && !['identifier','category','timestamp','counter'].includes(field.context?.role || '');
export const hasMissing = (field: ProfileField) => field.coverage?.basis === 'sample_rows' && field.coverage.missing > 0;
export const unitHint = (field: ProfileField) => field.context?.unit ? `${field.context.unit} (${field.context.basis === 'user' ? 'your definition' : field.context.basis === 'platform' ? 'platform' : 'name hint'})` : 'Units unconfirmed';
export const fieldMeaning = (field: ProfileField) => field.context?.meaning ? `${field.context.meaning} (your definition)`
  : !field.context || field.context.role === 'unknown' ? 'Meaning unconfirmed'
  : `${(field.context.quantity || field.context.role).replaceAll('_',' ')} (${field.context.basis === 'platform' ? 'platform' : field.context.basis === 'user' ? 'your definition' : 'name hint'})`;
export const sampleCoverage = (field: ProfileField, rows: number) => field.coverage?.basis === 'sample_rows'
  ? `${field.present}/${rows} present · ${field.coverage.missing} missing${(field.context?.role === 'measurement' || field.numeric) && field.coverage.numeric < field.present ? ` · ${field.coverage.numeric} numeric` : ''}${field.coverage.multivalue ? ' · includes multiple values' : ''}`
  : `${field.present} observed · coverage unverified`;
