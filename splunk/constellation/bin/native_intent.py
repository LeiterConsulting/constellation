"""Conservative checks for explicitly requested native visualization families.

This is a guard against silent substitutions, not a natural-language planner.
Ambiguous choices and ordinary references to existing charts stay with the model.
"""
import re
from provider_service import ProviderError

ALIASES = {
    'splunk.map': r'(?:marker|bubble|geographic|geospatial|choropleth)[ -]map|splunk\.map',
    'splunk.choropleth.svg': r'choropleth[ -]svg|svg[ -]choropleth|splunk\.choropleth\.svg',
    'splunk.sankey': r'sankey(?:\s+diagram)?',
    'splunk.parallelcoordinates': r'parallel[ -]?coordinates',
    'splunk.timeline': r'timeline',
    'splunk.linkgraph': r'link[ -]?graph',
    'splunk.networkGraph': r'network[ -]?graph',
    'splunk.punchcard': r'punch[ -]?card',
    'splunk.treemap': r'tree[ -]?map',
    'splunk.pie': r'pie(?:\s+chart)?|donut(?:\s+chart)?',
}


def requested_types(prompt):
    """Only positive creation clauses, not negations, choices or quoted titles."""
    text = re.sub(r'["“][^"”]*["”]', '', prompt)
    found = set()
    for clause in re.split(r'[!?\n]|\.(?:\s|$)', text):
        clause = re.sub(r'\b(?:not|without|avoid|instead\s+of|rather\s+than|don.t|do\s+not|never|no)\b.*', '', clause, flags=re.I)
        if not re.search(r'\b(?:create|build|make|add|include|use)\b', clause, re.I): continue
        if re.search(r'\b(?:or|either|perhaps|could|consider|might)\b', clause, re.I): continue
        for kind, alias in ALIASES.items():
            if re.search(r'(?<!\w)(?:splunk\.)?(?:' + alias + r')(?!\w)', clause, re.I): found.add(kind)
    return found


def unavailable_requested_types(prompt, environment):
    requested = requested_types(prompt)
    advertised = environment.get('visualizations')
    missing = requested - set(advertised) if isinstance(advertised, list) and all(isinstance(v, str) for v in advertised) else set()
    if 'splunk.networkGraph' in requested and not environment.get('features', {}).get('networkGraph'):
        missing.add('splunk.networkGraph')
    return sorted(missing)


def validate_native_intent(prompt, document, previous, focus):
    if document == previous: return
    charts = document.get('visualizations', {})
    if not previous.get('visualizations') and not previous.get('dataSources'):
        missing = requested_types(prompt) - {item.get('type') for item in charts.values()}
        if missing:
            raise ProviderError('Create the explicitly requested native chart types: ' + ', '.join(sorted(missing)) + '. Tables or promises to bind charts later do not fulfill this request. Use native visualization objects with actual source bindings; preserve requested pages and searches.', 422, 'native_chart_intent')
    if focus.get('kind') == 'visualization':
        for kind, alias in ALIASES.items():
            if re.search(r'\b(?:convert|change|switch|turn)\b[^.!?]{0,80}\b(?:to|into)\s+(?:a\s+|an\s+)?(?:native\s+)?(?:' + alias + r')(?!\w)', prompt, re.I):
                if charts.get(focus.get('id'), {}).get('type') != kind:
                    raise ProviderError('Convert the selected visualization to ' + kind + ', preserving its identity and unrelated work. Do not substitute another chart type.', 422, 'native_chart_intent')
