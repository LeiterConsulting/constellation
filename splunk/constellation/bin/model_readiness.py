"""Public model diagnostics. Never infer provider capacity from a model name."""
CREATE_OUTPUT_TOKENS = 8500
EDIT_OUTPUT_TOKENS = 6500
OLLAMA_CONTEXT_TOKENS = 32768


def ollama_context(details):
    info = (details or {}).get('model_info', {})
    if not isinstance(info, dict): return None
    capacity = info.get(str(info.get('general.architecture')) + '.context_length')
    return capacity if type(capacity) is int and 0 < capacity <= 100_000_000 else None


def report(provider, details=None, metadata_error=False, usage=None):
    usage = usage if isinstance(usage, dict) else {}
    limits = [] if provider == 'aitk' else [{'label': 'Maximum requested output', 'value': 'Up to 8,500 tokens for creation; 6,500 for edits. Internal foundations use 3,500; context budgeting can reduce these limits.'}]
    warnings = []
    if provider == 'aitk':
        limits.append({'label': 'Model and token limits', 'value': 'Managed by the named AI Toolkit connection; not verified by Constellation.'})
        warnings.append('Check Max Tokens in AI Toolkit → Connections. A small output limit can pass this test but prevent dashboard creation. Reasoning models may consume that budget before returning visible JSON.')
    elif provider == 'ollama':
        limits.append({'label': 'Requested context window', 'value': 'Up to 32,768 tokens, capped by reported model capacity; shared by instructions, conversation, dashboard and output.'})
        capacity = ollama_context(details)
        if capacity:
            limits.append({'label': 'Reported model context', 'value': format(capacity, ',') + ' tokens (Ollama /api/show).'})
            if capacity < OLLAMA_CONTEXT_TOKENS:
                warnings.append('The model reports a smaller context window than the app’s usual allocation. The app caps requests to that capacity; keep dashboards and conversations small or choose a model with more context.')
        else:
            limits.append({'label': 'Model context capacity', 'value': 'Not reported; capacity is unverified.'})
        if metadata_error: warnings.append('Model metadata could not be checked. Confirm the endpoint and installed model, then test again.')
        warnings.append('Context capacity does not guarantee reliable structured dashboard edits. Larger local models may need more memory and time.')
    else:
        limits.append({'label': 'Model context and maximum output', 'value': 'Not exposed by model discovery; check the selected model’s documentation.'})
        warnings.append('Reasoning tokens share the output budget. Large dashboards, long conversations and attachments can reach model limits even when a small test passes.')
    observed = {}
    for key in ('input_tokens', 'output_tokens'):
        value = (usage or {}).get(key)
        if type(value) is int and value >= 0: observed[key] = value
    reasoning = (usage or {}).get('output_tokens_details', {}).get('reasoning_tokens') if isinstance((usage or {}).get('output_tokens_details'), dict) else None
    if type(reasoning) is int and reasoning >= 0: observed['reasoning_tokens'] = reasoning
    return {'limits': limits, 'warnings': warnings, 'usage': observed, 'tested': False,
            'scope': 'The test checks a small structured response. It does not qualify full dashboard creation, speed or context capacity.'}
