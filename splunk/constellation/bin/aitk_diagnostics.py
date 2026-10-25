"""Allowlisted AITK failure guidance; native log text never leaves this module."""
import re
from urllib.parse import quote


def failure_guidance(runtime, job_path):
    """Read only this caller's failed AITK job, returning fixed public messages."""
    fallback = ('AITK inference failed. Test the named connection in AI Toolkit as this Splunk user.', 502, 'aitk_inference_failed')
    user = getattr(runtime, 'user', '')
    prefix = '/servicesNS/' + quote(user, safe='') + '/Splunk_ML_Toolkit/search/jobs/'
    if not user or not job_path.startswith(prefix) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,300}', job_path[len(prefix):]):
        return fallback
    reader = getattr(runtime, 'aitk_job_log', None)
    if reader is None: return fallback
    try: text = reader(job_path)
    except Exception: return fallback
    if not isinstance(text, str): return fallback
    # Do not forward/log native messages: they may contain prompts, endpoints or secrets.
    text = text[:1_000_000].lower()
    if 'no configuration found for llm connection' in text:
        return ('This AITK connection is unavailable to your Splunk user. Ask its owner to provide a connection you can use, then test it again. Your dashboard is unchanged.', 403, 'aitk_connection_unavailable')
    if re.search(r'failed to fetch secret[^\n]{0,300}(?:\b403\b|authorizationfailed|forbidden|access denied)', text):
        return ('AITK was denied access to its stored credential for this request. Ask an AITK administrator to review access for your Splunk user. Open the AITK setup guide in Settings for the test steps.', 403, 'aitk_secret_access_denied')
    if 'insufficient quota' in text or 'insufficient_quota' in text:
        return ('The AITK provider has insufficient quota. Ask the connection owner to check its provider account.', 429, 'aitk_provider_quota')
    if 'context_length_exceeded' in text or 'maximum context length' in text:
        return ('The AITK model context limit was exceeded. Use a connection with enough context for this dashboard.', 422, 'aitk_context_limit')
    return fallback
