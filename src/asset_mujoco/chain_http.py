"""共享本机文件系统的有界 HTTP 客户端；不重试生成、不跟随重定向。"""
import http.client
import ipaddress
import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from .chain_contracts import MAX_JSON, parse_json

START_SCRIPT = '/home/mcl/workspace/3D-Assets-Agent/scripts/start_server.sh'


class Phase1Error(Exception):
    def __init__(self, code, message, *, http_status=None, details=None, raw_body=b'',
                 truncated=False, result_unknown=False):
        super().__init__(message)
        self.code, self.message = code, message
        self.http_status, self.details = http_status, details
        self.raw_body, self.truncated = raw_body[:MAX_JSON], truncated
        self.result_unknown = result_unknown

    def as_dict(self):
        return {key: getattr(self, key) for key in
                ('code', 'message', 'http_status', 'details', 'truncated', 'result_unknown')}


def validate_base_url(value: str) -> str:
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ValueError('CHAIN_INVALID_BASE_URL')
    parsed = urlsplit(value)
    if (parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost', '::1')
            or parsed.port is None or not 1 <= parsed.port <= 65535
            or parsed.username is not None or parsed.password is not None
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('CHAIN_LOOPBACK_HTTP_REQUIRED')
    host = '[::1]' if parsed.hostname == '::1' else parsed.hostname
    return f'http://{host}:{parsed.port}'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LocalGenerationClient:
    def __init__(self, base_url: str):
        self.base_url = validate_base_url(base_url)
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def _check_resolution(self):
        parsed = urlsplit(self.base_url)
        if parsed.hostname == 'localhost':
            addresses = socket.getaddrinfo('localhost', parsed.port, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_loopback for a in addresses):
                raise ValueError('CHAIN_LOCALHOST_NOT_LOOPBACK')

    def _read(self, response, generation):
        status = response.code
        data = response.read(MAX_JSON + 1)
        if len(data) > MAX_JSON:
            raise Phase1Error('RESPONSE_TOO_LARGE', 'HTTP response exceeds 1 MiB', http_status=status,
                              raw_body=data, truncated=True, result_unknown=generation)
        length = response.headers.get('Content-Length')
        if length is not None and int(length) != len(data):
            raise Phase1Error('RESPONSE_INCOMPLETE', 'HTTP body ended before declared length',
                              http_status=status, raw_body=data, result_unknown=generation)
        return data

    def _request(self, path, payload=None):
        generation = payload is not None
        try:
            self._check_resolution()
        except (OSError, ValueError) as error:
            raise Phase1Error('LOCAL_ADDRESS_REJECTED', str(error)) from error
        request = Request(self.base_url + path,
                          data=json.dumps(payload, allow_nan=False).encode() if generation else None,
                          headers={'Content-Type': 'application/json', 'Accept': 'application/json'})
        try:
            with self.opener.open(request, timeout=1800 if generation else 10) as response:
                return self._read(response, generation)
        except HTTPError as error:
            with error:
                raw = error.read(MAX_JSON + 1)
            truncated = len(raw) > MAX_JSON
            body = raw[:MAX_JSON]
            code, message, details = f'HTTP_{error.code}', str(error), None
            if not truncated:
                try:
                    parsed = parse_json(body)
                    business = parsed.get('error')
                    if isinstance(business, dict):
                        code = str(business.get('code', code))
                        message = str(business.get('message', message))
                        details = business.get('details')
                    elif 'detail' in parsed:
                        details = parsed['detail']
                except (ValueError, UnicodeError):
                    pass
            raise Phase1Error(code, message, http_status=error.code, details=details,
                              raw_body=body, truncated=truncated) from error
        except Phase1Error:
            raise
        except (OSError, URLError, http.client.HTTPException, ValueError) as error:
            raw = getattr(error, 'partial', b'')
            raise Phase1Error('GENERATION_RESULT_UNKNOWN' if generation else 'HTTP_CONNECTION_FAILED',
                              str(error), raw_body=raw, result_unknown=generation) from error

    def health(self) -> dict:
        try:
            body = self._request('/health')
            result = parse_json(body)
            if result.get('status') != 'ok':
                raise ValueError('unrecognized health status')
            return result
        except (Phase1Error, ValueError, UnicodeError) as error:
            raise Phase1Error('LOCAL_3D_SERVER_NOT_RUNNING',
                              f'本地生成服务不可用；请手动启动 {START_SCRIPT}',
                              details={'cause': str(error)}, raw_body=getattr(error, 'raw_body', b'')) from error

    def generate(self, endpoint: str, payload: dict) -> bytes:
        if endpoint not in ('text', 'image', 'texture'):
            raise ValueError('CHAIN_INVALID_ENDPOINT')
        return self._request('/generate/' + endpoint, payload)
