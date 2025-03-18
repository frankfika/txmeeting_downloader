"""
腾讯会议视频下载器 - 视频下载核心功能
"""

import os
import sys
import requests
from utils.progress import ProgressBar

def is_valid_url(url):
    """
    检查URL是否有效
    """
    try:
        return url.startswith(('http://', 'https://')) and 'meeting.tencent.com' in url
    except (AttributeError, TypeError):
        return False

def get_file_size(url):
    """
    获取远程文件大小（字节）
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://meeting.tencent.com/',
            'Range': 'bytes=0-1'  # 只请求第一个字节来获取文件大小
        }
        response = requests.head(url, headers=headers, timeout=10)
        
        # 从响应中获取文件大小
        if 'Content-Length' in response.headers:
            return int(response.headers.get('Content-Length', 0))
        return 0
    except Exception as e:
        print(f"\033[0;31m无法获取文件大小: {str(e)}\033[0m", file=sys.stderr)
        return 0

def human_readable_size(size_bytes):
    """
    将字节大小转换为人类可读格式
    """
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def download_video(video_url, output_file):
    """
    下载视频文件
    
    参数:
        video_url (str): 视频URL
        output_file (str): 输出文件路径
    
    返回:
        bool: 是否成功
    """
    # 验证URL
    if not is_valid_url(video_url):
        raise ValueError("无效的视频URL")
    
    # 检查文件是否存在
    if os.path.exists(output_file):
        print(f"\033[0;33m警告: 文件 '{output_file}' 已存在，将被覆盖\033[0m")
    
    # 设置请求头
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://meeting.tencent.com/'
    }
    
    try:
        # 获取文件大小
        total_size = get_file_size(video_url)
        if total_size > 0:
            print(f"视频大小: {human_readable_size(total_size)}")
            # 检查磁盘空间
            if os.name == 'posix':  # Unix/Linux/MacOS
                stat = os.statvfs(os.path.dirname(os.path.abspath(output_file)) or '.')
                free_space = stat.f_frsize * stat.f_bavail
                if free_space < total_size:
                    print(f"\033[0;31m警告: 磁盘空间不足。需要 {human_readable_size(total_size)}，"
                          f"但只有 {human_readable_size(free_space)}\033[0m", file=sys.stderr)
        
        # 初始化进度条
        print("\033[0;32m开始下载视频...\033[0m")
        progress = ProgressBar(total_size)
        
        # 开始下载
        with requests.get(video_url, headers=headers, stream=True) as response:
            response.raise_for_status()  # 如果请求不成功则抛出异常
            
            with open(output_file, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress.update(downloaded)
        
        # 完成下载
        progress.finish()
        print(f"\033[0;32m下载完成: {output_file}\033[0m")
        return True
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求错误: {str(e)}")
    except Exception as e:
        raise Exception(f"下载失败: {str(e)}") 