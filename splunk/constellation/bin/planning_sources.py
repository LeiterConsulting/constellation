"""Share compatible typed aggregates without changing any requested binding.

Only compatible stats or fixed-bin timecharts over the same verified base qualify.
Explicit projections prevent newly shared columns from changing an all-fields
consumer. Only a strict literal stats subset of raw SPL can join the pool;
different populations and other native expressions are never rewritten here.
Native source/measurement/output checks still run.
"""
import re
from creation_recipes import compile_recipe
from provider_service import ProviderError


def simple_stats(pipeline):
    """Recognize only literal independent aggregates, without other commands.

    No expression evaluation, alias guessing, row filters or generic SPL rewrite.
    The returned recipe must pass the normal verified-input compiler as well.
    """
    match = re.fullmatch(r'\s*\|\s*stats\s+(.+?)(?:\s+BY\s+([A-Za-z_][A-Za-z0-9_]*))?\s*', pipeline, re.I)
    if not match: return None
    metrics = []; position = 0
    term = re.compile(r'\s*(?:(avg|min|max|sum|median|stdev|latest|earliest|count)\(\s*([A-Za-z_][A-Za-z0-9_]*|)\s*\)|(count))\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)\s*', re.I)
    while position < len(match[1]):
        metric = term.match(match[1], position)
        if not metric: return None
        function = (metric[1] or metric[3]).lower();field = metric[2] or ''
        if not field and function != 'count': return None
        metrics.append({'function':function,'field':field,'alias':metric[4]});position = metric.end()
    if not metrics or len({m['alias'] for m in metrics}) != len(metrics): return None
    return {'kind':'stats','metrics':metrics,'groupBy':match[2] or ''}


def simple_timechart(pipeline):
    match=re.fullmatch(r'\s*\|\s*timechart\s+(?:(bins=[1-9][0-9]{0,4}|span=[1-9][0-9]{0,4}[smhdw])\s+)?(.+?)\s*',pipeline,re.I)
    if not match:return None
    recipe=simple_stats('| stats '+match[2])
    if not recipe or recipe['groupBy']:return None
    return dict(recipe,kind='timechart',header='| timechart '+(match[1]+' 'if match[1]else''))


def shared_stats(sources, pipelines, panels, profile, unbound_pool=False):
    result = dict(pipelines);buckets = []
    def projected(panel):
        kind = panel['type'];binding = panel['bindings']
        if not isinstance(binding, dict): return False
        if kind == 'splunk.singlevalue': return set(binding) == {'value'}
        if kind == 'splunk.table': return set(binding) == {'columns'} and isinstance(binding['columns'], list) and bool(binding['columns'])
        if kind in ('splunk.line','splunk.area','splunk.bar','splunk.column'):
            return set(binding) == {'x','y'} and isinstance(binding['y'], list) and bool(binding['y'])
        return False
    for source in sources:
        recipe = source.get('recipe') or simple_stats(pipelines[source['id']]) or simple_timechart(pipelines[source['id']])
        if not isinstance(recipe, dict) or recipe.get('kind') not in ('stats','timechart'): continue
        kind=recipe['kind'];group=recipe.get('groupBy','')
        header=recipe.get('header','| timechart bins=100 'if kind=='timechart'else'| stats ')
        # A raw literal aggregate must satisfy the same input/alias rules as a
        # recipe before it can join the sharing pool. Other SPL stays unchanged.
        if 'recipe' not in source:
            try:
                for offset in range(0,len(recipe['metrics']),8):
                    compile_recipe({'kind':'stats','metrics':recipe['metrics'][offset:offset+8],'groupBy':group},'splunk.table',profile,format_values=False)
            except ProviderError: continue
        consumers = [p for p in panels if p['source'] == source['id']]
        # Before composition, a fresh source pool has no consumers to preserve.
        # Bound plans must retain the stricter explicit-projection condition.
        if not unbound_pool and (not consumers or not all(projected(p) for p in consumers)): continue
        metrics = {m['alias']:m for m in recipe['metrics']}
        if group in metrics: continue
        match = next((b for b in buckets if b['kind']==kind and b['header']==header and b['group'] == group and not any(alias in b['metrics'] and b['metrics'][alias] != metric for alias,metric in metrics.items())), None)
        if match is None:
            match = {'kind':kind,'header':header,'group':group,'sources':[],'metrics':{}};buckets.append(match)
        match['sources'].append(source['id']);match['metrics'].update(metrics)
    for bucket in buckets:
        keys=[tuple(sorted((k,v)for k,v in m.items()if k!='alias'))for m in bucket['metrics'].values()]
        if len(bucket['sources'])<2 and len(set(keys))==len(keys):continue
        # Keep the original eight-metric recipe admission bound for each chunk.
        # Compatible independently calculated stats share one output population;
        # concatenation changes no aggregate, input, alias or null semantics.
        metrics=[];canonical={};copies=[];pieces=[]
        for metric in bucket['metrics'].values():
            key=tuple(sorted((k,v)for k,v in metric.items()if k!='alias'))
            if key in canonical:copies.append(metric['alias']+'='+canonical[key])
            else:canonical[key]=metric['alias'];metrics.append(metric)
        for offset in range(0,len(metrics),8):
            pipeline,_,_ = compile_recipe({'kind':'stats','metrics':metrics[offset:offset+8],'groupBy':bucket['group']},'splunk.table',profile,format_values=False)
            expression = pipeline[len('| stats '):]
            if bucket['group']: expression = expression[:-len(' BY '+bucket['group'])]
            pieces.append(expression)
        combined = bucket['header']+' '.join(pieces)+(' BY '+bucket['group'] if bucket['group'] else '')
        if copies:combined+=' | eval '+', '.join(copies)
        for sid in bucket['sources']: result[sid] = combined
    return result
