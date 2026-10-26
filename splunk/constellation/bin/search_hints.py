"""Controlled search-repair guidance; never rewrite queries or relax their limits."""
import re
from measurement_constraints import pipeline_commands

HISTOGRAM_GUIDANCE = '''For SPL numeric distributions, use bin FIELD span=WIDTH with an explicit
positive width in the field's recorded units, then aggregate. Explain the width in
the chart description. Automatic bins=N and eventstats min/max range prepasses
can outlive the bounded preview. If units are unclear, ask or show a verified
five-number summary instead. Never truncate events or widen the range to pass.'''


def preview_repair_hint(query, language, code):
    if code != 'preview_timeout' or language != 'spl' or not isinstance(query, str): return ''
    for _start, _end, command in pipeline_commands('| ' + query):
        if re.match(r'(?i:bin)\s+', command) and re.search(r'(?i:\bbins)\s*=\s*\d+', command) and not re.search(r'(?i:\bspan)\s*=', command):
            return 'Automatic numeric binning did not finish within the preview deadline. ' + ' '.join(HISTOGRAM_GUIDANCE.split())
    return ''
