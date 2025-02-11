import requests

def download_video(video_url, output_file):
    """
    直接从URL下载视频
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': 'https://meeting.tencent.com/'
    }
    
    try:
        print("开始下载视频...")
        response = requests.get(video_url, headers=headers, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_file, 'wb') as file:
            downloaded = 0
            for data in response.iter_content(chunk_size=1024*1024):
                file.write(data)
                downloaded += len(data)
                progress = (downloaded / total_size) * 100
                print(f"下载进度: {progress:.2f}%", end='\r')
                
        print(f"\n下载完成: {output_file}")
        
    except Exception as e:
        print(f"下载失败: {str(e)}")

# 如果直接运行此文件
if __name__ == "__main__":
    print("请使用 start.sh 启动程序") 