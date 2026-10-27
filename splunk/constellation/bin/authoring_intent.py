"""Check explicit, observable page requests against the resulting native document."""
import re
from provider_service import ProviderError


def validate_page_intent(prompt, message, document, previous, focus, purposes=None):
    problems = []
    tabs = document.get('layout', {}).get('tabs', {}).get('items', [])
    if not previous.get('visualizations') and not previous.get('dataSources') and document!=previous:
        count=re.search(r'\bexactly\s+(one|two|three|four|five|six|seven|eight|[1-9][0-9]?)\s+(?:charts|panels|tiles|visualizations)\b',prompt,re.I)
        repeated=re.search(r'\b(?:reuse|repeat|copy)\b[^.!?]{0,80}\b(?:pages|tabs)\b',prompt,re.I)
        if count and not repeated:
            names={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8}
            expected=names.get(count[1].lower(),int(count[1])if count[1].isdigit()else 0)
            charts=document.get('visualizations',{});placed=[entry.get('item')for page in document.get('layout',{}).get('layoutDefinitions',{}).values()for entry in page.get('structure',[])if entry.get('item')in charts]
            if len(charts)!=expected or len(placed)!=expected or len(set(placed))!=expected:
                problems.append('The new dashboard requires exactly '+str(expected)+' charts, each placed once on its requested page. Remove unrequested duplicate cross-page placements; preserve the requested charts, page names and analysis. Intentional reuse must be explicitly requested.')
    if focus.get('kind')=='page':
        renamed=re.fullmatch(r'\s*Rename\s+only\s+this\s+selected\s+page\s+from\s+(.+?)\s+to\s+([^.!?]+)\.[\s\S]*',prompt,re.I)
        before=next((tab for tab in previous.get('layout',{}).get('tabs',{}).get('items',[])if tab.get('layoutId')==focus['id']),{})
        if renamed and before.get('label','').casefold()==renamed[1].strip(' "\u201c\u201d').casefold():
            expected=renamed[2].strip(' "\u201c\u201d')
            if not any(tab.get('layoutId')==focus['id']and tab.get('label')==expected for tab in tabs):
                problems.append('Rename the focused existing page label to '+expected[:200]+', retaining its layout ID and navigation. Do not repeat a completed historical button edit.')
    if document != previous:
        counts = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6}
        for match in re.finditer(r'\b(?:with|include|create|build|make|add)\s+(?:a\s+)?(one|two|three|four|five|six|[1-9][0-9]?)[ -]pages?\b', prompt, re.I):
            if re.search(r"(?:don't|do not|never)\s*$", prompt[max(0, match.start()-12):match.start()], re.I): continue
            requested = counts.get(match[1].lower(), int(match[1]) if match[1].isdigit() else 0)
            if len(tabs) < requested:
                problems.append('The request needs at least ' + str(requested) + ' pages, but the candidate has ' + str(len(tabs)) + '. Create every requested page with op:page, preserving its requested name and purpose, and place its charts there.')
        if purposes is not None and re.search(r'\bpage\s+purposes?\b', prompt, re.I):
            old_ids = {item['layoutId'] for item in previous.get('layout', {}).get('tabs', {}).get('items', [])}
            blank = not previous.get('visualizations') and not previous.get('dataSources')
            missing = [item['layoutId'] for item in tabs if (blank or item['layoutId'] not in old_ids) and not purposes.get(item['layoutId'], '').strip()]
            if missing: problems.append('Supply the requested purpose using op:page for: ' + ', '.join(missing)[:300])
    # A syntactically valid link can still point back to its source page. Check
    # explicitly named row-navigation destinations before claiming success.
    # Page labels can themselves contain "device" or "table". A focused
    # button edit is direct navigation, not evidence of a requested row route.
    if focus.get('kind') != 'input' and re.search(r'\b(?:row|device|table)\b', prompt, re.I) and re.search(r'\b(?:open|navigate|drill|link)\b', prompt, re.I):
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
    if focus.get('kind') == 'input' and previous.get('inputs', {}).get(focus.get('id'), {}).get('type') == 'input.button':
        item = document.get('inputs', {}).get(focus['id'], {})
        label_request=re.search(r'\brename\s+it\s+["\u201c]([^"\u201d]+)["\u201d]',prompt,re.I)
        if label_request and item.get('options',{}).get('label')!=label_request[1]:
            problems.append('Set the selected button label to the exact requested text: '+label_request[1][:200]+'.')
        destinations = {handler.get('options', {}).get('tabId') for handler in item.get('eventHandlers', [])
                        if handler.get('type') == 'drilldown.switchToTab'}
        # Quoted replacement labels are display text, not another destination.
        request = re.sub(r'\b(?:rename\s+(?:it|the\s+button)|label\s+it)\s+["\u201c][^"\u201d]*["\u201d]', '', prompt, flags=re.I)
        for tab in tabs:
            label = tab.get('label', '')
            if label and re.search(r'\b(?:open|navigate\s+to|link\s+to|return\s+to|back\s+to)\s+(?:the\s+)?["\u201c]?' + re.escape(label) + r'(?!\w)', request, re.I) and tab['layoutId'] not in destinations:
                problems.append('The selected navigation button must target ' + label[:200] + ' (' + tab['layoutId'] + '); preserve other elements and update this input\'s native switchToTab handler.')
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
        for tab in tabs:
            label = tab.get('label', '')
            if label and re.search(r'\b(?:return|back)[ -]+to[ -]+(?:the[ -]+)?' + re.escape(label) + r'(?!\w)', prompt, re.I) and tab['layoutId'] not in destinations:
                problems.append('Add the requested placed return button with targetPageId=' + tab['layoutId'] + ' (' + label[:120] + ').')
        if focus.get('kind') == 'page' and re.search(r'\bmatching\b|\bbetween pages\b|\bboth pages\b', prompt, re.I) and (focus['id'] not in destinations or not any(destination != focus['id'] for destination in destinations)):
            problems.append('Add the matching button on the other page with targetPageId equal to the focused page, in addition to its return button.')
    if problems: raise ProviderError(' '.join(problems))
