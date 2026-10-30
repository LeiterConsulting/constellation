"""Larger first drafts with shared searches and explicit page membership.

The model chooses meaning, calculations and membership. This compiler owns
native bindings, geometry, source reuse and destination-local row navigation.
All existing native/search/intent checks run on the complete atomic proposal.
"""
import copy
import json
import re
from compact_creation import empty_canvas, exact, identifier
from creation_strategy import explicit_panel_count
from creation_recipes import RECIPE_PANEL, compile_recipe
from native_builders import CHANNELS, binding_schema, native_options, network_nodes, network_edges
from native_intent import requested_types
from provider_service import ProviderError

MAX_PAGES, MAX_PANELS, MAX_SOURCES = 8, 24, 8
WORDS = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8}
NUMBER = r'(?:one|two|three|four|five|six|seven|eight|[1-9][0-9]?)'

def number(value): return WORDS.get(value.lower(), int(value) if value.isdigit() else 0)

def counts(prompt):
    pages = {number(v) for v in re.findall(r'\b('+NUMBER+r')[ -](?:named\s+|distinct\s+|separate\s+)?pages?\b', prompt, re.I)}
    if len(pages) != 1: return None
    pages = next(iter(pages));total = explicit_panel_count(prompt)
    per = {number(v) for v in re.findall(r'\b('+NUMBER+r')\s+(?:charts?|panels?|tiles?|visualizations?)\s+(?:on\s+each|per)\s+page\b', prompt, re.I)}
    if len(per) > 1: return None
    per = next(iter(per)) if per else None
    if per:
        explicit = {number(v) for v in re.findall(r'\bexactly\s+('+NUMBER+r')\s+(?:total\s+)?(?:charts?|panels?|tiles?|visualizations?)\b',prompt,re.I)}
        if explicit and explicit != {pages * per}: return None
        total = pages * per
    return (pages, total, per) if total and 1 <= pages <= MAX_PAGES and pages <= total <= MAX_PANELS else None


def page_names(prompt, count):
    # Only an explicit quoted list is deterministic; prose names stay with the
    # general model and existing intent checks rather than guessed extraction.
    match = re.search(r'\bpages?\s+(?:named|called)\s+([^\n.!?]+)', prompt, re.I)
    if not match: return []
    names = re.findall(r'["“]([^"”]+)["”]', match[1])
    return names if len(names) == count and len(set(names)) == count else []


def page_types(prompt):
    result = {}
    for name, clause in re.findall(r'(?im)^\s*(?:On|In)\s+["“]([^"”]+)["”]\s*[:,]?\s+([^\n]+)', prompt):
        kinds = requested_types('Create '+clause)
        for term, kind in [('line','line'),('area','area'),('bar','bar'),('column','column'),('table','table'),('single[ -]value','singlevalue')]:
            if re.search(r'\b'+term+(r'\b' if kind in ('table','singlevalue') else r'\s+(?:chart|trend)\b'), clause, re.I): kinds.add('splunk.'+kind)
        if kinds: result.setdefault(name, set()).update(kinds)
    return {name:sorted(kinds) for name,kinds in result.items()}


def eligible(context, document):
    count = counts(context['request']);profile = context.get('dataProfile', {})
    if not count or not empty_canvas(document) or profile.get('scope', {}).get('language', 'spl') != 'spl' or profile.get('scope', {}).get('report'): return False
    pages, panels, _ = count
    if pages <= 4 and panels <= 8 and 'splunk.networkGraph' not in requested_types(context['request']): return False
    if not requested_types(context['request']) <= set(CHANNELS): return False
    brief = context.get('dashboardBrief', {})
    prompt = context['request'] + '\n' + '\n'.join(str(brief.get(k, '')) for k in ('purpose','requirements'))
    # Admission only: explicit prohibitions are not requests for unsupported
    # styling/assets. The unchanged original goal/brief still reaches the model
    # and every validator; positive clauses after a semicolon remain visible.
    clauses = re.split(r'(?<=[.!?;])\s+|\n', prompt)
    prompt = '\n'.join(c for c in clauses if not re.match(r'\s*(?:no|avoid|never|without|do not|don.t)\b', c, re.I))
    if any('splunk.'+name not in CHANNELS for name in re.findall(r'\bsplunk\.([A-Za-z][A-Za-z0-9_.]*)', prompt)): return False
    advanced = r'\b(?:dropdown|multiselect|cascad\w*|trellis|auto[- ]?refresh|conditional|visibility|markdown|images?|sketch|PDF|SPL2|uploads?|icons?|pixels?|width|height|colors?|colou?rs?|thresholds?|columnFormat|tokens?|scatter|gauges?|funnel|singlevalueicon|singlevalueradial|annotations?|rectangles?|ellipses?|richtext|legend|styling|style|stacked|stacking|precision|decimals?|theme|palette|formatting|sparklines?)\b|\$'
    if re.search(r'\b(?:no|without)\s+(?:(?:return|back)\s+)?buttons?\b|\bfilter\s+only\s+(?:one|the)\b|\b(?:shared|global)\s+(?:entity\s+)?filter\b|\bbutton[^.!?]{0,40}\b(?:named|labelled|labeled|called)\b', prompt, re.I): return False
    return not re.search(advanced, prompt, re.I)


