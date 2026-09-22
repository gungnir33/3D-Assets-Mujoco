import json
import pytest


@pytest.mark.parametrize('value', ['https://localhost:8080', 'http://example.com:8080',
    'http://127.0.0.1', 'http://127.0.0.1:0', 'http://user@localhost:8080',
    'http://localhost:8080/path', 'http://localhost:8080/?secret=x', 'http://localhost:8080/#frag'])
def test_nonlocal_or_ambiguous_urls_rejected(value):
    from asset_mujoco.chain_http import validate_base_url
    with pytest.raises(ValueError):
        validate_base_url(value)


def test_redirect_is_not_followed(mock_server):
    from asset_mujoco.chain_http import LocalGenerationClient, Phase1Error
    url, calls, respond = mock_server
    respond(307, b'forward', {'Location': url + '/other'})
    with pytest.raises(Phase1Error) as caught:
        LocalGenerationClient(url).generate('text', {'prompt': 'box', 'format': 'glb'})
    assert caught.value.http_status == 307
    assert [c['path'] for c in calls] == ['/generate/text']


@pytest.mark.parametrize('status,body,code', [
    (422, {'detail': [{'loc': ['body', 'prompt'], 'msg': 'bad prompt'}]}, 'HTTP_422'),
    (503, {'error': {'code': 'CUDA_OUT_OF_MEMORY', 'message': 'OOM', 'details': {'free': 0}}}, 'CUDA_OUT_OF_MEMORY'),
    (500, None, 'HTTP_500')])
def test_http_error_details_preserved(mock_server, status, body, code):
    from asset_mujoco.chain_http import LocalGenerationClient, Phase1Error
    url, calls, respond = mock_server
    respond(status, b'<html>error</html>' if body is None else json.dumps(body).encode())
    with pytest.raises(Phase1Error) as caught:
        LocalGenerationClient(url).generate('text', {'prompt': 'box'})
    error = caught.value
    assert error.code == code and error.http_status == status
    assert error.raw_body and not error.result_unknown
    assert len(calls) == 1
    if status == 422:
        assert error.details == body['detail']


def test_success_body_preserved_and_environment_proxy_ignored(mock_server, monkeypatch):
    from asset_mujoco.chain_http import LocalGenerationClient
    url, calls, respond = mock_server
    monkeypatch.setenv('HTTP_PROXY', 'http://127.0.0.1:1')
    monkeypatch.setenv('http_proxy', 'http://127.0.0.1:1')
    respond(200, b'not json')
    client = LocalGenerationClient(url)
    assert client.health()['status'] == 'ok'
    assert client.generate('image', {'image': '/synthetic.png'}) == b'not json'
    assert calls[-1]['payload'] == {'image': '/synthetic.png'}


@pytest.mark.parametrize('body,headers', [(b'x' * (1024 * 1024 + 1), {}),
                                       (b'short', {'Content-Length': '100'})])
def test_bounded_or_incomplete_success_is_unknown(mock_server, body, headers):
    from asset_mujoco.chain_http import LocalGenerationClient, Phase1Error
    url, calls, respond = mock_server
    respond(200, body, headers)
    with pytest.raises(Phase1Error) as caught:
        LocalGenerationClient(url).generate('text', {'prompt': 'box'})
    assert caught.value.result_unknown and len(caught.value.raw_body) <= 1024 * 1024
    assert len(calls) == 1


def test_timeout_has_no_retry_and_uses_1800_seconds(monkeypatch):
    from asset_mujoco.chain_http import LocalGenerationClient, Phase1Error
    client = LocalGenerationClient('http://127.0.0.1:12345')
    timeouts = []
    def timeout(request, timeout):
        timeouts.append(timeout)
        raise TimeoutError('injected')
    monkeypatch.setattr(client.opener, 'open', timeout)
    with pytest.raises(Phase1Error) as caught:
        client.generate('text', {'prompt': 'box'})
    assert caught.value.result_unknown and timeouts == [1800]


def test_invalid_health_prevents_generation(mock_server):
    from asset_mujoco.chain_http import LocalGenerationClient, Phase1Error
    url, calls, respond = mock_server
    respond(200, b'{}', health=b'{"status":"bad"}')
    with pytest.raises(Phase1Error) as caught:
        LocalGenerationClient(url).health()
    assert caught.value.code == 'LOCAL_3D_SERVER_NOT_RUNNING'
    assert 'start_server.sh' in caught.value.message
    assert [c['method'] for c in calls] == ['GET']


def test_localhost_external_resolution_rejected(monkeypatch):
    import socket
    from asset_mujoco.chain_http import LocalGenerationClient, Phase1Error
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **kw: [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.0.2.1', 1))])
    with pytest.raises(Phase1Error):
        LocalGenerationClient('http://localhost:12345').health()
