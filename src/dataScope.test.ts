import { describe, expect, it } from 'vitest';
import { dataScopeKey, type DataScope } from './data';

describe('report data scope identity', () => {
  const scope: DataScope = {query:'| makeresults | lookup fixture key',language:'spl',earliest:'-1h',report:{ref:'Fixture report',app:'search'}};
  it('keeps identical queries in different native report apps separate', () => {
    expect(dataScopeKey(scope)).not.toBe(dataScopeKey({...scope,report:{...scope.report!,app:'constellation'}}));
    expect(dataScopeKey(scope)).not.toBe(dataScopeKey({...scope,report:{...scope.report!,ref:'Other report'}}));
    expect(dataScopeKey(scope)).not.toBe(dataScopeKey({...scope,report:undefined}));
  });
  it('retains context across JSON persistence and excludes field notes from query identity', () => {
    expect(dataScopeKey(JSON.parse(JSON.stringify(scope)))).toBe(dataScopeKey(scope));
    expect(dataScopeKey({...scope,fieldDefinitions:{value:{unit:'W'}}})).toBe(dataScopeKey(scope));
  });
});
