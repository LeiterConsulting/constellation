"""Metadata-only field evidence. Name hints never become measured business facts."""
import copy
import math
import re
from provider_service import ProviderError

POLICY = ('Field roles and units from names are hints, not verified definitions. User declarations are intent, not independent source verification. '
          'A nameUnitConflict needs clarification before conversions or thresholds. Never treat numeric identifiers/states as measurements. Missing, nonnumeric and excluded readings are distinct from zero. '
          'Count each measurement independently from source rows; a source row is an observation unless its grain is defined. '
          'Do not infer outages or expected cadence from missing sample values. Sample coverage is not full-window completeness. '
          'Preserve aggregate search grain. Ask one question before an ambiguous unit conversion or threshold; do not invent status meanings.')
UNIT_NAMES = {'fahrenheit': ('°F', 'temperature'), 'celsius': ('°C', 'temperature'), 'milliseconds': ('ms', 'duration'),
              'seconds': ('s', 'duration'), 'microseconds': ('µs', 'duration'), 'dbm': ('dBm', 'signal_strength'),
              'percent': ('%', 'ratio'), 'bytes': ('B', 'size'), 'ms': ('ms', 'duration'),
              'sec': ('s', 'duration'), 's': ('s', 'duration'), 'us': ('µs', 'duration'),
              '°f': ('°F', 'temperature'), '°c': ('°C', 'temperature')}


def scalar_number(value):
    if isinstance(value, (bool, list, dict)) or value in (None, ''): return False
    try: return math.isfinite(float(value))
    except (ValueError, TypeError, OverflowError): return False


def present(value):
    return value is not None and value != '' and value != []


def sample_fields(result):
    rows = result['results'][:200]
    fields = []
    def priority(entry):
        name = entry.get('name', '')
        if not isinstance(name, str): return 9
        if name == '_time': return 0
        if name.startswith(('_','date_')) or name in ('source','sourcetype','index','linecount','punct','splunk_server','splunk_server_group'): return 8
        return {'measurement':1,'identifier':2,'category':3,'counter':4}.get(name_context(name)['role'], 5)
    for entry in sorted(result['fields'], key=priority)[:80]:
        name = entry['name']
        if not isinstance(name, str) or len(name) > 200 or name in ('_raw', '_cd', '_bkt', '_serial'): continue
        values = [row[name] for row in rows if present(row.get(name))]
        numeric = sum(scalar_number(value) for value in values)
        fields.append({'name': name, 'numeric': bool(values) and numeric == len(values), 'present': len(values),
                       'coverage': {'missing': len(rows) - len(values), 'numeric': numeric,
                                    'multivalue': sum(isinstance(value, list) for value in values), 'basis': 'sample_rows'}})
    return fields[:60], len(rows)


def name_context(name):
    n = name.lower()
    role, quantity, unit = 'unknown', '', ''
    if n == '_time': return {'role': 'timestamp', 'basis': 'platform', 'unit': 's', 'quantity': 'event_time'}
    if re.search(r'(?:^|_)(?:id|pid|ppid|uid|gid|tid|port|version)$', n) or n in ('host','hostname','device_name','process_name','service','service_name','entity','device','name'):
        role = 'identifier'
    elif re.search(r'(?:^|_)(?:state|status|code|outcome|result|severity|level|enabled|valid|ok|wrapped)$', n): role = 'category'
    elif re.search(r'(?:count|counter|total)(?:_|$)', n): role = 'counter'
    elif re.search(r'(?:^|_)(?:temp|temperature)(?:_|$)', n):
        role, quantity = 'measurement', 'temperature'
        if re.search(r'(?:^|_)(?:temp|temperature)_f$', n): unit = '°F'
        elif re.search(r'(?:^|_)(?:temp|temperature)_c$', n): unit = '°C'
    elif re.search(r'(?:latency|duration|response_(?:time|ms)|elapsed)', n) and not re.search(r'censored|bound|resolution|threshold', n):
        role, quantity = 'measurement', 'duration'
        for suffix, symbol in (('_ms','ms'),('_us','µs'),('_seconds','s'),('_s','s')):
            if n.endswith(suffix): unit = symbol; break
    elif re.search(r'rssi|signal_strength', n): role, quantity = 'measurement', 'signal_strength'
    elif n.endswith(('_pct','_percent')): role, quantity, unit = 'measurement', 'ratio', '%'
    elif n.endswith('_bytes'): role, quantity, unit = 'measurement', 'size', 'B'
    context = {'role': role, 'basis': 'field_name' if role != 'unknown' else 'unknown'}
    if quantity: context['quantity'] = quantity
    if unit: context['unit'] = unit
    return context


