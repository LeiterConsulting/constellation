"""Small internal batches within the same atomic, bounded authoring turn."""
import copy
import json
import re
from model_readiness import CREATE_OUTPUT_TOKENS, EDIT_OUTPUT_TOKENS, OLLAMA_CONTEXT_TOKENS
from provider_service import ProviderError
from studio_contract import model_document


class AuthoringBudget:
    def __init__(self, saved, context):
        self.context = copy.deepcopy(context)
        self.provider = saved.get('provider', 'openai')
        self.creation = context['canvasState'] == 'blank'
        complex_goal = bool(re.search(r'\b(?:multi[- ]page|(?:two|three|four|[2-9])\s+pages|pages\s*:)', context['request'], re.I))
        self.phase = 'foundation' if self.creation and context.get('dataProfile') and self.provider in ('ollama', 'aitk') and complex_goal else 'complete'
        self.stages = 0

    def prepare(self, request, document):
        if not hasattr(self, 'instructions'):
            self.instructions = request['instructions']
            self.schema = copy.deepcopy(request['text']['format']['schema'])
        context = dict(self.context, definition=model_document(document))
        if self.phase == 'foundation':
            context['authoringStage'] = 'INTERNAL FOUNDATION: Build only one useful chart and its search on the first requested page. At most one search and one chart. Give that page its requested purpose. Defer other pages, charts, filters and navigation to the next internal stage. Do not ask the user to split the request. The draft will remain unchanged until all stages pass.'
            request['max_output_tokens'] = 3500
            context['originalGoal'] = context['request']
            context['request'] = 'Build only the first useful chart and its search on the first requested page of originalGoal. Do not build the rest yet. The server will request the remaining work in the next stage.'
            from authoring_actions import LEGACY_CHANGE, SEARCH_ACTION, CHART_ACTION, PAGE_ACTION
            title = copy.deepcopy(LEGACY_CHANGE)
            title['properties']['path']['enum'] = ['/title']
            title['properties']['op']['enum'] = ['set']
            schema = copy.deepcopy(self.schema)
            schema['properties']['changes']['items'] = {'anyOf': [title, SEARCH_ACTION, CHART_ACTION, PAGE_ACTION]}
            schema['properties']['changes']['maxItems'] = 5
            request['text']['format']['schema'] = schema
        else:
            context['authoringStage'] = 'COMPLETE THE ORIGINAL GOAL: This definition includes any validated internal foundation. Add the remaining requested pages, charts, filters, purposes and interactions. Preserve working configuration. Describe the completed dashboard in its native description; never leave internal progress or promises about a next stage in native properties. Return only remaining changes. All original requirements must now be fulfilled.'
            request['max_output_tokens'] = CREATE_OUTPUT_TOKENS if self.creation else EDIT_OUTPUT_TOKENS
            request['text']['format']['schema'] = copy.deepcopy(self.schema)
        request['instructions'] = self.instructions + '\n\nCURRENT SERVER-CONTROLLED STAGE (takes precedence over whole-dashboard completion instructions):\n' + context['authoringStage']
        content = request['input'][0]['content']
        # A conservative estimate, not a tokenizer or a verified upstream limit.
        # Drop only rolling history; the durable brief and exact document remain.
        if self.provider == 'ollama':
            overhead = len(request['instructions'].encode()) + len(json.dumps(request['text']).encode())
            reported = context.get('modelLimits', {}).get('contextTokens')
            capacity = min(OLLAMA_CONTEXT_TOKENS, reported) if type(reported) is int and reported > 0 else OLLAMA_CONTEXT_TOKENS
            request['max_output_tokens'] = min(request['max_output_tokens'], capacity // 3)
            allowance = (capacity - request['max_output_tokens'] - 1024) * 3
            while context['history'] and overhead + len(json.dumps(context).encode()) > allowance:
                context['history'] = context['history'][1:]
            if overhead + len(json.dumps(context).encode()) > allowance:
                raise ProviderError('This dashboard exceeds the conservative input budget for the Ollama context window. Use a smaller dashboard or a provider with more context. Your draft is preserved.', 413, 'model_context_budget')
        request['input'] = [{'role': 'user', 'content': [{'type': 'input_text', 'text': json.dumps(context)}] + [part for part in content if part.get('type') != 'input_text']}]

    def advance(self, request, document):
        self.stages += 1
        self.phase = 'complete'
        self.prepare(request, document)

    def actions(self, actions, document):
        """Keep page identity stable when completing this turn's new foundation."""
        if self.phase == 'foundation' and isinstance(actions, list):
            return [action for action in actions if not isinstance(action, dict) or action.get('path') != '/description']
        if not self.creation or not self.stages or not isinstance(actions, list): return actions
        tabs = document.get('layout', {}).get('tabs', {}).get('items', [])
        existing = {tab['layoutId'] for tab in tabs}
        aliases = {}
        for action in actions:
            if not isinstance(action, dict) or action.get('op') != 'page' or action.get('layoutId') in existing: continue
            matches = [tab['layoutId'] for tab in tabs if tab.get('label', '').strip().casefold() == str(action.get('label', '')).strip().casefold()]
            if len(matches) == 1: aliases[action['layoutId']] = matches[0]
        if not aliases: return actions
        result = copy.deepcopy(actions)
        for action in result:
            if not isinstance(action, dict): continue
            keys = {'page': ('layoutId',), 'link': ('pageId',), 'button': ('pageId', 'targetPageId')}.get(action.get('op'), ())
            for key in keys:
                if action.get(key) in aliases: action[key] = aliases[action[key]]
        return result

    def feedback(self, request, envelope):
        """Keep the current candidate and latest feedback, not every failed reply."""
        request['input'] = request['input'][:1]
        entry = {'role': 'user', 'content': [{'type': 'input_text', 'text': ''}]}
        request['input'].append(entry)
        reported = self.context.get('modelLimits', {}).get('contextTokens')
        capacity = min(OLLAMA_CONTEXT_TOKENS, reported) if type(reported) is int and reported > 0 else OLLAMA_CONTEXT_TOKENS
        for maximum in (20000, 10000, 4000, 0):
            compact = dict(envelope, rejectedOutput=envelope['rejectedOutput'][:maximum])
            entry['content'][0]['text'] = json.dumps(compact)
            if self.provider != 'ollama': return
            size = len(request['instructions'].encode()) + len(json.dumps(request['text']).encode())
            size += sum(len(part['text'].encode()) for item in request['input'] for part in item['content'] if part.get('type') == 'input_text')
            if size <= (capacity - request['max_output_tokens'] - 1024) * 3: return
        raise ProviderError('The repair exceeds the conservative Ollama context budget. Your accepted draft is preserved.', 413, 'model_context_budget')
