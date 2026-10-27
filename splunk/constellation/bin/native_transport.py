"""Bounded retries for native reads; never replay dispatch, inference or writes."""
import http.client
import json
import socket
import ssl
import time
from urllib.error import URLError


def transport_failure(error):
    cause = error.reason if isinstance(error, URLError) else error
    # Certificate/identity errors require configuration repair, never bypass.
    if isinstance(cause, ssl.SSLError): return False
    if isinstance(cause, (ConnectionError, TimeoutError, socket.gaierror,
                          http.client.IncompleteRead, http.client.RemoteDisconnected,
                          json.JSONDecodeError)): return True
    if type(cause).__name__ in ('ServerNotFoundError', 'SocketError', 'ConnectTimeout', 'ReadTimeout'): return True
    return str(getattr(error, 'statusCode', '')) in ('502', '503', '504')


def native_read_retry(call, resource, namespace, method, timeout, check_cancel=None, clock=time.monotonic, **kwargs):
    safe = method == 'GET'
    if method == 'POST':
        import re
        prefix = namespace + '/search/v2/jobs/'
        safe = resource.startswith(prefix) and bool(re.fullmatch(r'[A-Za-z0-9_.-]{1,200}/results', resource[len(prefix):]))
    deadline = clock() + timeout
    for attempt in range(2):
        try:
            return call(resource, method=method, timeout=timeout if not attempt else max(.001, deadline-clock()), **kwargs)
        except Exception as error:
            if attempt or not safe or not transport_failure(error) or clock() >= deadline: raise
            if check_cancel: check_cancel()
