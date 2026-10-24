"""Check explicit, observable page requests against the resulting native document."""
import re
from provider_service import ProviderError


def validate_page_intent(prompt, message, document, previous, focus):
    problems = []
    # A syntactically valid link can still point back to its source page. Check
    # explicitly named row-navigation destinations before claiming success.
    if re.search(r'\b(?:row|device|table)\b', prompt, re.I) and re.search(r'\b(?:open|navigate|drill|link)\b', prompt, re.I):
        for tab in document.get('layout', {}).get('tabs', {}).get('items', []):
            label = tab.get('label', '')
            if not label or not re.search(r'\b(?:open|navigate\s+to|link\s+to|drill\s+(?:down\s+)?(?:to|into))\s+(?:and\s+filter\s+)?(?:the\s+)?' + re.escape(label) + r'(?!\w)', prompt, re.I): continue
            target = tab['layoutId']
            linked = []
            for item in document.get('visualizations', {}).values():
                if item.get('type') != 'splunk.table': continue
                handlers = item.get('eventHandlers', [])
                row_fields = {field for handler in handlers if handler.get('type') == 'drilldown.setToken'
                              for field in handler.get('options', {}).get('fields', [])
                              if any(token.get('key') == 'row.' + field + '.value' for token in handler.get('options', {}).get('tokens', []))}
                linked.extend(handler for handler in handlers if handler.get('type') == 'drilldown.switchToTab'
                              and handler.get('options', {}).get('tabId') == target
                              and row_fields.intersection(handler.get('options', {}).get('fields', [])))
            if not linked:
                problems.append('The requested row drilldown must open page ' + label[:200] + ' (' + target + '). Use op:link on the overview table with pageId equal to that destination, plus a verified field/token; a link back to its source page is insufficient.')
    if focus.get('kind') == 'page' and re.search(r'\bmove\b', prompt, re.I) and not re.search(r"\b(?:don't|do not|never)\s+move\b", prompt, re.I):
        target = focus['id']
        for identifier, item in previous.get('visualizations', {}).items():
            title = item.get('title', '')
            if not title or title.lower() not in prompt.lower(): continue
            placements = [key for key, page in document.get('layout', {}).get('layoutDefinitions', {}).items()
                          if any(entry.get('item') == identifier for entry in page.get('structure', []))]
            if placements != [target]:
                problems.append('Move ' + identifier + ' onto the focused page only. Use op:page with moveItems:true; copying it to both pages does not satisfy this request.')
    requests_button = (re.search(r'\b(?:add|create|include)\b[^.!?]{0,180}\bbutton\b', prompt, re.I) and re.search(r'\b(?:return|back|navigation)\b', prompt, re.I))
    claims_button = re.search(r'\b(?:added|adding|created)\b[^.!?]{0,100}\b(?:navigation|return|back)\b[^.!?]{0,40}\bbuttons?\b', message, re.I)
    if requests_button or claims_button:
        buttons = {key: item for key, item in document.get('inputs', {}).items() if item.get('type') == 'input.button'}
        placements = {entry.get('item') for page in document.get('layout', {}).get('layoutDefinitions', {}).values() for entry in page.get('structure', [])}
        destinations = {handler.get('options', {}).get('tabId') for key, item in buttons.items() if key in placements
                        for handler in item.get('eventHandlers', []) if handler.get('type') == 'drilldown.switchToTab'}
        if not destinations:
            problems.append('The requested navigation button is absent. Use op:button to create, place and connect a native page button atomically; mentioning a button in the message does not create it.')
        if focus.get('kind') == 'page' and re.search(r'\bmatching\b|\bbetween pages\b|\bboth pages\b', prompt, re.I) and (focus['id'] not in destinations or not any(destination != focus['id'] for destination in destinations)):
            problems.append('Add the matching button on the other page with targetPageId equal to the focused page, in addition to its return button.')
    if problems: raise ProviderError(' '.join(problems))
