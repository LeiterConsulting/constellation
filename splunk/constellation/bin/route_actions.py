"""Compile an explicit table route without delegating native wiring to a model.

This builder has no execution authority. Normal scope, output, measurement,
native and current-user search validation still runs on the compiled candidate.
"""
import copy
import hashlib
import json
import re
from provider_service import ProviderError
from page_service import compile_link, compile_button, button_label_width
from search_chart_actions import compile_filter, compile_token
from studio_contract import apply_changes
from token_service import default_token_values

ROUTE_ACTION = {'type':'object','properties':{
    'op':{'type':'string','enum':['route']},
    'sourceId':{'type':'string','description':'Existing source table ID; preserve its query and visible columns.'},
    'pageId':{'type':'string','description':'Destination page ID. All its data charts will be row-filtered.'},
    'field':{'type':'string','description':'Verified raw field also returned by the source table.'},
    'returnLabel':{'type':'string','description':'Label for a return-to-source-page button, or empty to preserve existing return navigation.'}},
    'required':['op','sourceId','pageId','field','returnLabel'],'additionalProperties':False}
BUTTON_ROUTE_ACTION = {'type':'object','properties':{
    'op':{'type':'string','enum':['buttonRoute']},'id':{'type':'string'},
    'pageId':{'type':'string','description':'Existing destination page ID.'},
    'label':{'type':'string','minLength':1,'maxLength':200}},
    'required':['op','id','pageId','label'],'additionalProperties':False}

INSTRUCTIONS = '''For a table row route to a populated page, prefer ONE op:route
{sourceId,pageId,field,returnLabel}. This creates or retargets that table FIELD's
native row navigation, safely filters ALL destination-page data charts before
aggregation, reuses a valid row token and places return navigation when returnLabel
is nonempty. An empty returnLabel leaves return buttons unchanged. sourceId is the
TABLE ID; pageId is the DESTINATION page ID. Preserve the table's query/columns.
No manual tokens, filter actions or duplicate buttons are needed for this route.
The builder clones a shared search for destination-only consumers, preserving
other pages. It supports verified scoped SPL and ordinary absolute pages; use
targeted native edits for advanced/SPL2/chain/conditional or ambiguous layouts.
For a selected EXISTING button, change only its options.label and native handlers
with set/remove or link, retaining its ID, geometry and unrelated handlers. A
button request is direct navigation, not a request to retarget table row links.'''


def focused_route(prompt, document, selected, profile, receipt, attachments):
    """Restrict explicit existing-row reroutes with all-destination filtering.

    Compound analytical/geometry edits and ambiguous page names stay general.
    The model still chooses a verified row field and concise return label.
    """
    table=document.get('visualizations',{}).get(selected,{})
    if attachments or not profile or not receipt or receipt.get('status')=='failed' or profile.get('scope',{}).get('language','spl')!='spl' or table.get('type')!='splunk.table':return None
    if not re.search(r'\b(?:retarget|redirect|reroute|change|switch)\b',prompt,re.I)or not re.search(r'\b(?:row|drilldown)\b',prompt,re.I)or not re.search(r'\bfilter\s+(?:both|every|all)\b',prompt,re.I):return None
    if not any(h.get('type')=='drilldown.switchToTab'for h in table.get('eventHandlers',[])):return None
    positive=re.sub(r'\b(?:do not|don.t|never)\b[^.!?]*','',prompt,flags=re.I)
    if re.search(r'\b(?:add|create|build|rename|remove|move|delete|calculate)\b[^.!?]{0,45}\b(?:charts?|panels?|tables?|metrics?|pages?|sources?|columns?)\b',positive,re.I):return None
    origins=[pid for pid,page in document['layout'].get('layoutDefinitions',{}).items()if any(item.get('item')==selected for item in page.get('structure',[]))]
    if len(origins)!=1:return None
    targets=[]
    for tab in document['layout'].get('tabs',{}).get('items',[]):
        label=tab.get('label','');pid=tab['layoutId']
        if pid in origins or document['layout']['layoutDefinitions'][pid].get('type')!='absolute' or not label:continue
        pattern=r'\b(?:open|(?:drilldown|route|navigation)\s+to)\s+["\u201c]?'+re.escape(label)+r'(?!\w)'
        if re.search(pattern,prompt,re.I):targets.append(pid)
    if len(targets)!=1:return None
    # Duplicate native labels are ambiguous even if one regex match was found.
    label=next(t['label']for t in document['layout']['tabs']['items']if t['layoutId']==targets[0])
    if sum(t.get('label','').casefold()==label.casefold()for t in document['layout']['tabs']['items'])!=1:return None
    from row_navigation import row_fields
    fields=row_fields(profile,receipt)
    if not fields:return None
    schema=copy.deepcopy(ROUTE_ACTION)
    for key,values in (('sourceId',[selected]),('pageId',targets),('field',fields)):schema['properties'][key]['enum']=values
    if re.search(r'\b(?:add|create|include)\b[^.!?]{0,60}\b(?:back|return)\b',positive,re.I):schema['properties']['returnLabel']['minLength']=1
    else:schema['properties']['returnLabel']['enum']=['']
    return schema


