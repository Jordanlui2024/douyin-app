import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
import threading
import os
import re
import requests
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sys

class DouyinCrawler:
    def __init__(self, log_callback=None):
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
            'referer': 'https://www.douyin.com/',
        }
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.log_callback = log_callback
        self.is_running = True

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)

    def clean_filename(self, filename):
        cleaned = re.sub(r'[\\/*?:"<>|]', '', filename)
        cleaned = cleaned.replace('\n', ' ').replace('\r', ' ')
        return cleaned[:100]

    def extract_sec_user_id(self, url):
        """从URL中提取sec_user_id"""
        patterns = [
            r'sec_user_id=([A-Za-z0-9_]+)',
            r'user/([A-Za-z0-9_]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_all_videos(self, user_url):
        """获取所有页面的视频"""
        if not self.is_running:
            return []

        sec_user_id = self.extract_sec_user_id(user_url)
        if not sec_user_id:
            self.log("错误: 无法从URL中提取用户ID")
            return []

        self.log(f"提取到用户ID: {sec_user_id}")
        url_list = []
        max_cursor = 0
        page_count = 0
        has_more = True

        while has_more and page_count < 10 and self.is_running:  # 限制页数
            page_count += 1
            self.log(f"正在获取第 {page_count} 页...")

            params = {
                'device_platform': 'webapp',
                'aid': '6383',
                'channel': 'channel_pc_web',
                'sec_user_id': sec_user_id,
                'max_cursor': str(max_cursor),
                'count': '18',
                'publish_video_strategy_type': '2',
            }

            try:
                response = self.session.get(
                    'https://www.douyin.com/aweme/v1/web/aweme/post/',
                    params=params,
                    headers=self.headers,
                    timeout=15
                )

                if response.status_code != 200:
                    self.log(f"请求失败，状态码: {response.status_code}")
                    break

                data = response.json()

                if "aweme_list" not in data or not data["aweme_list"]:
                    self.log("没有找到视频数据")
                    break

                # 处理当前页的视频
                video_count = 0
                for aweme in data["aweme_list"]:
                    if not self.is_running:
                        break
                    try:
                        title = self.clean_filename(aweme.get("desc", f"视频_{aweme['aweme_id']}"))
                        if (aweme.get("video") and
                                aweme["video"].get("play_addr") and
                                aweme["video"]["play_addr"].get("url_list")):
                            url = aweme["video"]["play_addr"]["url_list"][0]
                            url_list.append((title, url))
                            video_count += 1
                            self.log(f"找到视频: {title}")
                    except Exception as e:
                        self.log(f"处理视频数据时出错: {e}")

                has_more = data.get("has_more", 0) == 1
                max_cursor = data.get("max_cursor", 0)
                self.log(f"第 {page_count} 页获取完成，找到 {video_count} 个视频")

                time.sleep(1)  # 添加延迟

            except Exception as e:
                self.log(f"获取第 {page_count} 页时出错: {str(e)}")
                break

        self.log(f"总共获取 {len(url_list)} 个视频")
        return url_list

    def download_video(self, title, url, directory, progress_callback=None):
        """下载单个视频"""
        if not self.is_running:
            return False

        try:
            time.sleep(0.5)  # 添加延迟
            self.log(f"开始下载: {title}")

            res = self.session.get(url, headers=self.headers, timeout=30, stream=True)

            if res.status_code != 200:
                self.log(f"下载失败，状态码: {res.status_code}")
                return False

            file_path = os.path.join(directory, f"{title}.mp4")
            total_size = int(res.headers.get('content-length', 0))
            downloaded_size = 0

            with open(file_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    if not self.is_running:
                        return False
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            progress_callback(progress)

            self.log(f"下载成功: {title}")
            return True

        except Exception as e:
            self.log(f"下载失败: {str(e)}")
            return False

    def stop(self):
        """停止爬虫"""
        self.is_running = False

class DouyinApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crawler = None
        self.download_directory = "/sdcard/Download/抖音视频"  # Android下载目录

    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 标题
        title_label = Label(text='抖音视频下载工具', font_size='24sp', size_hint_y=0.1)
        self.layout.add_widget(title_label)
        
        # URL输入区域
        url_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        url_layout.add_widget(Label(text='用户主页URL:', size_hint_x=0.3))
        self.url_input = TextInput(
            text='https://www.douyin.com/user/MS4wLjABAAAA7i8qr60SqQKvqu8Gnnp3y-78EPbH2KhZ9v_x3SKam7w',
            multiline=False, 
            size_hint_x=0.7
        )
        url_layout.add_widget(self.url_input)
        self.layout.add_widget(url_layout)
        
        # 状态显示
        self.status_label = Label(text='请输入抖音用户主页URL', size_hint_y=0.1)
        self.layout.add_widget(self.status_label)
        
        # 进度条
        self.progress_bar = ProgressBar(max=100, size_hint_y=0.05)
        self.layout.add_widget(self.progress_bar)
        
        # 日志区域
        scroll_view = ScrollView(size_hint=(1, 0.6))
        self.log_label = Label(
            text='准备就绪...\n',
            size_hint_y=None,
            text_size=(None, None),
            halign='left',
            valign='top'
        )
        self.log_label.bind(texture_size=self.log_label.setter('size'))
        scroll_view.add_widget(self.log_label)
        self.layout.add_widget(scroll_view)
        
        # 按钮区域
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        
        self.start_button = Button(text='开始下载')
        self.start_button.bind(on_press=self.start_download)
        button_layout.add_widget(self.start_button)
        
        self.stop_button = Button(text='停止', disabled=True)
        self.stop_button.bind(on_press=self.stop_download)
        button_layout.add_widget(self.stop_button)
        
        self.clear_button = Button(text='清空日志')
        self.clear_button.bind(on_press=self.clear_log)
        button_layout.add_widget(self.clear_button)
        
        self.layout.add_widget(button_layout)
        
        return self.layout
    
    def log_message(self, message):
        """添加日志消息（线程安全）"""
        def update_log(dt):
            current_text = self.log_label.text
            if len(current_text) > 10000:  # 限制日志长度
                current_text = current_text[-5000:]
            self.log_label.text = current_text + f"\n{message}"
        
        Clock.schedule_once(update_log, 0)
    
    def update_progress(self, progress):
        """更新进度条（线程安全）"""
        def update(dt):
            self.progress_bar.value = progress
        
        Clock.schedule_once(update, 0)
    
    def update_status(self, status):
        """更新状态（线程安全）"""
        def update(dt):
            self.status_label.text = status
        
        Clock.schedule_once(update, 0)
    
    def clear_log(self, instance):
        """清空日志"""
        self.log_label.text = '日志已清空\n'
    
    def start_download(self, instance):
        """开始下载"""
        if self.crawler and self.crawler.is_running:
            self.log_message("下载正在进行中...")
            return
            
        url = self.url_input.text.strip()
        if not url:
            self.log_message("错误: 请输入URL")
            return
        
        self.start_button.disabled = True
        self.stop_button.disabled = False
        self.progress_bar.value = 0
        
        # 创建下载目录
        try:
            os.makedirs(self.download_directory, exist_ok=True)
        except:
            self.download_directory = "/data/data/org.douyin.app/files"  # 备用目录
            os.makedirs(self.download_directory, exist_ok=True)
        
        # 在新线程中运行爬虫
        self.crawler = DouyinCrawler(log_callback=self.log_message)
        thread = threading.Thread(target=self.run_download, args=(url,))
        thread.daemon = True
        thread.start()
    
    def run_download(self, url):
        """运行下载逻辑"""
        try:
            self.update_status("正在获取视频列表...")
            self.log_message("开始获取视频列表...")
            
            # 获取视频列表
            video_list = self.crawler.get_all_videos(url)
            
            if not video_list:
                self.update_status("没有找到视频")
                return
            
            total_videos = len(video_list)
            self.log_message(f"开始下载 {total_videos} 个视频...")
            
            # 下载视频
            success_count = 0
            for i, (title, video_url) in enumerate(video_list):
                if not self.crawler.is_running:
                    break
                    
                self.update_status(f"下载中 ({i+1}/{total_videos})")
                self.update_progress((i / total_videos) * 100)
                
                if self.crawler.download_video(title, video_url, self.download_directory, self.update_progress):
                    success_count += 1
            
            self.update_status(f"下载完成: {success_count}/{total_videos}")
            self.log_message(f"下载完成! 成功: {success_count}, 失败: {total_videos - success_count}")
            self.update_progress(100)
            
        except Exception as e:
            self.log_message(f"下载过程中出错: {str(e)}")
            self.update_status("下载失败")
        finally:
            self.start_button.disabled = False
            self.stop_button.disabled = True
    
    def stop_download(self, instance):
        """停止下载"""
        if self.crawler:
            self.crawler.stop()
            self.log_message("下载已停止")
            self.update_status("已停止")
            self.start_button.disabled = False
            self.stop_button.disabled = True

if __name__ == '__main__':
    DouyinApp().run()
