import { expect, it } from 'vitest';
import { createBlank } from './document';
import { elementLabel } from './elementLabels';

it('uses visible token labels and heading text without exposing IDs or evaluating model code', () => {
  const document = createBlank();
  document.inputs = { toggle: { type: 'input.button', options: { label: '$eval:NOTES_LABEL$' } } };
  document.visualizations.heading = { type: 'splunk.markdown', options: { markdown: '# Analysis\nMore text' } };
  expect(elementLabel(document, 'toggle', { eval: { NOTES_LABEL: 'Show notes' } })).toBe('Show notes');
  expect(elementLabel(document, 'toggle')).toBe('Button');
  expect(elementLabel(document, 'heading')).toBe('Analysis');
  expect((document.inputs as Record<string, { options: { label: string } }>).toggle.options.label).toBe('$eval:NOTES_LABEL$');
});
