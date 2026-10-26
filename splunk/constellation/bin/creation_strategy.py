"""Small creation turns can reserve both repairs instead of always staging."""
import json
import re

MAX_COMPLETE_CONTEXT_BYTES = 36000


def explicit_page_count(prompt):
    """Only an unambiguous small page count can constrain compact composition."""
    counts = {1 if match.lower() in ('one','1') else 2 for match in re.findall(r'\b(one|two|1|2)(?:-|\s+)pages?\b', prompt, re.I)}
    if len(counts) != 1 or re.search(r'\b(?:three|four|five|six|seven|eight|nine|[3-9]|\d{2,})(?:-|\s+)pages?\b|\bmulti[- ]page\b', prompt, re.I): return None
    return counts.pop()


def bounded_aitk_creation(context):
    """A workload heuristic, never a claim about the connection's token window."""
    prompt = context['request']
    if not context.get('dataProfile') or explicit_page_count(prompt) is None: return False
    # Ambiguous/larger page counts and explicitly large chart requests stage.
    if re.search(r'\b(?:three|four|five|six|seven|eight|nine|[3-9]|\d{2,})\s+pages\b|\b(?:seven|eight|nine|[7-9]|\d{2,})\s+(?:charts|panels|tiles|visualizations)\b', prompt, re.I): return False
    return len(json.dumps(context, ensure_ascii=True, separators=(',', ':')).encode()) <= MAX_COMPLETE_CONTEXT_BYTES


CONCISE_CREATION = '''Return compact JSON without indentation. Keep new IDs short and
meaningful; never shorten user-specified page names or lose requirements. Put units
in chart titles and keep native descriptions concise, avoiding repeated copies of
the goal. Give a short completed-result message (one or two sentences). Suggest at
most ONE useful contextual next step with a brief label, prompt and reason, or [].
The complete dashboard, data checks, navigation and original requirements still
take priority over brevity. Never omit requested work to shorten the response.'''
