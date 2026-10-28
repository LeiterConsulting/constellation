"""Native Studio interaction contract, validated without executing expressions."""
import re
from provider_service import ProviderError
from table_cells import validate_table_options


def feature_contract():
    return {'conditionalVisibility': {'root': 'expressions.conditions', 'references': 'containerOptions.visibility.showConditions/hideConditions',
                                     'matching': ['all-true', 'any-true'], 'minimumEnterprise': '10.2'},
            'evaluatedTokens': {'root': 'expressions.eval', 'reference': '$eval:EXPRESSION_NAME$', 'language': 'JSONata'},
            'buttons': {'type': 'input.button', 'label': 'options.label', 'action': 'drilldown.setToken'},
            'cartesianBindings': {'x': "> primary | seriesByName('category')", 'y': "> primary | frameBySeriesNames('metric')", 'note': 'Bind fields with native pipelines, never raw field-name strings.'},
            'scatterBindings': {'x': "> primary | seriesByName('x_metric')", 'y': "> primary | seriesByName('y_metric')", 'category': "> primary | seriesByName('label')", 'note': 'Scatter uses one series per axis, not a frame; point groups use category, not series.'},
            'inlineConceptData': {'type': 'ds.test', 'options': {'data': {'fields': [{'name': 'category'}, {'name': 'metric'}], 'columns': [['A', 'B'], [12, 19]]}}},
            'tokenDefaults': 'defaults.tokens.default.TOKEN = {value: VALUE}',
            'tabActions': {'type': 'drilldown.switchToTab', 'target': 'options.tabId = layoutDefinitions ID'},
            'preservation': 'Unknown existing configuration is preserved; new references must resolve.'}


