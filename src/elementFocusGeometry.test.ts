import {describe,it,expect} from 'vitest';
import {visibleFocusRects,type FocusRect} from './elementFocusGeometry';

const rect:FocusRect={id:'navigation',label:'Back',left:20,top:500,width:200,height:80};
describe('visible canvas focus targets',()=>{
  it('omits off-screen controls and admits them after native scrolling',()=>{
    expect(visibleFocusRects([rect],{width:600,height:300})).toEqual([]);
    expect(visibleFocusRects([{...rect,top:200}],{width:600,height:300})).toEqual([{...rect,top:200}]);
  });
  it('clips a partial target without changing its native input geometry',()=>{
    const original={...rect,left:-20,top:270};
    expect(visibleFocusRects([original],{width:600,height:300})).toEqual([{...original,left:0,width:180,height:30}]);
    expect(original).toEqual({...rect,left:-20,top:270});
  });
  it('does not expose zero-area, invalid or wholly horizontal off-screen targets',()=>{
    expect(visibleFocusRects([{...rect,top:300},{...rect,left:700,top:10},{...rect,top:NaN}],{width:600,height:300})).toEqual([]);
  });
});
