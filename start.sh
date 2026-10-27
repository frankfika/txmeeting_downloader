#!/bin/bash
set -eu
cd -- "$(dirname -- "$0")"

# 比较整数版本元组，支持 3.10 及以后版本。
check_python() {
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'
}
if [ ! -x .venv/bin/python ]; then
    if ! command -v python3 >/dev/null 2>&1 || ! check_python python3; then
        echo "错误：请先安装 Python 3.9 或更高版本" >&2
        exit 1
    fi
    echo "正在创建项目 Python 环境…"
    python3 -m venv .venv
fi
PYTHON="$PWD/.venv/bin/python"
if ! check_python "$PYTHON"; then
    echo "错误：项目环境需要 Python 3.9 或更高版本" >&2
    exit 1
fi
if ! "$PYTHON" -c 'import requests' >/dev/null 2>&1; then
    "$PYTHON" -m pip install -r requirements.txt
fi
VERSION=$("$PYTHON" -c 'from downloader import __version__; print(__version__)')
echo "腾讯会议视频下载器 v$VERSION"
echo "请输入视频真实 URL（云录制播放页中 video 元素的 src）："
if ! IFS= read -r video_url || [ -z "$video_url" ]; then
    echo "错误：视频 URL 不能为空" >&2
    exit 1
fi
echo "请输入保存文件名（回车默认：下载视频.mp4）："
if ! IFS= read -r output_file; then
    echo "错误：未读取到文件名" >&2
    exit 1
fi
output_file="${output_file:-下载视频.mp4}"
case "$output_file" in
    *.[mM][pP]4) ;;
    *) output_file="${output_file}.mp4" ;;
esac
# 用户输入只作为参数传递，不拼进 Python 源码。
"$PYTHON" - "$video_url" "$output_file" <<'PY'
import sys
from downloader.video import download_video

try:
    download_video(sys.argv[1], sys.argv[2])
except KeyboardInterrupt:
    print('\n已取消下载', file=sys.stderr)
    sys.exit(130)
except Exception as exc:
    print(f'下载失败：{exc}', file=sys.stderr)
    sys.exit(1)
PY
