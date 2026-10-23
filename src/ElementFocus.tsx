import { useEffect, useRef, useState, type RefObject } from 'react';
import { useDashboardCoreApi } from '@splunk/dashboard-context';
import styled from 'styled-components';
import { variables as v } from '@splunk/themes';
import type { StudioDefinition } from './document';
import { elementsOf, pagesOf } from './pages';

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
type Rect={id:string;label:string;left:number;top:number;width:number;height:number};

export default function ElementFocus({definition,activeTab,selected,selecting,frame,onSelect}:{
  definition:StudioDefinition;activeTab?:string;selected:string;selecting:boolean;frame:RefObject<HTMLDivElement>;onSelect:(id:string)=>void;
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
      for(const item of elementsOf(definition)) {
        if(!selecting&&item.id!==selected)continue;
        if(item.kind==='visualization') {
          const rect=api.getVisualizationDomElement(item.id)?.getBoundingClientRect();
          if(rect&&rect.width&&rect.height)next.push({id:item.id,label:item.label,left:rect.left-box.left,top:rect.top-box.top,width:rect.width,height:rect.height});
        } else if(layout?.type==='absolute'&&canvas&&layout.options?.width) {
          const position=layout.structure?.find(entry=>entry.item===item.id)?.position,scale=canvas.width/layout.options.width;
          if(position)next.push({id:item.id,label:item.label,left:canvas.left-box.left+position.x*scale,top:canvas.top-box.top+position.y*scale,width:position.w*scale,height:position.h*scale});
        }
      }
      const signature=JSON.stringify(next);if(signature!==last.current){last.current=signature;setRects(next);}
    };
    const schedule=()=>{cancelAnimationFrame(scheduled);scheduled=requestAnimationFrame(measure);};
    const resize=new ResizeObserver(schedule);resize.observe(root);
    const mutations=new MutationObserver(schedule);mutations.observe(root,{childList:true,subtree:true});
    window.addEventListener('resize',schedule);root.addEventListener('scroll',schedule,true);schedule();
    return()=>{alive=false;cancelAnimationFrame(scheduled);resize.disconnect();mutations.disconnect();window.removeEventListener('resize',schedule);root.removeEventListener('scroll',schedule,true);};
  },[api,definition,activeTab,selected,selecting,frame]);
  return <>{rects.map(({id,label,...rect})=>selecting
    ? <Target key={id} type="button" style={rect} aria-label={`Focus on ${label}`} onClick={event=>{event.stopPropagation();onSelect(id);}}><span>{label}</span></Target>
    : <Outline key={id} style={rect} aria-hidden="true"/>)}</>;
}