def validate_definitions(definitions):
    if definitions is None: return {}
    if not isinstance(definitions, dict) or len(definitions) > 40:
        raise ProviderError('Keep field definitions to at most 40 fields in the selected data.')
    result = {}
    for name, item in definitions.items():
        if (not isinstance(name, str) or not 1 <= len(name) <= 200 or any(ord(c) < 32 for c in name)
                or not isinstance(item, dict) or not item or set(item) - {'unit','meaning'}):
            raise ProviderError('Use a field name, recorded unit and short meaning for field definitions.')
        if 'unit' in item and (not isinstance(item['unit'], str) or item['unit'] not in {value[0] for value in UNIT_NAMES.values()}):
            raise ProviderError('Choose a supported recorded unit for this field.')
        if 'meaning' in item and (not isinstance(item['meaning'], str) or not 1 <= len(item['meaning']) <= 240):
            raise ProviderError('Keep each field meaning within 240 characters.')
        result[name] = dict(item)
    return result


def enrich_profile(profile, intent=''):
    """Only exact observed field declarations can override hints; no model summaries."""
    if not isinstance(intent, str) or len(intent) > 32000:
        raise ProviderError('Keep field context within the dashboard brief and question limits.')
    result = copy.deepcopy(profile)
    definitions = validate_definitions(profile['scope'].get('fieldDefinitions'))
    for field in result['fields']:
        context = name_context(field['name'])
        declared = dict(definitions.get(field['name'], {}))
        # Deliberately require an exact field and an explicit recorded-unit verb.
        escaped = re.escape(field['name'])
        pattern = r'(?<![\w.])(?:["`\']?)' + escaped + r'(?:["`\']?)\s+(?:is measured in|is recorded in|uses units of|units are)\s+(' + '|'.join(re.escape(unit) for unit in sorted(UNIT_NAMES, key=len, reverse=True)) + r')(?=\s|[.,;!?]|$)'
        declarations = list(re.finditer(pattern, intent, re.I))
        if declarations: declared['unit'] = UNIT_NAMES[declarations[-1][1].lower()][0]
        definition = list(re.finditer(r'(?<![\w.])["`\']?' + escaped + r'["`\']?\s+(?:means|represents)\s+([^\n.!?]{1,240})', intent, re.I))
        if definition: declared['meaning'] = definition[-1][1].strip()
        if declared:
            definitions[field['name']] = declared
            if declared.get('unit') and context['role'] not in ('identifier','category','timestamp'):
                symbol = declared['unit']
                quantity = next(quantity for unit, quantity in UNIT_NAMES.values() if unit == symbol)
                if context.get('unit') and context['unit'] != symbol: context['nameUnitConflict'] = context['unit']
                context.update(role='measurement', quantity=quantity, unit=symbol, basis='user')
            if declared.get('meaning'): context['meaning'] = declared['meaning']; context['meaningBasis'] = 'user'
        field['context'] = context
    definitions = validate_definitions(definitions)
    if definitions: result['scope']['fieldDefinitions'] = definitions
    result['fieldPolicy'] = POLICY
    result['grain'] = 'existing_search_output' if profile['scope'].get('query') else 'indexed_observations'
    result['sampledRowsBasis'] = 'returned_rows'
    # A user definition is retained in their brief, never derived from event cells.
    return result


def validate_missing_measurements(query, profile, language='spl'):
    """Reject narrow zero imputation of observed sparse measurements; never rewrite."""
    if language != 'spl': return
    from measurement_constraints import pipeline_commands
    vulnerable = {field['name'] for field in profile['fields'] if field.get('numeric')
                  and field.get('coverage', {}).get('missing', 0) > 0
                  and field.get('context', {}).get('role') == 'measurement'}
    if not vulnerable: return
    for _start, _end, command in pipeline_commands('| ' + query):
        # Follow only unambiguous simple aggregate aliases, not general lineage.
        syntax = re.sub(r'"(?:\\.|[^"\\])*"', '""', command)
        for source, alias in re.findall(r'(?i)(?:avg|mean|min|max|latest|earliest)\(\s*([A-Za-z_]\w*)\s*\)\s+AS\s+([A-Za-z_]\w*)', syntax if re.match(r'(?i)(?:stats|timechart|chart|eventstats|streamstats)\s', syntax) else ''):
            if source in vulnerable: vulnerable.add(alias)
        fill = re.fullmatch(r'(?i:fillnull)\s+value\s*=\s*(?:"0"|0(?:\.0+)?)\s*(.*)', command.strip())
        if fill and (not fill[1] or vulnerable.intersection(fill[1].split())):
            raise ProviderError('Missing measurements are unknown, not zero. Keep them null and show independent valid-reading counts alongside source-row counts.', 422, 'missing_measurements')
        for field in vulnerable:
            name = re.escape(field)
            if re.search(r'(?i)(?<![\w.])' + name + r'\s*=\s*coalesce\(\s*' + name + r'\s*,\s*0(?:\.0+)?\s*\)', syntax):
                raise ProviderError('Do not replace missing ' + field[:100] + ' readings with zero. Retain null measurements and their independent coverage counts.', 422, 'missing_measurements')


