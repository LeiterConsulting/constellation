"""Create and reconcile caller-private dashboards and drafts for the MCP pilot."""
import json
from urllib.parse import urlencode
from xml.sax.saxutils import escape

from authoring_actions import compile_actions
from dashboard_library import DashboardLibrary, parse_view, snapshot
from dashboard_plan import expand
from data_service import DataService
from draft_service import state_digest, validate_snapshot
from mcp_pilot_authoring import build_authoring
from mcp_pilot_input import PILOT_PANELS
from mcp_pilot_ledger import CLAIM_SECONDS
from page_service import proposed_purposes
from provider_service import ProviderError
from studio_contract import apply_changes
from studio_features import validate_features

FIXTURE = {'code': 'pilot_fixture', 'message': 'This dashboard uses the fixed pilot count recipes.'}
PARTIAL = {'code': 'search_partial', 'message': 'A bounded search returned a partial preview.'}
VERIFIED = {'draft_readback': 'verified', 'native_readback': 'verified',
            'owner_and_privacy': 'verified', 'search_checks': 'bounded'}
AUTHORING_LEASE_SECONDS = 240
AUTHORING_QUESTIONS = {
    'source_unavailable': 'Can you choose a source and time range that this Splunk connection can inspect?',
    'no_data': 'No rows were returned for the selected source and time range. Can you choose a different source or range?',
    'panel_coverage': 'Can you simplify the requested pages or panels so each panel can be verified?',
    'authoring_settings': 'Can you select the approved provider and model in Constellation Settings?',
    'authoring_input': 'Can you clarify the dashboard plan or choose a source and time range with data?',
}
FAILURE_CODES = {
    'no_data': 'no_data',
    'provider_timeout': 'provider_timeout',
    'provider_connection': 'provider_connection',
    'openai_connection_unavailable': 'provider_connection',
    'model_context_budget': 'model_token_limit',
    'model_token_limit': 'model_token_limit',
    'model_output_limit': 'model_output_limit',
    'recovery_budget': 'recovery_budget',
}


def build_fixture(runtime, brief):
    """Compile only shipped recipes and verify native bindings against actual caller output."""
    source = brief['source']
    data = DataService(runtime)
    profile = data.profile({'index': source['index'], 'sourcetype': source.get('sourcetype', ''),
                            'earliest': brief['time_range']['earliest']})
    if not profile['sampledRows']:
        raise ProviderError('Choose a range with events in the pilot index.', 422, 'no_data')
    blank = {'title': 'New dashboard', 'visualizations': {}, 'dataSources': {}, 'inputs': {},
             'layout': {'type': 'absolute', 'structure': []}}
    plan = {'op': 'boardPlan', 'title': brief['title'], 'description': brief['purpose'],
            'pages': [], 'panels': [], 'sources': [], 'links': []}
    for page_number, page in enumerate(brief['pages']):
        plan['pages'].append({'label': page['name'], 'columns': 2, 'purpose': brief['purpose']})
        for panel_number, panel in enumerate(page['panels']):
            kind, pipeline, bindings = PILOT_PANELS[panel]
            name = 'metric_' + str(list(PILOT_PANELS).index(panel))
            if name not in {entry['id'] for entry in plan['sources']}:
                plan['sources'].append({'id': name, 'pipeline': pipeline})
            plan['panels'].append({'id': f'panel_{page_number}_{panel_number}', 'page': page_number,
                                   'type': kind, 'source': name, 'title': panel, 'bindings': bindings})
    intent = f"Create {len(plan['pages'])} pages with exactly {len(plan['panels'])} charts."
    actions = expand([plan], blank, profile, intent)
    definition = apply_changes(blank, compile_actions(blank, actions, profile))
    validate_features(definition, blank, runtime.environment())
    receipts = data.validate_searches(definition, blank, profile)
    if any(receipt['status'] == 'empty' for receipt in receipts):
        raise ProviderError('Choose a range with results for all pilot panels.', 422, 'no_data')
    state = snapshot(definition)
    requirements = brief.get('requirements', '')
    state.update(dataContext=profile['scope'], searchesEnabled=True, activeTab='layout_board_0',
                 pagePurposes=proposed_purposes(actions, {}, definition),
                 brief={'purpose': brief['purpose'], 'requirements': requirements})
    request = ['Create ' + brief['title'] + '.', brief['purpose']]
    if 'provenance' in brief:
        request.append('Context: ' + brief['provenance']['label'] + '.')
    request.extend(page['name'] + ': ' + ', '.join(page['panels']) for page in brief['pages'])
    state['messages'] = [
        {'id': 1, 'user': True, 'text': '\n'.join(request)},
        {'id': 2, 'user': False, 'text': 'Created and checked the requested dashboard pilot panels.'},
    ]
    warnings = [FIXTURE]
    if any(r['status'] == 'partial' for r in receipts):
        warnings.append(PARTIAL)
    return validate_snapshot(state), warnings


