"""Small first-draft SPL recipes; native execution still verifies every output.

Only verified literal fields and ordinary aggregates are compiled here. Complex
queries keep the existing pipeline/native path. There is no execution authority.
"""
import re
import copy
from provider_service import ProviderError

FUNCTIONS = ('avg', 'min', 'max', 'sum', 'median', 'stdev', 'count', 'latest', 'earliest')
RECIPE = {'type': 'object', 'properties': {
    'kind': {'type': 'string', 'enum': ['stats', 'timechart', 'table']},
    'metrics': {'type': 'array', 'maxItems': 8, 'items': {'type': 'object', 'properties': {
        'function': {'type': 'string', 'enum': list(FUNCTIONS)},
        'field': {'type': 'string', 'description': 'Exact verified input field; empty only for count of all events.'},
        'alias': {'type': 'string', 'description': 'Distinct literal output name.'}},
        'required': ['function', 'field', 'alias'], 'additionalProperties': False}},
    'groupBy': {'type': 'string', 'description': 'One verified group field for stats, otherwise empty.'},
    'columns': {'type': 'array', 'maxItems': 80, 'items': {'type': 'string'},
                'description': 'Ordered verified raw fields for table; empty for aggregates.'}},
    'required': ['kind', 'metrics', 'groupBy', 'columns'], 'additionalProperties': False}
RECIPE_PANEL = {'type': 'object', 'properties': {
    'id': {'type': 'string'},
    'type': {'type': 'string', 'enum': ['splunk.line', 'splunk.area', 'splunk.column', 'splunk.bar', 'splunk.singlevalue', 'splunk.table']},
    'title': {'type': 'string'}, 'recipe': RECIPE},
    'required': ['id', 'type', 'title', 'recipe'], 'additionalProperties': False}
SCALAR_METRIC = copy.deepcopy(RECIPE['properties']['metrics']['items'])
SPARKLINE_METRIC = {'type': 'object', 'properties': {
    'function': {'type': 'string', 'enum': ['sparkline']},
    'aggregation': {'type': 'string', 'enum': ['avg', 'min', 'max', 'sum', 'count']},
    'field': {'type': 'string'}, 'alias': {'type': 'string'},
    'span': {'type': 'string', 'description': 'Positive literal time bucket such as 1h; at most 200 buckets in the selected window.'}},
    'required': ['function', 'aggregation', 'field', 'alias', 'span'], 'additionalProperties': False}
RECIPE['properties']['metrics']['items'] = {'anyOf': [SCALAR_METRIC, SPARKLINE_METRIC]}
# Models choose a calculation, not empty fields belonging to another kind.
# Runtime still accepts the older complete form, but never drops populated
# fields or unknown properties to make a rejected proposal pass.
RECIPE_PANEL['properties']['recipe'] = {'anyOf': [
    {'type': 'object', 'properties': {key: ({'type': 'string', 'enum': [kind]} if key == 'kind' else RECIPE['properties'][key]) for key in keys},
     'required': list(keys), 'additionalProperties': False}
    for kind, keys in (('stats', ('kind', 'metrics', 'groupBy')),
                       ('timechart', ('kind', 'metrics')),
                       ('table', ('kind', 'columns')))
]}
for variant in RECIPE_PANEL['properties']['recipe']['anyOf']:
    key = 'columns' if variant['properties']['kind']['enum'] == ['table'] else 'metrics'
    variant['properties'][key] = dict(variant['properties'][key], minItems=1)
FIELD = r'[A-Za-z_][A-Za-z0-9_]*'