def recorded_unit_intent(profile, prompt, history):
    """Bind a short answer only to one observed field's recorded-unit question."""
    answer = re.match(r'(?i)^\s*(?:use\s+|it is\s+|they are\s+)?(fahrenheit|celsius|milliseconds|microseconds|seconds|dbm|percent|bytes|ms|°f|°c)(?=\s|[.!?,]|$)', prompt)
    if not answer or re.search(r'(?i)\b(?:convert\w*|display\w*|show\w*|label\w*|axis|prefer\w*)\b', prompt): return prompt
    question = next((entry.get('text','') for entry in reversed(history) if entry.get('role') == 'assistant'), '')
    if question.count('?') != 1: return prompt
    question = question.split('?',1)[0] + '?'
    if not re.search(r'(?i)unit|recorded|stored|measured|fahrenheit|celsius', question): return prompt
    if re.search(r'(?i)\b(?:convert\w*|display\w*|show\w*|label\w*|axis|prefer\w*)\b', question): return prompt
    mentioned = {UNIT_NAMES[match[0].lower()][0] for match in re.finditer(r'(?i)\b(?:fahrenheit|celsius|milliseconds|microseconds|seconds|dbm|percent|bytes|ms)\b|°[fc]', prompt)}
    if len(mentioned) != 1: return prompt
    symbol, quantity = UNIT_NAMES[answer[1].lower()]
    eligible = [field for field in profile['fields'] if field.get('numeric') and name_context(field['name'])['role'] not in ('identifier','category','counter','timestamp')]
    named = [field for field in eligible if re.search(r'(?<![\w.])' + re.escape(field['name']) + r'(?![\w.])', question, re.I)]
    unknown = [field for field in eligible if name_context(field['name']).get('quantity') == quantity and not field.get('context', {}).get('unit')]
    selected = named if named else unknown
    if len(selected) != 1: return prompt
    name = selected[0]['name']
    unit_word = next(word for word, value in UNIT_NAMES.items() if value[0] == symbol)
    return prompt + '\n' + name + ' is recorded in ' + unit_word + '.'


def recorded_unit_question(profile, prompt, brief):
    """One clear source-unit question, without inference or premature edits."""
    explicit = bool(re.search(r'(?i)\bask me\b.{0,120}\bunits?\b', prompt) and re.search(r'(?i)\bmake no dashboard changes\b', prompt))
    text = prompt + '\n' + brief.get('purpose','') + '\n' + brief.get('requirements','')
    threshold = bool(re.search(r'(?i)\b(?:exclude|ignore|threshold|cutoff)\b.{0,100}\b(?:above|over|greater than)\s*-?\d', text))
    if not (explicit or threshold): return None
    fields = [field for field in profile['fields'] if field.get('numeric') and field.get('context', {}).get('quantity') in ('temperature','duration','signal_strength')
              and not field.get('context', {}).get('unit')]
    if not explicit: fields = [field for field in fields if field['context']['quantity'] == 'temperature']
    if len(fields) != 1: return None
    field = fields[0];quantity = field['context']['quantity']
    choices = {'temperature': [('Fahrenheit','°F'),('Celsius','°C')], 'duration':[('milliseconds','ms'),('seconds','s')], 'signal_strength':[('dBm','dBm')]}[quantity]
    name = field['name']
    message = 'Which units are recorded in "' + name + '": ' + ', '.join(label for label,_symbol in choices) + ', or another unit?'
    cards = [{'label':'Use ' + label,'prompt':name + ' is recorded in ' + label + '. Continue the original dashboard goal.',
              'reason':'Confirm the stored measurement unit; this does not convert values.','kind':'refine'} for label,_symbol in choices]
    return message,cards