SOURCE = {'anyOf': [
    {'type':'object','properties':{'id':{'type':'string'},'pipeline':{'type':'string'}},'required':['id','pipeline'],'additionalProperties':False},
    {'type':'object','properties':{'id':{'type':'string'},'recipe':copy.deepcopy(RECIPE_PANEL['properties']['recipe'])},'required':['id','recipe'],'additionalProperties':False},
]}
INSTRUCTIONS = '''Create the COMPLETE current dashboard with one boardPlan action:
{op:"boardPlan",title,description,pages:[{label,purpose,columns:1 or 2}],
sources:[{id,pipeline} OR {id,recipe}],panels:[{id,page:0,type,title,source,bindings}],
links:[{from:"summary_table_id",to:1,field:"verified_entity"}]}.
Page membership is an integer index; honor every requested name, count, purpose,
chart, calculation and exclusion. Declare every panel exactly once. No empty pages.
Sources are a SHARED POOL, not one search per tile. Reuse one aggregate for several
KPI/table/chart consumers whenever their population and output are the same.
An overall KPI needs ungrouped stats. A per-entity summary is a DIFFERENT source
with groupBy; never bind an overall single value to a grouped output's last row.
At most eight expanded sources, including filtered detail clones and network node
sources. Plan fewer base searches when links or a network graph need that space.
Never omit requested work to meet a budget; correct the shared plan on feedback.
A source uses pipeline starting with | appended to the verified server-held base,
OR a recipe. Never repeat the base or supply alternate index/source selectors.
Recipes: stats {kind:"stats",metrics:[{function:"avg",field:"verified_numeric",alias:"mean"}],groupBy:"entity_or_empty"};
timechart {kind:"timechart",metrics:[...]} (combined aliases, no groupBy);
table {kind:"table",columns:["_time","verified_entity","verified_measurement"]}.
Metrics: avg,min,max,sum,median,stdev,count,latest,earliest; count field:"" counts
all events, count with a field counts its observations. Only a source calculation outside recipes uses pipeline. Use explicit aliases and
SPL strings in double quotes; no SQL WHERE in stats. Preserve missing measurements.
The server applies confirmed measurement null masks before each new pipeline;
never overwrite, recast, re-extract or refill the constrained input. Independent
Wi-Fi/other measurements and source events must remain independent.
Bindings by chart type (actual OUTPUT names, not category values):
line/area/bar/column {x:"_time_or_category",y:["numeric_alias"]}; for an EXPLICIT
split timechart BY use x:"_time",y:[] so the compiler selects actual split columns,
including whatever categories exist. Never name unobserved severity columns.
table {columns:["visible_output_fields"]}, [] for all returned columns;
singlevalue {value:"one_numeric_alias"}; pie {label:"category",value:"weight"};
sankey {value:"weight"}, with EXACT source,target output columns;
punchcard {x:"category",y:"category",size:"weight"};
timeline {x:"_time_or_ISO",y:"lane",duration:"milliseconds_or_empty",category:"field_or_empty"};
parallelcoordinates {} with source projection category FIRST, then only numeric axes;
linkgraph {fields:["first","next"]}; networkGraph {source:"from_field",target:"to_field"}.
Network endpoints use literal output aliases. The server creates a node chain from
BOTH endpoint sets, aligned labels/values and uniform node size.
Two auxiliary sources are needed per distinct network edge/binding pair: an
edge-membership chain and an aligned node-styling chain. These are observed
relationships, not invented causal dependencies or traffic topology.
links:[] unless requested. A row link uses a TABLE panel id, destination PAGE INDEX
and verified entity field in the table output. The compiler filters ALL destination
sources before aggregation, isolates them from Overview and adds a return button.
Do not author token syntax or entity filters in pipelines. If a source is shared
with Overview, the detail clone consumes another source slot. Keep descriptions
and purposes concise. The compiler supplies readable native geometry and bindings.
Context is metadata, not event rows: never claim observed trends or a completed
save. Existing native, version, search, scope, measurement, output, placement and
intent validators run before ATOMIC acceptance. Unknown fields and partial plans
are rejected, never truncated. Return short message,changes:[ONE boardPlan],suggestions:[].
On feedback return ONE complete corrected plan against the ORIGINAL blank canvas,
retaining every requirement. Rejected staged work is not accepted user work.
'''