def focused_button_route(prompt, document, selected, attachments):
    button=document.get('inputs',{}).get(selected,{})
    if attachments or button.get('type')!='input.button'or not any(h.get('type')=='drilldown.switchToTab'for h in button.get('eventHandlers',[])):return None
    if not re.search(r'\b(?:change|retarget|redirect|make)\b',prompt,re.I)or not re.search(r'\b(?:open|navigate|target|link)\b',prompt,re.I):return None
    positive=re.sub(r'\b(?:do not|don.t|never)\b[^.!?]*','',prompt,flags=re.I)
    if re.search(r'\b(?:add|create|build|remove|move|resize|delete|calculate)\b',positive,re.I):return None
    pages=document['layout'].get('layoutDefinitions',{})
    origins=[pid for pid,page in pages.items()if any(item.get('item')==selected for item in page.get('structure',[]))]
    if len(origins)!=1 or pages[origins[0]].get('type')!='absolute':return None
    schema=copy.deepcopy(BUTTON_ROUTE_ACTION);schema['properties']['id']['enum']=[selected]
    schema['properties']['pageId']['enum']=list(pages)
    return schema


def compile_button_route(document,action):
    if not isinstance(action,dict)or set(action)!=set(BUTTON_ROUTE_ACTION['required'])or action.get('op')!='buttonRoute':raise ProviderError('Use exactly buttonRoute with id, pageId and label.')
    identifier=action['id'];button=document.get('inputs',{}).get(identifier,{})if isinstance(identifier,str)else{}
    if button.get('type')!='input.button'or not isinstance(action['label'],str)or not 1<=len(action['label'])<=200 or not isinstance(action['pageId'],str):
        raise ProviderError('buttonRoute needs an existing button, page ID and concise label.')
    placements=[entry for page in document['layout'].get('layoutDefinitions',{}).values()for entry in page.get('structure',[])if entry.get('item')==identifier]
    if len(placements)!=1 or placements[0].get('position',{}).get('w',0)<button_label_width(action['label']):
        raise ProviderError('The new button label must fit its existing rectangle. Use a shorter label or an explicit native resize; preserve its current placement.')
    link=compile_link(document,{'op':'link','sourceId':identifier,'pageId':action['pageId'],'targetId':'','field':'','token':''})
    return [{'op':'set','path':'/inputs/'+identifier.replace('~','~0').replace('/','~1')+'/options/label','value':json.dumps(action['label'])},link]


