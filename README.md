# 腾讯会议视频下载器

下载你有权访问的腾讯会议云录制 MP4 视频。需要提供播放页中 video 元素的真实视频地址，普通分享页面链接无法直接下载。

## 安装与启动

需要 Python 3.9 或更高版本，以及网络连接。

```bash
git clone https://github.com/chenjunyan1/txmeeting_downloader.git
cd txmeeting_downloader
chmod +x start.sh
./start.sh
```

启动脚本会自动创建项目独立环境 `.venv` 并安装依赖。Mac 用户也可以在 Finder 中双击 `启动下载器.command`。

1. 在浏览器打开腾讯会议云录制分享链接，按页面提示登录或输入密码并进入播放页。
2. 右键选择“检查”，搜索 `test-video_html5_api`、`yunluzhi` 或 `video`，找到视频元素的 `src` 地址。
3. 将真实视频地址粘贴到下载器并回车，再输入保存文件名；直接回车默认保存为 `下载视频.mp4`。

![获取视频地址示例](docs/images/url_example.png)

## 下载行为

- 支持 `meeting.tencent.com` 及其子域名；重定向到其他域名会拒绝。其他 CDN 地址、HLS 播放列表和 `blob:` 地址暂不支持。
- 默认保存到项目目录。同名文件会拒绝覆盖，请更换文件名。
- 根据实际下载响应显示总大小；服务器未提供大小时显示“大小未知”，仍可正常下载。
- 下载前检查 MP4 文件头，拒绝网页、错误信息和不完整的分段响应；有总大小时校验实际收到的字节数，并检查 MP4 顶层数据块是否收齐。这些检查不能替代视频解码或播放验证。
- 保存目录需要支持硬链接，启动下载前会检查；视频先写入同目录临时文件，完成后才生成最终文件；正常报错或按 Ctrl+C 取消会清理临时文件。目前不支持断点续传。
- 连接超时为 10 秒，连续 30 秒收不到数据会停止并报错。链接 token 过期时，需要重新从播放页获取地址。
- 输入中的引号和反斜杠会按普通字符处理。失败返回非零退出码，便于脚本判断结果。

## 测试

```bash
.venv/bin/python -m unittest discover -s tests -v
```

测试包括进度条内存保护、文件覆盖保护、响应检查、启动参数处理，以及本地 HTTP 服务下的断线、超时、分块传输和重定向。GitHub Actions 会在 Python 3.9、3.10、3.13 上运行。

## 来源与许可证

本项目 fork 自 [frankfika/txmeeting_downloader](https://github.com/frankfika/txmeeting_downloader)，采用 [MIT 许可证](LICENSE)。
