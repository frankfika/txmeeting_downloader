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
        self.total = total if total > 0 else 100  # 避免除以零错误
        self.width = width
        self.suffix = suffix
        self.color = color
        self.start_time = time.time()
        self.last_update = 0
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
    
    def update(self, current):
        """
        更新进度条显示
        
        参数:
            current (int): 当前进度
        """
        # 避免频繁更新导致闪烁
        current_time = time.time()
        if current_time - self.last_update < 0.1 and current < self.total:
            return
        self.last_update = current_time
        
        # 计算进度
        percent = min(100, int(current / self.total * 100))
        filled_width = int(self.width * current / self.total)
        bar = '█' * filled_width + '-' * (self.width - filled_width)
        
        # 计算速度和剩余时间
        elapsed = current_time - self.start_time
        if elapsed > 0 and current > 0:
            speed = current / elapsed
            remaining = (self.total - current) / speed if speed > 0 else 0
            elapsed_str = self._format_time(elapsed)
            remaining_str = self._format_time(remaining)
            speed_str = self._format_size(speed) + "/s"
            progress_suffix = f"{self._format_size(current)}/{self._format_size(self.total)} | {speed_str} | {elapsed_str}<{remaining_str}"
        else:
            progress_suffix = f"{self._format_size(current)}/{self._format_size(self.total)}"
        
        # 构建进度条显示
        if self.color:
            if percent < 30:
                bar_colored = self._get_color(bar, 'yellow')
            elif percent < 60:
                bar_colored = self._get_color(bar, 'blue')
            else:
                bar_colored = self._get_color(bar, 'green')
        else:
            bar_colored = bar
        
        # 显示进度条
        sys.stdout.write(f"\r[{bar_colored}] {percent}% | {progress_suffix} {self.suffix}")
        sys.stdout.flush()
        
        # 完成时换行
        if current >= self.total:
            sys.stdout.write('\n')
    
    def finish(self):
        """完成进度，显示最终结果"""
        self.update(self.total) 