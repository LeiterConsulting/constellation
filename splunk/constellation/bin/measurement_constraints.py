"""Narrow, explicit temperature exclusions compiled at the measurement boundary.

This is not a general natural-language or SPL semantics engine. Only a verified
Fahrenheit temperature field and an explicit upper exclusion qualify. Nulling the
measurement preserves events for other measurements and protects every ordinary
null-ignoring aggregate, including latest, rather than just a chosen average.
"""
import json
import math
import re
from provider_service import ProviderError
from search_scope import scoped_suffix

FIELD = r'[A-Za-z_][A-Za-z0-9_]*'


def temperature_constraints(prompt, brief, profile):
    if not profile or profile['scope'].get('language', 'spl') != 'spl': return []
    text = '\n'.join([brief.get('purpose', ''), brief.get('requirements', ''), prompt])
    # Most recent explicit upper bound wins. Do not derive units from model IDs,
    # event values, chart titles, or an ambiguous Celsius/Fahrenheit conversion.
    fahrenheit = bool(re.search(r'\bfahrenheit\b|°\s*F\b|\d\s+F\b', text, re.I))
    if not fahrenheit: return []
    limit = None
    for clause in re.split(r'[\n!?;]|\.(?=\s|$)', text):
        if re.search(r'\b(?:remove|disable|drop)\b[^;]{0,50}\b(?:temperature\s+)?(?:cutoff|exclusion)\b|\binclude all temperature', clause, re.I):
            limit = None
            continue
        if not re.search(r'\b(?:exclud\w*|ignor\w*|cutoff)\b', clause, re.I): continue
        if re.search(r'\b(?:do not|don.t|never)\s+(?:exclude|ignore)\b', clause, re.I): continue
        match = re.search(r'\b(?:above|over|greater than)\s*(-?\d+(?:\.\d+)?)\s*(?:°\s*)?(F(?:ahrenheit)?|C(?:elsius)?)?\b', clause, re.I)
        if match:
            limit = float(match[1]) if not match[2] or match[2].lower().startswith('f') else None
            if limit is not None and not math.isfinite(limit): limit = None
    if limit is None: return []
    fields = [item['name'] for item in profile.get('fields', []) if item.get('numeric') and
              re.fullmatch(r'(?:temperature|temp)(?:_f|_fahrenheit)', item['name'], re.I)]
    # A unitless field is eligible only when the user explicitly names it and
    # states Fahrenheit, with no competing Celsius instruction.
    if not fields and not re.search(r'\bcelsius\b|°\s*C\b', text, re.I):
        fields = [item['name'] for item in profile.get('fields', []) if item.get('numeric') and
                  item['name'] in ('temperature', 'temp') and re.search(r'\b' + item['name'] + r'\b', text, re.I)]
    return [{'field': field, 'maximum': limit, 'unit': 'F'} for field in fields]


def mask_command(rule):
    field, limit = rule['field'], format(rule['maximum'], '.15g')
    return 'eval ' + field + '=if(' + field + '<=' + limit + ',' + field + ',null())'


def normalize_measurements(document, previous, profile):
    rules = profile.get('measurementConstraints', []) if profile else []
    if not rules: return []
    changes = []
    for identifier, source in document.get('dataSources', {}).items():
        query = source.get('options', {}).get('query', '')
        if query == previous.get('dataSources', {}).get(identifier, {}).get('options', {}).get('query'): continue
        if source.get('type') != 'ds.search': continue
        suffix = scoped_suffix(query, profile)
        if suffix is None: continue  # The scope validator supplies its own error.
        syntax = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', suffix)
        commands = []
        for rule in rules:
            field = rule['field']
            if not re.search(r'\b' + re.escape(field) + r'\b', syntax): continue
            command = mask_command(rule)
            # Remove only our exact generated clause, then restore it at the
            # boundary. Entity-filter compilation may have moved it one pipe.
            suffix = re.sub(r'\|\s*' + re.escape(command) + r'(?=\s*(?:\||$))', '', suffix)
            before = re.split(r'\|\s*(?:stats|timechart|chart)\b', suffix, maxsplit=1, flags=re.I)[0]
            before = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', before)
            if re.search(r'\b(?:eval|rename|rex|spath|fillnull)\b[^|]*\b' + re.escape(field) + r'\b', before, re.I):
                raise ProviderError('Preserve the verified ' + field + ' measurement before aggregation. The server excludes values above ' +
                    format(rule['maximum'], '.15g') + ' F by setting only that measurement to null. Do not overwrite, fill or re-extract it before aggregation; compute derived output aliases in stats/timechart instead. Other measurements retain their events.', 422, 'measurement_constraint')
            commands.append(command)
        if commands:
            normalized = profile['baseQuery'].strip() + ' | ' + ' | '.join(commands) + ' ' + suffix.strip()
            if normalized != query:
                changes.append({'op': 'set', 'path': '/dataSources/' + identifier.replace('~', '~0').replace('/', '~1') + '/options/query', 'value': json.dumps(normalized)})
    return changes