def compile_route(document, action, profile):
    if not isinstance(action,dict) or set(action)!=set(ROUTE_ACTION['required']) or action.get('op')!='route':
        raise ProviderError('Use the documented route fields: sourceId, pageId, field and returnLabel.')
    if any(not isinstance(action[key],str) or len(action[key])>200 for key in ('sourceId','pageId','field','returnLabel')):
        raise ProviderError('Use exact existing route IDs, a verified field and a short return label.')
    if action['returnLabel'] and not action['returnLabel'].strip():raise ProviderError('Use a readable return label or an empty string to preserve existing return controls.')
    source_id,page_id,field=action['sourceId'],action['pageId'],action['field']
    if not profile or profile.get('scope',{}).get('language','spl')!='spl' or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*',field) or field not in {f['name']for f in profile.get('fields',[])}:
        raise ProviderError('route needs an inspected SPL scope and exact verified raw row field; preserve other languages with native edits.')
    table=document.get('visualizations',{}).get(source_id,{})
    pages=document.get('layout',{}).get('layoutDefinitions',{})
    origins=[key for key,page in pages.items()if any(item.get('item')==source_id for item in page.get('structure',[]))]
    target=pages.get(page_id,{})
    if table.get('type')!='splunk.table' or len(origins)!=1 or page_id==origins[0] or target.get('type')!='absolute':
        raise ProviderError('route requires a table placed on exactly one page and a different existing absolute destination page.')
    placed={item.get('item')for item in target.get('structure',[])}
    static={'splunk.markdown','splunk.richtext','splunk.rectangle','splunk.ellipse','splunk.image'}
    charts={key:value for key,value in document['visualizations'].items()if key in placed and value.get('type')not in static}
    if not charts: raise ProviderError('Place the destination data charts before compiling a table route.')
    sources={}
    for key,chart in charts.items():
        other_pages=[pid for pid,page in pages.items()if pid!=page_id and any(item.get('item')==key for item in page.get('structure',[]))]
        bindings=chart.get('dataSources',{})
        if other_pages or chart.get('containerOptions',{}).get('visibility') or set(bindings)!={'primary'}:
            raise ProviderError('route cannot change a reused/conditional chart or ambiguous source bindings. Use explicit targeted native edits preserving other pages.')
        sid=bindings['primary']
        if document.get('dataSources',{}).get(sid,{}).get('type')!='ds.search':
            raise ProviderError('route filters scoped ds.search sources only; preserve chain/SPL2/native source semantics with targeted edits.')
        sources.setdefault(sid,[]).append(key)
    if len(sources)>8: raise ProviderError('A row route can change at most eight destination search sources in one turn.')
    occupied=set(document['visualizations'])|set(document.get('inputs',{}))|set(document.get('dataSources',{}))|set(pages)|set(default_token_values(document))
    def allocate(kind):
        seed='route_'+hashlib.sha256((source_id+'\0'+page_id+'\0'+kind).encode()).hexdigest()[:12]
        for n in range(1000):
            key=seed+('_'+str(n)if n else '')
            if key not in occupied:occupied.add(key);return key
        raise ProviderError('No bounded route namespace is available.')
    tokens={t.get('token')for handler in table.get('eventHandlers',[])if handler.get('type')=='drilldown.setToken'
            and handler.get('options',{}).get('fields')==[field]for t in handler.get('options',{}).get('tokens',[])
            if t.get('key')=='row.'+field+'.value'and isinstance(t.get('token'),str)and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,149}',t['token'])}
    values=default_token_values(document)
    reusable=sorted(t for t in tokens if values.get(t)=='*' and t not in ('__proto__','constructor','prototype'))
    token=reusable[0] if reusable else allocate('token')
    result=[];candidate=copy.deepcopy(document)
    def stage(changes):
        nonlocal candidate
        candidate=apply_changes(candidate,changes);result.extend(changes)
    escape=lambda key:key.replace('~','~0').replace('/','~1')
    if token not in values:
        defaults=copy.deepcopy(candidate.get('defaults',{}));compile_token({'op':'token','name':token,'value':'*'},defaults)
        stage([{'op':'set','path':'/defaults','value':json.dumps(defaults)}])
    # Clone searches shared with charts outside the destination, inputs or chains.
    # Rebind destination charts only; unrelated consumers keep exact source bytes.
    for sid,consumers in sources.items():
        outside=any(key not in charts and sid in item.get('dataSources',{}).values()for key,item in document['visualizations'].items())
        outside |= any(sid in item.get('dataSources',{}).values()for item in document.get('inputs',{}).values())
        outside |= any(item.get('options',{}).get('extend')==sid for item in document.get('dataSources',{}).values())
        target_sid=allocate('source_'+sid)if outside else sid
        if outside:
            stage([{'op':'set','path':'/dataSources/'+escape(target_sid),'value':json.dumps(candidate['dataSources'][sid])}])
            for key in consumers:stage([{'op':'set','path':'/visualizations/'+escape(key)+'/dataSources/primary','value':json.dumps(target_sid)}])
        stage([compile_filter({'op':'filter','sourceId':target_sid,'field':field,'token':token},candidate,profile)])
    stage([compile_link(candidate,{'op':'link','sourceId':source_id,'pageId':page_id,'targetId':'','field':field,'token':token})])
    if action['returnLabel']:
        returns=[key for key,item in candidate.get('inputs',{}).items()if key in placed and item.get('type')=='input.button'
                 and any(h.get('type')=='drilldown.switchToTab'and h.get('options',{}).get('tabId')==origins[0]for h in item.get('eventHandlers',[]))]
        if len(returns)>1: raise ProviderError('Several return buttons target the source page; select one explicitly instead of replacing unrelated navigation.')
        if returns:
            # Existing return controls retain exact position/unknown properties.
            stage([{'op':'set','path':'/inputs/'+escape(returns[0])+'/options/label','value':json.dumps(action['returnLabel'])}])
        else:
            bottom=max((item.get('position',{}).get('y',0)+item.get('position',{}).get('h',0)for item in target.get('structure',[])),default=0)+20
            stage(compile_button(candidate,{'op':'button','id':allocate('back'),'label':action['returnLabel'],'pageId':page_id,
                 'targetPageId':origins[0],'targetId':'','x':20,'y':int(bottom),'w':300,'h':80}))
    return result


