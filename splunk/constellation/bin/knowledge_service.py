"""Small, bundled, source-attributed retrieval; no embedding service or external database."""
import json
from pathlib import Path
import re
from compatibility import version_tuple

GUIDANCE = json.loads((Path(__file__).parent / 'contracts/knowledge.json').read_text())


def retrieve_guidance(prompt, document, environment, real_data=False, maximum=4, brief=None, focus=None):
    intent = (prompt + ' ' + json.dumps(brief or {}, ensure_ascii=False)).lower()
    selected = document.get('visualizations', {}).get((focus or {}).get('id'), {}).get('type', '')
    text = (intent + ' ' + selected + ' ' + ' '.join(viz.get('type', '') for viz in document.get('visualizations', {}).values())).lower()
    current = version_tuple(environment.get('version', ''))
    scored = []
    for item in GUIDANCE:
        if current < version_tuple(item['minimumEnterprise']): continue
        score = sum(3 for tag in item['tags'] if re.search(r'(?<!\w)' + re.escape(tag) + r'(?!\w)', text))
        score += sum(8 for tag in item['tags'] if re.search(r'(?<!\w)' + re.escape(tag) + r'(?!\w)', intent))
        if item['id'] == 'real-searches' and real_data: score += 20
        if item['id'] == 'series-bindings': score += 2
        if score: scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1]['id']))
    return [dict(item) for _, item in scored[:maximum]]
