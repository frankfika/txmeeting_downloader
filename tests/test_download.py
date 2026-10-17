import contextlib
import errno
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import requests
from downloader.video import download_video, is_valid_url

VIDEO = (b'\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42'
         + b'\x00\x00\x00\x08moov' + b'\x00\x00\x00\x6cmdat' + b'video' * 20)
URL = 'https://meeting.tencent.com/video?token=test'
ROOT = Path(__file__).resolve().parents[1]


class Response:
    def __init__(self, body=VIDEO, status=200, headers=None, chunks=None):
        self.status_code = status
        self.headers = {'Content-Length': str(len(body)), 'Content-Type': 'video/mp4'}
        if headers is not None:
            self.headers = headers
        self.chunks = [body] if chunks is None else chunks
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.closed = True

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError('test HTTP error')

    def iter_content(self, chunk_size):
        for chunk in self.chunks:
            if callable(chunk):
                chunk = chunk()
            if isinstance(chunk, BaseException):
                raise chunk
            yield chunk


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dest = Path(self.temp.name) / 'video.mp4'
        self.stdout = io.StringIO()
        head = patch('requests.sessions.Session.send', return_value=Response())
        head.start()
        self.addCleanup(head.stop)

    def run_download(self, response):
        def transport(request, **kwargs):
            return Response() if request.method == 'HEAD' else response
        with patch('requests.sessions.Session.send', side_effect=transport) as get, \
                contextlib.redirect_stdout(self.stdout):
            result = download_video(URL, str(self.dest))
        return result, get

    def assert_clean_failure(self, response):
        with self.assertRaises(Exception):
            self.run_download(response)
        self.assertFalse(self.dest.exists())
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])
        self.assertNotIn('下载完成', self.stdout.getvalue())

    def test_valid_mp4_saved_exactly_with_bounded_timeouts(self):
        result, get = self.run_download(Response())
        self.assertTrue(result)
        self.assertEqual(self.dest.read_bytes(), VIDEO)
        self.assertIn('下载完成', self.stdout.getvalue())
        timeout = get.call_args.kwargs.get('timeout')
        self.assertIsInstance(timeout, tuple)
        self.assertTrue(all(0 < value <= 30 for value in timeout))
        self.assertFalse(get.call_args.kwargs['allow_redirects'])

    def test_unsupported_filesystem_rejected_before_network(self):
        with patch('os.link', side_effect=OSError(errno.EOPNOTSUPP, 'unsupported')), \
                patch('requests.sessions.Session.send') as send:
            with self.assertRaises(OSError):
                download_video(URL, str(self.dest))
        send.assert_not_called()
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_existing_file_preserved_before_network(self):
        self.dest.write_bytes(b'original')
        with patch('requests.sessions.Session.send') as get:
            with self.assertRaises(FileExistsError):
                download_video(URL, str(self.dest))
        self.assertEqual(self.dest.read_bytes(), b'original')
        get.assert_not_called()

    def test_broken_symlink_preserved(self):
        self.dest.symlink_to('missing-target')
        with self.assertRaises(FileExistsError):
            self.run_download(Response())
        self.assertTrue(self.dest.is_symlink())

    def test_destination_created_during_download_preserved(self):
        def concurrent_file():
            self.dest.write_bytes(b'created-by-someone-else')
            return VIDEO
        with self.assertRaises(FileExistsError):
            self.run_download(Response(chunks=[concurrent_file]))
        self.assertEqual(self.dest.read_bytes(), b'created-by-someone-else')
        self.assertEqual(list(Path(self.temp.name).iterdir()), [self.dest])

    def test_html_json_empty_and_partial_are_rejected(self):
        cases = [Response(b'<html>login</html>', headers={'Content-Type': 'text/html'}),
                 Response(b'<html>error</html>', headers={'Content-Type': 'application/octet-stream'}),
                 Response(b'{"error":"expired"}'), Response(b''),
                 Response(VIDEO, status=204),
                 Response(VIDEO[:8], status=206,
                          headers={'Content-Range': f'bytes 0-7/{len(VIDEO)}', 'Content-Length': '8'}),
                 Response(status=206, headers={'Content-Length': str(len(VIDEO))})]
        for response in cases:
            with self.subTest(status=response.status_code, headers=response.headers):
                self.assert_clean_failure(response)

    def test_incorrect_content_length_rejected(self):
        self.assert_clean_failure(Response(headers={'Content-Length': str(len(VIDEO) + 10)}))

    def test_small_network_chunks_form_valid_mp4(self):
        chunks = [VIDEO[index:index + 4] for index in range(0, len(VIDEO), 4)]
        self.assertTrue(self.run_download(Response(chunks=chunks))[0])
        self.assertEqual(self.dest.read_bytes(), VIDEO)

    def test_truncated_mp4_box_rejected_with_or_without_length(self):
        body = VIDEO[:16]
        for headers in [{}, {'Content-Length': '16'}]:
            with self.subTest(headers=headers):
                self.assert_clean_failure(Response(body, headers=headers))

    def test_complete_range_accepted(self):
        response = Response(status=206, headers={
            'Content-Range': f'bytes 0-{len(VIDEO) - 1}/{len(VIDEO)}',
            'Content-Length': str(len(VIDEO))})
        self.assertTrue(self.run_download(response)[0])

    def test_network_failure_removes_partial_file(self):
        self.assert_clean_failure(Response(chunks=[VIDEO, requests.ReadTimeout('stalled')]))

    def test_cancel_removes_partial_file(self):
        with self.assertRaises(KeyboardInterrupt):
            self.run_download(Response(chunks=[VIDEO, KeyboardInterrupt()]))
        self.assertEqual(list(Path(self.temp.name).iterdir()), [])

    def test_get_size_used_without_head(self):
        def transport(request, **kwargs):
            if request.method == 'HEAD':
                raise requests.HTTPError()
            return Response()
        with patch('requests.sessions.Session.send', side_effect=transport) as head, \
                contextlib.redirect_stdout(self.stdout):
            self.assertTrue(download_video(URL, str(self.dest)))
        self.assertIn('100%', self.stdout.getvalue())
        self.assertNotIn('大小未知', self.stdout.getvalue())
        self.assertTrue(all(call.args[0].method == 'GET' for call in head.call_args_list))

    def test_no_length_still_downloads_with_unknown_size(self):
        self.assertTrue(self.run_download(Response(headers={}))[0])
        self.assertIn('大小未知', self.stdout.getvalue())
        self.assertEqual(self.dest.read_bytes(), VIDEO)

    def test_redirect_validated_before_second_request(self):
        redirect = Response(status=302, headers={'Location': 'https://example.invalid/video'})
        with patch('requests.sessions.Session.send', return_value=redirect) as get, \
                contextlib.redirect_stdout(self.stdout):
            with self.assertRaises(ValueError):
                download_video(URL, str(self.dest))
        self.assertEqual(get.call_count, 1)
        self.assertTrue(redirect.closed)

    def test_tencent_redirect_followed_with_same_guards(self):
        redirect = Response(status=302, headers={'Location': '/actual.mp4'})
        with patch('requests.sessions.Session.send', side_effect=[redirect, Response()]) as get, \
                contextlib.redirect_stdout(self.stdout):
            self.assertTrue(download_video(URL, str(self.dest)))
        self.assertEqual(get.call_args.args[0].url, 'https://meeting.tencent.com/actual.mp4')
        self.assertTrue(redirect.closed)

    def test_only_real_tencent_hosts_accepted(self):
        for url in [URL, 'https://cdn.meeting.tencent.com/v.mp4', 'http://meeting.tencent.com/v.mp4']:
            self.assertTrue(is_valid_url(url), url)
        for url in ['https://example.invalid/meeting.tencent.com',
                    'https://meeting.tencent.com.example.invalid/v',
                    'http://127.0.0.1/?x=meeting.tencent.com',
                    'https://meeting.tencent.com@evil.invalid/',
                    'https://user:password@meeting.tencent.com/',
                    'https://meeting.tencent.com:bad/', '\n' + URL, None]:
            self.assertFalse(is_valid_url(url), repr(url))