class PilotCreation:
    def __init__(self, runtime, drafts, ledger, settings):
        self.runtime = runtime
        self.drafts = drafts
        self.ledger = ledger
        self.settings = settings
        self.owner = runtime.user
        self.views = DashboardLibrary(drafts).base

    @staticmethod
    def reply(request_id, status, **fields):
        return {'schema_version': '1', 'request_id': request_id, 'status': status, 'warnings': [], **fields}

    def draft(self, identifier):
        try:
            return self.drafts.read(identifier)['state']
        except ProviderError as error:
            if error.status in (403, 404, 409):
                return None
            raise

    def native(self, identifier):
        try:
            result = self.drafts.request(self.views + '/' + identifier)
            entries = (result or {}).get('entry', [])
            if len(entries) != 1 or entries[0].get('name') != identifier:
                return None
            self.drafts.verify(entries[0])
            return parse_view(entries[0]['content'].get('eai:data'))[1]
        except ProviderError as error:
            if error.status < 500:
                return None
            raise

    def links(self, record, draft, view):
        result = {}
        base = self.settings['web_base'] + '/app/constellation/'
        if draft is not None:
            result.update(draft_id=record['draft'], title=draft['definition']['title'],
                          edit_url=base + 'workspace?' + urlencode({'draft': record['draft']}))
        if view is not None:
            result.setdefault('title', view['title'])
            result.update(dashboard_id=record['view'], view_url=base + record['view'])
        return result

    def completed(self, request_id, record, draft, view):
        warnings = list(record.get('warnings', []))
        if draft is None or view is None:
            warnings.append({'code': 'artifact_unavailable', 'message': 'A saved artifact is unavailable.'})
        return self.reply(request_id, 'created', warnings=warnings, validation=VERIFIED,
                          **self.links(record, draft, view))

    def status(self, request_id, record=None):
        record = record if record is not None else self.ledger.get(self.owner, request_id)
        if record is None:
            return self.reply(request_id, 'not_found')
        stage = record['stage']
        if stage == 'created':
            return self.completed(request_id, record, self.draft(record['draft']), self.native(record['view']))
        if stage == 'draft_only':
            draft = self.draft(record['draft'])
            return self.reply(request_id, 'draft_only', warnings=record['warnings'],
                              **self.links(record, draft, None))
        if stage == 'needs_input':
            details = {'code': record['code']} if 'code' in record else {}
            return self.reply(request_id, 'needs_input', question=record['question'], **details)
        if stage == 'failed':
            return self.reply(request_id, 'failed', code=record['code'])
        if self.ledger.active(record):
            return self.reply(request_id, 'running', stage=stage, poll_after_ms=1500)
        if 'draft_digest' not in record:
            return self.reply(request_id, 'failed', code='operation_interrupted')

        # Reconcile ambiguous delivery by reading preassigned IDs. This never
        # issues writes, reuses upstream authority, or repeats a search.
        draft = self.draft(record['draft'])
        exact_draft = draft is not None and state_digest(draft) == record['draft_digest']
        if exact_draft and 'native_digest' not in record:
            return self.reply(request_id, 'draft_only', warnings=[{
                'code': 'native_not_started', 'message': 'The draft was saved before native creation began.'
            }], **self.links(record, draft, None))
        if exact_draft:
            view = self.native(record['view'])
            if view is not None and state_digest(view) == record['native_digest']:
                return self.completed(request_id, record, draft, view)
        return self.reply(request_id, 'indeterminate', code='write_unconfirmed',
                          **self.links(record, draft if exact_draft else None, None))

    def create(self, request_id, issued_at, brief):
        authoring = self.settings['mode'] == 'authoring'
        record, acquired = self.ledger.claim(self.owner, request_id, issued_at, state_digest(brief),
                                             lease=AUTHORING_LEASE_SECONDS if authoring else CLAIM_SECONDS)
        if not acquired:
            return self.status(request_id, record)
        stage = 'accepted'
        try:
            unsupported = (brief['source']['kind'] != 'index'
                           or brief['source'].get('index') != self.settings['index']
                           or bool(brief.get('requirements'))
                           or any(name not in PILOT_PANELS for page in brief['pages'] for name in page['panels']))
            if not authoring and unsupported:
                record = self.ledger.advance(self.owner, request_id, stage, 'needs_input', question=(
                    'Can you use the configured pilot index and fixed count recipes without additional requirements? Available panels: ' +
                    ', '.join(PILOT_PANELS) + '?'))
                return self.status(request_id, record)

            if authoring:
                self.ledger.advance(self.owner, request_id, stage, 'authoring')
                stage = 'authoring'
                state, warnings = build_authoring(self.runtime, brief, self.settings['provider_route'])
            else:
                self.ledger.advance(self.owner, request_id, stage, 'validating')
                stage = 'validating'
                state, warnings = build_fixture(self.runtime, brief)
            definition = state['definition']
            with self.drafts.locked():
                self.ledger.advance(self.owner, request_id, stage, 'saving_draft',
                                    draft_digest=state_digest(state), warnings=warnings)
                stage = 'saving_draft'
                saved = self.drafts.write(record['draft'], 0, state, active=False, write_id=record['draft'])
            if saved.get('state') != state or saved.get('id') != record['draft']:
                raise ProviderError('The pilot could not confirm the draft write.', 503, 'write_unconfirmed')

            self.ledger.advance(self.owner, request_id, stage, 'saving_native',
                                native_digest=state_digest(definition))
            stage = 'saving_native'
            body = json.dumps(definition, ensure_ascii=True).replace(']]>', ']]]]><![CDATA[>')
            xml = ('<dashboard version="2" theme="light"><label>' + escape(definition['title'])
                   + '</label><description>' + escape(definition['description'])
                   + '</description><definition><![CDATA[' + body + ']]></definition></dashboard>')
            try:
                self.drafts.request(self.views, 'POST', {'name': record['view'], 'eai:data': xml})
            except ProviderError as error:
                if error.status != 403:
                    raise
                record = self.ledger.advance(self.owner, request_id, stage, 'draft_only', warnings=warnings + [{
                    'code': 'native_save_denied', 'message': 'Splunk denied creation of the native dashboard.'
                }])
                return self.status(request_id, record)
            view = self.native(record['view'])
            if view != definition:
                raise ProviderError('The pilot could not confirm the native write.', 503, 'write_unconfirmed')
            record = self.ledger.advance(self.owner, request_id, stage, 'created')
            return self.completed(request_id, record, state, view)
        except ProviderError as error:
            if stage in ('saving_draft', 'saving_native'):
                record = self.ledger.advance(self.owner, request_id, stage, 'indeterminate')
            else:
                reason = getattr(error, 'authoring_reason', error.code)
                if not isinstance(reason, str):
                    reason = None
                if authoring and reason in AUTHORING_QUESTIONS:
                    details = {} if reason == 'authoring_input' else {'code': reason}
                    record = self.ledger.advance(self.owner, request_id, stage, 'needs_input',
                                                 question=AUTHORING_QUESTIONS[reason], **details)
                else:
                    code = FAILURE_CODES.get(reason, 'validation_failed')
                    record = self.ledger.advance(self.owner, request_id, stage, 'failed', code=code)
            return self.status(request_id, record)
