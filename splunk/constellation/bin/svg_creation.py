"""Small first-map plans; existing/advanced boards retain native authoring."""
import json
import re
from provider_service import ProviderError
from search_chart_actions import identifier
from measurement_constraints import pipeline_commands,derived_eval

FIELDS=('pageLabel','purpose','mapTitle','tableTitle','pipeline','measurementField','areaField','valueField','selectionToken','clearLabel')
ACTION={'type':'object','properties':{'op':{'type':'string','enum':['svgCompose']},**{name:{'type':'string','minLength':1,'maxLength':12000 if name=='pipeline' else 1200 if name=='purpose' else 200}for name in FIELDS}},'required':['op',*FIELDS],'additionalProperties':False}
INSTRUCTIONS='''Return ONE complete svgCompose plan using plain strings. This is the first analytical board from one uploaded SVG, not a request to recreate its asset. The compiler retains its exact ID/reference and unknown properties, reuses its existing page, binds the map, adds one summary table, selected-area filtering and a clear button. No native JSON strings or separate actions.
pipeline starts with | and contains ONLY row-level search/where/eval commands deriving areaField. DO NOT include stats, fields, table or aggregation. Use where for isnull/isnotnull and other eval-function predicates; search does not evaluate those functions. measurementField is the exact inspected source measurement the user wants counted. The compiler excludes its null/masked values and counts valid readings BY areaField into valueField; you do not author that aggregation. Use inspected fields and user-defined area meanings; match svgAssets path IDs exactly. Derive a NEW area alias; never overwrite/recast measured source fields. The server applies measurement exclusions first. Never infer real geography from artwork IDs. The table repeats these counts and filters the aggregated area field with the selected token; the map stays unfiltered. Use the exact requested selectionToken, pageLabel, titles and clearLabel. Do not add token predicates to the map pipeline. The server supplies native area.click name delivery, initial All (*), explicit clear, neutral palette and nonoverlapping layout. All final search, scope, units, intent, field, shape and version validators still apply. On repair return one corrected complete plan against the original scaffold, not a partial patch. Existing/advanced changes retain native editing outside this small path.'''


def eligible(context, document):
    prompt=context['request'];items=list(document.get('visualizations',{}).values());tabs=document.get('layout',{}).get('tabs',{}).get('items',[])
    return bool(context.get('svgAssets') and context.get('dataProfile',{}).get('scope',{}).get('language','spl')=='spl'
        and len(items)==1 and items[0].get('type')=='splunk.choropleth.svg' and not items[0].get('dataSources')
        and not document.get('dataSources') and not document.get('inputs') and len(tabs)==1
        and document.get('layout',{}).get('layoutDefinitions',{}).get(tabs[0]['layoutId'],{}).get('type')=='absolute'
        and re.search(r'\b(?:build|create|make)\s+exactly\s+(?:one|1)\s+page\b',prompt,re.I)
        and re.search(r'\bexactly\s+(?:two|2)\s+visualizations\b',prompt,re.I)
        and re.search(r'\bsummary\s+table\b',prompt,re.I) and re.search(r'\bclear\s+selection\s+button\b',prompt,re.I)
        and re.search(r'\bcount\b',prompt,re.I) and not re.search(r'\b(?:avg|average|median|sum|minimum|maximum)\b',prompt,re.I)
        and not re.search(r'\b(?:grid|custom layout|background|markdown|multiselect|dropdown|animation|trellis|custom palette)\b',prompt,re.I))


def expand(actions, document, profile):
    if not isinstance(actions,list) or len(actions)!=1 or not isinstance(actions[0],dict) or set(actions[0])!=set(ACTION['required']) or actions[0].get('op')!='svgCompose':
        raise ProviderError('Return one complete svgCompose plan with plain string fields.',422,'svg_plan')
    plan=actions[0]
    for name in FIELDS:
        value=plan[name]
        if not isinstance(value,str) or not 1<=len(value)<=ACTION['properties'][name]['maxLength']:raise ProviderError('Invalid SVG plan '+name+'.',422,'svg_plan')
    for name in ('measurementField','areaField','valueField','selectionToken'):
        if not re.fullmatch(r'[A-Za-z_]\w{0,148}',plan[name]):raise ProviderError('Use simple SVG output fields and token names.',422,'svg_plan')
    fields={item['name'] for item in profile.get('fields',[])}
    if plan['measurementField'] not in fields:
        raise ProviderError('Count an exact inspected source measurement, not an invented output alias.',422,'svg_plan')
    if plan['areaField'] in fields or plan['areaField']==plan['valueField'] or plan['valueField']==plan['measurementField']:
        raise ProviderError('Use distinct new area/count aliases and retain the inspected measurement field.',422,'svg_plan')
    commands=pipeline_commands(plan['pipeline'])
    if not commands or any(not re.match(r'^(?:search|where|eval)\b',part,re.I) for _start,_end,part in commands):
        raise ProviderError('SVG count pipeline needs only row-level search/where/eval classification. Remove stats/fields/table; the server counts non-missing measurementField readings BY areaField.',422,'svg_plan')
    if any(re.match(r'^eval\b',part,re.I) and not derived_eval(part,fields) for _start,_end,part in commands):
        raise ProviderError('Create new area aliases without overwriting inspected source fields.',422,'svg_plan')
    map_id=next(iter(document['visualizations']));page_id=document['layout']['tabs']['items'][0]['layoutId']
    used=set(document['visualizations'])|set(document.get('dataSources',{}))|set(document.get('inputs',{}))
    def fresh(name):
        while name in used:name+='_'
        identifier(name);used.add(name);return name
    source,detail,table,clear=[fresh('constellation_'+name)for name in ('map','detail','summary','clear')]
    token=plan['selectionToken'];area=plan['areaField'];value=plan['valueField']
    pipeline=plan['pipeline']+' | where isnotnull('+plan['measurementField']+') AND isnotnull('+area+') | stats count AS '+value+' BY '+area
    return [
        {'op':'search','id':source,'pipeline':pipeline},
        {'op':'search','id':detail,'pipeline':pipeline+' | where $'+token+'|s$="*" OR '+area+'=$'+token+'|s$'},
        {'op':'bindSvg','id':map_id,'sourceId':source,'areaField':area,'valueField':value,'title':plan['mapTitle'],'selectionToken':token},
        {'op':'chart','id':table,'chartType':'splunk.table','sourceId':detail,'title':plan['tableTitle'],'description':'','x':'','y':[area,value]},
        {'op':'set','path':'/inputs/'+clear,'value':json.dumps({'type':'input.button','options':{'label':plan['clearLabel']},'eventHandlers':[{'type':'drilldown.setToken','options':{'tokens':[{'token':token,'value':'*'}]}}]})},
        {'op':'token','name':token,'value':'*'},
        {'op':'page','layoutId':page_id,'label':plan['pageLabel'],'purpose':plan['purpose'],'moveItems':True,'width':1200,'height':800,'items':[
            {'id':map_id,'kind':'block','x':20,'y':20,'w':560,'h':400},{'id':table,'kind':'block','x':600,'y':20,'w':580,'h':400},{'id':clear,'kind':'input','x':20,'y':440,'w':240,'h':80}]}]
