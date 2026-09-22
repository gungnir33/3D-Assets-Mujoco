"""仅测试使用的短生命周期 loopback 模拟服务，不调用第一阶段。"""
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from threading import Thread
import pytest


@pytest.fixture
def mock_server():
    state = {'status': 200, 'body': b'{}', 'headers': {}, 'health': b'{"status":"ok"}'}
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            calls.append({'method': 'GET', 'path': self.path})
            self.send_response(200)
            self.end_headers()
            self.wfile.write(state['health'])
        def do_POST(self):
            body = self.rfile.read(int(self.headers['Content-Length']))
            calls.append({'method': 'POST', 'path': self.path, 'payload': json.loads(body)})
            self.send_response(state['status'])
            for name, value in state['headers'].items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(state['body'])
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    def response(status, body, headers=None, health=None):
        state.update(status=status, body=body, headers=headers or {})
        if health is not None:
            state['health'] = health
    try:
        yield f'http://127.0.0.1:{server.server_port}', calls, response
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