def compile_recipe(recipe, chart_type, profile, format_values=True):
    if not isinstance(recipe, dict):
        raise ProviderError('Use one documented search recipe object.')
    required = {'stats': {'kind', 'metrics', 'groupBy'}, 'timechart': {'kind', 'metrics'}, 'table': {'kind', 'columns'}}.get(recipe.get('kind') if isinstance(recipe.get('kind'), str) else '')
    if not required or not required <= set(recipe) or not set(recipe) <= set(RECIPE['required']):
        raise ProviderError('Use stats {kind,metrics,groupBy}, timechart {kind,metrics}, or table {kind,columns}; do not invent recipe fields.')
    recipe = dict({'metrics': [], 'groupBy': '', 'columns': []}, **recipe)
    if not profile or profile.get('scope', {}).get('language', 'spl') != 'spl':
        raise ProviderError('First-draft recipes require a verified SPL scope.')
    known = {f['name']: f for f in profile.get('fields', [])}
    def field(value):
        if not isinstance(value, str) or not re.fullmatch(FIELD, value) or value not in known:
            raise ProviderError('Use exact verified literal input fields in the search recipe, not aggregate output aliases. Available inputs: '+', '.join(sorted(known))[:600])
        return value
    kind, metrics, group, columns = (recipe[k] for k in RECIPE['required'])
    if kind not in ('stats', 'timechart', 'table') or not isinstance(metrics, list) or not isinstance(columns, list) or not isinstance(group, str):
        raise ProviderError('Use a supported recipe kind and literal metric/column lists.')
    if kind == 'table':
        if chart_type != 'splunk.table' or metrics or group or not 1 <= len(columns) <= 80 or len(set(map(str, columns))) != len(columns):
            raise ProviderError('A raw table recipe needs distinct verified columns, no metrics and no grouping.')
        return '| table ' + ' '.join(field(c) for c in columns), '', list(columns)
    if columns:
        raise ProviderError('Only raw table recipes use columns. For stats/timechart set columns:[]; the group field and metric aliases already define the displayed outputs. Preserve the requested metrics in this panel.')
    if not 1 <= len(metrics) <= 8:
        raise ProviderError('A stats/timechart recipe needs 1–8 metrics. Keep the requested calculations together in their existing panel.')
    if kind == 'timechart' and group:
        raise ProviderError('A timechart recipe uses groupBy:"" to keep its declared metric aliases. Row navigation already filters its device; only stats recipes may group by a field. Preserve this trend and its metrics.')
    if group: field(group)
    aliases, expressions, formatting, copies, canonical = [], [], [], [], {}
    for metric in metrics:
        sparkline = isinstance(metric, dict) and metric.get('function') == 'sparkline'
        required_metric = set(SPARKLINE_METRIC['required']) if sparkline else {'function', 'field', 'alias'}
        if not isinstance(metric, dict) or set(metric) != required_metric:
            raise ProviderError('Each recipe metric needs function, field and alias.')
        function, value, alias = (metric[k] for k in ('function', 'field', 'alias'))
        if sparkline:
            if chart_type != 'splunk.table' or kind != 'stats':
                raise ProviderError('Sparkline recipe metrics belong in a stats table, not an axis chart or timechart.')
            function = metric['aggregation']
            span = re.fullmatch(r'([1-9][0-9]*)(s|m|h|d)', metric['span']) if isinstance(metric['span'], str) else None
            window = {'-15m': 900, '-1h': 3600, '-24h': 86400, '-7d': 604800}.get(profile.get('scope', {}).get('earliest'))
            if (function not in SPARKLINE_METRIC['properties']['aggregation']['enum'] or not span or not window
                    or window / (int(span[1]) * {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}[span[2]]) + 2 > 200):
                raise ProviderError('Use a supported sparkline aggregate and literal time span covering the selected window within 200 buckets.')
        if function not in FUNCTIONS or not isinstance(alias, str) or not re.fullmatch(FIELD, alias) or alias in aliases or alias == group or kind == 'timechart' and alias == '_time':
            raise ProviderError('Use supported aggregates and distinct output aliases without grouping/time collisions.')
        if value == '' and function == 'count': expression = 'count'
        else:
            field(value)
            # Verbose sampling can serialize native _time as a date string.
            # Its numeric search-time semantics are known only for catalog
            # scopes; an arbitrary supplied query could have overwritten it.
            native_time = value == '_time' and function in ('min', 'max') and profile.get('scope', {}).get('index') and not profile.get('scope', {}).get('query')
            if function not in ('count', 'latest', 'earliest') and known[value].get('numeric') is not True and not native_time:
                raise ProviderError('Recipe metric ' + alias + ': ' + function + '(' + value + ') requires an inspected numeric input field. Preserve the metric; use a native timestamp aggregate for _time.')
            expression = function + '(' + value + ')'
        if sparkline: expression = 'sparkline(' + expression + ',' + metric['span'] + ')'
        if expression in canonical:copies.append(alias+'='+canonical[expression])
        else:expressions.append(expression+' AS '+alias);canonical[expression]=alias
        aliases.append(alias)
        if format_values and chart_type == 'splunk.table' and value and not sparkline:
            timestamp = value == '_time' and function in ('min', 'max', 'latest', 'earliest') and (known[value].get('numeric') is True or profile.get('scope', {}).get('index') and not profile.get('scope', {}).get('query'))
            if timestamp: formatting.append(alias + '=strftime(' + alias + ',"%Y-%m-%d %H:%M:%S")')
            elif function != 'count' and known[value].get('numeric') is True: formatting.append(alias + '=round(' + alias + ',2)')
    pipeline = '| ' + kind + (' bins=100' if kind == 'timechart' else '') + ' ' + ' '.join(expressions) + (' BY ' + group if group else '')
    if copies:pipeline += ' | eval '+', '.join(copies)
    if formatting: pipeline += ' | eval ' + ', '.join(formatting)
    if chart_type == 'splunk.table': return pipeline, '', (['_time'] if kind == 'timechart' else [group] if group else []) + aliases
    if chart_type == 'splunk.singlevalue':
        if group or len(aliases) != 1 or kind != 'stats':
            raise ProviderError('A single value recipe needs exactly one ungrouped stats metric.')
        return pipeline, '', aliases
    if chart_type not in ('splunk.line', 'splunk.area', 'splunk.column', 'splunk.bar') or kind == 'stats' and not group:
        raise ProviderError('An axis recipe needs timechart or one stats grouping field.')
    return pipeline, '_time' if kind == 'timechart' else group, aliases
