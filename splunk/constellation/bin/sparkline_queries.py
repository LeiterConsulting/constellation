"""Native value sparklines: distinguish missing buckets from observed zero."""
import hashlib
import json
import re
from compatibility import version_tuple
from measurement_constraints import pipeline_commands
from provider_service import ProviderError

EXPRESSION = re.compile(r'\bsparkline\(\s*(avg|min|max|sum)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*,\s*([1-9][0-9]*[smhd])\s*\)\s+AS\s+([A-Za-z_][A-Za-z0-9_]*)', re.I)


def preserve_gaps(prompt, brief):
    # A deliberate native zero-fill choice applies only to sparkline buckets;
    # unrelated measurements retain their existing missing-value guards.
    relevant = r'\b(?:sparkline\w*|empty\s+(?:time\s+)?buckets?|gaps?)\b'
    negative = re.search(r'\b(?:do not|don.t|never|without)\b[^.!?\n]{0,100}\bzero\b', prompt, re.I)
    if negative and re.search(relevant, negative[0], re.I): return True
    if re.search(r'\b(?:preserve|keep)\b[^.!?\n]{0,60}\b(?:sparkline\w*\s+(?:gaps|buckets)|missing\s+sparkline\w*\s+buckets)\b[^.!?\n]{0,30}\b(?:unknown|missing|gaps)\b', prompt, re.I): return True
    def accepts_zero(text):
        for clause in re.split(r'[.!?;\n]', text):
            if not re.search(relevant, clause, re.I) or not re.search(r'\bzero\b', clause, re.I): continue
            if re.search(r'\b(?:do not|don.t|never|without)\b', clause, re.I): continue
            if re.search(r'\b(?:allow|accept|may|use|display|show|render|treat|fill|replace)\w*\b', clause, re.I): return True
        return False
    if accepts_zero(prompt): return False
    return not accepts_zero('\n'.join(str((brief or {}).get(key, '')) for key in ('purpose', 'requirements')))


def gap_limit(prompt, document, environment, brief):
    if version_tuple(environment.get('version', '')) >= (10, 4): return False
    if document.get('visualizations') and not re.search(r'\b(?:add|create|include)\b[^.!?;]{0,100}\bsparklines?\b', prompt, re.I): return False
    if not re.search(r'\bsparklines?\b', prompt, re.I) or not preserve_gaps(prompt, brief): return False
    if re.search(r'\b(?:omit|without|no|remove)\s+(?:table\s+)?sparklines?\b', prompt, re.I): return False
    # Event-count sparklines legitimately use zero for an empty bucket.
    return bool(EXPRESSION.search(prompt)) or not re.search(r'\bsparkline\(\s*count\b', prompt, re.I)


def profile_policy(prompt, brief, environment):
    return {'preserveSparklineGaps': preserve_gaps(prompt, brief),
            'nativeTableSparklineGaps': version_tuple(environment.get('version', '')) >= (10, 4)}


def validate_native_gap_policy(document, previous, profile):
    if not profile or not profile.get('preserveSparklineGaps') or profile.get('nativeTableSparklineGaps'): return
    for table in document.get('visualizations', {}).values():
        if table.get('type') != 'splunk.table': continue
        sid = table.get('dataSources', {}).get('primary')
        source = document.get('dataSources', {}).get(sid, {})
        query = source.get('options', {}).get('query', '')
        if query != previous.get('dataSources', {}).get(sid, {}).get('options', {}).get('query') and EXPRESSION.search(query):
            raise ProviderError('This native Studio version plots missing table-sparkline buckets at zero. Preserve missing measurements with a standard trend chart unless the user explicitly accepts native zero-filled sparkline gaps.', 422, 'table_sparkline_gaps')


def normalize_sparklines(document, previous, profile):
    if not profile: return []
    changes = []
    for sid, source in document.get('dataSources', {}).items():
        query = source.get('options', {}).get('query', '')
        if source.get('type') != 'ds.search' or query == previous.get('dataSources', {}).get(sid, {}).get('options', {}).get('query'): continue
        if not isinstance(query, str) or not EXPRESSION.search(query): continue
        if not profile.get('preserveSparklineGaps'):
            # A deliberate native zero-fill choice needs a visible data note.
            for vid, table in document.get('visualizations', {}).items():
                if table.get('type') != 'splunk.table' or table.get('dataSources', {}).get('primary') != sid: continue
                note = 'Empty time buckets appear as zero in these sparklines.'
                description = table.get('description', '')
                if note not in description:
                    changes.append({'op': 'set', 'path': '/visualizations/' + vid.replace('~', '~0').replace('/', '~1') + '/description', 'value': json.dumps((description + '\n' + note).strip())})
            continue
        if not profile.get('nativeTableSparklineGaps'): continue
        commands = [(start - 1, end - 1, command) for start, end, command in pipeline_commands('|' + query)
                    if re.match(r'stats\b', command, re.I)]
        if len(commands) != 1: continue
        start, end, command = commands[0]
        matches = list(EXPRESSION.finditer(command))
        if not matches: continue
        additions, operations = [], []
        for match in matches:
            function, field, span, alias = match.groups()
            if field not in {f['name'] for f in profile.get('fields', []) if f.get('numeric') is True}: continue
            prefix = 'ctSpk_' + hashlib.sha256((sid + '\0' + alias).encode()).hexdigest()[:12]
            # Idempotence requires the exact generated transformation, not just
            # the presence of a helper-like name in untrusted query text.
            def operations_for(name):
                count, pairs = name + 'Count', name + 'Pairs'
                extract = 'mvindex(split(' + pairs + ',"::"),'
                transform = ' | eval ' + pairs + '=mvzip(' + alias + ',' + count + ',"::")'
                transform += ' | eval ' + alias + '=mvmap(' + pairs + ',case(' + extract + '0)=="##__SPARKLINE__##","##__SPARKLINE__##",tonumber(' + extract + '1))>0,' + extract + '0),true(),"null"))'
                transform += ' | fields - ' + count + ' ' + pairs
                return count, transform
            count, transform = operations_for(prefix)
            if transform in query and 'sparkline(count(' + field + '),' + span + ') AS ' + count in command: continue
            while re.search(r'\b' + re.escape(prefix) + r'(?:Count|Pairs)\b', query): prefix += '_'
            count, transform = operations_for(prefix)
            additions.append('sparkline(count(' + field + '),' + span + ') AS ' + count)
            operations.append(transform)
        if additions:
            syntax = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', lambda m: ' ' * len(m[0]), command)
            by = re.search(r'\s+BY\s+', syntax, re.I)
            position = by.start() if by else len(command)
            updated = command[:position].rstrip() + ' ' + ' '.join(additions) + command[position:] + ''.join(operations)
            updated = query[:start] + '| ' + updated + (' ' if end < len(query) else '') + query[end:]
            changes.append({'op': 'set', 'path': '/dataSources/' + sid.replace('~', '~0').replace('/', '~1') + '/options/query', 'value': json.dumps(updated)})
    return changes
