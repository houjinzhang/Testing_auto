import sys
import time
import os
import threading
import subprocess
import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal

# =======================
# 基础配置
# =======================
DEVICE_SERIAL = 'ASQH015820000074'
REPORT_DIR = "report_ai_enhance"
os.makedirs(REPORT_DIR, exist_ok=True)

# =======================
# ADB 方法
# =======================
def run_adb_command(command):
    try:
        full_cmd = f"adb -s {DEVICE_SERIAL} shell {command}"
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, encoding='utf-8')
        return result.returncode, result.stdout.strip()
    except Exception as e:
        return -1, f"ADB 错误: {e}"

def run_adb_pull(src, dst, log_func=None):
    cmd = f'adb -s {DEVICE_SERIAL} pull "{src}" "{dst}"'
    if log_func:
        log_func(f"拉取 {src} 到 {dst}")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        if log_func:
            log_func(f"拉取失败: {e}")

def get_timestamp_folder(ver_str=""):
    now = datetime.datetime.now()
    return f"Logs_{ver_str}_{now.strftime('%Y%m%d_%H%M%S')}" if ver_str else now.strftime('%Y%m%d_%H%M%S')

# =======================
# 录屏
# =======================
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

# =======================
# 信号类
# =======================
class Communicate(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

# =======================
# 主窗口
# =======================
class MainApp(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("抠图恢复压测100次（去除 Allure + 90~100 录屏版）")
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
        self.record_proc = None

        self.append_log("程序就绪。")

    # -----------------------------
    def append_log(self, msg):
        self.logEdit.append(msg)
        self.logEdit.ensureCursorVisible()

    # -----------------------------
    def click_to_start(self):
        self.is_running = True
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.append_log("\n开始测试...")
        threading.Thread(target=self.run_test, daemon=True).start()

    # -----------------------------
    def click_to_stop(self):
        self.is_running = False
        self.append_log("停止请求已发送，请等待当前循环结束")
        self.stopButton.setEnabled(False)
        if self.record_proc:
            stop_recording(self.record_proc)

    # -----------------------------
    def execute_step(self, command, name, sleep_after=1.0):
        if not self.is_running:
            return True
        self.append_log(f"- {name}")
        status, output = run_adb_command(command)
        if status != 0:
            self.append_log(f"步骤失败：{output}")
            self.is_running = False
            return True
        time.sleep(sleep_after)
        return False

    # -----------------------------
    def take_screenshot(self, name):
        try:
            path = os.path.join(REPORT_DIR, f"{name}.png")
            subprocess.run(
                f"adb -s {DEVICE_SERIAL} exec-out screencap -p > \"{path}\"",
                shell=True, check=True
            )
            self.append_log(f"截图已保存：{path}")
        except Exception as e:
            self.append_log(f"截图失败：{e}")

    def export_html_report(self):
        html_path = os.path.join(REPORT_DIR, "test_report.html")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write("""
    <html>
    <head>
        <meta charset="utf-8">
        <title>压测报告</title>
        <style>
            body { font-family: Arial, sans-serif; padding: 20px; }
            h1 { color: #0078D7; }
            h2 { margin-top: 30px; }
            .log-box { 
                white-space: pre-wrap; 
                background: #F5F5F5; 
                padding: 15px; 
                border-radius: 6px; 
                border: 1px solid #DDD; 
                max-height: 400px;
                overflow-y: scroll;
            }
            img { border: 1px solid #CCC; margin-top: 10px; }
            video { margin-top: 10px; border: 1px solid #CCC; }
        </style>
    </head>
    <body>

    <h1>📄 抠图恢复 100 次压测报告</h1>
    <p>自动生成时间：""" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "</p>")

            # --------------------
            # 日志内容
            # --------------------
            f.write("<h2>📘 测试日志</h2>")
            f.write("<div class='log-box'>")
            f.write(self.logEdit.toPlainText().replace("\n", "<br>"))
            f.write("</div>")

            # --------------------
            # 最终截图
            # --------------------
            end_png = os.path.join(REPORT_DIR, "压测结束截图.png")
            if os.path.exists(end_png):
                f.write("<h2>📸 压测结束截图</h2>")
                f.write(f"<img src='{end_png}' width='40%'>")

            # --------------------
            # 90~100 循环录屏
            # --------------------
            video = os.path.join(REPORT_DIR, "循环90_100录屏.mp4")
            if os.path.exists(video):
                f.write("<h2>🎥 循环 90~100 录屏</h2>")
                f.write(f"<video width='400' controls><source src='{video}' type='video/mp4'></video>")

            # 结束
            f.write("</body></html>")

        self.append_log(f"HTML 报告已生成：{html_path}")
        os.startfile(html_path)

    # -----------------------------
    def run_test(self):
        try:
            # 固定步骤
            if self.execute_step('input tap 771 1689', "点击图库", 1): return
            if self.execute_step('input tap 131 2508', "点击照片页", 1): return
            if self.execute_step('input swipe 244 1235 244 1235 1000', "长按第一张", 1): return
            if self.execute_step('input tap 620 1199', "选第二张", 0.5): return
            if self.execute_step('input tap 1063 1210', "选第三张", 0.5): return
            if self.execute_step('input tap 233 1649', "选第四张", 0.5): return
            if self.execute_step('input tap 627 2489', "点击创作", 1): return
            if self.execute_step('input tap 742 2245', "点击拼图", 1): return
            if self.execute_step('input tap 959 2131', "选择四方格", 1): return

            # 循环100次
            for i in range(100):
                if not self.is_running:
                    break

                self.append_log(f"--- 循环 {i+1}/100 ---")

                if i == 89:  # 第90次开始录屏
                    self.append_log("开始录屏：第 90 次")
                    self.record_proc = start_recording()

                if i == 99 and self.record_proc:  # 第100次结束录屏
                    path = stop_recording(self.record_proc)
                    self.record_proc = None
                    self.append_log(f"录屏已保存：{path}")

                if self.execute_step('input tap 245 807', "选第一张", 1): break
                if self.execute_step('input tap 181 1642', "扣图", 2): break
                if self.execute_step('input tap 245 807', "再次选第一张", 1): break
                if self.execute_step('input tap 602 1223', "恢复", 2): break

            self.take_screenshot("压测结束截图")

        except Exception as e:
            self.append_log(f"异常：{e}")

        finally:
            self.comm.finished_signal.emit()

    # -----------------------------
    def on_test_finished(self):
        self.is_running = False
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

        if self.record_proc:
            stop_recording(self.record_proc)

        self.append_log("测试完成，正在生成 HTML 报告...")
        self.export_html_report()

    # -----------------------------
    def click_to_collect_logs(self):
        threading.Thread(target=self.collect_device_logs, daemon=True).start()

    def collect_device_logs(self, ver_str=""):
        folder = get_timestamp_folder(ver_str)
        path = os.path.join(os.getcwd(), folder)
        self.append_log(f"开始采集日志：{path}")

        run_adb_command("remount")

        pull_list = [
            ("/data/log/android_logs", "android_logs"),
            ("/data/tombstones", "tombstones"),
        ]
        for src, name in pull_list:
            dst = os.path.join(path, name)
            run_adb_pull(src, dst, self.append_log)

        self.append_log(f"日志采集完成：{path}")

# =======================
# 主入口
# =======================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainApp()
    win.show()
    sys.exit(app.exec())
