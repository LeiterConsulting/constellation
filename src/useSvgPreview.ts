import { useEffect, useState } from 'react';
import type { StudioDefinition } from './document';
import { isPackagedImage } from './mediaReferences';
import { readPackagedAsset } from './packagedAssets';
import { svgAreaIds, svgText } from './svgAssets';

const emptyMaps:Record<string,{svg?:string;error?:string}>={};
/** Resolve only registered same-origin media in the private preview clone. */
export function useSvgPreview(definition: StudioDefinition) {
  const [state,setState]=useState<{definition:StudioDefinition;maps:Record<string,{svg?:string;error?:string}>}>();
  useEffect(()=>{
    let current=true;const maps:Record<string,{svg?:string;error?:string}>={};
    const selected=Object.entries(definition.visualizations).filter(([,item])=>item.type==='splunk.choropleth.svg'&&typeof item.options?.svg==='string'&&isPackagedImage(item.options.svg));
    void Promise.all(selected.slice(0,8).map(async([id,item])=>{
      try{const asset=await readPackagedAsset(String(item.options!.svg),'image');svgAreaIds(asset.dataURI);maps[id]={svg:svgText(asset.dataURI)};}
      catch{maps[id]={error:'Open in native Studio or replace this map with a supported, accessible SVG.'};}
    })).then(()=>{if(current)setState({definition,maps});});
    return()=>{current=false;};
  },[definition]);
  return state?.definition===definition?state.maps:emptyMaps;
}
