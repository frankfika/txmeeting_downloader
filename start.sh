#!/bin/bash

# 腾讯会议视频下载器 - 启动脚本
# Tencent Meeting Video Downloader - Launch Script

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 版本信息
VERSION="1.0.0"

# 打印标题
echo -e "${BLUE}腾讯会议视频下载器 v${VERSION}${NC}"
echo -e "${BLUE}=============================${NC}"
echo ""

# 检查 Python3 是否安装
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 未找到 Python3，请先安装 Python3${NC}"
    exit 1
fi

# 检查Python版本
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.6"
if [ $(echo "$PYTHON_VERSION < $REQUIRED_VERSION" | bc -l) -eq 1 ]; then
    echo -e "${RED}错误: Python版本过低 (${PYTHON_VERSION})，需要 ${REQUIRED_VERSION} 或更高版本${NC}"
    exit 1
fi

# 安装依赖
echo -e "${YELLOW}正在安装必要的依赖...${NC}"
if python3 -m pip install --break-system-packages requests &> /dev/null; then
    echo -e "${GREEN}依赖安装成功!${NC}"
elif python3 -m pip install --user requests &> /dev/null; then
    echo -e "${GREEN}依赖安装成功!${NC}"
else
    echo -e "${RED}依赖安装失败，请手动安装requests库:${NC}"
    echo "python3 -m pip install --user requests"
    exit 1
fi

# 检查目录结构
DOWNLOADER_DIR="downloader"
UTILS_DIR="utils"

# 检查核心文件是否存在
if [ ! -d "$DOWNLOADER_DIR" ] || [ ! -f "${DOWNLOADER_DIR}/video.py" ]; then
    echo -e "${RED}错误: 未找到核心下载模块${NC}"
    echo -e "${YELLOW}确保项目目录结构完整，可尝试重新克隆仓库${NC}"
    exit 1
fi

# 导入模块路径
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 获取用户输入
echo -e "${YELLOW}请输入视频URL:${NC}"
echo -e "${BLUE}提示: 在腾讯会议视频页面中右键选择'检查'(Inspect)，${NC}"
echo -e "${BLUE}      然后搜索'test-video_html5_api'或'yunluzhi'，找到视频URL${NC}"
read video_url

if [ -z "$video_url" ]; then
    echo -e "${RED}错误: 视频URL不能为空${NC}"
    exit 1
fi

echo -e "${YELLOW}请输入保存的文件名 (例如: 我的会议录制.mp4):${NC}"
read output_file

# 如果用户没有输入文件名，使用默认值
if [ -z "$output_file" ]; then
    output_file="下载视频.mp4"
    echo -e "${BLUE}使用默认文件名: ${output_file}${NC}"
fi

# 如果文件名没有.mp4后缀，添加它
if [[ ! $output_file =~ \.mp4$ ]]; then
    output_file="${output_file}.mp4"
    echo -e "${BLUE}已添加.mp4后缀: ${output_file}${NC}"
fi

# 启动下载
echo -e "${GREEN}正在启动下载程序...${NC}"
python3 -c "
from downloader.video import download_video

try:
    download_video('$video_url', '$output_file')
except Exception as e:
    import sys
    print(f'\033[0;31m下载失败: {str(e)}\033[0m', file=sys.stderr)
    sys.exit(1)
"

# 检查下载结果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}下载完成!${NC}"
    echo -e "${BLUE}文件保存在: $(pwd)/${output_file}${NC}"
else
    echo -e "${RED}下载过程中出现错误${NC}"
    echo -e "${YELLOW}请检查视频URL是否有效，或网络连接是否正常${NC}"
fi

echo -e "${BLUE}感谢使用腾讯会议视频下载器!${NC}" 