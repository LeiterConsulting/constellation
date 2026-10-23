"""Per-turn recovery limits and reusable current-user search evidence."""
import copy
import json
import time
from provider_service import ProviderError

MAX_MODEL_CALLS = 3
MAX_QUERY_CHECKS = 16
MAX_SECONDS = 120


class RecoverySession:
    def __init__(self, runtime, clock=time.monotonic):
        self.runtime, self.clock = runtime, clock
        self.started = clock()
        self.cache, self.notes = {}, []
        self.calls = 0

    def check_time(self):
        if self.clock() - self.started >= MAX_SECONDS:
            raise ProviderError('The automatic recovery time budget is exhausted. Your previous dashboard is preserved.', 422, 'recovery_budget')

    def model_call(self):
        self.check_time()
        if self.calls >= MAX_MODEL_CALLS:
            raise ProviderError('The automatic recovery attempt budget is exhausted.', 422, 'recovery_budget')
        self.calls += 1

    def preview(self, body):
        key = json.dumps(body, sort_keys=True)
        if key in self.cache:
            result = self.cache[key]
            if isinstance(result, ProviderError): raise result
            return copy.deepcopy(result)
        self.check_time()
        if len(self.cache) >= MAX_QUERY_CHECKS:
            raise ProviderError('The automatic recovery search budget is exhausted. Your previous dashboard is preserved.', 422, 'recovery_budget')
        try:
            result = self.runtime.preview(body)
        except ProviderError as error:
            self.cache[key] = error
            raise
        self.cache[key] = copy.deepcopy(result)
        return result

    def evidence(self):
        return {'modelCalls': self.calls, 'queryChecks': len(self.cache), 'maximumModelCalls': MAX_MODEL_CALLS,
                'maximumQueryChecks': MAX_QUERY_CHECKS, 'seconds': round(self.clock() - self.started, 2)}
