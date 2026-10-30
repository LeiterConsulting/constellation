"""Verify a larger source pool before asking a smaller model to bind panels.

Both calls belong to the existing recovery session. No partial dashboard is
staged, persisted or delivered, and indexed values never enter the next prompt.
"""
import copy
import re
from compact_creation import exact, identifier
from creation_recipes import compile_recipe
from dashboard_plan import schema_for, expand, page_types
from measurement_constraints import pipeline_commands
from native_builders import BASIC
from native_intent import requested_types
from provider_service import ProviderError
from planning_sources import shared_stats


SOURCE_INSTRUCTIONS = '''Plan ONLY the shared searches for the COMPLETE original
dashboard request. Return message, changes:[ONE {op:"boardSources",sources:[{id,
recipe}]}], suggestions:[]. Do not create pages or panels yet.
The server will verify these searches, then request page composition internally.
Include ALL calculations needed anywhere in the original goal. Prefer a small
shared pool: independent overall KPI aggregates with groupBy:""; a separate
per-entity summary with its verified groupBy; shared timecharts; a raw detail
table only where requested. Reuse outputs rather than one query per tile.
Combine related independent metrics into the same stats/timechart, preserving
nulls and the population of each measure. Reserve room within eight expanded
sources for row-filtered detail clones and any native graph dependencies.
Use ONLY recipes for this basic aggregate task. No pipeline/native actions.
Recipe shapes: {kind:"stats",metrics:[{function:"avg",field:"numeric_input",
alias:"mean_input"}],groupBy:"entity_or_empty"}; {kind:"timechart",metrics:[...]};
{kind:"table",columns:["_time","entity","measurement"]}. Do not add unused keys.
Metrics: avg,min,max,sum,median,stdev,count,latest,earliest. Each metric has exactly
function,field,alias. Use globally distinct aliases for different calculations.
Input fields must be exact
verified names, never output aliases. Give outputs stable distinct aliases and
include every requested min/max/average/count. Count with field:"" counts all
source observations; count with a measurement field counts that measurement.
An overall KPI source MUST NOT group by entity. Never reduce an overall value
to the last grouped row. A timechart includes _time and every requested series.
Never repeat or replace the server-held base. No entity/token filters: the server
adds destination-local filtering later. The server applies confirmed measurement
null masks; never overwrite, re-extract, refill or filter away a constrained input.
Independent measurements and source observations must retain their populations.
No invented data, health scores or thresholds. This is an internal plan, not a
completed dashboard or save. On feedback return the complete corrected pool for
the SAME goal. Use short stable source IDs and compact aliases; no prose outside
the response object. Actual searches still use caller permissions and existing limits.
'''

LAYOUT_INSTRUCTIONS = '''Compose the COMPLETE original dashboard using only the
verifiedSourcePool. Return message, changes:[ONE {op:"boardLayout",title,
description,pages:[{label,purpose,columns:1 or 2}],panels:[{id,page:0,type,title,
source,bindings}],links:[{from:"table_id",to:1,field:"verified_entity"}]}],suggestions:[].
Sources are held on the server: do not emit, replace or modify them. Their fields
are ACTUAL verified output names. Match each panel's intended population, metric
and time grain to the right source. Overall KPIs use ungrouped summary sources;
time trends use timechart outputs, never a per-entity summary. Include EVERY
requested page, chart and calculation exactly once, with the requested names,
membership and purpose. Never substitute a different calculation or drop work.
Bind literal output aliases using the schema channels. For line/area/bar/column
use x for time/category and y for the requested numeric aliases; never mix units
or bind categorical fields as metrics. Tables project their requested columns.
Exact bindings: splunk.line/area/bar/column {x:"output",y:["numeric_output"]};
splunk.table {columns:["output_fields"]}; splunk.singlevalue {value:"numeric_output"}.
Use exact pool source IDs; choose the output with all required fields, not a
similarly named source. The compiler supplies native geometry and bindings.
For requested row navigation, links uses a TABLE panel id, destination page
index and verified entity field present in its output. The server filters ALL
destination charts before aggregation, keeps Overview independent and adds a
return button. Filtered clones count toward the eight-source expansion limit;
reuse the same sources for overview/detail where calculations match. Emit no
token syntax or separate native changes. Unknown/partial plans fail atomically.
On feedback return ONE complete corrected boardLayout against the original blank
canvas, retaining every requirement. Keep new titles short and each page purpose
one sentence under 100 characters unless the user supplied exact longer wording.
Use one short result sentence and no repeated compliance explanations.
No partial work has been delivered or saved.
'''


