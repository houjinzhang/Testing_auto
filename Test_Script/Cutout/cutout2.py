import sys
import time
import os
import threading
import subprocess
import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal


# ======================================================
# 基础配置
# ======================================================
DEVICE_SERIAL = 'ASQH015820000074'
REPORT_DIR = "report_ai_enhance"
os.makedirs(REPORT_DIR, exist_ok=True)


# ======================================================
# ADB 执行器
# ======================================================
def run_adb_command(command):
    try:
        full_cmd = f"adb -s {DEVICE_SERIAL} shell {command}"
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, encoding='utf-8', check=False)
        return result.returncode, result.stdout.strip()
    except Exception as e:
        return -1, f"ADB 错误: {e}"


def run_adb_pull(src, dst, log_func=None):
    cmd = f'adb -s {DEVICE_SERIAL} pull "{src}" "{dst}"'
    if log_func:
        log_func(f"拉取 {src} 到 {dst}")
    try:
        os.makedirs(dst, exist_ok=True)
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        if log_func:
            log_func(f"<font color='#FF0000'>拉取失败: {e}</font>")


def get_timestamp_folder(ver_str=""):
    now = datetime.datetime.now()
    date = now.strftime("%Y%m%d_%H%M%S")
    return f"Logs_{ver_str}_{date}" if ver_str else f"Logs_{date}"


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
        self.setWindowTitle("抠图恢复压测（录屏 + HTML 报告版）")
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

        self.append_log("程序就绪。")

    # ======================================
    # GUI 日志
    # ======================================
    def append_log(self, message):
        self.logEdit.append(message)
        self.logEdit.ensureCursorVisible()

    # ======================================
    # 录屏控制
    # ======================================
    def start_recording(self):
        self.append_log("开始录屏（设备）...")
        self.recording_file = "/sdcard/test_record.mp4"
        cmd = f"adb -s {DEVICE_SERIAL} shell screenrecord {self.recording_file}"
        self.recording_proc = subprocess.Popen(cmd, shell=True)

    def stop_recording(self):
        try:
            self.append_log("停止录屏…")
            self.recording_proc.terminate()
            time.sleep(1)

            local_path = os.path.join(REPORT_DIR, "循环15到20_录屏.mp4")
            pull_cmd = f'adb -s {DEVICE_SERIAL} pull "{self.recording_file}" "{local_path}"'
            subprocess.run(pull_cmd, shell=True)

            self.append_log(f"录屏已保存 → {local_path}")
        except Exception as e:
            self.append_log(f"录屏停止失败: {e}")

    # ======================================
    # HTML 报告生成器
    # ======================================
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

