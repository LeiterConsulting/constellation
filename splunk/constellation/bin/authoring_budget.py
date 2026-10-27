"""Small internal batches within the same atomic, bounded authoring turn."""
import copy
import json
import re
from model_readiness import CREATE_OUTPUT_TOKENS, EDIT_OUTPUT_TOKENS, OLLAMA_CONTEXT_TOKENS
from provider_service import ProviderError
from studio_contract import model_document
from creation_strategy import bounded_aitk_creation, explicit_page_count, explicit_panel_count, CONCISE_CREATION
from compact_creation import COMPOSE_ACTION, COMPACT_INSTRUCTIONS, RECIPE_COMPOSE_ACTION, RECIPE_COMPACT_INSTRUCTIONS, compact_goal, empty_canvas, expand_compose
from prompt_suggestions import SUGGESTION_INSTRUCTIONS
from search_hints import HISTOGRAM_GUIDANCE
from creation_outline import outline_schema, nested_outline, outline_instructions


def omit_compose(request):
    items = request.get('text', {}).get('format', {}).get('schema', {}).get('properties', {}).get('changes', {}).get('items', {})
    if 'anyOf' in items: items['anyOf'] = [action for action in items['anyOf'] if action != COMPOSE_ACTION]


class AuthoringBudget:
    def __init__(self, saved, context):
        self.context = copy.deepcopy(context)
        self.provider = saved.get('provider', 'openai')
        self.creation = context['canvasState'] == 'blank'
        complex_goal = bool(re.search(r'\b(?:multi[- ]page|(?:two|three|four|five|six|seven|eight|nine|[2-9])[- ]pages|pages\s*:)', context['request'], re.I))
        reported = context.get('modelLimits', {}).get('contextTokens')
        # A verified 32K+ Ollama window can carry the complete typed proposal,
        # reserving both repairs. Never infer capacity from a model's name.
        foundation = ((self.provider == 'aitk' and not bounded_aitk_creation(context)) or
                      (self.provider == 'ollama' and (type(reported) is not int or reported < OLLAMA_CONTEXT_TOKENS)))
        self.phase = 'foundation' if self.creation and context.get('dataProfile') and foundation and complex_goal else 'complete'
        self.stages = 0
        self.recipe_panels = 0

    def prepare(self, request, document):
        if not hasattr(self, 'instructions'):
            self.instructions = request['instructions']
            self.schema = copy.deepcopy(request['text']['format']['schema'])
        context = dict(self.context, definition=model_document(document), modelLimits=dict(self.context.get('modelLimits', {})))
        if self.phase == 'foundation':
            context['authoringStage'] = 'INTERNAL FOUNDATION: Build only one useful chart and its search on the first requested page. At most one search and one chart. Give that page its requested purpose. Defer other pages, charts, filters and navigation to the next internal stage. Do not ask the user to split the request. The draft will remain unchanged until all stages pass.'
            request['max_output_tokens'] = 3500
            context['originalGoal'] = context['request']
            context['request'] = 'Build only the first useful chart and its search on the first requested page of originalGoal. Do not build the rest yet. The server will request the remaining work in the next stage.'
            from authoring_actions import LEGACY_CHANGE, SEARCH_ACTION, CHART_ACTION_SCHEMA, PAGE_ACTION, DASHBOARD_ACTION
            title = copy.deepcopy(LEGACY_CHANGE)
            title['properties']['path']['enum'] = ['/title']
            title['properties']['op']['enum'] = ['set']
            schema = copy.deepcopy(self.schema)
            schema['properties']['changes']['items'] = {'anyOf': [title, DASHBOARD_ACTION, SEARCH_ACTION, *CHART_ACTION_SCHEMA['anyOf'], PAGE_ACTION]}
            schema['properties']['changes']['maxItems'] = 5
            request['text']['format']['schema'] = schema
        else:
            context['authoringStage'] = ('COMPLETE THE ORIGINAL GOAL: This definition includes any validated internal foundation. Add the remaining requested pages, charts, filters, purposes and interactions. Preserve working configuration. Describe the completed dashboard in its native description; never leave internal progress or promises about a next stage in native properties. Return only remaining changes. All original requirements must now be fulfilled.' if self.creation else
                                        'EDIT THE REQUESTED TARGET: Make only the requested change against the current definition or verified focused receipt. Preserve unrelated work and standing requirements. Do not complete unrelated pages or reconstruct the dashboard.')
            request['max_output_tokens'] = CREATE_OUTPUT_TOKENS if self.creation else EDIT_OUTPUT_TOKENS
            request['text']['format']['schema'] = copy.deepcopy(self.schema)
        request['instructions'] = self.instructions + '\n\nCURRENT SERVER-CONTROLLED STAGE (takes precedence over whole-dashboard completion instructions):\n' + context['authoringStage']
        compose = (self.provider in ('ollama', 'aitk') and self.phase == 'complete' and self.creation and context.get('dataProfile')
                   and context['dataProfile'].get('scope', {}).get('language', 'spl') == 'spl' and empty_canvas(document))
        self.compact = bool(compose and compact_goal(context) and bounded_aitk_creation(context)
                            and all(part.get('type') == 'input_text' for item in request['input'] for part in item['content']))
        omit_compose(request)
        if self.compact:
            request['instructions'] = RECIPE_COMPACT_INSTRUCTIONS if self.provider == 'aitk' else outline_instructions(RECIPE_COMPACT_INSTRUCTIONS)
            request['text']['format']['schema']['properties']['changes']['items'] = copy.deepcopy(RECIPE_COMPOSE_ACTION)
            # Encode the explicit small page count for schema-aware adapters;
            # actions() also enforces it for schema-ignoring adapters.
            pages = request['text']['format']['schema']['properties']['changes']['items']['properties']['pages']
            count = explicit_page_count(context['request'])
            pages.update(minItems=count, maxItems=count)
            if self.provider == 'ollama':
                panels = explicit_panel_count(context['request']) if re.search(r'\bexactly\s+\w+\s+(?:charts|panels|tiles|visualizations)\b', context['request'], re.I) else None
                request['text']['format']['schema']['properties']['changes']['items'] = outline_schema(RECIPE_COMPOSE_ACTION, count, panels)
            request['text']['format']['schema']['properties']['changes']['maxItems'] = 1
        if self.creation and context.get('dataProfile'):
            request['instructions'] += '\n\n' + CONCISE_CREATION
            properties = request['text']['format']['schema'].get('properties', {})
            if 'message' in properties: properties['message']['maxLength'] = 300
            if 'suggestions' in properties:
                properties['suggestions']['maxItems'] = 1
                suggestion = properties['suggestions'].get('items', {}).get('properties', {})
                for field, maximum in (('label', 48), ('prompt', 200), ('reason', 100)):
                    if field in suggestion: suggestion[field]['maxLength'] = maximum
        content = request['input'][0]['content']
        if self.compact:
            # These stable standard-chart actions do not need the unrelated
            # catalog or advanced native-action examples. Preserve the exact
            # blank document, user brief, inspected data and environment.
            context = {key: context[key] for key in ('request', 'definition', 'canvasState', 'environment', 'history', 'focus', 'pagePurposes', 'dashboardBrief', 'modelLimits', 'dataProfile') if key in context}
            if self.provider == 'ollama':
                request['max_output_tokens'] = 5500 if (explicit_panel_count(context['request']) or 0) > 4 else 3500
        if self.creation:
            request['instructions'] += '\n\n' + SUGGESTION_INSTRUCTIONS
            if context.get('dataProfile', {}).get('scope', {}).get('language', 'spl') == 'spl':
                request['instructions'] += '\n\n' + HISTOGRAM_GUIDANCE
        if context.get('formattingOnly'):
            # The only admitted action uses these verified output fields. The
            # exact document stays on the server for compilation/validation.
            context = {key: context[key] for key in ('request', 'focus', 'focusedSourceReceipt', 'formattingOnly', 'dashboardBrief', 'history', 'modelLimits') if key in context}
        if context.get('rowNavigationOnly'):
            context = {key: context[key] for key in ('request','focus','focusedSourceReceipt','dataProfile','dashboardBrief','history','modelLimits','rowNavigationOnly','rowFields') if key in context}
            request['max_output_tokens'] = min(request['max_output_tokens'],3500)
        if context.get('routeOnly'):
            context = {key:context[key]for key in ('request','focus','focusedSourceReceipt','dataProfile','dashboardBrief','history','modelLimits','routeOnly')if key in context}
            request['max_output_tokens'] = min(request['max_output_tokens'],1500)
        if context.get('buttonRouteOnly'):
            context={key:context[key]for key in ('request','focus','dashboardBrief','history','modelLimits','buttonRouteOnly')if key in context}
            request['max_output_tokens']=min(request['max_output_tokens'],1500)
        if context.get('pageMetadataOnly'):
            context={key:context[key]for key in ('request','focus','dashboardBrief','history','modelLimits','pageMetadataOnly')if key in context}
            request['max_output_tokens']=min(request['max_output_tokens'],1500)
        if context.get('calculationOnly'):
            context={key:context[key]for key in ('request','focus','dataProfile','dashboardBrief','history','modelLimits','calculationOnly')if key in context}
            request['max_output_tokens']=min(request['max_output_tokens'],3500)
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
        context['modelLimits']['outputTokens'] = request['max_output_tokens']
        # AITK receives one text prompt. Put the actual current instruction after
        # rolling history, so a completed historical request is not the last goal.
        current_request=context.pop('request',None)
        if current_request is not None:context['request']=current_request
        request['input'] = [{'role': 'user', 'content': [{'type': 'input_text', 'text': json.dumps(context, separators=(',', ':'))}] + [part for part in content if part.get('type') != 'input_text']}]

    def advance(self, request, document):
        self.stages += 1
        self.phase = 'complete'
        self.prepare(request, document)

    def actions(self, actions, document):
        """Keep page identity stable when completing this turn's new foundation."""
        if getattr(self, 'compact', False) and isinstance(actions, list):
            actions = [nested_outline(action) for action in actions]
        if getattr(self, 'compact', False) and isinstance(actions, list):
            if actions and (len(actions)!=1 or not isinstance(actions[0],dict)or actions[0].get('op')!='compose'):
                raise ProviderError('This compact first draft requires ONE complete compose plan. Do not emit separate search, chart, page, native or navigation actions; the server compiles those mechanics.',422,'compact_plan')
            for action in actions:
                if isinstance(action, dict) and action.get('op') == 'compose':
                    count = explicit_page_count(self.context['request'])
                    if not isinstance(action.get('pages'), list) or len(action['pages']) != count:
                        raise ProviderError('This request requires exactly ' + str(count) + ' complete pages, including every row-link destination.')
                    panels=explicit_panel_count(self.context['request'])
                    if panels is not None and re.search(r'\bexactly\s+\w+\s+(?:charts|panels|tiles|visualizations)\b',self.context['request'],re.I):
                        total=sum(len(page.get('panels',[]))for page in action['pages']if isinstance(page,dict))
                        if total!=panels:
                            distribution=', '.join(str(len(page.get('panels',[]))) for page in action['pages'] if isinstance(page,dict))
                            raise ProviderError('Received '+str(total)+' charts ('+distribution+' by page), but this request requires exactly '+str(panels)+' charts total. Return one corrected complete compose plan. Combine metrics requested in one summary into that single table panel; do not create one panel per metric.',422,'compact_plan')
        recipe_panels = sum(1 for action in actions if isinstance(action, dict) and action.get('op') == 'compose'
                            for page in action.get('pages', []) if isinstance(page, dict)
                            for panel in page.get('panels', []) if isinstance(panel, dict) and 'recipe' in panel) if isinstance(actions, list) else 0
        actions = expand_compose(actions, document, self.context.get('dataProfile'), self.context['request'] if getattr(self,'compact',False) else '')
        if recipe_panels: self.recipe_panels = recipe_panels
        if self.phase == 'foundation' and isinstance(actions, list):
            from search_chart_actions import compile_dashboard
            result = []
            for action in actions:
                if isinstance(action, dict) and action.get('op') == 'dashboard':
                    result.extend(compile_dashboard(action)[:1])
                elif not isinstance(action, dict) or action.get('path') != '/description': result.append(action)
            return result
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
        if self.context.get('rowNavigationOnly'):
            envelope = dict(envelope,recoveryFeedback={key:value for key,value in envelope.get('recoveryFeedback',{}).items() if key not in ('candidateDefinition','placementHint')},
                            request='Return one complete corrected rowDetail plan for the same original request. The server recompiles this uncommitted detail page; never emit native or separate navigation actions.')
            envelope['recoveryFeedback']['editsApplyTo']='original'
        if self.context.get('routeOnly'):
            envelope = dict(envelope,recoveryFeedback={key:value for key,value in envelope.get('recoveryFeedback',{}).items()if key not in ('candidateDefinition','placementHint')},
                            request='Return one complete corrected route action using routeOnly for the current request. The server recompiles against the exact original dashboard, preserving unrelated work.')
            envelope['recoveryFeedback']['editsApplyTo']='original'
        if self.context.get('buttonRouteOnly'):
            envelope = dict(envelope,recoveryFeedback={key:value for key,value in envelope.get('recoveryFeedback',{}).items()if key not in ('candidateDefinition','placementHint')},
                            request='Return one complete corrected buttonRoute action for the current request. The server holds the original dashboard; preserve all unrelated work.')
            envelope['recoveryFeedback']['editsApplyTo']='original'
        if self.context.get('pageMetadataOnly'):
            envelope=dict(envelope,recoveryFeedback={key:value for key,value in envelope.get('recoveryFeedback',{}).items()if key not in ('candidateDefinition','placementHint')},
                          request='Return one corrected pageMeta action for the current selected-page request. The exact original dashboard stays on the server; purpose is draft metadata.')
            envelope['recoveryFeedback']['editsApplyTo']='original'
        if self.context.get('calculationOnly'):
            envelope=dict(envelope,recoveryFeedback={key:value for key,value in envelope.get('recoveryFeedback',{}).items()if key not in ('candidateDefinition','placementHint')},
                          request='Return one corrected complete search pipeline for calculationOnly.sourceId against its original pipeline, retaining every existing output field and adding the exact requested alias. Use actual search feedback, not a previous completed goal.')
            envelope['recoveryFeedback']['editsApplyTo']='original'
        retain_compact = getattr(self,'compact',False)and envelope.get('recoveryFeedback',{}).get('editsApplyTo')=='original'
        if retain_compact:
            envelope=dict(envelope,rejectedOutput='',request='Return ONE complete corrected compose plan for the current original goal. The server supplies all IDs, positions, filters and navigation. Do not emit ordinary or native edits.')
        if getattr(self, 'compact', False)and not retain_compact:
            request['text']['format']['schema'] = copy.deepcopy(self.schema)
            request['instructions'] = self.instructions + '\n\nRepair the original goal against the supplied uncommitted candidate. Use ordinary native/typed actions; keep working configuration and correct all validation feedback. Return compact JSON.\n\n' + SUGGESTION_INSTRUCTIONS
            if self.provider == 'ollama':
                reported = self.context.get('modelLimits', {}).get('contextTokens')
                capacity = min(OLLAMA_CONTEXT_TOKENS, reported) if type(reported) is int and reported > 0 else OLLAMA_CONTEXT_TOKENS
                request['max_output_tokens'] = min(CREATE_OUTPUT_TOKENS, capacity // 3)
                part = request['input'][0]['content'][0]
                context = json.loads(part['text'])
                context['modelLimits']['outputTokens'] = request['max_output_tokens']
                part['text'] = json.dumps(context, separators=(',', ':'))
            omit_compose(request)
            self.compact = False
        if not empty_canvas(envelope.get('recoveryFeedback', {}).get('candidateDefinition', {})): omit_compose(request)
        if envelope.get('recoveryFeedback', {}).get('editsApplyTo') == 'candidate':
            # The exact staged document already represents the parsed proposal.
            # Do not resend a second copy in its older action/wire representation.
            envelope = dict(envelope, rejectedOutput='')
        request['input'] = request['input'][:1]
        entry = {'role': 'user', 'content': [{'type': 'input_text', 'text': ''}]}
        request['input'].append(entry)
        reported = self.context.get('modelLimits', {}).get('contextTokens')
        capacity = min(OLLAMA_CONTEXT_TOKENS, reported) if type(reported) is int and reported > 0 else OLLAMA_CONTEXT_TOKENS
        for maximum in (20000, 10000, 4000, 0):
            compact = dict(envelope, rejectedOutput=envelope['rejectedOutput'][:maximum])
            entry['content'][0]['text'] = json.dumps(compact, separators=(',', ':'))
            if self.provider != 'ollama': return
            size = len(request['instructions'].encode()) + len(json.dumps(request['text']).encode())
            size += sum(len(part['text'].encode()) for item in request['input'] for part in item['content'] if part.get('type') == 'input_text')
            if size <= (capacity - request['max_output_tokens'] - 1024) * 3: return
        raise ProviderError('The repair exceeds the conservative Ollama context budget. Your accepted draft is preserved.', 413, 'model_context_budget')
