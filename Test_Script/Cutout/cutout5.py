import sys
import time
import os
import threading
import subprocess
import datetime
import urllib.parse
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal
from appium import webdriver
from appium.options.common.base import AppiumOptions
from selenium.webdriver.common.actions.action_builder import ActionBuilder


# ======================================================
# 基础配置
# ======================================================
DEVICE_SERIAL = 'ASQH015820000074'
REPORT_DIR = "report_ai_enhance"
os.makedirs(REPORT_DIR, exist_ok=True)


# ======================================================
# ADB 录屏控制
# ======================================================
def start_recording():
    cmd = f"adb -s {DEVICE_SERIAL} shell screenrecord /sdcard/loop90_100.mp4"
    return subprocess.Popen(cmd, shell=True)

def stop_recording(proc):
    try:
        proc.terminate()
        time.sleep(1)
        local_path = os.path.join(REPORT_DIR, "循环90_100录屏.mp4")
        pull_cmd = f"adb -s {DEVICE_SERIAL} pull /sdcard/loop90_100.mp4 \"{local_path}\""
        subprocess.run(pull_cmd, shell=True)
        return local_path
    except:
        return None


# ======================================================
# Appium 初始化
# ======================================================
def init_driver():
    options = AppiumOptions()
    options.load_capabilities({
        "platformName": "Android",
        "platformVersion": "16",
        "deviceName": "DNP_AN00",
        "appPackage": "com.hihonor.photos",
        "appActivity": "com.hihonor.gallery.app.GalleryMain",
        "newCommandTimeout": 7200,
        "noReset": True
    })
    return webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)


# ======================================================
# 手势封装
# ======================================================
def w3c_long_press(driver, point, hold_time=500):
    actions = ActionBuilder(driver)
    finger = actions.add_pointer_input("touch", "finger1")
    finger.create_pointer_move(duration=0, x=point[0], y=point[1])
    finger.create_pointer_down(button=0)
    finger.create_pause(hold_time / 1000)
    finger.create_pointer_up(button=0)
    actions.perform()


