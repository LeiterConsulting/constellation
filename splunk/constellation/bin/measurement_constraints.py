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
from population_guard import validate_populations

FIELD = r'[A-Za-z_][A-Za-z0-9_]*'


def temperature_constraints(prompt, brief, profile):
    if not profile or profile['scope'].get('language', 'spl') != 'spl': return []
    text = '\n'.join([brief.get('purpose', ''), brief.get('requirements', ''), prompt])
    # Most recent explicit upper bound wins. Do not derive units from model IDs,
    # event values, chart titles, or an ambiguous Celsius/Fahrenheit conversion.
    fahrenheit = bool(re.search(r'\bfahrenheit\b|°\s*F\b|\d\s*F\b', text, re.I))
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


def pipeline_commands(suffix):
    """Retain exact command spans; quoted pipes and native token filters stay put."""
    starts, quoted, token, escaped = [], None, False, False
    for index, char in enumerate(suffix):
        if escaped: escaped = False; continue
        if char == '\\': escaped = True; continue
        if quoted:
            if char == quoted: quoted = None
        elif token:
            if char == '$': token = False
        elif char in ('"', "'"): quoted = char
        elif char == '$': token = True
        elif char == '|': starts.append(index)
    if quoted or token or escaped or (starts and suffix[:starts[0]].strip()): return []
    return [(start, end, suffix[start+1:end].strip()) for start, end in zip(starts, starts[1:] + [len(suffix)])]


def without_redundant_cutoff(suffix, rule):
    """Only a complete, exact upper-bound command before aggregation qualifies."""
    removed = []
    for start, end, command in pipeline_commands(suffix):
        if re.match(r'(?:stats|timechart|chart|eventstats|streamstats)\b', command, re.I): break
        match = re.fullmatch(r'(?:where|search)\s+(.+)', command, re.I)
        if not match: continue
        predicate = match[1].strip()
        if predicate.startswith('(') and predicate.endswith(')'): predicate = predicate[1:-1].strip()
        field = "(?:" + re.escape(rule['field']) + "|'" + re.escape(rule['field']) + "')"
        bound = re.fullmatch(field + r'\s*<=\s*(-?\d+(?:\.\d+)?)', predicate)
        if not bound: bound = re.fullmatch(r'(-?\d+(?:\.\d+)?)\s*>=\s*' + field, predicate)
        if bound and float(bound[1]) == rule['maximum']: removed.append((start, end))
    for start, end in reversed(removed): suffix = suffix[:start] + suffix[end:]
    return suffix


def without_misplaced_cutoff(suffix, rule):
    """An exact raw-field cutoff after an aggregate is not a valid SPL WHERE.

    The same verified exclusion is supplied at the measurement boundary. Never
    move a global filter, remove compound predicates or rewrite an output alias.
    """
    field = re.escape(rule['field'])
    tail = r'\s+(?i:where)\s+' + field + r'\s*<=\s*(-?\d+(?:\.\d+)?)\s*$'
    replacements = []
    for start, end, command in pipeline_commands(suffix):
        if not re.match(r'(?:stats|timechart|chart)\b', command, re.I): continue
        match = re.search(tail, command)
        if not match or float(match[1]) != rule['maximum']: continue
        prefix = command[:match.start()]
        # Here the predicate names an input measurement, not an aggregate alias
        # or grouping field. Ambiguous/output-level conditions require repair.
        grouping = re.search(r'(?i:\bBY\b)(.*)', prefix)
        if (re.search(r'(?i:\bAS\s+)[\'\"]?' + field + r'\b', prefix)
                or grouping and re.search(r'\b' + field + r'\b', grouping[1])): continue
        replacements.append((start, end, '| ' + prefix.rstrip() + ' '))
    for start, end, value in reversed(replacements): suffix = suffix[:start] + value + suffix[end:]
    return suffix


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
        original_suffix = suffix
        for rule in rules: suffix = without_misplaced_cutoff(suffix, rule)
        coupled = False
        if profile.get('independentMeasurements'):
            try: validate_populations(query, profile)
            except ProviderError as error:
                if error.code != 'population_coupling': raise
                coupled = True
        def field_syntax(value):
            def mask(match):
                return ' ' + match[0][1:-1] + ' ' if match[0].startswith("'") and match[0][1:-1] in {r['field'] for r in rules} else ' ' * len(match[0])
            return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', mask, value)
        syntax = field_syntax(suffix)
        commands = []
        for rule in rules:
            field = rule['field']
            if not re.search(r'\b' + re.escape(field) + r'\b', syntax): continue
            command = mask_command(rule)
            # Remove only our exact generated clause, then restore it at the
            # boundary. Entity-filter compilation may have moved it one pipe.
            for start, end, candidate in reversed(pipeline_commands(suffix)):
                if candidate == command: suffix = suffix[:start] + suffix[end:]
            if coupled or profile.get('retainSourceRows'): suffix = without_redundant_cutoff(suffix, rule)
            before_parts = []
            for _start, _end, part in pipeline_commands(suffix):
                if re.match(r'(?:stats|timechart|chart)\b', part, re.I): break
                before_parts.append(part)
                if profile.get('retainSourceRows') and re.match(r'(?:where|search)\b',part,re.I):
                    selected = re.fullmatch(r'search\s+' + re.escape(field) + r'=\$[A-Za-z_]\w*\|s\$',part,re.I)
                    if not selected and re.search(r'(?<![\w.])' + re.escape(field) + r'(?![\w.])',field_syntax(part)):
                        raise ProviderError('Keep all source observations as requested. The verified temperature mask already excludes the measurement; do not drop rows with an additional temperature filter. Preserve other predicates and count valid measurements independently.',422,'population_coupling')
            before = field_syntax('|'.join(before_parts))
            if re.search(r'\b(?:eval|rename|rex|spath|fillnull)\b[^|]*\b' + re.escape(field) + r'\b', before, re.I):
                raise ProviderError('Preserve the verified ' + field + ' measurement before aggregation. The server excludes values above ' +
                    format(rule['maximum'], '.15g') + ' F by setting only that measurement to null. Do not overwrite, fill or re-extract it before aggregation; compute derived output aliases in stats/timechart instead. Other measurements retain their events.', 422, 'measurement_constraint')
            commands.append(command)
        if commands or suffix != original_suffix:
            normalized = profile['baseQuery'].strip() + (' | ' + ' | '.join(commands) if commands else '') + ' ' + suffix.strip()
            if normalized != query:
                changes.append({'op': 'set', 'path': '/dataSources/' + identifier.replace('~', '~0').replace('/', '~1') + '/options/query', 'value': json.dumps(normalized)})
    return changes
