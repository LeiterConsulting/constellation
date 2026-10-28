"""Small creation turns can reserve both repairs instead of always staging."""
import json
import re

MAX_COMPLETE_CONTEXT_BYTES = 36000


def explicit_page_count(prompt):
    """Only an unambiguous small page count can constrain compact composition."""
    names = {'one':1,'two':2,'three':3,'four':4}
    page_noun = r'(?:-|\s+)(?:(?:named|distinct|separate)\s+)?pages?\b'
    counts = {names.get(match.lower(), int(match) if match.isdigit() else 0) for match in re.findall(r'\b(one|two|three|four|[1-4])' + page_noun, prompt, re.I)}
    if len(counts) != 1 or re.search(r'\b(?:five|six|seven|eight|nine|[5-9]|\d{2,})' + page_noun, prompt, re.I): return None
    return counts.pop()


def explicit_panel_count(prompt):
    names = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8}
    matches = re.findall(r'\b(one|two|three|four|five|six|seven|eight|\d+)\s+(?:charts?|panels?|tiles?|visualizations?)\b', prompt, re.I)
    counts = {names.get(value.lower(), int(value) if value.isdigit() else 0) for value in matches}
    return counts.pop() if len(counts) == 1 else None


def bounded_aitk_creation(context):
    """A workload heuristic, never a claim about the connection's token window."""
    prompt = context['request']
    pages, panels = explicit_page_count(prompt), explicit_panel_count(prompt)
    if not context.get('dataProfile') or pages is None: return False
    # More pages need an explicit bounded total; unknown/large goals still stage.
    if pages > 2 and (panels is None or not pages <= panels <= 8): return False
    if panels is not None and not 1 <= panels <= 8: return False
    return len(json.dumps(context, ensure_ascii=True, separators=(',', ':')).encode()) <= MAX_COMPLETE_CONTEXT_BYTES


CONCISE_CREATION = '''Return compact JSON without indentation. Keep new IDs short and
meaningful; never shorten user-specified page names or lose requirements. Put units
in chart titles and keep native descriptions concise, avoiding repeated copies of
the goal. Give a short completed-result message (one or two sentences). Suggest at
most ONE useful contextual next step with a brief label, prompt and reason, or [].
The complete dashboard, data checks, navigation and original requirements still
take priority over brevity. Never omit requested work to shorten the response.'''
