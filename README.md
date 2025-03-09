## 当别人给你分享腾讯视频云录制的时候，有时候无法下载，这个脚本可以帮你解决这个问题

## 使用方法

1. 添加执行权限：
   ```bash
   chmod +x start.sh
   ```

2. 运行启动脚本：
   ```bash
   ./start.sh
   ```

3. 根据提示：
   - 输入视频URL（输入密码进入云录制的视频页面，在腾讯会议网页中右键选择inspect【最后一个选项】，然后搜索”test-video_html5_api“，找到里面对应的连接，选择"复制"）。   
   - 输入要保存的文件名（可选，默认为"下载视频.mp4"）

## 注意事项

- 视频URL中的token有时效性，过期需要重新获取
- 确保有足够的磁盘空间
- 下载时间取决于视频大小和网络速度

## 常见问题

1. 下载失败可能原因：
   - 视频链接已过期
   - 网络连接问题
   - 磁盘空间不足

2. 如果提示权限错误：
   - 检查文件夹写入权限
   - 确认输出文件未被占用
   - 确保已经运行了 chmod +x start.sh
