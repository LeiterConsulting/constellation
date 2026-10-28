"""Metadata-only sample evidence; never turn missing values into missing schema."""
import re
from measurement_constraints import pipeline_commands
from search_scope import scoped_suffix

REASONS = {
    'Search stopped at a resource limit.',
    'Only the first 200 result rows are shown.',
    'Splunk did not verify completion.',
    'Splunk reported search diagnostics; results may be incomplete.',
    'Field inspection reached the result-size limit; coverage refers only to the retained sample.',
}


def sample_completion(result):
    evidence = result.get('evidence')
    if not isinstance(evidence, dict): evidence = {}
    state = result.get('state', evidence.get('state', 'unknown'))
    if state not in ('complete', 'partial'): state = 'unknown'
    reasons = [reason for reason in evidence.get('reasons', []) if isinstance(reason, str) and reason in REASONS]
    return {'state': state, 'reasons': reasons}


def empty_columns(fields, rows):
    return [field for field in fields if not any(row.get(field) not in (None, '', []) for row in rows)]


def verified_null_columns(query, language, profile):
    """Conservative provenance for empty columns, after native execution.

    Merely returning an alias cannot verify avg(misspelled_input). Unknown
    transformation syntax retains ordinary repair rather than gaining an empty
    output exception. This does not parse or rewrite the native query.
    """
    known = {field['name'] for field in profile.get('fields', [])}
    suffix = scoped_suffix(query, profile)
    if suffix is None or language != 'spl': return set()
    field = r'[A-Za-z_][A-Za-z0-9_.]*'
    name = r'(?:' + field + r'|"[^"\\]+"|\'[^\'\\]+\')'
    for _start, _end, command in pipeline_commands(suffix):
        if re.match(r'(?i:stats|chart|timechart)\b', command):
            outputs = set()
            for match in re.finditer(r'\b([A-Za-z_][A-Za-z0-9_]*)\(\s*(' + name + r')\s*\)(?:\s+(?i:AS)\s+(' + name + r'))?', command):
                source = match[2].strip('"\'')
                if source in known:
                    outputs.add(match[3].strip('"\'') if match[3] else match[1] + '(' + source + ')')
            # A common explicit measurement exclusion keeps its aggregate
            # column even when every selected reading is excluded. Recognize
            # only the same verified field, a numeric comparison and null().
            conditional = (r'\b(?:avg|mean|min|max|sum|median|latest|earliest|count)\(\s*eval\(\s*if\(\s*('
                           + name + r')\s*(?:<=|>=|!=|==|<|>|=)\s*-?\d+(?:\.\d+)?\s*,\s*('
                           + name + r')\s*,\s*null\(\s*\)\s*\)\s*\)\s*\)\s+AS\s*(' + name + r')')
            for match in re.finditer(conditional, command, re.I):
                source, value = match[1].strip('"\''), match[2].strip('"\'')
                if source == value and source in known: outputs.add(match[3].strip('"\''))
            group = re.search(r'(?i:\bBY\s+)(.*)$', command)
            if group: outputs.update(value for value in re.findall(field, group[1]) if value in known)
            if re.match(r'(?i:timechart)\b', command): outputs.add('_time')
            known = outputs
        elif re.match(r'(?i:eval)\s+', command):
            # Separate assignments only at unquoted, top-level commas.
            text = command[command.index(' ') + 1:];parts=[];start=depth=0;quoted=None;escaped=False
            for index,char in enumerate(text):
                if escaped: escaped=False;continue
                if char=='\\': escaped=True;continue
                if quoted:
                    if char==quoted:quoted=None
                elif char in ('"',"'"):quoted=char
                elif char=='(':depth+=1
                elif char==')':depth-=1
                elif char==',' and depth==0:parts.append(text[start:index]);start=index+1
            parts.append(text[start:])
            if quoted or escaped or depth: return set()
            for part in parts:
                assignment=re.fullmatch(r'\s*(' + field + r')\s*=\s*(.+)',part,re.S)
                if not assignment: return set()
                expression=re.sub(r'"(?:\\.|[^"\\])*"','',assignment[2])
                quoted_fields=re.findall(r"'([^'\\]+)'",expression)
                expression=re.sub(r"'[^'\\]+'",'',expression)
                expression=re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()','',expression)
                expression=re.sub(r'\b(?:AND|OR|NOT|XOR|IN|LIKE)\b','',expression,flags=re.I)
                expression=re.sub(r'(?<![\w.])\d+(?:\.\d+)?(?:[eE][+-]?\d+)?','',expression)
                refs=set(re.findall(field,expression))|set(quoted_fields)
                if refs and refs <= known: known.add(assignment[1])
                else: known.discard(assignment[1])
        elif not re.match(r'(?i:search|where|fields|table|sort|head|tail|dedup|bin|bucket)\b',command):
            return set()
    return known
