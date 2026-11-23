"""Author a bounded Discovery brief through the normal caller-scoped agent."""
from agent_service import AgentService
from dashboard_library import snapshot
from draft_service import validate_snapshot
from provider_service import ProviderError, user_provider
from search_service import read_only_query
from studio_contract import apply_changes


def require_provider(saved, approved):
    provider = saved['provider']
    route = 'https://api.openai.com/v1' if provider == 'openai' else saved.get('base_url', '').rstrip('/')
    if (provider, route, saved.get('model')) != approved:
        raise ProviderError('Select the administrator-approved authoring connection in Constellation Settings.',
                            409, 'authoring_settings')


def authoring_scope(brief):
    source = brief['source']
    scope = {'earliest': brief['time_range']['earliest']}
    if source['kind'] == 'index':
        return dict(scope, **{key: source[key] for key in ('index', 'sourcetype') if key in source})
    if source['kind'] == 'spl':
        try:
            read_only_query(source['query'])
        except ProviderError:
            raise ProviderError('Use an index or a bounded read-only search for this dashboard.',
                                422, 'source_unavailable') from None
        return dict(scope, query=source['query'], language='spl')
    raise ProviderError('Choose an index or supply the underlying read-only search.',
                        422, 'source_unavailable')


def authoring_prompt(brief):
    pages = brief['pages']
    count = sum(len(page['panels']) for page in pages)
    lines = [f'Create {len(pages)} pages with exactly {count} charts for the dashboard titled {brief["title"]}.',
             f'Use the selected scope and {brief["time_range"]["earliest"]} time range.',
             f'Purpose: {brief["purpose"]}']
    if brief.get('requirements'):
        lines.append('Requirements: ' + brief['requirements'])
    for number, page in enumerate(pages, 1):
        lines.append(f'Page {number}, named {page["name"]}, with exactly {len(page["panels"])} charts:')
        lines.extend('- ' + panel for panel in page['panels'])
    if brief.get('findings'):
        lines.append('Discovery observations for context. Verify measures against the selected Splunk data:')
        lines.extend('- ' + finding for finding in brief['findings'])
    return '\n'.join(lines)


def check_coverage(document, expected):
    layout = document['layout']
    tabs = layout.get('tabs', {}).get('items', [])
    definitions = layout.get('layoutDefinitions', {})
    visualizations = set(document['visualizations'])
    if tabs:
        pages = [definitions[tab['layoutId']] for tab in tabs]
    else:
        pages = list(definitions.values()) or [layout]
    placed = [{item['item'] for item in page.get('structure', [])} & visualizations for page in pages]
    if ([len(items) for items in placed] != [len(page['panels']) for page in expected]
            or len(visualizations) != sum(len(items) for items in placed)
            or set().union(*placed) != visualizations
            or (tabs and [tab['label'] for tab in tabs] != [page['name'] for page in expected])):
        raise ProviderError('Can you simplify the requested pages or panels so every panel can be verified?',
                            422, 'panel_coverage')
    return tabs[0]['layoutId'] if tabs else next(iter(definitions), '')


def build_authoring(runtime, brief, approved):
    scope = authoring_scope(brief)
    blank = {'title': 'New dashboard', 'visualizations': {}, 'dataSources': {}, 'inputs': {},
             'layout': {'type': 'absolute', 'structure': []}}
    editorial = {'purpose': brief['purpose'], 'requirements': brief.get('requirements', '')}
    prompt = authoring_prompt(brief)
    try:
        result = AgentService(user_provider(runtime), runtime).assist(
            {'prompt': prompt, 'definition': blank, 'revision': 0, 'brief': editorial, 'dataContext': scope},
            check_provider=lambda saved: require_provider(saved, approved))
    except ProviderError as error:
        if error.status == 409 and not error.code and not getattr(error, 'authoring_reason', None):
            raise ProviderError('Configure the approved connection and model in Constellation Settings.',
                                409, 'authoring_settings') from None
        raise
    if not result['changes']:
        profile = result.get('dataProfile') or {}
        if profile.get('sampledRows') == 0:
            complete = (profile.get('completion') or {}).get('state') == 'complete'
            raise ProviderError('The selected source returned no usable rows in the bounded sample.',
                                422, 'no_data' if complete else 'source_unavailable')
        raise ProviderError('Can you clarify the dashboard plan or choose a source and time range with data?',
                            422, 'authoring_input')
    definition = apply_changes(blank, result['changes'])
    definition.update(title=brief['title'], description=brief['purpose'])
    active_tab = check_coverage(definition, brief['pages'])
    receipts = result.get('searchReceipts', [])
    if not receipts or any(receipt['status'] not in ('results', 'partial') for receipt in receipts):
        raise ProviderError('Choose a source and range with results for every requested chart.',
                            422, 'panel_coverage')
    warnings = []
    if any(receipt['status'] == 'partial' for receipt in receipts):
        warnings.append({'code': 'search_partial', 'message': 'A bounded search returned a partial preview.'})
    state = snapshot(definition)
    provenance = brief.get('provenance')
    if provenance:
        prompt += '\nDiscovery context: ' + provenance['label'] + '.'
    state.update(dataContext=result['dataContext'], searchesEnabled=True, activeTab=active_tab,
                 pagePurposes=result['pagePurposes'], brief=editorial,
                 messages=[{'id': 1, 'user': True, 'text': prompt},
                           {'id': 2, 'user': False, 'text': result['message'][:8000]}])
    return validate_snapshot(state), warnings