# ======================================================
# 信号类
# ======================================================
class Communicate(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()


# ======================================================
# 主窗口
# ======================================================
class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("抠图恢复压测100次 - Appium 极速（含 HTML 报告 & 90~100 录屏）")
        self.setGeometry(200, 200, 600, 600)

        layout = QVBoxLayout()
        self.startButton = QPushButton("开始测试")
        self.stopButton = QPushButton("停止测试")
        self.clearButton = QPushButton("清空日志")
        self.collectLogButton = QPushButton("采集设备日志 （预留）")
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

        self.is_running = False
        self.stopButton.setEnabled(False)
        self.driver = None
        self.current_loop = 0
        self.record_proc = None

        self.append_log("程序就绪，请连接设备。")

    # ======================================================
    # 工具方法
    # ======================================================
    def append_log(self, msg):
        self.logEdit.append(msg)
        self.logEdit.ensureCursorVisible()

    def safe_screenshot(self, name):
        try:
            png = self.driver.get_screenshot_as_png()
            path = os.path.join(REPORT_DIR, f"{name}.png")
            with open(path, "wb") as f:
                f.write(png)
            self.append_log(f"📸 截图保存：{path}")
        except Exception as e:
            self.append_log(f"截图失败: {e}")

    # ======================================================
    # 控件事件
    # ======================================================
    def click_to_start(self):
        self.is_running = True
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)

        self.append_log("\n▶️ 开始压测")
        threading.Thread(target=self.run_test, daemon=True).start()

    def click_to_stop(self):
        self.is_running = False
        self.append_log("\n⏹ 正在停止，等待当前循环结束…")
        self.stopButton.setEnabled(False)

        if self.record_proc:
            stop_recording(self.record_proc)

    # ======================================================
    # HTML 报告（已修复视频无法播放问题）
    # ======================================================
    def export_html_report(self):
        html = os.path.join(REPORT_DIR, "test_report.html")

        with open(html, "w", encoding="utf-8") as f:
            f.write(f"""
<html>
<head>
<meta charset="utf-8">
<title>压测报告</title>
<style>
body {{font-family: Arial; padding:20px;}}
h1{{color:#0078D7;}}
.log{{white-space:pre-wrap;background:#F5F5F5;padding:10px;border:1px solid #CCC;max-height:400px;overflow:auto;}}
img{{border:1px solid #CCC;margin-top:10px;}}
video{{margin-top:10px; border:1px solid #CCC;}}
</style>
</head>
<body>

<h1>📄 Appium 抠图恢复 100 次压测报告</h1>
<p>生成时间：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

<h2>📘 测试日志</h2>
<div class='log'>{self.logEdit.toPlainText().replace("\n","<br>")}</div>
""")

        # 压测结束截图（处理中文路径）
        end_png = os.path.join(REPORT_DIR, "压测结束截图.png")
        if os.path.exists(end_png):
            png_url = urllib.parse.quote("压测结束截图.png")
            f.write(f"<h2>📸 压测结束截图</h2>")
            f.write(f"<img src='{png_url}' width='40%'>")

        # 录像部分（核心修复：URL 编码 + 直接 src）
        video_path = os.path.join(REPORT_DIR, "循环90_100录屏.mp4")
        if os.path.exists(video_path):
            video_url = urllib.parse.quote("循环90_100录屏.mp4")
            f.write(f"<h2>🎥 第 90~100 次循环录屏</h2>")
            f.write(f"<video width='400' controls src='{video_url}' type='video/mp4'></video>")

        f.write("</body></html>")

        self.append_log(f"📄 HTML 报告生成：{html}")
        os.startfile(html)

    # ======================================================
    # 压测逻辑
    # ======================================================
    def restart_driver(self):
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

            subprocess.run(f"adb -s {DEVICE_SERIAL} shell am force-stop com.hihonor.photos", shell=True)
            time.sleep(1)

            self.driver = init_driver()
            self.append_log("已重启 Appium 会话")
        except Exception as e:
            self.append_log(f"重启 Appium 失败: {e}")
            self.comm.finished_signal.emit()

    def init_gallery(self):
        self.append_log("初始化图库…")
        time.sleep(2)

    def loop_test(self):
        for i in range(self.current_loop, 100):
            if not self.is_running:
                break

            self.append_log(f"--- 第 {i+1}/100 次 ---")

            if i == 89:
                self.append_log("开始录屏（第90次）")
                self.record_proc = start_recording()

            if i == 99 and self.record_proc:
                stop_recording(self.record_proc)
                self.append_log("录屏结束")
                self.record_proc = None

            try:
                w3c_long_press(self.driver, (244, 1235), 800)
                time.sleep(1)
                self.driver.tap([(620, 1199)]); time.sleep(0.5)
                self.driver.tap([(1063, 1210)]); time.sleep(0.5)
                self.driver.tap([(233, 1649)]); time.sleep(0.5)
                self.driver.tap([(627, 2489)]); time.sleep(1)
                self.driver.tap([(742, 2245)]); time.sleep(2)
                self.driver.tap([(959, 2131)]); time.sleep(1)
                self.driver.tap([(244, 1235)]); time.sleep(1)
                self.driver.tap([(191, 1688)]); time.sleep(12)
                self.driver.tap([(244, 1235)]); time.sleep(1)
                self.driver.tap([(594, 1196)])
                self.safe_screenshot(f"第{i+1}次-恢复后")
                time.sleep(1)
                self.driver.tap([(1085, 282)]); time.sleep(1)
                self.driver.tap([(631, 2093)]); time.sleep(2)
                self.driver.tap([(110, 246)]); time.sleep(1)
                self.driver.tap([(110, 246)]); time.sleep(2)
                w3c_long_press(self.driver, (244, 1235), 800); time.sleep(1)
                self.driver.tap([(876, 2512)]); time.sleep(1)
                self.driver.tap([(877, 2400)]); time.sleep(2)

                self.current_loop = i + 1

            except Exception as e:
                self.append_log(f"⚠️ 循环异常，正在恢复: {e}")
                self.restart_driver()
                break

    def run_test(self):
        try:
            self.driver = init_driver()
            self.init_gallery()
            self.loop_test()
        except Exception as e:
            self.append_log(f"❌ 测试异常: {e}")
            self.restart_driver()

        self.comm.finished_signal.emit()

    # ======================================================
    # 测试结束
    # ======================================================
    def on_test_finished(self):
        self.append_log("测试结束，正在生成报告…")

        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

        if self.record_proc:
            stop_recording(self.record_proc)

        self.safe_screenshot("压测结束截图")
        self.export_html_report()

        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

    # ======================================================
    def click_to_collect_logs(self):
        self.append_log("采集日志功能留空，可自行扩展。")


# ======================================================
# 主入口
# ======================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainApp()
    win.show()
    sys.exit(app.exec())
