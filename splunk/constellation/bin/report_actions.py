"""Compile a focused per-row report suffix without rewriting native sources."""
import json
import re
from provider_service import ProviderError
from search_context import source_report
from search_chart_actions import identifier

ACTION = {'type': 'object', 'properties': {
    'op': {'type': 'string', 'enum': ['reportTransform']},
    'pipeline': {'type': 'string', 'minLength': 1, 'maxLength': 8000,
                 'description': 'Pipe-prefixed SPL suffix appended to the selected report output. Preserve existing rows and fields. No base query, source IDs, native JSON or aggregation unless explicitly requested.'}},
    'required': ['op', 'pipeline'], 'additionalProperties': False}
INSTRUCTIONS = '''Update only the selected report-backed table with a per-row calculation.
Return JSON message,changes,suggestions with exactly ONE reportTransform action
{op:"reportTransform",pipeline:"| eval ... | table ..."}. Supply only the SPL
suffix appended to the verified current selected output. Retain every existing
row and requested column. The server creates a fresh ds.chain extending the exact
selected source and binds only the selected table, preserving every original
source, report reference/app, other element and native property. Do not repeat the
base query, reuse another chain's aggregation, emit native JSON or typed search
or chart actions. Actual output, source scope, units, exclusions and population
validation still run. On repair replace the complete suffix against the original
selected output. Describe the visible result, without claiming a save.'''


def eligible(prompt, selected, document, profile, attachments):
    table = document.get('visualizations', {}).get(selected, {})
    # Preservation clauses name unrelated pages/inputs; they are not new goals.
    # Compound active requests retain general authoring instead of losing work
    # when a narrow suffix plan cannot express the complete requested change.
    clauses = re.split(r'[.;]\s*(?:preserve|keep|retain)\b', prompt, maxsplit=1, flags=re.I)
    active = clauses[0]
    if len(clauses) > 1 and re.search(r'\b(?:add|append|create|move|resize|rename|remove|delete|change|set|switch|sort|format|style|make|show|hide|filter)\b', clauses[1], re.I):
        return False
    return bool(not attachments and profile and profile.get('scope', {}).get('report')
                and table.get('type') == 'splunk.table' and set(table.get('dataSources', {})) == {'primary'}
                and re.search(r'\bfor each (?:existing )?row\b', prompt, re.I)
                and re.search(r'\b(?:add|append)\b', prompt, re.I)
                and not re.search(r'\b(?:move|resize|rename|remove|delete|navigation|drilldown|create|pages?|tabs?|charts?|inputs?|dropdowns?|menus?|layout|title|width|colou?r|style|format|sort)\b', active, re.I))


def compile_plan(actions, document, context):
    if (not isinstance(actions, list) or len(actions) != 1 or not isinstance(actions[0], dict)
            or set(actions[0]) != {'op', 'pipeline'} or actions[0]['op'] != 'reportTransform'):
        raise ProviderError('Return one complete reportTransform suffix for the selected table.', 422, 'report_plan')
    pipeline = actions[0]['pipeline']
    if not isinstance(pipeline, str) or not pipeline.strip().startswith('|') or len(pipeline) > 8000:
        raise ProviderError('Start the report transform with a pipe and keep it under 8000 characters.', 422, 'report_plan')
    plan = context['reportTransform'];fresh = identifier(plan['freshId']);parent = plan['parentId'];selected = context['focus']['id']
    table = document.get('visualizations', {}).get(selected, {})
    sources = document.get('dataSources', {})
    if (fresh in sources or table.get('type') != 'splunk.table' or table.get('dataSources') != {'primary': parent}
            or source_report(sources, parent) != context['dataProfile']['scope']['report']):
        raise ProviderError('The selected report source changed. Reselect its table before editing.', 422, 'report_plan')
    escape = lambda value: value.replace('~', '~0').replace('/', '~1')
    source = {'type': 'ds.chain', 'options': {'extend': parent, 'query': pipeline.strip()}}
    return [{'op': 'set', 'path': '/dataSources/' + fresh, 'value': json.dumps(source)},
            {'op': 'set', 'path': '/visualizations/' + escape(selected) + '/dataSources/primary', 'value': json.dumps(fresh)}]
