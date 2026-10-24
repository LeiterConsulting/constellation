"""Exact, single-element presentation instructions that need no inference.

Deliberately small grammar: additional goals, ambiguous prose, attachments and
other chart conversions use normal model authoring and validation.
"""
import json
import re
from studio_contract import apply_changes


def quick_edit(prompt, document, selected, attachments):
    if attachments or not isinstance(selected, str) or selected not in document['visualizations']: return None
    viz = document['visualizations'][selected]
    title = re.fullmatch(r'Rename only (?:this |the )?selected chart to "([^"\n]{1,200})"\.?', prompt, re.I)
    change = re.fullmatch(r'Change only this selected chart to an (area|line) chart and rename it "([^"\n]{1,200})"\. Preserve its search, page placement, interactions and every other element\.', prompt, re.I)
    if not title and not change: return None
    if change and viz.get('type') not in ('splunk.line', 'splunk.area'): return None
    path = '/visualizations/' + selected.replace('~', '~0').replace('/', '~1')
    changes = [{'op': 'set', 'path': path + '/title', 'value': json.dumps(title[1] if title else change[2])}]
    if change: changes.append({'op': 'set', 'path': path + '/type', 'value': json.dumps('splunk.' + change[1].lower())})
    apply_changes(document, changes)
    return changes
