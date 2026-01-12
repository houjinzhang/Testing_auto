import sys
import time
import os
import threading
import subprocess
import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal

DEVICE_SERIAL = 'AF2Q015811000014'  # 修改为你的设备序列号
REPORT_DIR = "report_ai_enhance"
os.makedirs(REPORT_DIR, exist_ok=True)

def run_adb_command(command):
    try:
        full_cmd = f"adb -s {DEVICE_SERIAL} shell {command}"
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, encoding='utf-8', check=False)
        return result.returncode, result.stdout.strip()
    except FileNotFoundError:
        return -1, "错误: 'adb' 未找到，请安装ADB并配置环境变量"
    except Exception as e:
        return -1, f"未知错误: {e}"

def run_adb_pull(src, dst, log_func=None):
    cmd = f'adb -s {DEVICE_SERIAL} pull "{src}" "{dst}"'
    if log_func:
        log_func(f"拉取 {src} 到 {dst}")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        if log_func:
            log_func(f"<font color='#FF0000'>拉取 {src} 失败：{e}</font>")

def get_timestamp_folder(ver_str=""):
    now = datetime.datetime.now()
    date_part = now.strftime("%Y%m%d_%H%M%S")
    folder = f"Logs_{ver_str}_{date_part}" if ver_str else f"Logs__{date_part}"
    return folder

class Communicate(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("live photo")
        self.setGeometry(200, 200, 600, 600)

        layout = QVBoxLayout()
        self.startButton = QPushButton("开始测试")
        self.stopButton = QPushButton("停止测试")
        self.clearButton = QPushButton("清空日志")
        self.collectLogButton = QPushButton("采集设备日志")
        self.logEdit = QTextEdit()
        self.logEdit.setReadOnly(True)
        layout.addWidget(self.startButton)
        layout.addWidget(self.stopButton)
        layout.addWidget(self.clearButton)
        layout.addWidget(self.collectLogButton)
        layout.addWidget(self.logEdit)
        self.setLayout(layout)

        self.comm = Communicate()
        self.comm.log_signal.connect(self.append_log)
        self.comm.finished_signal.connect(self.on_test_finished)

        self.startButton.clicked.connect(self.click_to_start)
        self.stopButton.clicked.connect(self.click_to_stop)
        self.clearButton.clicked.connect(self.logEdit.clear)
        self.collectLogButton.clicked.connect(self.click_to_collect_logs)

        self.is_running = False
        self.stopButton.setEnabled(False)

        self.append_log("💡 **程序就绪**：请确保设备已连接并开启USB调试。")
        self.append_log(f"  - 设备序列号: `{DEVICE_SERIAL}`")
        self.append_log(f"  - 报告将保存在: `{os.path.abspath(REPORT_DIR)}`")

    def append_log(self, message):
        self.logEdit.append(message)
        self.logEdit.ensureCursorVisible()

    def click_to_start(self):
        self.is_running = True
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.append_log("\n▶️ **测试已开始...**")
        t = threading.Thread(target=self.run_test, daemon=True)  # 修正了这里
        t.start()

    def click_to_stop(self):
        if self.is_running:
            self.is_running = False
            self.append_log("\n⏹️ **正在请求停止... (请等待当前循环结束)**")
            self.stopButton.setEnabled(False)

    def on_test_finished(self):
        self.is_running = False
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        self.append_log("\n✅ **测试流程已结束。**")

    def execute_step(self, command, step_name, sleep_after=0.8):
        if not self.is_running:
            return True
        self.comm.log_signal.emit(f"  - {step_name}")
        status, output = run_adb_command(command)
        if status != 0:
            error_msg = f'<font color="#FF0000">❌ 错误: 步骤 "{step_name}" 失败！<br>  ADB输出: {output}</font>'
            self.comm.log_signal.emit(error_msg)
            self.is_running = False
            return True
        time.sleep(sleep_after)
        return False

    def take_screenshot(self, name):
        try:
            path = os.path.join(REPORT_DIR, f"{name}.png")
            subprocess.run(f"adb -s {DEVICE_SERIAL} exec-out screencap -p > \"{path}\"", shell=True, check=True)
            self.comm.log_signal.emit(f'📸 **截图成功**: 已保存至 `{path}`')
        except Exception as e:
            self.comm.log_signal.emit(f'<font color="#FF8C00">⚠️ 截图失败: {e}</font>')

    def run_test(self):
        try:
            if self.execute_step('input tap 767 1688', "进入图库app", sleep_after=1.5): return
            if self.execute_step('input tap 158 2530', "进入图库后点击指定区域", sleep_after=1.0): return
            if self.execute_step('input tap 212 1185', "选择第一张照片", sleep_after=1.5): return
            if self.execute_step('input tap 984 278', "点击右上角", sleep_after=1.0): return
            if self.execute_step('input tap 841 612' , "点击慢放",sleep_after=20): return

            for i in range(100):
                if not self.is_running: break
                self.comm.log_signal.emit(f"--- 第 {i+1}/200 次循环 ---")
                if self.execute_step('input tap 120 2516', "返回照片页", sleep_after=2): break
                if self.execute_step('input tap 115 260', "返回照片页2", sleep_after=2): break
                if self.execute_step('input swipe 212 1185 212 1185 1000', "长按第一张照片", sleep_after=1.5): return
                if self.execute_step('input tap 855 2488', "删除", sleep_after=1.5): return
                if self.execute_step('input tap 855 2488', "删除", sleep_after=1.5): return
                if self.execute_step('input tap 892 2438', "确认删除", sleep_after=1.5): return
                if self.execute_step('input tap 212 1185', "选择第一张照片", sleep_after=1.5): return
                if self.execute_step('input tap 984 278', "点击右上角", sleep_after=1.0): return
                if self.execute_step('input tap 841 612', "点击慢放", sleep_after=20): return



            self.take_screenshot("完成截图")
        except Exception as e:
            self.append_log(f'<font color="#FF0000">❌ 测试流程异常：{e}</font>')
        finally:
            self.comm.finished_signal.emit()

    def click_to_collect_logs(self):
        t = threading.Thread(target=self.collect_device_logs, daemon=True)
        t.start()

    def collect_device_logs(self, ver_str=""):
        folder = get_timestamp_folder(ver_str)
        full_path = os.path.join(os.getcwd(), folder)
        self.append_log(f"####start to get log to ({full_path})...")
        subfolders = [
            "dropbox", "tombstones", "corefile", "apanic", "diaglogs", "LogService",
            "archive", "database", "databases", "Screenshots"
        ]
        for sub in subfolders:
            os.makedirs(os.path.join(full_path, sub), exist_ok=True)

        run_adb_command("remount")
        pull_steps = [
            ("/data/log/android_logs", "android_logs"),
            ("/data/tombstones", "tombstones"),
            ("/data/system/dropbox", "dropbox"),
            ("/data/log/hilogs", "hilogs"),
            ("/sdcard/Pictures/Screenshots", "Screenshots"),
            ("data/data/com.hihonor.photos/databases/", "databases/gallery"),
            ("data/data/com.android.providers.media/databases/", "databases/media"),
            ("data/data/com.android.providers.media.module/databases/", "databases/modulemedia"),
            ("data/data/com.hihonor.medialibrary/databases/", "databases/medialibrary"),
        ]
        for src, dst in pull_steps:
            dst_path = os.path.join(full_path, dst)
            run_adb_pull(src, dst_path, self.append_log)
        self.append_log(f"日志采集完成，全部保存在: {full_path}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())


# pyinstaller -F -w -n "live_photo_4" --icon=hou.ico live_photo4.py