def recipe_goal(context):
    """Keep complex arithmetic/native families on the existing full-plan path."""
    brief=context.get('dashboardBrief',{})
    prompt=context['request']+'\n'+'\n'.join(str(brief.get(k,''))for k in ('purpose','requirements'));types=requested_types(prompt)
    for kinds in page_types(prompt).values():types.update(kinds)
    if not types<=set(BASIC):return False
    complex_goal=r'\b(?:outliers?|percentiles?|p\d{2,3}|forecast\w*|predict\w*|moving|rolling|cumulative|ratios?|rates?|deriv\w*|delta|sparklines?|joins?|lookups?|transactions?|distinct|dc|convert\w*|correlat\w*|split)\b|\btimechart\b[^.!?\n]{0,80}\bby\b'
    return not re.search(complex_goal,prompt,re.I)


def source_schema(context):
    sources = copy.deepcopy(schema_for(context)['properties']['sources'])
    recipe=sources['items']['anyOf'][1]
    for variant in recipe['properties']['recipe']['anyOf']:
        metrics=variant['properties'].get('metrics')
        if metrics:metrics['items']=metrics['items']['anyOf'][0]
    sources['items']=recipe
    return {'type':'object','properties':{'op':{'type':'string','enum':['boardSources']},'sources':sources},
            'required':['op','sources'],'additionalProperties':False}


def source_actions(actions, context, server_pool=False):
    if not isinstance(actions,list) or len(actions)!=1:
        raise ProviderError('Return one complete boardSources plan for all requested calculations.',422,'board_sources')
    action=actions[0];exact(action,('op','sources'))
    if action['op']!='boardSources' or not isinstance(action['sources'],list) or not 1<=len(action['sources'])<=8:
        raise ProviderError('Use one shared source pool with at most eight searches including room for detail clones.',422,'board_sources')
    compiled=[];ids=set()
    for source in action['sources']:
        if not server_pool and (not isinstance(source,dict)or 'pipeline'in source):
            raise ProviderError('Use verified stats/timechart/table recipes for this basic source plan, not raw pipelines.',422,'board_sources')
        exact(source,('id','recipe') if isinstance(source,dict)and 'recipe'in source else ('id','pipeline'))
        sid=identifier(source['id'])
        if sid in ids:raise ProviderError('Give each shared source a unique ID.',422,'board_sources')
        ids.add(sid)
        if 'recipe'in source:
            kind='splunk.line'if isinstance(source['recipe'],dict)and source['recipe'].get('kind')=='timechart'else'splunk.table'
            pipeline=compile_recipe(source['recipe'],kind,context['dataProfile'],format_values=False)[0]
        else:pipeline=source['pipeline']
        if not isinstance(pipeline,str)or not pipeline.strip().startswith('|'):
            raise ProviderError('Use verified recipes or appended pipelines for the shared pool.',422,'board_sources')
        compiled.append({'op':'search','id':'ds_plan_'+sid,'pipeline':pipeline})
    return compiled


def normalize_plan(actions, context):
    """Coalesce independent aggregates before panel choices exist.

    This is a new pool, not an edit to accepted consumers. The next model sees
    the combined outputs and chooses explicit bindings against actual receipts.
    Complex pipelines and conflicting aliases remain separate.
    """
    compiled=source_actions(actions,context);sources=actions[0]['sources']
    pipelines={item['id'][len('ds_plan_'):]:item['pipeline']for item in compiled}
    merged=shared_stats(sources,pipelines,[],context['dataProfile'],unbound_pool=True)
    result=[];seen=set()
    for source in sources:
        pipeline=merged[source['id']].strip()
        if pipeline in seen:continue
        seen.add(pipeline);result.append({'id':source['id'],'pipeline':pipeline})
    return [{'op':'boardSources','sources':result}]


def pool_context(sources, receipts):
    fields={r['source']:r['fields']for r in receipts}
    return [dict(copy.deepcopy(s),fields=fields['ds_plan_'+s['id']]) for s in sources]


