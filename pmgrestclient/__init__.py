import requests
from logging import getLogger
from json.decoder import JSONDecodeError
from time import sleep

logger = getLogger(__name__)

class ApiCallException(Exception):
    def __init__(self, error_code_type, **kwargs):
        self.given_args = kwargs
        self.url = kwargs.get('url')
        if 'message' in kwargs:
            super(ApiCallException, self).__init__(kwargs['message'])
        else:
            err = lambda v: v if not isinstance(v, error_code_type) else v.value[0]
            super(ApiCallException, self).__init__(', '.join([f'{k}: {err(v)}' for k, v in kwargs.items()]))

    @property
    def status_code(self):
        return self.given_args.get('status_code')

    class EmptyError:
        value = None
        name = None

    @property
    def error(self):
        return self.given_args.get('error', ApiCallException.EmptyError())

    @property
    def response_body(self):
        return self.given_args.get('response_body', {})

class ApiBase(object):
    def __init__(self, base, error_code_type, stat404retry_count=None, stat404retry_delay=None):
        self.base = base
        self.error_code_type = error_code_type
        self.stat404retry_count = stat404retry_count or 0
        self.stat404retry_delay = stat404retry_delay or 0
        self.errors_by_code = {e.value[0]:e for e in error_code_type}

    def get(self, path, headers=None, data=None, params=None, **kwargs):
        return self._call(requests.get, path, headers=headers, data=data, params=params, **kwargs)

    def delete(self, path, headers=None, data=None, params=None, **kwargs):
        return self._call(requests.delete, path, headers=headers, data=data, params=params, **kwargs)

    def put(self, path, headers=None, data=None, params=None, **kwargs):
        return self._call(requests.put, path, headers=headers, data=data, params=params, **kwargs)

    def post(self, path, headers=None, data=None, params=None, **kwargs):
        return self._call(requests.post, path, headers=headers, data=data, params=params, **kwargs)

    def _url(self, path):
        return f'{self.base}/{path}'

    def _call(self, call, path, headers=None, data=None, params=None, **kwargs):
        for i in range(0, self.stat404retry_count + 1):
            try:
                res = call(self._url(path), headers=(headers or self.headers(**kwargs)), json=data if data else None, params=params)
            except requests.exceptions.ConnectionError as e:
                raise ApiCallException(self.error_code_type, message=f'Connection error', url=self._url(path))
            if 200 <= res.status_code <= 299:
                return (json(res), res.status_code)
            if res.status_code == 404 and i < self.stat404retry_count:
                logger.warning(f'Call to {self._url(path)} returned 404 (call {i+1} of {self.stat404retry_count} trying again with delay of {self.stat404retry_delay} seconds)')
                sleep(self.stat404retry_delay)
                continue
            break

        try:
            resp_j = json(res)
            logger.debug(f'Error Response in call to {path}: {resp_j}')
            if resp_j.get('error') in self.errors_by_code:
                raise ApiCallException(self.error_code_type, status_code=res.status_code, error=self.errors_by_code.get(resp_j.get('error')),
                        url=self._url(path), response_body=resp_j)
        except ValueError:
            pass
        raise ApiCallException(self.error_code_type, status_code=res.status_code, url=self._url(path))

    def headers(self, **kwargs):
        return None

def json(resp):
    try:
        return resp.json()
    except JSONDecodeError:
        return {}