def schema_for(context):
    pages, panels, _ = counts(context['request'])
    variants = []
    for kind in CHANNELS:
        environment = context.get('environment', {})
        advertised = environment.get('visualizations')
        if isinstance(advertised, list) and kind not in advertised: continue
        if kind == 'splunk.networkGraph' and environment.get('features', {}).get('networkGraph') is False: continue
        properties = {'id':{'type':'string'},'page':{'type':'integer','enum':list(range(pages))},
                      'type':{'type':'string','enum':[kind]},'title':{'type':'string'},'source':{'type':'string'},
                      'bindings':binding_schema(kind)}
        variants.append({'type':'object','properties':properties,'required':list(properties),'additionalProperties':False})
    source_schema = copy.deepcopy(SOURCE)
    for variant in source_schema['anyOf'][1]['properties']['recipe']['anyOf']:
        metrics=variant['properties'].get('metrics')
        if metrics:metrics['items']['anyOf']=metrics['items']['anyOf'][:1]
    known = sorted({f['name'] for f in context.get('dataProfile', {}).get('fields', [])})
    if known:
        recipe = source_schema['anyOf'][1]['properties']['recipe']
        for variant in recipe.get('anyOf', [recipe]):
            properties = variant.get('properties', {})
            if 'metrics' in properties:
                for metric in properties['metrics']['items'].get('anyOf', [properties['metrics']['items']]):
                    metric['properties']['field']['enum'] = ['', *known]
            if 'groupBy' in properties: properties['groupBy']['enum'] = ['', *known]
            if 'columns' in properties: properties['columns']['items']['enum'] = known
    props = {'op':{'type':'string','enum':['boardPlan']},'title':{'type':'string'},'description':{'type':'string'},
             'pages':{'type':'array','minItems':pages,'maxItems':pages,'items':{'type':'object','properties':{
                 'label':{'type':'string'},'purpose':{'type':'string'},'columns':{'type':'integer','enum':[1,2]}},
                 'required':['label','purpose','columns'],'additionalProperties':False}},
             'sources':{'type':'array','minItems':1,'maxItems':MAX_SOURCES,'items':source_schema},
             'panels':{'type':'array','minItems':panels,'maxItems':panels,'items':{'anyOf':variants}},
             'links':{'type':'array','maxItems':4,'items':{'type':'object','properties':{
                 'from':{'type':'string'},'to':{'type':'integer','enum':list(range(pages))},'field':{'type':'string'}},
                 'required':['from','to','field'],'additionalProperties':False}}}
    return {'type':'object','properties':props,'required':list(props),'additionalProperties':False}