def validate_features(document, previous, environment):
    """Check changed native interactions; retain future/unknown existing features."""
    expressions = document.get('expressions', {})
    if not isinstance(expressions, dict): raise ProviderError('Studio expressions must be an object.')
    for group in ('conditions', 'eval'):
        entries = expressions.get(group, {})
        if not isinstance(entries, dict) or len(entries) > 200:
            raise ProviderError('Use up to 200 named Studio expressions per group.')
        names = set()
        for expr in entries.values():
            if (not isinstance(expr, dict) or not isinstance(expr.get('name'), str)
                    or not expr['name'] or not isinstance(expr.get('value'), str) or len(expr['value']) > 8000):
                raise ProviderError('Each Studio expression needs a name and a text value.')
            if expr['name'] in names: raise ProviderError('Studio expression names must be unique within their group.')
            names.add(expr['name'])
    eval_names = {item['name'] for item in expressions.get('eval', {}).values()}
    old_names = {item.get('name') for item in previous.get('expressions', {}).get('eval', {}).values() if isinstance(item, dict)}
    removed_names = old_names - eval_names

    def check_eval_refs(value):
        if isinstance(value, dict):
            for child in value.values(): check_eval_refs(child)
        elif isinstance(value, list):
            for child in value: check_eval_refs(child)
        elif isinstance(value, str):
            if any(name not in eval_names for name in re.findall(r'\$eval:([^$]+)\$', value)):
                raise ProviderError('An evaluated token refers to a missing named Studio expression.')

    if expressions != previous.get('expressions', {}): check_eval_refs(expressions)
    for root in ('inputs', 'visualizations'):
        for key, item in document.get(root, {}).items():
            if item != previous.get(root, {}).get(key) or removed_names:
                check_eval_refs(item.get('eventHandlers', []))
                check_eval_refs(item.get('options', {}).get('label', ''))
                check_eval_refs(item.get('title', ''))
    conditions = expressions.get('conditions', {})
    layouts = document['layout'].get('layoutDefinitions', {})
    for root in ('visualizations', 'inputs', 'dataSources'):
        for key, item in document.get(root, {}).items():
            if not isinstance(item, dict): raise ProviderError('Studio items must be objects.')
            before = previous.get(root, {}).get(key, {})
            if root == 'visualizations' and item.get('type') == 'splunk.table':
                options, old_options = item.get('options', {}), before.get('options', {})
                validate_table_options(options, old_options, environment)
                if 'formatTable' in options and ('formatTable' not in old_options or options['formatTable'] != old_options['formatTable']):
                    raise ProviderError('formatTable is an authoring action, not a native table option. Return an op:formatTable action using the selected table and its verified focusedSourceReceipt. For new tables or broader calculation edits, format output aliases with final SPL eval after aggregation. Do not save options.formatTable; Studio ignores it.')
            if root == 'visualizations' and item.get('type', '').startswith('splunk.'):
                for label in ('title', 'description'):
                    value = item.get('options', {}).get(label)
                    if value is not None and value != before.get('options', {}).get(label):
                        raise ProviderError('Visualization title and description belong beside type/options, not inside options. Move options.' + label + ' to the visualization ' + label + ' property so Studio displays it.')
            if root == 'visualizations' and item.get('type') == 'splunk.scatter' and item != before:
                options, old_options = item.get('options', {}), before.get('options', {})
                if 'series' in options and options['series'] != old_options.get('series'):
                    raise ProviderError('Scatter point groups use options.category with seriesByName, not options.series.')
                for channel in ('x', 'y', 'category'):
                    value = options.get(channel)
                    if value != old_options.get(channel) and isinstance(value, str) and re.search(r'\|\s*frame\w*\([^)]*\)\s*$', value):
                        raise ProviderError('Scatter axes/category need one series, for example "> primary | seriesByName(\"metric\")", not frameBySeriesNames.')
            if root == 'visualizations' and item.get('type') in ('splunk.line', 'splunk.area', 'splunk.bar', 'splunk.column', 'splunk.scatter', 'splunk.bubble'):
                for channel in ('x', 'y', 'y2'):
                    value = item.get('options', {}).get(channel)
                    if value != before.get('options', {}).get(channel) and isinstance(value, str) and not value.lstrip().startswith(('>', '$')):
                        raise ProviderError('Chart data channels need native pipelines: x="> primary | seriesByName(\"category\")", y="> primary | frameBySeriesNames(\"metric\")". Raw field-name strings are not data bindings.')
            if root == 'dataSources' and item.get('type') == 'ds.test' and item != before:
                data = item.get('options', {}).get('data', {})
                if not isinstance(data, dict) or not isinstance(data.get('fields'), list) or not isinstance(data.get('columns'), list):
                    raise ProviderError('Inline concept data needs data.fields [{name:...}] and column-oriented data.columns arrays.')
                fields, columns = data['fields'], data['columns']
                if (len(fields) != len(columns) or any(not isinstance(field, dict) or not isinstance(field.get('name'), str) for field in fields)
                        or any(not isinstance(column, list) or len(column) > 200 for column in columns)
                        or len({len(column) for column in columns}) > 1):
                    raise ProviderError('Inline data needs one equal-length column per named field, up to 200 illustrative rows.')
            visibility = item.get('containerOptions', {}).get('visibility', {})
            old_visibility = before.get('containerOptions', {}).get('visibility', {})
            if visibility != old_visibility:
                if not isinstance(visibility, dict): raise ProviderError('Visibility options must be an object.')
                if any(k in visibility for k in ('showConditions', 'hideConditions')) and not environment.get('features', {}).get('conditionalVisibility'):
                    raise ProviderError('Conditional visibility requires a verified Splunk 10.2 or later target.')
                for mode in ('show', 'hide'):
                    refs = visibility.get(mode + 'Conditions', [])
                    if not isinstance(refs, list) or any(not isinstance(ref, str) or ref not in conditions for ref in refs):
                        raise ProviderError('A visibility rule refers to a missing Studio condition.')
                    if visibility.get(mode + 'WhenConditions', 'all-true') not in ('all-true', 'any-true'):
                        raise ProviderError('Visibility conditions use all-true or any-true matching.')
            handlers = item.get('eventHandlers', [])
            if handlers != before.get('eventHandlers', []):
                if not isinstance(handlers, list) or len(handlers) > 50: raise ProviderError('Use up to 50 event handlers per Studio item.')
                for handler in handlers:
                    if not isinstance(handler, dict) or not isinstance(handler.get('type'), str) or not isinstance(handler.get('options', {}), dict):
                        raise ProviderError('Each Studio event handler needs a type and options.')
                    options = handler.get('options', {})
                    if handler['type'] == 'drilldown.switchToTab' and options.get('tabId') not in layouts:
                        raise ProviderError('A tab action refers to a missing Studio layout.')
                    if handler['type'] == 'drilldown.setToken':
                        tokens = options.get('tokens')
                        if not isinstance(tokens, list) or any(not isinstance(token, dict) or not isinstance(token.get('token'), str) or not token['token'] or not ('value' in token or 'key' in token) for token in tokens):
                            raise ProviderError('Token actions need token names and a value or event key.')
                    if handler['type'] in ('drilldown.resetTokens', 'drilldown.unsetTokens'):
                        for field in ('tokenNames', 'tokenNamespaces'):
                            names = options.get(field, [])
                            if not isinstance(names, list) or any(not isinstance(name, str) or not name for name in names):
                                raise ProviderError('Native reset/unset actions use tokenNames and tokenNamespaces arrays of nonempty names.')
                        if any(field in options for field in ('tokens', 'token')):
                            raise ProviderError('Native reset/unset actions use tokenNames, not tokens/token. Preserve the exact intended token scope.')
                    if handler['type'] == 'drilldown.setTimeRange' and (not isinstance(options.get('token'), str) or not options['token']):
                        raise ProviderError('A native time-range action needs options.token, the timerange token prefix.')
    # Deleting a referenced condition is an edit even when the panel is unchanged.
    removed = set(previous.get('expressions', {}).get('conditions', {})) - set(conditions)
    if removed:
        for root in ('visualizations', 'inputs'):
            for item in document.get(root, {}).values():
                visibility = item.get('containerOptions', {}).get('visibility', {})
                if any(ref in removed for mode in ('show', 'hide') for ref in visibility.get(mode + 'Conditions', [])):
                    raise ProviderError('Remove visibility references before deleting their condition.')
