import { useEffect, useRef, useState, type RefObject } from 'react';
import { useDashboardCoreApi } from '@splunk/dashboard-context';
import styled from 'styled-components';
import { variables as v } from '@splunk/themes';
import type { StudioDefinition } from './document';
import { elementsOf, pagesOf } from './pages';
import type { LabelBindings } from './elementLabels';
import { visibleFocusRects,type FocusRect } from './elementFocusGeometry';

const Target = styled.button`
  position:absolute; padding:0; margin:0; background:transparent; cursor:crosshair;
  border:2px dashed ${v.borderColor}; border-radius:${v.borderRadius};
  &:hover, &:focus-visible { outline:2px solid ${v.focusColor}; outline-offset:2px; }
  span { position:absolute; top:0; left:0; padding:${v.spacingXSmall}; max-width:100%;
    background:${v.backgroundColorSection}; color:${v.contentColorDefault}; font-size:${v.fontSizeSmall}; overflow-wrap:anywhere; }
`;
const Outline = styled.div`
  position:absolute; pointer-events:none; outline:2px solid ${v.focusColor}; outline-offset:2px; border-radius:${v.borderRadius};
`;
type Rect=FocusRect;

export default function ElementFocus({definition,activeTab,selected,selecting,frame,onSelect,bindings}:{
  definition:StudioDefinition;activeTab?:string;selected:string;selecting:boolean;frame:RefObject<HTMLDivElement>;onSelect:(id:string)=>void;
  bindings?: LabelBindings;
}) {
  const api=useDashboardCoreApi(),[rects,setRects]=useState<Rect[]>([]),last=useRef('');
  useEffect(()=>{if(activeTab&&api.getActiveTab()!==activeTab)api.setActiveTab(activeTab);},[api,activeTab]);
  useEffect(()=>{if(selected&&!selecting){const frameId=requestAnimationFrame(()=>{
    const element=api.getVisualizationDomElement(selected),rect=element?.getBoundingClientRect();
    if(rect&&(rect.bottom<=0||rect.top>=window.innerHeight))element?.scrollIntoView({block:'nearest'});
  });return()=>cancelAnimationFrame(frameId);}},[api,selected,selecting,activeTab]);
  useEffect(()=>{
    const root=frame.current;if(!root)return;
    let scheduled=0,alive=true;
    const measure=()=>{
      if(!alive)return;const box=root.getBoundingClientRect();
      const page=pagesOf(definition).find(page=>page.id===(activeTab||pagesOf(definition)[0]?.id));
      const canvas=api.getCanvasDomElement(page?.id)?.getBoundingClientRect();
      const layout=(definition.layout.layoutDefinitions as Record<string,{type:string;options?:{width?:number};structure?:Array<{item:string;position?:{x:number;y:number;w:number;h:number}}>}>|undefined)?.[page?.id||''];
      const next:Rect[]=[];
      for(const item of elementsOf(definition, bindings)) {
        if(!page?.items.includes(item.id))continue;
        if(!selecting&&item.id!==selected)continue;
        if(item.kind==='visualization') {
          const rect=api.getVisualizationDomElement(item.id)?.getBoundingClientRect();
          if(rect&&rect.width&&rect.height)next.push({id:item.id,label:item.label,left:rect.left-box.left,top:rect.top-box.top,width:rect.width,height:rect.height});
        } else if(layout?.type==='absolute'&&canvas&&layout.options?.width) {
          const position=layout.structure?.find(entry=>entry.item===item.id)?.position,scale=canvas.width/layout.options.width;
          if(position)next.push({id:item.id,label:item.label,left:canvas.left-box.left+position.x*scale,top:canvas.top-box.top+position.y*scale,width:position.w*scale,height:position.h*scale});
        }
      }
      const visible=visibleFocusRects(next,box);
      const signature=JSON.stringify(visible);if(signature!==last.current){last.current=signature;setRects(visible);}
    };
    const schedule=()=>{cancelAnimationFrame(scheduled);scheduled=requestAnimationFrame(measure);};
    const wheel=(event:WheelEvent)=>{
      if(!(event.target instanceof Element)||!event.target.closest('[data-constellation-focus-target]'))return;
      const page=activeTab||pagesOf(definition)[0]?.id;
      let viewport=api.getCanvasDomElement(page);
      // Use the public canvas node and standard DOM scrolling semantics; no
      // generated Framework classes or private component state are consulted.
      while(viewport&&viewport!==root&&root.contains(viewport)){
        const style=getComputedStyle(viewport);
        if((/auto|scroll/.test(style.overflowY)&&viewport.scrollHeight>viewport.clientHeight)||(/auto|scroll/.test(style.overflowX)&&viewport.scrollWidth>viewport.clientWidth)){
          const factor=event.deltaMode===1?16:event.deltaMode===2?viewport.clientHeight:1;
          event.preventDefault();event.stopPropagation();viewport.scrollBy({top:event.deltaY*factor,left:event.deltaX*factor});return;
        }
        viewport=viewport.parentElement;
      }
    };
    const resize=new ResizeObserver(schedule);resize.observe(root);
    const mutations=new MutationObserver(schedule);mutations.observe(root,{childList:true,subtree:true});
    window.addEventListener('resize',schedule);root.addEventListener('scroll',schedule,true);schedule();
    if(selecting)root.addEventListener('wheel',wheel,{capture:true,passive:false});
    return()=>{alive=false;cancelAnimationFrame(scheduled);resize.disconnect();mutations.disconnect();window.removeEventListener('resize',schedule);root.removeEventListener('scroll',schedule,true);root.removeEventListener('wheel',wheel,true);};
  },[api,definition,activeTab,selected,selecting,frame,bindings]);
  return <>{rects.map(({id,label,...rect})=>selecting
    ? <Target key={id} type="button" style={rect} data-constellation-focus-target="" aria-label={`Focus on ${label}`} onPointerDown={event=>event.stopPropagation()} onMouseDown={event=>event.stopPropagation()} onClick={event=>{event.stopPropagation();onSelect(id);}}><span>{label}</span></Target>
    : <Outline key={id} style={rect} aria-hidden="true"/>)}</>;
}
