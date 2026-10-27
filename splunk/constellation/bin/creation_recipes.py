"""Small first-draft SPL recipes; native execution still verifies every output.

Only verified literal fields and ordinary aggregates are compiled here. Complex
queries keep the existing pipeline/native path. There is no execution authority.
"""
import re
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
FIELD = r'[A-Za-z_][A-Za-z0-9_]*'


def compile_recipe(recipe, chart_type, profile):
    if not isinstance(recipe, dict) or set(recipe) != set(RECIPE['required']):
        raise ProviderError('Use kind, metrics, groupBy and columns for a complete search recipe.')
    if not profile or profile.get('scope', {}).get('language', 'spl') != 'spl':
        raise ProviderError('First-draft recipes require a verified SPL scope.')
    known = {f['name']: f for f in profile.get('fields', [])}
    def field(value):
        if not isinstance(value, str) or not re.fullmatch(FIELD, value) or value not in known:
            raise ProviderError('Use exact verified literal input fields in the search recipe.')
        return value
    kind, metrics, group, columns = (recipe[k] for k in RECIPE['required'])
    if kind not in ('stats', 'timechart', 'table') or not isinstance(metrics, list) or not isinstance(columns, list) or not isinstance(group, str):
        raise ProviderError('Use a supported recipe kind and literal metric/column lists.')
    if kind == 'table':
        if chart_type != 'splunk.table' or metrics or group or not 1 <= len(columns) <= 80 or len(set(map(str, columns))) != len(columns):
            raise ProviderError('A raw table recipe needs distinct verified columns, no metrics and no grouping.')
        return '| table ' + ' '.join(field(c) for c in columns), '', list(columns)
    if columns or not 1 <= len(metrics) <= 8 or kind == 'timechart' and group:
        raise ProviderError('Aggregate recipes need 1–8 metrics; only stats may group, and columns stays empty.')
    if group: field(group)
    aliases, expressions, formatting = [], [], []
    for metric in metrics:
        if not isinstance(metric, dict) or set(metric) != {'function', 'field', 'alias'}:
            raise ProviderError('Each recipe metric needs function, field and alias.')
        function, value, alias = (metric[k] for k in ('function', 'field', 'alias'))
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
        expressions.append(expression + ' AS ' + alias);aliases.append(alias)
        if chart_type == 'splunk.table' and value:
            timestamp = value == '_time' and function in ('min', 'max', 'latest', 'earliest') and (known[value].get('numeric') is True or profile.get('scope', {}).get('index') and not profile.get('scope', {}).get('query'))
            if timestamp: formatting.append(alias + '=strftime(' + alias + ',"%Y-%m-%d %H:%M:%S")')
            elif function != 'count' and known[value].get('numeric') is True: formatting.append(alias + '=round(' + alias + ',2)')
    pipeline = '| ' + kind + (' bins=100' if kind == 'timechart' else '') + ' ' + ' '.join(expressions) + (' BY ' + group if group else '')
    if formatting: pipeline += ' | eval ' + ', '.join(formatting)
    if chart_type == 'splunk.table': return pipeline, '', (['_time'] if kind == 'timechart' else [group] if group else []) + aliases
    if chart_type == 'splunk.singlevalue':
        if group or len(aliases) != 1 or kind != 'stats':
            raise ProviderError('A single value recipe needs exactly one ungrouped stats metric.')
        return pipeline, '', aliases
    if chart_type not in ('splunk.line', 'splunk.area', 'splunk.column', 'splunk.bar') or kind == 'stats' and not group:
        raise ProviderError('An axis recipe needs timechart or one stats grouping field.')
    return pipeline, '_time' if kind == 'timechart' else group, aliases
