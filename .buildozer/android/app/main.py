import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
import threading
import time


class DouyinApp(App):
    def build(self):
        # 主布局
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        # 标题
        title_label = Label(text='抖音视频工具', font_size='24sp', size_hint_y=0.15)
        layout.add_widget(title_label)

        # URL 输入框
        url_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        url_layout.add_widget(Label(text='用户URL:', size_hint_x=0.3))
        self.url_input = TextInput(
            text='https://www.douyin.com/user/MS4wLjABAAAA7i8qr60SqQKvqu8Gnnp3y-78EPbH2KhZ9v_x3SKam7w',
            multiline=False,
            size_hint_x=0.7
        )
        url_layout.add_widget(self.url_input)
        layout.add_widget(url_layout)

        # 状态标签
        self.status_label = Label(text='准备就绪', size_hint_y=0.1)
        layout.add_widget(self.status_label)

        # 日志区域（带滚动条）
        self.log_label = Label(
            text='欢迎使用抖音视频工具！\n请输入用户主页URL并点击开始。\n',
            size_hint_y=None,
            text_size=(None, None),
            halign='left',
            valign='top'
        )
        self.log_label.bind(texture_size=self.log_label.setter('size'))

        scroll_view = ScrollView(size_hint=(1, 0.5))
        scroll_view.add_widget(self.log_label)
        layout.add_widget(scroll_view)

        # 按钮区域
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=0.15)

        self.start_button = Button(text='开始获取')
        self.start_button.bind(on_press=self.start_process)
        button_layout.add_widget(self.start_button)

        self.clear_button = Button(text='清空日志')
        self.clear_button.bind(on_press=self.clear_log)
        button_layout.add_widget(self.clear_button)

        layout.add_widget(button_layout)

        return layout

    def log_message(self, message):
        """添加日志消息（线程安全）"""

        def update_log(dt):
            current_text = self.log_label.text
            # 限制日志长度，避免内存问题
            if len(current_text) > 5000:
                lines = current_text.split('\n')
                current_text = '\n'.join(lines[-20:])
            self.log_label.text = current_text + f"\n{message}"

        Clock.schedule_once(update_log, 0)

    def update_status(self, status):
        """更新状态（线程安全）"""

        def update(dt):
            self.status_label.text = status

        Clock.schedule_once(update, 0)

    def clear_log(self, instance):
        """清空日志"""
        self.log_label.text = '日志已清空\n'

    def start_process(self, instance):
        """开始处理"""
        url = self.url_input.text.strip()
        if not url:
            self.log_message("错误: 请输入有效的URL")
            return

        self.start_button.disabled = True
        self.update_status('处理中...')
        self.log_message(f'开始处理URL: {url}')

        # 在新线程中运行处理逻辑
        thread = threading.Thread(target=self.process_data, args=(url,))
        thread.daemon = True
        thread.start()

    def process_data(self, url):
        """处理数据（在后台线程中运行）"""
        try:
            # 模拟处理过程
            self.log_message("步骤1: 解析用户ID...")
            time.sleep(1)

            self.log_message("步骤2: 获取视频列表...")
            time.sleep(2)

            self.log_message("步骤3: 处理视频数据...")
            for i in range(3):
                time.sleep(1)
                self.log_message(f"  处理视频 {i + 1}/3")

            self.log_message("处理完成!")
            self.update_status('完成')

        except Exception as e:
            self.log_message(f"处理过程中出错: {str(e)}")
            self.update_status('错误')
        finally:
            # 重新启用开始按钮
            def enable_button(dt):
                self.start_button.disabled = False

            Clock.schedule_once(enable_button, 0)


if __name__ == '__main__':
    DouyinApp().run()