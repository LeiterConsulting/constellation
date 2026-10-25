"""Conservative independent-measurement checks, not a general SPL semantic proof."""
import re
from provider_service import ProviderError
from search_scope import scoped_suffix


def independent_measurements(prompt, brief):
    # Explicit current revisions override a retained independence request.
    if re.search(r'\b(?:same|shared)\s+population\b|\b(?:no longer|stop)\b[^.!?]{0,80}\bindependent', prompt, re.I): return False
    text = '\n'.join([prompt, brief.get('purpose', ''), brief.get('requirements', '')])
    return bool(re.search(r'\b(?:retain|keep|preserve)\b[^.!?]{0,160}\bindependent(?:ly)?\b|\bindependent(?:ly)?\b[^.!?]{0,80}\b(?:measurements|observations|readings|metrics)\b', text, re.I))


def validate_populations(query, profile):
    if profile['scope'].get('language', 'spl') != 'spl': return
    suffix = scoped_suffix(query, profile)
    if suffix is None: return  # The scope guard supplies its own precise error.
    numeric = {item['name'] for item in profile.get('fields', []) if item.get('numeric') and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', item['name'])}
    def mask(match):
        return ' ' + match[0][1:-1] + ' ' if match[0].startswith("'") and match[0][1:-1] in numeric else ' ' * len(match[0])
    syntax = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', mask, suffix)
    aggregate = re.search(r'(?:^|\|)\s*(?:stats|timechart|chart)\b', syntax, re.I)
    if not aggregate: return
    before = syntax[:aggregate.start()]
    filtered = set()
    for condition in re.findall(r'(?:^|\|)\s*(?:where|search)\s+([^|]*)', before, re.I):
        filtered.update(field for field in re.findall(r'\b([A-Za-z_][A-Za-z0-9_.]*)\s*(?:<=|>=|!=|==|=|<|>)\s*-?\d+(?:\.\d+)?\b', condition) if field in numeric)
        filtered.update(field for field in re.findall(r'-?\d+(?:\.\d+)?\s*(?:<=|>=|!=|==|=|<|>)\s*([A-Za-z_][A-Za-z0-9_.]*)\b', condition) if field in numeric)
        filtered.update(field for field in re.findall(r'\bisnotnull\s*\(\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\)', condition, re.I) if field in numeric)
    if not filtered: return
    segment = syntax[aggregate.end():].split('|', 1)[0]
    measured = set()
    for match in re.finditer(r'\b(?:avg|mean|min|max|sum|latest|earliest|median|stdev|stdevp|var|varp|range|perc\d+)\s*\(', segment, re.I):
        start, cursor, depth = match.end(), match.end(), 1
        while cursor < len(segment) and depth:
            if segment[cursor] == '(': depth += 1
            elif segment[cursor] == ')': depth -= 1
            cursor += 1
        if depth: continue  # Native syntax validation handles incomplete syntax.
        arguments = segment[start:cursor-1]
        measured.update(field for field in numeric if re.search(r'(?<![A-Za-z0-9_.])' + re.escape(field) + r'(?![A-Za-z0-9_.])', arguments))
    affected = filtered & measured
    if affected and len(measured) > 1:
        others = measured - {sorted(affected)[0]}
        raise ProviderError('The request retains independent measurements, but this shared aggregate filters ' +
            ', '.join(sorted(affected))[:250] + ' before also calculating ' + ', '.join(sorted(others))[:250] +
            '. That discards events from the other measurements. Remove the global measurement filter and condition only the affected aggregate, for example avg(eval(if(FIELD<=LIMIT,FIELD,null()))), while calculating other measurements from all selected events. Preserve the requested cutoff, device grouping and time scope.', 422, 'population_coupling')
