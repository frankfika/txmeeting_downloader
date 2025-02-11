#!/bin/bash

# 确保脚本在正确的目录下执行
cd "$(dirname "$0")"

echo "腾讯会议视频下载器启动脚本"
echo "=========================="

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未安装 Python3"
    exit 1
fi

# 安装依赖
echo "正在安装必要的依赖..."
python3 -m pip install requests

# 检查 download.py 是否存在
if [ ! -f "download.py" ]; then
    echo "错误: 未找到 download.py 文件"
    exit 1
fi

# 提示用户输入视频URL
echo "请输入腾讯会议回放视频URL:"
read video_url

# 提示用户输入保存文件名
echo "请输入保存的文件名(包含扩展名，如 video.mp4):"
read output_file

# 运行 Python 脚本
python3 -c "
from download import download_video
download_video('$video_url', '$output_file')
" 