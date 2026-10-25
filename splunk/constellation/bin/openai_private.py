"""System authority is confined to the verified caller's own encrypted record.

Never accept a username, credential ID, URL or arbitrary REST resource. Never
return keys; inference uses only the fixed official OpenAI client.
"""
import copy
import os
import re
from connection_store import secretless
from credential_store import CredentialStore
from model_capabilities import attachment_parts
from provider_service import OpenAIClient, ProviderError


def config_fields(body):
    if not isinstance(body, dict) or set(body) - {'api_key', 'key_configured', 'model', 'active_provider', 'connections'}:
        raise ProviderError('Provide valid private connection settings.')
    result = copy.deepcopy(body)
    result.pop('key_configured', None)
    key = result.pop('api_key', '')
    if not isinstance(key, str) or len(key) > 8192 or any(c.isspace() for c in key):
        raise ProviderError('Enter a valid API key without spaces or line breaks.')
    secretless(result)
    if result.get('active_provider', 'openai') not in ('openai', 'ollama', 'aitk'):
        raise ProviderError('Choose a supported provider.')
    model = result.get('model', '')
    if not isinstance(model, str) or (model and not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,200}', model)):
        raise ProviderError('Enter a valid model ID.')
    for value in result.get('connections', {}).values():
        if any(len(v) > 500 for v in value.values()): raise ProviderError('The connection settings are too large.')
    return result, key


def public_config(config):
    if config is None: return None
    # Validate the saved schema before projecting; unknown legacy fields cannot
    # become a route for returning secret-bearing values.
    fields, key = config_fields(config)
    return dict(fields, key_configured=bool(key))


def inference_request(body, config):
    if (not isinstance(body, dict) or set(body) - {'model', 'store', 'instructions', 'input', 'max_output_tokens', 'text', 'reasoning'}
            or body.get('model') != config.get('model') or not config.get('model')
            or type(body.get('max_output_tokens')) is not int or not 1 <= body['max_output_tokens'] <= 16000
            or not isinstance(body.get('instructions'), str) or len(body['instructions'].encode()) > 250_000
            or not isinstance(body.get('text'), dict) or set(body['text']) != {'format'}):
        raise ProviderError('Provide a bounded structured OpenAI request for your configured model.')
    fmt = body['text']['format']
    if not isinstance(fmt, dict) or fmt.get('type') != 'json_schema' or set(fmt) - {'type', 'name', 'strict', 'schema'}:
        raise ProviderError('Use a structured JSON schema response.')
    result = copy.deepcopy(body); result['store'] = False
    inputs, files, positions = result.get('input'), [], []
    if isinstance(inputs, str):
        if len(inputs.encode()) > 1_000_000: raise ProviderError('This OpenAI context is too large.', 413)
    elif isinstance(inputs, list) and len(inputs) <= 32:
        for entry in inputs:
            if (not isinstance(entry, dict) or set(entry) != {'role', 'content'} or entry.get('role') not in ('user', 'assistant')
                    or not isinstance(entry.get('content'), list) or len(entry['content']) > 16):
                raise ProviderError('Provide a supported OpenAI conversation.')
            for i, part in enumerate(entry['content']):
                if not isinstance(part, dict): raise ProviderError('Provide supported input content.')
                kind = part.get('type')
                if kind == 'input_text' and set(part) == {'type', 'text'} and isinstance(part.get('text'), str):
                    if len(part['text'].encode()) > 1_000_000: raise ProviderError('This OpenAI context is too large.', 413)
                elif kind == 'input_image' and not set(part) - {'type', 'image_url', 'detail'}:
                    files.append({'name': 'reference image', 'data': part.get('image_url')}); positions.append((entry['content'], i))
                elif kind == 'input_file' and set(part) == {'type', 'filename', 'file_data'}:
                    files.append({'name': 'reference.pdf', 'data': part.get('file_data')}); positions.append((entry['content'], i))
                else: raise ProviderError('Only text and supported inline image/PDF inputs are allowed.')
        for (parts, i), canonical in zip(positions, attachment_parts(files, config['model'])): parts[i] = canonical
    else: raise ProviderError('Provide a supported OpenAI conversation.')
    return result


def execute(caller, privileged, action, body=None, client=None, slot_root=None):
    context = caller.request('/services/authentication/current-context')['entry'][0]['content']
    if context.get('username') != caller.user or 'search' not in context.get('capabilities', []):
        raise ProviderError('This private connection is unavailable to this user.', 403)
    # The platform verified caller is the sole authority for both ID and owner.
    store = CredentialStore(caller.user, privileged.token)
    if action == 'connection':
        if body is None: return {'config': public_config(store.read())}
        fields, key = config_fields(body)
        previous = store.read() or {}
        key = key or previous.get('api_key', '')
        if not key: raise ProviderError('Enter an OpenAI API key.')
        store.write(dict(fields, api_key=key))
        return {'saved': True}
    if action not in ('models', 'responses'): raise ProviderError('Unsupported OpenAI operation.', 404)
    config = store.read() or {}
    if not config.get('api_key'): raise ProviderError('Add your OpenAI key in Settings first.', 409)
    client = client or OpenAIClient()
    request = inference_request(body, config) if action == 'responses' else None
    if action == 'models' and body is not None: raise ProviderError('This OpenAI operation does not accept a request body.')
    from inference_admission import admission
    root = slot_root or os.path.join(os.environ['SPLUNK_HOME'], 'var', 'run', 'splunk', 'constellation_openai')
    with admission(caller.user, root, provider='openai'): return client.call(config['api_key'], action, request)