def expand(actions, document, profile, prompt):
    def fail(message): raise ProviderError(message, 422, 'board_plan')
    if not isinstance(actions, list) or len(actions) != 1 or not isinstance(actions[0], dict) or actions[0].get('op') != 'boardPlan':
        fail('Return ONE complete boardPlan against the original blank canvas.')
    if not empty_canvas(document) or not profile or profile.get('scope', {}).get('language', 'spl') != 'spl' or profile.get('scope', {}).get('report'):
        fail('Board planning requires the original empty inspected SPL canvas.')
    action = actions[0];exact(action, ('op','title','description','pages','sources','panels','links'))
    expected = counts(prompt)
    if not expected: fail('Use a bounded explicit page/chart count for board planning.')
    pages, total, per = expected
    if not isinstance(action['pages'], list) or len(action['pages']) != pages or not isinstance(action['panels'], list) or len(action['panels']) != total:
        fail('Complete all '+str(pages)+' pages and '+str(total)+' panels; do not repeat the full chart list on each page.')
    if not isinstance(action['sources'], list) or not 1 <= len(action['sources']) <= MAX_SOURCES or not isinstance(action['links'], list) or len(action['links']) > 4:
        fail('Plan at most eight sources including dependencies and four row routes; reuse common outputs.')
    names = page_names(prompt, pages)
    for index, page in enumerate(action['pages']):
        exact(page, ('label','purpose','columns'))
        if (not isinstance(page['label'], str) or not 1 <= len(page['label']) <= 200 or not isinstance(page['purpose'], str)
                or not 1 <= len(page['purpose']) <= 1200 or type(page['columns']) is not int or page['columns'] not in (1,2)):
            fail('Give each page its requested readable name, purpose and one/two columns.')
        if names and page['label'] != names[index]: fail('Preserve the requested page names and order: '+', '.join(names))
    if len({p['label'].casefold() for p in action['pages']}) != pages: fail('Give requested pages distinct names.')
    sources = {};declared = set()
    consumed = {p.get('source') for p in action['panels'] if isinstance(p,dict) and isinstance(p.get('source'),str)}
    for source in action['sources']:
        exact(source, ('id','recipe') if isinstance(source,dict) and 'recipe' in source else ('id','pipeline'))
        sid = identifier(source['id'])
        if sid in declared: fail('Use unique source IDs.')
        declared.add(sid)
        # Dead declarations are model staging on a blank canvas, not user work.
        # Do not compile/dispatch an unused placeholder. Every requested panel
        # and its actual consumed output still passes all final validators.
        if sid not in consumed: continue
        if 'recipe' in source:
            chart_type = 'splunk.line' if isinstance(source['recipe'], dict) and source['recipe'].get('kind') == 'timechart' else 'splunk.table'
            pipeline = compile_recipe(source['recipe'], chart_type, profile, format_values=False)[0]
        else: pipeline = source['pipeline']
        if not isinstance(pipeline, str) or not pipeline.strip().startswith('|'): fail('Each source needs an appended pipeline or verified recipe.')
        sources[sid] = pipeline
    panels = {};membership = [[] for _ in range(pages)]
    for panel in action['panels']:
        exact(panel, ('id','page','type','title','source','bindings'));pid = identifier(panel['id'])
        if pid in panels or type(panel['page']) is not int or not 0 <= panel['page'] < pages or panel['source'] not in sources or panel['type'] not in CHANNELS:
            fail('Use distinct panels, declared sources, supported types and existing page indexes.')
        if not isinstance(panel['title'], str) or not 1 <= len(panel['title']) <= 200: fail('Give each panel a readable metric/units title.')
        panels[pid] = panel;membership[panel['page']].append(pid)
    if any(not m or (per and len(m) != per) for m in membership): fail('Put every requested chart on its intended page; each page needs its requested panel count.')
    required_types = page_types(prompt)
    for index, page in enumerate(action['pages']):
        missing = set(required_types.get(page['label'], [])) - {panels[pid]['type'] for pid in membership[index]}
        if missing: fail('Page '+page['label']+' still needs its requested native families: '+', '.join(sorted(missing))+'. Preserve page membership; a chart elsewhere does not fulfill this page.')
    from planning_sources import shared_stats
    sources = shared_stats([s for s in action['sources'] if s['id'] in sources], sources, list(panels.values()), profile)
    routes = {};origins = set();known = {f['name'] for f in profile.get('fields', [])}
    for link in action['links']:
        exact(link, ('from','to','field'));source = panels.get(link['from'])
        if (not source or source['type'] != 'splunk.table' or link['from'] in origins or type(link['to']) is not int
                or not 0 <= link['to'] < pages or link['to'] == source['page'] or link['field'] not in known
                or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', link['field'])):
            fail('Connect a declared summary table to another page using its verified literal entity field.')
        if link['to'] in routes: fail('Give each row destination one unambiguous source route in this initial plan.')
        routes[link['to']] = link;origins.add(link['from'])
    taken=set(document.get('expressions',{}));route_tokens={}
    token_defaults=document.get('defaults',{}).get('tokens',{}) if routes else {}
    if not isinstance(token_defaults,dict):fail('Preserve nonstandard native token defaults with general native authoring.')
    for values in token_defaults.values():
        if isinstance(values,dict):taken.update(values)
    for page in routes:
        base='select_page_'+str(page);token=base;number=2
        while token in taken:token=base+'_'+str(number);number+=1
        route_tokens[page]=token;taken.add(token)
    changes = [{'op':'dashboard','title':action['title'],'description':action['description']}]
    pool = {};panel_sources = {};used_ids = set();node_pool = {}
    for pid,panel in panels.items():
        route = routes.get(panel['page']);filter_key = (route['field'],route_tokens[panel['page']]) if route else None
        key = (sources[panel['source']].strip(), filter_key)
        if key not in pool:
            sid = 'ds_plan_'+panel['source']+('_p'+str(panel['page']) if route else '')
            if sid in used_ids: fail('Source IDs collide after page isolation; use shorter distinct IDs.')
            used_ids.add(sid);pool[key] = sid
            changes.append({'op':'search','id':sid,'pipeline':sources[panel['source']]})
            if route: changes.append({'op':'filter','sourceId':sid,'field':filter_key[0],'token':filter_key[1]})
        panel_sources[pid] = pool[key]
    for pid,panel in panels.items():
        if panel['type'] == 'splunk.singlevalue':
            from measurement_constraints import pipeline_commands
            if any(re.match(r'(?i)stats\b.*\bBY\s+', command) for _,_,command in pipeline_commands(sources[panel['source']])):
                fail('An overall single-value panel needs an ungrouped stats output, not the last row of a per-entity summary. Share one ungrouped aggregate among the KPI cards and keep grouped summaries separate.')
        sid = panel_sources[pid];options = native_options(panel['type'], panel['bindings'], sources[panel['source']]);aliases = {'primary':sid}
        if panel['type'] == 'splunk.networkGraph':
            key = (sid,panel['bindings']['source'],panel['bindings']['target'])
            if key not in node_pool:
                node_id = 'nodes_'+pid;edge_id = 'edges_'+pid;node_source,node_options = network_nodes(sid,panel['bindings']);node_pool[key]=(node_id,edge_id,node_options)
                changes.append({'op':'set','path':'/dataSources/'+node_id,'value':json.dumps(node_source)})
                changes.append({'op':'set','path':'/dataSources/'+edge_id,'value':json.dumps(network_edges(sid,panel['bindings']))})
            node_id,edge_id,node_options = node_pool[key];aliases.update(primary=edge_id,nodeSource=node_id);options.update(node_options)
        visualization = {'type':panel['type'],'title':panel['title'],'options':options,'dataSources':aliases}
        changes.append({'op':'set','path':'/visualizations/'+pid,'value':json.dumps(visualization)})
    if len(pool)+2*len(node_pool) > MAX_SOURCES:
        fail('The expanded plan needs '+str(len(pool)+2*len(node_pool))+' affected sources; the limit is eight including filtered clones and network node dependencies. Reuse shared compatible aggregates; keep every requested page and chart.')
    for index,page in enumerate(action['pages']):
        items=[];row=column=0
        for pid in membership[index]:
            panel=panels[pid];wide = page['columns']==1 or panel['type'] in ('splunk.table','splunk.networkGraph','splunk.sankey','splunk.parallelcoordinates','splunk.timeline')
            if wide and column:row+=1;column=0
            items.append({'id':pid,'kind':'block','x':20+590*column,'y':20+380*row,'w':1160 if wide else 570,'h':360})
            column += page['columns'] if wide else 1
            if column >= page['columns']:row+=1;column=0
        bottom=20+(row+bool(column))*380
        changes.append({'op':'page','layoutId':'layout_board_'+str(index),'label':page['label'],'purpose':page['purpose'],'moveItems':False,
                        'width':1200,'height':bottom+120 if index in routes else bottom+20,'items':items})
        if index in routes:
            link=routes[index];token=route_tokens[index];origin=panels[link['from']]['page']
            changes.extend([{'op':'token','name':token,'value':'*'},
                            {'op':'link','sourceId':link['from'],'pageId':'layout_board_'+str(index),'targetId':membership[index][0],'field':link['field'],'token':token},
                            {'op':'button','id':'back_board_'+str(index),'label':('Back to '+action['pages'][origin]['label'])[:100],
                             'pageId':'layout_board_'+str(index),'targetPageId':'layout_board_'+str(origin),'targetId':'','x':20,'y':bottom,'w':300,'h':80}])
    if len(changes)>64: fail('Keep the full expanded board within the existing 64-action bound; share sources instead of dropping requested work.')
    return changes
