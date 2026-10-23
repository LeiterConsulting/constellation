"""Provider-specific wire formats; no credentials, raw errors, or prompts in logs."""
import ipaddress
import json
import re
import socket
import ssl
import time
from urllib.parse import urlsplit, quote
from urllib.request import Request, build_opener, HTTPSHandler, ProxyHandler
from urllib.error import HTTPError, URLError
from provider_service import ProviderError, NoRedirect


def ollama_origin(value):
    if not isinstance(value, str) or len(value) > 500:
        raise ProviderError('Enter an Ollama server URL.')
    parsed = urlsplit(value)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
        raise ProviderError('Use an Ollama origin such as http://server:11434, without a path or credentials.')
    try:
        port = parsed.port
        addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(parsed.hostname, port or (443 if parsed.scheme == 'https' else 80))}
    except (ValueError, OSError):
        raise ProviderError('The Ollama server name could not be resolved.') from None
    if not addresses or any(ip.is_link_local or ip.is_multicast or ip.is_unspecified or (ip.is_reserved and not ip.is_loopback) for ip in addresses):
        raise ProviderError('This address is not allowed for an Ollama connection.')
    if parsed.scheme == 'http' and any(not (ip.is_private or ip.is_loopback) for ip in addresses):
        raise ProviderError('Public Ollama endpoints require HTTPS.')
    return value.rstrip('/')


class OllamaClient:
    def call(self, origin, resource, body=None):
        if resource not in ('tags', 'show', 'chat'):
            raise ProviderError('Unsupported Ollama operation.')
        origin = ollama_origin(origin)
        request = Request(origin + '/api/' + resource, data=json.dumps(body).encode() if body is not None else None,
                          headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                          method='POST' if body is not None else 'GET')
        try:
            # Direct private-LAN connections must not leak prompts to an environment proxy.
            opener = build_opener(ProxyHandler({}), NoRedirect, HTTPSHandler(context=ssl.create_default_context()))
            with opener.open(request, timeout=90 if resource == 'chat' else 8) as response:
                raw = response.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise ProviderError('The Ollama response exceeded the allowed size.', 502)
                result = json.loads(raw)
                if not isinstance(result, dict) or result.get('error'):
                    raise ProviderError('Ollama could not complete this request. Check the server and selected model.', 502)
                return result
        except HTTPError as error:
            raise ProviderError('Ollama returned HTTP ' + str(error.code) + '. Check the endpoint and installed model.', 502) from None
        except (URLError, OSError, ssl.SSLError, TimeoutError):
            raise ProviderError('The Splunk server could not reach Ollama. Check its network listener and endpoint.', 502) from None
        except (ValueError, TypeError):
            raise ProviderError('Ollama returned an unreadable response.', 502) from None

    def complete(self, saved, request):
        messages = [{'role': 'system', 'content': request['instructions']}]
        entries = request['input'] if isinstance(request['input'], list) else [{'role': 'user', 'content': [{'type': 'input_text', 'text': request['input']}]}]
        for entry in entries:
            content, images = [], []
            for part in entry['content']:
                if part['type'] == 'input_text': content.append(part['text'])
                elif part['type'] == 'input_image': images.append(part['image_url'].split(',', 1)[1])
                else: raise ProviderError('Ollama accepts image references here; PDF transmission is blocked.', 409)
            message = {'role': entry['role'], 'content': '\n'.join(content)}
            if images: message['images'] = images
            messages.append(message)
        schema = request['text']['format']['schema']
        messages[0]['content'] += '\nReturn JSON only matching this schema: ' + json.dumps(schema)
        body = {'model': saved['model'], 'messages': messages, 'stream': False, 'format': schema,
                'options': {'temperature': 0, 'num_predict': request['max_output_tokens'], 'num_ctx': 32768}}
        details = self.call(saved['base_url'], 'show', {'model': saved['model']})
        if False in details.get('thinking', {}).get('values', []): body['think'] = False
        response = self.call(saved['base_url'], 'chat', body)
        if response.get('done') is not True or response.get('done_reason') == 'length':
            raise ProviderError('Ollama did not finish its edit. Your dashboard is unchanged.', 502)
        return normalized(response.get('message', {}).get('content', ''))