class StartupTests(unittest.TestCase):
    def run_start(self, data, version='3.13'):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'start.sh').write_bytes((ROOT / 'start.sh').read_bytes())
            (root / 'downloader').mkdir()
            (root / 'downloader/__init__.py').write_text("__version__ = 'test'\n")
            log = root / 'args.json'
            (root / 'downloader/video.py').write_text(
                "import json, os\ndef download_video(url, output):\n"
                "    if url == 'invalid': raise ValueError('invalid URL')\n"
                "    with open(os.environ['TX_TEST_LOG'], 'w') as f: json.dump([url, output], f)\n")
            (root / 'requirements.txt').write_text('requests>=2.28.0\n')
            (root / '.venv/bin').mkdir(parents=True)
            wrapper = root / 'python3'
            wrapper.write_text('''#!/bin/bash
if [ "$1" = "-c" ] && [[ "$2" == "import sys; print(f"* ]]; then
    echo "$TX_TEST_VERSION"; exit 0
fi
if [ "$1" = "-m" ] && [ "$2" = "pip" ]; then exit 0; fi
exec "$TX_TEST_PYTHON" "$@"
''')
            wrapper.chmod(0o700)
            python = root / '.venv/bin/python'
            python.write_text('#!/bin/bash\nexec "$TX_TEST_PYTHON" "$@"\n')
            python.chmod(0o700)
            env = {**os.environ, 'PATH': str(root) + os.pathsep + os.environ['PATH'],
                   'TX_TEST_PYTHON': sys.executable, 'TX_TEST_VERSION': version, 'TX_TEST_LOG': str(log)}
            result = subprocess.run(['bash', str(root / 'start.sh')], input=data, cwd=root,
                                    text=True, capture_output=True, env=env, timeout=5)
            return result, json.loads(log.read_text()) if log.exists() else None

    def test_quotes_and_backslashes_are_literal(self):
        value = "https://meeting.tencent.com/' + str(print('INJECTION_EXECUTED')) + '\\path"
        result, args = self.run_start(value + '\n' + "John's meeting.mp4\n")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(args, [value, "John's meeting.mp4"])
        self.assertNotIn('INJECTION_EXECUTED', result.stdout)

    def test_project_environment_ignores_system_python_version(self):
        for version in ['3.10', '3.11', '3.12', '3.13']:
            result, args = self.run_start(URL + '\nnew.mp4\n', version)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(args, [URL, 'new.mp4'])

    def test_url_expression_is_not_executed(self):
        value = "https://meeting.tencent.com/' + str(print('INJECTION_EXECUTED')) + '"
        result, args = self.run_start(value + '\nfile.mp4\n', version='3.9')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(args, [value, 'file.mp4'])
        self.assertNotIn('INJECTION_EXECUTED', result.stdout)

    def test_download_failure_propagates_exit_status(self):
        result, _ = self.run_start('invalid\nfile.mp4\n', version='3.9')
        self.assertNotEqual(result.returncode, 0)

    def test_default_filename(self):
        result, args = self.run_start(URL + '\n\n', version='3.9')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(args, [URL, '下载视频.mp4'])
