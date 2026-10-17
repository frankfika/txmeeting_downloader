"""腾讯会议 MP4 下载：验证响应，完成前不生成或覆盖最终文件。"""

from contextlib import contextmanager
import itertools
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urljoin, urlsplit

import requests
from utils.progress import ProgressBar

REQUEST_TIMEOUT = (10, 30)  # 连接超时、连续无数据的读取超时（秒）
CHUNK_SIZE = 64 * 1024
MAX_REDIRECTS = 5
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://meeting.tencent.com/',
    'Accept-Encoding': 'identity',
}


def is_valid_url(url):
    """只接受腾讯会议域名和其子域名，不把路径或查询参数当域名。"""
    if not isinstance(url, str) or any(char.isspace() or ord(char) < 32 for char in url):
        return False
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower().rstrip('.')
        parsed.port  # 触发非法端口的校验。
        return (parsed.scheme in ('http', 'https') and parsed.username is None and parsed.password is None
                and (host == 'meeting.tencent.com' or host.endswith('.meeting.tencent.com')))
    except ValueError:
        return False


class _StreamingSession(requests.Session):
    def resolve_redirects(self, *args, **kwargs):
        # Session.send 即使关闭自动跳转，也会为 _next 读取整个 3xx body。
        # 禁止该隐式路径，交给 _request 只按响应头逐跳处理。
        return iter(())


@contextmanager
def _request(method, url, **kwargs):
    """复用 Cookie 会话，逐跳校验并立即关闭重定向响应体。"""
    with _StreamingSession() as session:
        for _ in range(MAX_REDIRECTS + 1):
            if not is_valid_url(url):
                raise ValueError('无效的视频 URL：只支持 meeting.tencent.com 及其子域名')
            response = getattr(session, method)(
                url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=False,
                stream=True, **kwargs)
            if response.status_code not in (301, 302, 303, 307, 308):
                try:
                    yield response
                finally:
                    response.close()
                return
            location = response.headers.get('Location')
            response.close()
            if not location:
                raise ValueError('视频重定向缺少目标地址')
            url = urljoin(url, location)
    raise requests.TooManyRedirects('视频重定向次数过多')


def _range(response):
    value = response.headers.get('Content-Range', '')
    match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', value)
    if match:
        start, end, total = map(int, match.groups())
        if 0 <= start <= end < total:
            return start, end, total
    return None


def get_file_size(url):
    """单独查询大小；下载时直接使用 GET 响应，不依赖 HEAD。"""
    try:
        with _request('head', url) as response:
            response.raise_for_status()
            if response.headers.get('Content-Range') or response.status_code == 206:
                byte_range = _range(response)
                return byte_range[2] if byte_range else 0
            return max(0, int(response.headers.get('Content-Length', 0)))
    except (requests.RequestException, ValueError, TypeError):
        return 0


def human_readable_size(size_bytes):
    if size_bytes == 0:
        return '0B'
    units = ('B', 'KB', 'MB', 'GB', 'TB', 'PB')
    index = 0
    while size_bytes >= 1024 and index < len(units) - 1:
        size_bytes /= 1024
        index += 1
    return f'{size_bytes:.2f} {units[index]}'


def _download_size(response):
    response.raise_for_status()
    if response.status_code not in (200, 206):
        raise ValueError(f'服务器未返回视频数据（HTTP {response.status_code}）')
    content_type = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
    if content_type.startswith('text/') or content_type in ('application/json', 'application/xml'):
        raise ValueError('服务器返回了网页或错误信息，请重新获取真实视频 URL')
    if response.headers.get('Content-Encoding', 'identity').lower() not in ('', 'identity'):
        raise ValueError('服务器返回了压缩响应，无法可靠校验视频大小')
    length = response.headers.get('Content-Length')
    total = int(length) if length is not None else 0
    if total < 0:
        raise ValueError('服务器返回了无效的视频大小')
    if response.status_code == 206 or response.headers.get('Content-Range'):
        byte_range = _range(response)
        if not byte_range or byte_range[0] != 0 or byte_range[1] != byte_range[2] - 1:
            raise ValueError('服务器只返回了部分视频，请重新获取完整视频 URL')
        if length is not None and total != byte_range[2]:
            raise ValueError('服务器返回的视频长度不一致')
        total = byte_range[2]
    return total


