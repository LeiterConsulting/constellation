export type FocusRect={id:string;label:string;left:number;top:number;width:number;height:number};

/** Off-screen controls must not become invisible keyboard/click targets. */
export function visibleFocusRects(rects:FocusRect[],viewport:{width:number;height:number}):FocusRect[] {
  if(!Number.isFinite(viewport.width)||!Number.isFinite(viewport.height)||viewport.width<=0||viewport.height<=0)return [];
  return rects.flatMap(rect=>{
    if(![rect.left,rect.top,rect.width,rect.height].every(Number.isFinite)||rect.width<=0||rect.height<=0)return [];
    const left=Math.max(0,rect.left),top=Math.max(0,rect.top);
    const width=Math.min(viewport.width,rect.left+rect.width)-left;
    const height=Math.min(viewport.height,rect.top+rect.height)-top;
    return width>0&&height>0?[{...rect,left,top,width,height}]:[];
  });
}
