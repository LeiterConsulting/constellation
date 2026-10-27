import { afterEach, describe, expect, it, vi } from 'vitest';
import { recoverRead } from './restDelivery';
afterEach(()=>vi.useRealTimers());
describe('read delivery budget',()=>{
  it('uses the remaining original deadline for a second read',async()=>{
    vi.useFakeTimers();vi.setSystemTime(0);const remaining:number[]=[];
    const result=await recoverRead(true,30_000,undefined,async milliseconds=>{
      remaining.push(milliseconds);
      if(remaining.length===1){vi.setSystemTime(10_000);throw new TypeError('fixture-private');}
      return 'read';
    });
    expect(result).toBe('read');expect(remaining).toEqual([30_000,20_000]);
  });
  it('does not reset an exhausted deadline',async()=>{
    vi.useFakeTimers();vi.setSystemTime(0);const operation=vi.fn(async()=>{vi.setSystemTime(30_000);throw new TypeError('fixture-private');});
    await expect(recoverRead(true,30_000,undefined,operation)).rejects.toThrow('Splunk connection');expect(operation).toHaveBeenCalledTimes(1);
  });
});
