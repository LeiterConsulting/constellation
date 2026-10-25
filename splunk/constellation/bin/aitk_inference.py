"""Opt-in inference-only boundary. Only this handler receives system authentication.

The caller supplies text, never SPL, an execution user, a job ID, or a provider URL.
The administrator pins the named AITK connection, execution namespace and audience.
Actual data searches, drafts and native saves never use this runtime.
"""
import fcntl
import hashlib
import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from urllib.parse import parse_qs
from provider_service import ProviderError

POLICY_PATH = '/servicesNS/nobody/constellation/configs/conf-constellation_aitk/inference'
CAPABILITY = 'constellation_use_aitk'


def policy(runtime, context):
    result = runtime.request(POLICY_PATH, optional=True)
    entries = result.get('entry', [])
    if not entries: return None
    entry = entries[0]
    value, acl = entry.get('content', {}), entry.get('acl', {})
    if value.get('enabled') not in (True, 1, '1', 'true'): return None
    # A personal shadow stanza or author-writable policy cannot authorize elevation.
    if (acl.get('owner') != 'nobody' or acl.get('app') != 'constellation' or acl.get('sharing') != 'app'
            or not isinstance(acl.get('perms', {}).get('write'), list)
            or set(acl['perms']['write']) - {'admin', ''}):
        raise ProviderError('The shared AITK policy is not restricted to administrators.', 503, 'aitk_policy_invalid')
    connection, executor = value.get('connection', ''), value.get('execution_user', '')
    roles = [r.strip() for r in value.get('allowed_roles', '').split(',') if r.strip()]
    if (not re.fullmatch(r'[A-Za-z0-9_. -]{1,200}', connection)
            or not re.fullmatch(r'[A-Za-z0-9_.@-]{1,100}', executor) or executor in ('-', 'nobody')
            or not roles or len(roles) > 30 or any(not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', r) for r in roles)):
        raise ProviderError('An administrator must finish the shared AITK policy.', 503, 'aitk_policy_invalid')
    if CAPABILITY not in context.get('capabilities', []) or not set(roles).intersection(context.get('roles', [])):
        raise ProviderError('This user is not authorized for the shared AITK connection.', 403, 'aitk_inference_denied')
    return {'connection': connection, 'execution_user': executor}


@contextmanager
def admission(user, root=None, clock=time.time):
    """Bound this privileged resource; retain only short-lived anonymous slot metadata."""
    root = root or os.path.join(os.environ['SPLUNK_HOME'], 'var', 'run', 'splunk', 'constellation_aitk')
    os.makedirs(root, mode=0o700, exist_ok=True)
    owner, name = hashlib.sha256(user.encode()).hexdigest(), secrets.token_hex(16) + '.json'
    path = os.path.join(root, name)
    def lock(): return os.fdopen(os.open(os.path.join(root, 'admission.lock'), os.O_CREAT | os.O_RDWR, 0o600), 'a')
    with lock() as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        active = []
        for filename in os.listdir(root):
            if not re.fullmatch(r'[a-f0-9]{32}\.json', filename): continue
            item_path = os.path.join(root, filename)
            try:
                with open(item_path) as source: item = json.load(source)
                valid = (isinstance(item, dict) and isinstance(item.get('expires'), (int, float))
                         and isinstance(item.get('owner'), str) and re.fullmatch(r'[a-f0-9]{64}', item['owner']))
            except (FileNotFoundError, ValueError): valid = False
            if not valid:
                try: os.unlink(item_path)
                except FileNotFoundError: pass
                continue
            if item['expires'] <= clock(): os.unlink(item_path)
            else: active.append(item)
        if len(active) >= 8 or sum(item['owner'] == owner for item in active) >= 2:
            raise ProviderError('Shared AITK is busy. Wait for the current request or stop it.', 429, 'aitk_busy')
        with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as target:
            json.dump({'owner': owner, 'expires': clock() + 180}, target)
    try: yield
    finally:
        with lock() as guard:
            fcntl.flock(guard, fcntl.LOCK_EX)
            try: os.unlink(path)
            except FileNotFoundError: pass


def execute(caller, privileged, body, slot_root=None):
    # Authenticate against Splunk with the caller token; body/session labels are not authority.
    context = caller.request('/services/authentication/current-context')['entry'][0]['content']
    if context.get('username') != caller.user or CAPABILITY not in context.get('capabilities', []):
        raise ProviderError('This user cannot use shared AITK inference.', 403, 'aitk_inference_denied')
    approved = policy(privileged, context)
    if body == {'action': 'status'}:
        return {'available': bool(approved), 'connection': approved['connection'] if approved else ''}
    if set(body) - {'action', 'connection', 'prompt', 'runHandle'} or body.get('action') != 'complete':
        raise ProviderError('This endpoint accepts a shared AITK prompt only.')
    if not approved or body.get('connection') != approved['connection']:
        raise ProviderError('This shared AITK connection is not approved.', 403, 'aitk_inference_denied')
    prompt = body.get('prompt')
    if not isinstance(prompt, str) or not 1 <= len(prompt.encode()) <= 250_000:
        raise ProviderError('Use an AITK prompt under 250 KB.', 413)
    # A fresh isolated runtime is used only for the constant synthetic inference query.
    from search_service import SearchService
    from provider_adapters import AITKClient
    worker = SearchService(approved['execution_user'], privileged.token)
    if body.get('runHandle'):
        from authoring_progress import AuthoringProgress
        control = AuthoringProgress(caller.user, caller.token)
        control.check(body['runHandle'])
        worker.check_cancel = lambda: control.check(body['runHandle'])
    with admission(caller.user, slot_root):
        return AITKClient(worker).complete_prompt(approved['connection'], prompt, encoded=True, delete_job=True)


def form_body(request):
    """The internal bridge uses a form POST; accept one value per known field."""
    raw = request.get('payload', '')
    if not isinstance(raw, str) or len(raw) > 1_100_000:
        raise ProviderError('This inference request is too large.', 413)
    try: values = parse_qs(raw, keep_blank_values=True, strict_parsing=True, max_num_fields=4)
    except ValueError: raise ProviderError('Provide a valid inference request.') from None
    if any(len(v) != 1 for v in values.values()): raise ProviderError('Duplicate inference fields are not allowed.')
    return {k: v[0] for k, v in values.items()}
