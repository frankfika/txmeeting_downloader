# 腾讯会议视频下载器 (Tencent Meeting Video Downloader)

![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.6%2B-brightgreen)

这个工具可以帮助你下载腾讯会议云录制的视频，特别是在分享链接不提供直接下载功能的情况下。

## 功能特点

- 简单易用的命令行界面
- 进度条显示下载进度
- 自动处理文件名和格式
- 无需额外登录，直接通过链接下载

## 安装要求

- Python 3.6 或更高版本
- 网络连接
- 基本的终端使用知识

## 快速开始

1. 克隆仓库:
   ```bash
   git clone https://github.com/yourusername/txmeeting_downloader.git
   cd txmeeting_downloader
   ```

2. 添加执行权限:
   ```bash
   chmod +x start.sh
   ```

3. 运行启动脚本:
   ```bash
   ./start.sh
   ```

4. 按照提示操作:
   - 输入视频URL (见下方详细说明)
   - 输入保存的文件名 (可选)

## 获取视频URL的详细步骤

1. 用浏览器打开腾讯会议分享的云录制链接
2. 输入密码 (如果需要) 进入视频播放页面
3. 在视频播放页面，右键点击，选择"检查"或"Inspect"(最后一个选项)
4. 在开发者工具中，按 Ctrl+F (Mac上使用 Cmd+F)，搜索 "test-video_html5_api"
5. 找到包含视频URL的元素，右键点击URL并选择"复制"
6. 将复制的URL粘贴到下载器提示中

![获取视频URL示例](docs/images/url_example.png)

## 注意事项

- 视频URL中的token通常有时效性，过期后需要重新获取
- 确保有足够的磁盘空间存储视频
- 下载时间取决于视频大小和网络连接速度
- 本工具仅用于个人学习和研究用途

## 项目结构

```
txmeeting_downloader/
├── LICENSE
├── README.md
├── start.sh           # 主启动脚本
├── downloader/        # 下载器核心代码
│   ├── __init__.py
│   └── video.py       # 视频下载功能
├── utils/             # 辅助工具
│   ├── __init__.py
│   └── progress.py    # 进度显示工具
└── docs/              # 文档
    └── images/        # 文档图片
        └── url_example.png  # 获取URL示例图片
```

## 常见问题

1. **下载失败可能的原因:**
   - 视频链接已过期，请重新获取
   - 网络连接问题，请检查您的网络
   - 磁盘空间不足，请确保有足够空间

2. **权限错误:**
   - 请确认已运行 `chmod +x start.sh`
   - 检查文件夹写入权限
   - 确保输出文件未被其他程序占用

3. **无法找到视频URL:**
   - 部分视频可能使用了不同的播放器，尝试搜索 "yunluzhi" 或 "video" 相关内容
   - 确认您有权限访问该视频

## 贡献指南

欢迎贡献代码、报告问题或提出建议！请通过GitHub issues或pull requests参与项目。

## 许可证

本项目采用 MIT 许可证 - 详情请查看 [LICENSE](LICENSE) 文件
