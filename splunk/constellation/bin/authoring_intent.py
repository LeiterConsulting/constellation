"""Check explicit, observable page requests against the resulting native document."""
import re
from provider_service import ProviderError


def validate_page_intent(prompt, message, document, previous, focus):
    problems = []
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