def validate_route_intent(prompt, document, previous, profile, focus):
    """Explicit row-filter/return requests must hold on each revised destination.

    This conservative postcondition admits the compiler's exact SPL predicate;
    it is not a general SPL parser or natural-language requirements extractor.
    Untouched navigation and non-SPL/advanced requests retain their validators.
    """
    if not profile or profile.get('scope',{}).get('language','spl')!='spl' or focus.get('kind')=='input': return
    needs_filter=bool(re.search(r'\bfilter\b',prompt,re.I))
    needs_return=bool(re.search(r'\b(?:add|include|create)\b[^.!?]{0,100}\b(?:back|return)\b',prompt,re.I))
    if not (needs_filter or needs_return): return
    from measurement_constraints import pipeline_commands
    from search_scope import scoped_suffix
    pages=document.get('layout',{}).get('layoutDefinitions',{})
    for key,table in document['visualizations'].items():
        if table.get('type')!='splunk.table' or table.get('eventHandlers',[])==previous.get('visualizations',{}).get(key,{}).get('eventHandlers',[]):continue
        origins={pid for pid,page in pages.items()if any(item.get('item')==key for item in page.get('structure',[]))}
        handlers=table.get('eventHandlers',[])
        for handler in handlers:
            if handler.get('type')!='drilldown.switchToTab':continue
            fields=handler.get('options',{}).get('fields',[]);target=handler.get('options',{}).get('tabId')
            mappings=[(f,t.get('token'))for setter in handlers if setter.get('type')=='drilldown.setToken'and setter.get('options',{}).get('fields',[])==fields
                      for f in fields for t in setter.get('options',{}).get('tokens',[])if t.get('key')=='row.'+f+'.value'and isinstance(t.get('token'),str)]
            if not mappings:continue
            items={item.get('item')for item in pages.get(target,{}).get('structure',[])}
            charts=[v for cid,v in document['visualizations'].items()if cid in items and v.get('dataSources')]
            if needs_filter:
                filtered=bool(charts)
                for chart in charts:
                    sid=chart.get('dataSources',{}).get('primary');source=document.get('dataSources',{}).get(sid,{})
                    suffix=scoped_suffix(source.get('options',{}).get('query',''),profile)if source.get('type')=='ds.search'else None
                    commands=[]
                    for _start,_end,command in pipeline_commands(suffix or ''):
                        if re.match(r'(?:stats|timechart|chart|eventstats|streamstats)\b',command,re.I):break
                        commands.append(command)
                    filtered &= any('search '+field+'=$'+token+'|s$' in commands for field,token in mappings)
                if not filtered:raise ProviderError('Filter every requested destination chart before aggregation using the table row field/token. Prefer one route action for this table/page; an unfiltered or post-aggregate detail source is incomplete.',422,'route_filter_missing')
            if needs_return and not any(cid in items and item.get('type')=='input.button'and any(h.get('type')=='drilldown.switchToTab'and h.get('options',{}).get('tabId')in origins for h in item.get('eventHandlers',[]))for cid,item in document.get('inputs',{}).items()):
                raise ProviderError('Place return navigation on each revised row destination, targeting its source table page. Use route.returnLabel or a correctly placed native button.',422,'route_return_missing')
