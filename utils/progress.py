"""
进度条显示工具
Progress Bar Display Utility
"""

import sys
import time

class ProgressBar:
    """
    控制台进度条显示工具
    """
    
    def __init__(self, total, width=50, suffix='', color=True):
        """
        初始化进度条
        
        参数:
            total (int): 总数据量
            width (int): 进度条宽度
            suffix (str): 后缀显示内容
            color (bool): 是否启用颜色
        """
        self.total = total if total > 0 else 0  # 0 表示未知大小
        self.width = width
        self.suffix = suffix
        self.color = color
        self.start_time = time.monotonic()
        self.last_update = None
        self.current = 0
        self.finished = False
        self.colors = {
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'end': '\033[0m'
        }
    
    def _format_time(self, seconds):
        """格式化时间为 hh:mm:ss"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        else:
            return f"{m:02d}:{s:02d}"
    
    def _format_size(self, size_bytes):
        """将字节大小转换为人类可读格式"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes/(1024*1024):.1f} MB"
        else:
            return f"{size_bytes/(1024*1024*1024):.2f} GB"
    
    def _get_color(self, text, color_name):
        """根据设置添加颜色"""
        if self.color:
            return f"{self.colors.get(color_name, '')}{text}{self.colors['end']}"
        return text
    
    def update(self, current, force=False):
        """固定宽度、限速刷新；未知或不可信的总大小只显示已下载量。"""
        if self.finished:
            return
        self.current = max(0, current)
        now = time.monotonic()
        if not force and self.last_update is not None and now - self.last_update < 0.5:
            return
        self.last_update = now
        elapsed = max(0, now - self.start_time)
        speed = self.current / elapsed if elapsed > 0 else 0
        if self.total > 0 and self.current <= self.total:
            ratio = min(1, self.current / self.total)
            filled = min(self.width, max(0, int(self.width * ratio)))
            bar = '█' * filled + '-' * (self.width - filled)
            label = f"{int(ratio * 100)}%"
            size = f"{self._format_size(self.current)}/{self._format_size(self.total)}"
            remaining = (self.total - self.current) / speed if speed else 0
            timing = f"{self._format_time(elapsed)}<{self._format_time(remaining)}"
        else:
            bar = '-' * self.width
            label = '大小未知'
            size = self._format_size(self.current)
            timing = self._format_time(elapsed)
        bar = self._get_color(bar, 'green')
        sys.stdout.write(
            f"\r[{bar}] {label} | {size} | {self._format_size(speed)}/s | {timing} {self.suffix}    "
        )
        sys.stdout.flush()

    def finish(self):
        """保留实际下载字节数，只在真正结束时换行。"""
        if not self.finished:
            self.update(self.current, force=True)
            self.finished = True
            sys.stdout.write('\n')
            sys.stdout.flush()