def layout_schema(context, sources, receipts):
    schema=copy.deepcopy(schema_for(context));schema['properties']['op']['enum']=['boardLayout']
    del schema['properties']['sources'];schema['required'].remove('sources')
    # Keep the smaller model's schema about this task: ordinary charts plus
    # every explicitly requested native family, rather than repeating unrelated
    # advanced families for every source. No requested family is removed.
    allowed=set(BASIC)|requested_types(context['request'])
    for kinds in page_types(context['request']).values():allowed.update(kinds)
    variants=[];fields={r['source']:r['fields']for r in receipts}
    for source in sources:
        names=fields['ds_plan_'+source['id']]
        if not names:continue
        recipe=source.get('recipe',{});pipeline=source.get('pipeline','')
        grouped=bool(recipe.get('groupBy'))or any(re.match(r'(?i)stats\b.*\bBY\s+',c)for _,_,c in pipeline_commands(pipeline))
        scalar_stats=recipe.get('kind')=='stats'or bool(re.match(r'^\s*\|\s*stats\b',pipeline,re.I))
        for template in schema['properties']['panels']['items']['anyOf']:
            kind=template['properties']['type']['enum'][0]
            if kind not in allowed:continue
            if kind=='splunk.singlevalue'and (grouped or not scalar_stats):continue
            if kind=='splunk.sankey'and not {'source','target'}<=set(names):continue
            item=copy.deepcopy(template);item['properties']['source']['enum']=[source['id']]
            for channel,rule in item['properties']['bindings']['properties'].items():
                selected=[n for n in names if channel not in ('y','value','size')or n!='_time']
                if rule['type']=='array':rule['items']['enum']=selected or names
                else:rule['enum']=(['']if rule.get('minLength')==0 else[])+(selected or names)
            variants.append(item)
    if not variants:raise ProviderError('The verified pool has no usable native panel bindings.',422,'board_sources')
    required=requested_types(context['request'])
    for kinds in page_types(context['request']).values():required.update(kinds)
    missing=required-{v['properties']['type']['enum'][0]for v in variants}
    if missing:raise ProviderError('The verified source pool lacks the output columns needed for '+', '.join(sorted(missing))+'. Correct the pool for every requested chart before composition.',422,'board_sources')
    schema['properties']['panels']['items']['anyOf']=variants
    return schema


def expand_layout(actions, document, context, sources, receipts=None):
    if not isinstance(actions,list)or len(actions)!=1:
        raise ProviderError('Return one complete boardLayout using the verified source pool.',422,'board_layout')
    action=actions[0];exact(action,('op','title','description','pages','panels','links'))
    if action['op']!='boardLayout':raise ProviderError('Use boardLayout with the existing verified source pool.',422,'board_layout')
    if receipts is not None:
        known={r['source'][len('ds_plan_'):]:set(r['fields'])for r in receipts}
        by_id={s['id']:s for s in sources}
        for panel in action['panels'] if isinstance(action['panels'],list)else[]:
            if not isinstance(panel,dict)or not isinstance(panel.get('source'),str)or not isinstance(panel.get('bindings'),dict):continue
            fields=set()
            for value in panel['bindings'].values():
                if isinstance(value,str)and value:fields.add(value)
                elif isinstance(value,list):fields.update(v for v in value if isinstance(v,str)and v)
            available=known.get(panel['source'],set());missing=fields-available
            if missing:raise ProviderError('Panel '+str(panel.get('id',''))[:100]+' selects '+panel['source'][:100]+' without '+', '.join(sorted(missing))[:300]+'. Choose the verified source containing those outputs; available here: '+', '.join(sorted(available))[:500]+'. A grouped summary is not a timechart.',422,'board_bindings')
            if panel.get('type')=='splunk.singlevalue':
                source=by_id.get(panel['source'],{});recipe=source.get('recipe',{});pipeline=source.get('pipeline','')
                scalar_stats=recipe.get('kind')=='stats'or bool(re.match(r'^\s*\|\s*stats\b',pipeline,re.I))
                if not scalar_stats:raise ProviderError('Overall KPI cards need the verified ungrouped stats source, not a timechart bucket or raw row.',422,'board_bindings')
    return expand([dict(action,op='boardPlan',sources=copy.deepcopy(sources))],document,context['dataProfile'],context['request'])
