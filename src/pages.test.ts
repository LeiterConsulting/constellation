import {describe,it,expect} from 'vitest';
import {createBlank,createStarter} from './document';
import {changePage,pagesOf,validFocus,navigationTarget,workspaceLink,readWorkspaceRoute} from './pages';
import {contextualPrompts,promptContextKey} from './prompts';

describe('pages and conversation focus',()=>{
  it('adds and renames native pages while retaining existing content and unknown settings',()=>{
    const original=createStarter();original.layout.future='keep';
    const added=changePage(original,'investigation','Investigation');
    expect(pagesOf(added).at(-1)?.name).toBe('Investigation');expect(added.visualizations).toEqual(original.visualizations);
    expect(added.layout.future).toBe('keep');expect(pagesOf(original)).toHaveLength(2);
    const renamed=changePage(added,'investigation','Device details');expect(pagesOf(renamed)).toHaveLength(3);expect(pagesOf(renamed).at(-1)?.name).toBe('Device details');
    expect(()=>changePage(added,'investigation',' ')).toThrow();
  });
  it('does not hide legacy layout content when adding tabs',()=>{
    const legacy={...createBlank(),layout:{type:'absolute',structure:[{item:'old'}]}};
    expect(()=>changePage(legacy,'details','Details')).toThrow('legacy');expect(legacy.layout.structure).toHaveLength(1);
  });
  it('creates owner-restricted draft routes without copying data-derived token parameters',()=>{
    const draft='a'.repeat(32),link=workspaceLink('https://splunk/app/constellation/workspace?form.device=private&tab=old&lang=en#old',draft,'details','chart');
    expect(readWorkspaceRoute(link)).toEqual({draft,page:'details',focus:'chart'});expect(link).not.toContain('private');expect(link).not.toContain('#');expect(link).toContain('lang=en');
    expect(readWorkspaceRoute('https://splunk/?draft=bad').draft).toBeUndefined();
  });
  it('distinguishes page, input and chart focus and provides directed suggestions',()=>{
    const doc=createStarter();doc.inputs={filter:{type:'input.dropdown',options:{label:'Device'}}};
    expect(validFocus(doc,'filter')).toBe(true);expect(validFocus(doc,'page:layout_overview')).toBe(true);expect(validFocus(doc,'page:deleted')).toBe(false);
    expect(promptContextKey(1,doc,'filter')).not.toBe(promptContextKey(1,doc,''));
    expect(contextualPrompts(doc,'filter')[0].label).toBe('Refine this input');
    doc.inputs={button:{type:'input.button',options:{label:'Back'}}};
    expect(contextualPrompts(doc,'button')[1].label).toBe('Improve page navigation');
    expect(contextualPrompts(doc,'page:layout_detail',0,null,{layout_detail:'Inspect failures'})[0].reason).toBe('Inspect failures');
  });
});


describe('field-scoped navigation focus',()=>{
  it('focuses only the linked field and reads past unrelated token handlers',()=>{
    const doc=createStarter();doc.visualizations.viz_services.eventHandlers=[
      {type:'drilldown.setToken',options:{tokens:[{token:'unrelated',value:'keep'}]}},
      {type:'drilldown.setToken',options:{fields:['service'],tokens:[{token:'constellation_focus',value:'viz_trend'}]}}
    ];
    expect(navigationTarget(doc,'viz_services','service')).toBe('viz_trend');
    expect(navigationTarget(doc,'viz_services','latency')).toBeUndefined();
  });
});