def normalized(text):
    if not isinstance(text, str) or len(text) > 1_000_000:
        raise ProviderError('The model returned an invalid text response.', 502)
    # Some AITK connections return a single markdown JSON fence. Never extract
    # arbitrary embedded JSON or execute text returned by a provider.
    match = re.fullmatch(r'\s*```(?:json)?\s*\n([\s\S]*?)\n```\s*', text)
    if match: text = match.group(1)
    return {'status': 'completed', 'output': [{'content': [{'type': 'output_text', 'text': text}]}]}


class AITKClient:
    """Use the documented ai command under the signed-in user's AITK context.

    AITK retains custody of credentials and enforces connection access. This
    path handles text only; no provider tokens or raw indexed events are read.
    """
    def __init__(self, runtime): self.runtime = runtime

    def complete(self, saved, request):
        if self.runtime is None: raise ProviderError('AITK requires an authenticated Splunk session.', 409)
        context = self.runtime.request('/services/authentication/current-context')['entry'][0]['content']
        if 'apply_ai_commander_command' not in context.get('capabilities', []):
            raise ProviderError('This Splunk user needs the AITK apply_ai_commander_command capability.', 403)
        texts = [request['instructions'], 'Return only JSON matching this schema: ' + json.dumps(request['text']['format']['schema'])]
        entries = request['input'] if isinstance(request['input'], list) else [{'content': [{'type': 'input_text', 'text': request['input']}]}]
        for entry in entries:
            for part in entry['content']:
                if part.get('type') != 'input_text': raise ProviderError('This AITK route supports text only. Attachments were not sent.', 409)
                texts.append(part['text'])
        prompt = '\n\n'.join(texts)
        if len(prompt.encode()) > 250_000: raise ProviderError('This document exceeds the AITK prompt limit. Use a smaller dashboard.', 413)
        # JSON strings are also safe SPL double-quoted literals. The template is
        # constant, so braces in dashboard JSON are never interpreted by AITK.
        query = '| makeresults | eval constellation_prompt=' + json.dumps(prompt, ensure_ascii=True) + ' | ai prompt="{constellation_prompt}" connection=' + json.dumps(saved['connection']) + ' | fields ai_result_1'
        base = '/servicesNS/' + quote(self.runtime.user, safe='') + '/Splunk_ML_Toolkit/search/jobs'
        job = self.runtime.request(base, 'POST', {'search': query, 'exec_mode': 'normal', 'earliest_time': '-1m', 'latest_time': 'now', 'max_time': '90', 'max_count': '1'})
        sid = job.get('sid')
        if not isinstance(sid, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,300}', sid):
            raise ProviderError('AITK did not start its inference job.', 502)
        path = base + '/' + quote(sid, safe='')
        deadline = time.monotonic() + 90
        try:
            while time.monotonic() < deadline:
                state = self.runtime.request(path)['entry'][0]['content']
                if state.get('dispatchState') in ('FAILED', 'BAD_INPUT_CANCEL'):
                    raise ProviderError('AITK inference failed. Check the named connection in AI Toolkit.', 502)
                if state.get('isDone') in (True, 1, '1'):
                    result = self.runtime.request(path + '/results')
                    rows = result.get('results', [])
                    if len(rows) != 1 or not isinstance(rows[0].get('ai_result_1'), str):
                        raise ProviderError('AITK returned no usable completion. Test the connection in AI Toolkit.', 502)
                    return normalized(rows[0]['ai_result_1'])
                time.sleep(0.5)
            raise ProviderError('AITK inference timed out. Your dashboard is unchanged.', 504)
        finally:
            # Cancel an outstanding job; completed jobs retain normal Splunk TTL.
            try: self.runtime.request(path + '/control', 'POST', {'action': 'cancel'})
            except ProviderError: pass