<h1>📄 抠图恢复压测报告</h1>
<p>自动生成时间：""" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "</p>")

            # 日志
            f.write("<h2>📘 测试日志</h2>")
            f.write("<div class='log-box'>")
            f.write(self.logEdit.toPlainText().replace("\n", "<br>"))
            f.write("</div>")

            # 截图
            end_png = os.path.join(REPORT_DIR, "压测结束截图.png")
            if os.path.exists(end_png):
                f.write("<h2>📸 压测结束截图</h2>")
                f.write(f"<img src='{end_png}' width='40%'>")

            # 录屏
            video = os.path.join(REPORT_DIR, "循环15到20_录屏.mp4")
            if os.path.exists(video):
                f.write("<h2>🎥 循环 15～20 录屏</h2>")
                f.write(f"<video width='400' controls><source src='{video}' type='video/mp4'></video>")

            f.write("</body></html>")

        self.append_log(f"HTML 报告已生成：{html_path}")
        os.startfile(html_path)

    # ======================================
    # 按钮：开始
    # ======================================
    def click_to_start(self):
        self.is_running = True
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)

        self.append_log("\n▶️ 开始测试...")

        threading.Thread(target=self.run_test, daemon=True).start()

    # ======================================
    # 按钮：停止
    # ======================================
    def click_to_stop(self):
        self.is_running = False
        self.append_log("\n⏹️ 请求停止（等待当前步骤完成）")
        self.stopButton.setEnabled(False)

        if hasattr(self, "recording_proc"):
            self.stop_recording()

    # ======================================
    # 执行单步
    # ======================================
    def execute_step(self, command, step_name, sleep_after=1.0):
        if not self.is_running:
            return True

        self.comm.log_signal.emit(f"- {step_name}")

        status, output = run_adb_command(command)
        if status != 0:
            err = f"{step_name} 失败: {output}"
            self.append_log(f"❌ {err}")
            self.is_running = False
            return True

        time.sleep(sleep_after)
        return False

    # ======================================
    # 截图
    # ======================================
    def take_screenshot(self, name):
        path = os.path.join(REPORT_DIR, f"{name}.png")
        try:
            subprocess.run(
                f"adb -s {DEVICE_SERIAL} exec-out screencap -p > \"{path}\"",
                shell=True, check=True
            )
            self.append_log(f"截图保存: {path}")
        except Exception as e:
            self.append_log(f"截图失败: {e}")

    # ======================================
    # 压测流程
    # ======================================
    def run_test(self):
        try:
            # 固定步骤
            if self.execute_step('input tap 771 1689', "点击图库", 1.5): return
            if self.execute_step('input tap 131 2508', "点击照片页", 1.0): return
            if self.execute_step('input swipe 244 1235 244 1235 1000', "长按第一张", 1.0): return

            if self.execute_step('input tap 620 1199', "选第二张", 0.5): return
            if self.execute_step('input tap 1063 1210', "选第三张", 0.5): return
            if self.execute_step('input tap 233 1649', "选第四张", 0.5): return

            if self.execute_step('input tap 627 2489', "点击创作", 1.0): return
            if self.execute_step('input tap 742 2245', "点击拼图", 1.0): return
            if self.execute_step('input tap 959 2131', "选择四方格", 1.0): return

            # 循环20次
            for i in range(20):
                if not self.is_running:
                    break

                self.comm.log_signal.emit(f"--- 循环 {i+1}/20 ---")

                # 第 15 次开始录屏
                if i == 14:
                    self.start_recording()

                # 第 20 次结束录屏
                if i == 19:
                    self.stop_recording()

                if self.execute_step('input tap 245 807', "选第一张", 1.0): break
                if self.execute_step('input tap 181 1642', "扣图", 10.0): break
                if self.execute_step('input tap 245 807', "选第一张", 1.0): break
                if self.execute_step('input tap 600 1184', "恢复1", 1.0): break

                if self.execute_step('input tap 913 776', "选第二个素材", 1.0): break
                if self.execute_step('input tap 181 1642', "扣图", 10.0): break
                if self.execute_step('input tap 913 776', "选第二个素材", 1.0): break
                if self.execute_step('input tap 952 1214', "恢复2", 1.0): break

                if self.execute_step('input tap 356 1335', "选第三个素材", 1.0): break
                if self.execute_step('input tap 181 1642', "扣图", 10.0): break
                if self.execute_step('input tap 356 1335', "选第三个素材", 1.0): break
                if self.execute_step('input tap 606 818', "恢复3", 1.0): break

                if self.execute_step('input tap 919 1312', "选第四个素材", 1.0): break
                if self.execute_step('input tap 181 1642', "扣图", 10.0): break
                if self.execute_step('input tap 919 1312', "选第四个素材", 1.0): break
                if self.execute_step('input tap 981 955', "恢复4", 1.0): break

            self.take_screenshot("压测结束截图")

        except Exception as e:
            self.append_log(f"异常: {e}")

        finally:
            self.comm.finished_signal.emit()

    # ======================================
    # 测试结束
    # ======================================
    def on_test_finished(self):
        self.is_running = False
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)

        if hasattr(self, "recording_proc"):
            self.stop_recording()

        self.append_log("\n测试结束，正在生成 HTML 报告…")

        self.export_html_report()

    # ======================================
    # 采集设备日志
    # ======================================
    def click_to_collect_logs(self):
        threading.Thread(target=self.collect_device_logs, daemon=True).start()

    def collect_device_logs(self, ver_str=""):
        folder = get_timestamp_folder(ver_str)
        full_path = os.path.join(os.getcwd(), folder)
        self.append_log(f"开始采集日志: {full_path}")

        run_adb_command("remount")

        pull_list = [
            ("/data/log/android_logs", "android_logs"),
            ("/data/tombstones", "tombstones"),
        ]

        for src, name in pull_list:
            dst = os.path.join(full_path, name)
            run_adb_pull(src, dst, self.append_log)

        self.append_log(f"日志采集完成 → {full_path}")


# ======================================================
# 主入口
# ======================================================
if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainApp()
    win.show()
    sys.exit(app.exec())
