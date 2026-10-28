import { execFileSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';

describe('native option inventory', () => {
  it('matches the pinned renderer rather than an independently maintained option list', () => {
    const result = execFileSync(process.execPath, ['scripts/update_studio_inventory.cjs', '--check'], { encoding: 'utf8' });
    expect(result).toContain('29 visualization contracts');
  });
});
