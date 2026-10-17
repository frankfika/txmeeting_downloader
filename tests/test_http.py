"""用本地 HTTP 服务验证 requests 实际流式读取和超时行为。"""
import contextlib
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlsplit
from unittest.mock import patch

import requests
from downloader.video import download_video, _request

VIDEO = (b'\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42'
         + b'\x00\x00\x00\x08moov' + b'\x00\x00\x00\x6cmdat' + b'video' * 20)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path in ('/redirect', '/cookie', '/redirect-body'):
            self.send_response(302)
            self.send_header('Location', '/need-cookie' if self.path == '/cookie' else '/video')
            self.send_header('Set-Cookie', 'access=yes; Path=/')
            if self.path == '/redirect-body':
                self.send_header('Content-Length', str(2 * 1024 * 1024))
            self.end_headers()
            if self.path == '/redirect-body':
                try:
                    self.wfile.write(b'x' * (2 * 1024 * 1024))
                except (BrokenPipeError, ConnectionResetError):
                    pass
            return
        if self.path == '/need-cookie' and 'access=yes' not in self.headers.get('Cookie', ''):
            self.send_response(403)
            self.end_headers()
            return
        if self.path == '/partial':
            self.send_response(206)
            self.send_header('Content-Range', f'bytes 0-7/{len(VIDEO)}')
            body = VIDEO[:8]
        else:
            self.send_response(200)
            body = b'<html>Login required</html>' if self.path == '/html' else VIDEO
        self.send_header('Content-Type', 'text/html' if self.path == '/html' else 'video/mp4')
        if self.path == '/chunked':
            self.send_header('Transfer-Encoding', 'chunked')
        elif self.path != '/unknown':
            self.send_header('Content-Length', str(len(body) + (100 if self.path == '/broken' else 0)))
        self.send_header('Connection', 'close')
        self.end_headers()
        if self.path == '/stall':
            self.wfile.write(body[:8])
            self.wfile.flush()
            self.server.release_stall.wait(2)
        elif self.path == '/chunked':
            for start in range(0, len(body), 4):
                chunk = body[start:start + 4]
                self.wfile.write(f'{len(chunk):x}\r\n'.encode() + chunk + b'\r\n')
            self.wfile.write(b'0\r\n\r\n')
        else:
            self.wfile.write(body)
        self.close_connection = True


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.release_stall = threading.Event()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.release_stall.set()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def run_case(self, path):
        original_send = requests.adapters.HTTPAdapter.send

        def local_send(adapter, request, **kwargs):
            url = request.url
            # 只把已通过生产域名检查的测试地址送往本地，禁用系统代理。
            self.assertEqual(urlsplit(url).hostname, 'meeting.tencent.com')
            target = f'http://127.0.0.1:{self.server.server_port}{urlsplit(url).path}'
            request.url = target
            kwargs['proxies'] = {'http': '', 'https': ''}
            try:
                return original_send(adapter, request, **kwargs)
            finally:
                request.url = url

        with tempfile.TemporaryDirectory() as temp, \
                patch('requests.adapters.HTTPAdapter.send', new=local_send), \
                patch('downloader.video.REQUEST_TIMEOUT', (1, 0.1)), \
                contextlib.redirect_stdout(io.StringIO()):
            if path == '/redirect-body':
                consumed = []
                original_close = requests.Response.close

                def close(response):
                    if response.status_code == 302:
                        consumed.append(response._content_consumed)
                    return original_close(response)

                with patch('requests.Response.close', new=close), \
                        _request('get', 'https://meeting.tencent.com' + path) as response:
                    self.assertEqual(response.status_code, 200)
                self.assertEqual(consumed, [False])
                return
            destination = Path(temp) / 'video.mp4'
            if path in ('/html', '/partial', '/broken', '/stall'):
                with self.assertRaises(Exception):
                    download_video('https://meeting.tencent.com' + path, str(destination))
                self.assertEqual(list(Path(temp).iterdir()), [])
            else:
                self.assertTrue(download_video('https://meeting.tencent.com' + path, str(destination)))
                self.assertEqual(destination.read_bytes(), VIDEO)
                self.assertEqual(list(Path(temp).iterdir()), [destination])

    def test_known_length(self):
        self.run_case('/video')

    def test_unknown_length(self):
        self.run_case('/unknown')

    def test_chunked_mp4_header_split(self):
        self.run_case('/chunked')

    def test_relative_redirect(self):
        self.run_case('/redirect')

    def test_redirect_body_not_buffered(self):
        self.run_case('/redirect-body')

    def test_redirect_cookie_preserved(self):
        self.run_case('/cookie')

    def test_html_rejected(self):
        self.run_case('/html')

    def test_partial_rejected(self):
        self.run_case('/partial')

    def test_broken_transfer_cleans_up(self):
        self.run_case('/broken')

    def test_stalled_transfer_times_out(self):
        self.run_case('/stall')
