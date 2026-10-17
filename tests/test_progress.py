import contextlib
import io
import unittest
from unittest.mock import patch, MagicMock
from utils.progress import ProgressBar
from downloader.video import get_file_size


class ProgressTests(unittest.TestCase):
    def test_incorrect_total_bounded_output(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            bar = ProgressBar(2, color=False)
            bar.update(8192)
        self.assertLess(len(output.getvalue()), 300)
        self.assertIn('8.0 KB', output.getvalue())

    def test_unknown_total_and_finish_keep_actual_bytes(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            bar = ProgressBar(0, color=False)
            bar.update(8192)
            bar.finish()
        self.assertLess(len(output.getvalue()), 600)
        self.assertIn('8.0 KB', output.getvalue().split('\r')[-1])
        self.assertNotIn('100%', output.getvalue())

    def test_exceeding_total_still_throttled(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('utils.progress.time.monotonic', return_value=10):
            bar = ProgressBar(2, color=False)
            for current in range(8192, 81921, 8192):
                bar.update(current)
        self.assertLessEqual(output.getvalue().count('\r'), 1)
        self.assertNotIn('\n', output.getvalue())

    def test_finish_only_newline_once(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            bar = ProgressBar(8192, color=False)
            bar.update(8192)
            bar.finish()
            bar.finish()
        self.assertEqual(output.getvalue().count('\n'), 1)

    def test_partial_response_uses_full_size(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 206
        response.headers = {'Content-Length': '2', 'Content-Range': 'bytes 0-1/500000'}
        with patch('requests.sessions.Session.send', return_value=response):
            self.assertEqual(get_file_size('https://meeting.tencent.com/test'), 500000)

    def test_ambiguous_partial_response_is_unknown(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 206
        response.headers = {'Content-Length': '2'}
        with patch('requests.sessions.Session.send', return_value=response):
            self.assertEqual(get_file_size('https://meeting.tencent.com/test'), 0)

    def test_head_full_response_and_no_range_request(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status_code = 200
        response.headers = {'Content-Length': '500000'}
        with patch('requests.sessions.Session.send', return_value=response) as head:
            self.assertEqual(get_file_size('https://meeting.tencent.com/test'), 500000)
            self.assertNotIn('Range', head.call_args.args[0].headers)


if __name__ == '__main__':
    unittest.main()