def _is_mp4_prefix(data):
    """检查 MP4 文件头，允许常见的前置 free/skip/wide box。"""
    offset = 0
    while offset + 8 <= len(data):
        size = int.from_bytes(data[offset:offset + 4], 'big')
        kind = data[offset + 4:offset + 8]
        if kind == b'ftyp':
            return size >= 16 and offset + 16 <= len(data)
        if kind not in (b'free', b'skip', b'wide') or size < 8:
            break
        offset += size
    return False


def _validate_mp4_file(path, size):
    """以固定内存检查顶层 box 边界，不把裸 EOF 当完整视频的证明。"""
    required = {b'ftyp', b'moov', b'mdat'}
    kinds = set()
    with open(path, 'rb') as source:
        offset = 0
        while offset < size:
            source.seek(offset)
            header = source.read(8)
            if len(header) != 8:
                raise ValueError('MP4 文件结构被截断')
            box_size = int.from_bytes(header[:4], 'big')
            header_size = 8
            if box_size == 1:
                extended = source.read(8)
                if len(extended) != 8:
                    raise ValueError('MP4 扩展长度被截断')
                box_size = int.from_bytes(extended, 'big')
                header_size = 16
            elif box_size == 0:
                box_size = size - offset
            if box_size < header_size or offset + box_size > size:
                raise ValueError('MP4 数据未收齐或文件结构无效')
            if header[4:8] in required:
                kinds.add(header[4:8])
            offset += box_size
    if kinds != required:
        raise ValueError('响应缺少完整 MP4 视频所需的数据')


def _check_destination_directory(parent):
    """先检查原子保存能力，避免不支持硬链接时白白下载大文件。"""
    descriptor, probe = tempfile.mkstemp(prefix='.txmeeting-check-', dir=parent)
    os.close(descriptor)
    linked = False
    try:
        os.link(probe, probe + '.link')
        linked = True
    except OSError as exc:
        raise OSError('保存目录不支持安全创建文件，请改用电脑本地目录') from exc
    finally:
        if linked:
            os.unlink(probe + '.link')
        os.unlink(probe)


def download_video(video_url, output_file):
    """流式下载到临时文件；成功后原子创建目标，同名文件始终保留。"""
    if not is_valid_url(video_url):
        raise ValueError('无效的视频 URL：请提供腾讯会议的真实视频地址')
    destination = Path(output_file).absolute()
    if os.path.lexists(destination):
        raise FileExistsError(f'文件已存在，请使用其他文件名：{destination.name}')
    _check_destination_directory(destination.parent)
    temporary = None
    try:
        with _request('get', video_url) as response:
            total = _download_size(response)
            if total and shutil.disk_usage(destination.parent).free < total:
                raise OSError('磁盘空间不足，无法保存完整视频')
            chunks = response.iter_content(chunk_size=CHUNK_SIZE)
            # HTTP 分块可能把文件头拆成多个小块，只缓存有上限的前缀。
            prefix = bytearray()
            for chunk in chunks:
                prefix.extend(chunk)
                if _is_mp4_prefix(prefix) or len(prefix) >= CHUNK_SIZE:
                    break
            first = bytes(prefix)
            if not _is_mp4_prefix(first):
                raise ValueError('响应不是可识别的 MP4 视频，请重新获取真实视频 URL')
            print(f'视频大小：{human_readable_size(total)}' if total else '视频总大小未知')
            print('开始下载视频…')
            progress = ProgressBar(total)
            descriptor, temporary = tempfile.mkstemp(
                prefix='.txmeeting-', suffix='.part', dir=destination.parent)
            with os.fdopen(descriptor, 'wb') as output:
                downloaded = 0
                for chunk in itertools.chain((first,), chunks):
                    if not chunk:
                        continue
                    downloaded += len(chunk)
                    if total and downloaded > total:
                        raise ValueError('实际下载量超过服务器报告的大小，视频未保存')
                    output.write(chunk)
                    progress.update(downloaded)
            if total and downloaded != total:
                raise ValueError('视频下载不完整，请重新获取链接并重试')
        _validate_mp4_file(temporary, downloaded)
        # 同目录硬链接原子创建目标；目标被其他进程创建时也不会覆盖。
        os.link(temporary, destination)
        progress.finish()
        print(f'下载完成：{destination}')
        return True
    except requests.RequestException as exc:
        raise RuntimeError(f'网络请求失败（{type(exc).__name__}），请检查网络或更新视频链接') from exc
    finally:
        if temporary is not None:
            os.unlink(temporary)
