import sys
import time
import os
import threading
import subprocess
import datetime
import webbrowser
import uuid
import shutil

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal

DEVICE_SERIAL = 'A22C015925000107'
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

class Communicate(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Live Photo 自动化测试 (极速版)")
        self.setGeometry(200, 200, 600, 500)

        layout = QVBoxLayout()
        self.startButton = QPushButton("开始测试")
        self.stopButton = QPushButton("停止测试")
        self.clearButton = QPushButton("清空日志")
        self.logEdit = QTextEdit()
        self.logEdit.setReadOnly(True)

        layout.addWidget(self.startButton)
        layout.addWidget(self.stopButton)
        layout.addWidget(self.clearButton)
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

        self.append_log("💡 **程序就绪 (极速版)**")
        self.append_log(f"  - 设备序列号: `{DEVICE_SERIAL}`")
        self.append_log(f"  - 截图保存在: `{os.path.abspath(REPORT_DIR)}`")

    def append_log(self, message):
        self.logEdit.append(message)
        self.logEdit.ensureCursorVisible()

    def click_to_start(self):
        self.is_running = True
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)
        self.append_log("\n▶️ **轮循测试已开始...**")
        t = threading.Thread(target=self.run_all_tests, daemon=True)
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
        self.append_log("\n✅ **所有测试流程已结束。**")

    def take_screenshot(self, name):
        try:
            safe_name = "".join(c for c in name if c.isalnum() or c in ('_', '-')).rstrip()
            path = os.path.join(REPORT_DIR, f"{safe_name}_{time.time():.0f}.png")
            subprocess.run(f"adb -s {DEVICE_SERIAL} exec-out screencap -p > \"{path}\"", shell=True, check=True)
            self.comm.log_signal.emit(f'📸 **截图成功**: 已保存至 `{path}`')
        except Exception as e:
            self.comm.log_signal.emit(f'<font color="#FF8C00">⚠️ 截图失败: {e}</font>')

    # 修改：增加 need_screenshot 参数，异常时仍强制截图
    def execute_step(self, step_name, command, sleep_after=1.0, need_screenshot=False):
        if not self.is_running: return False
        try:
            self.comm.log_signal.emit(f"  - {step_name}")
            status, output = run_adb_command(command)
            if status != 0:
                raise Exception(f"ADB命令执行失败: {output}")
            if sleep_after > 0: time.sleep(sleep_after)
            if need_screenshot:
                self.take_screenshot(step_name)
            return True
        except Exception as e:
            error_msg = f'<font color="#FF0000">❌ 错误: 步骤 "{step_name}" 失败！<br>  原因: {e}</font>'
            self.comm.log_signal.emit(error_msg)
            self.take_screenshot(f"失败截图_{step_name}")
            self.is_running = False
            return False

    def run_all_tests(self):
        try:
            total_loop_count = 99
            tests = [
                {"name": "慢放", "steps": [('input tap 984 278', "点击右上角"), ('input tap 841 612', "点击慢放", 17)]},
                {"name": "幻影", "steps": [('input tap 945 253', "点击右上角"), ('input tap 963 806', "点击幻影", 17)]},
                {"name": "分身", "steps": [('input tap 945 253', "点击右上角"), ('input tap 970 878', "点击分身", 17)]}
            ]
            for loop in range(total_loop_count):
                if not self.is_running:
                    self.comm.log_signal.emit("测试被手动停止。")
                    break
                current_test = tests[loop % len(tests)]
                test_name = current_test["name"]
                self.comm.log_signal.emit(
                    f"\n--- 第 {loop + 1}/{total_loop_count} 次循环: **开始 {test_name} 测试** ---")
                try:
                    # 关键步骤截图
                    if not self.execute_step("强制停止图库", 'am force-stop com.hihonor.photos', 1.0): break
                    if not self.execute_step("home", 'input tap 654 2660', 1.0, need_screenshot=True): break
                    if not self.execute_step("进入图库app", 'input tap 767 1688', 1.0, need_screenshot=True): break
                    if not self.execute_step("进入图库后点击指定区域", 'input tap 158 2530', 0.5): break
                    if not self.execute_step("选择第一张照片", 'input tap 212 1185', 1.0, need_screenshot=True): break
                    # 变换测试类型步骤
                    for cmd, desc, *sleep_arg in current_test["steps"]:
                        sleep_time = sleep_arg[0] if sleep_arg else 1.0
                        # 关键步骤截图
                        if not self.execute_step(desc, cmd, sleep_time, need_screenshot=True): break
                    if not self.is_running: break
                    if not self.execute_step("点击Home键", 'input keyevent 3', 0.5): break
                    if not self.execute_step("强制停止文件管理", 'am force-stop com.hihonor.filemanager', 0.5): break
                    if not self.execute_step("点击文件管理", 'input tap 786 2000', 0.5): break
                    if not self.execute_step("点击浏览", 'input tap 1012 2548', 0.5): break
                    if not self.execute_step("点击我的手机", 'input tap 581 1636', 0.5): break
                    if not self.execute_step("点击pictures", 'input tap 600 2176', 0.5): break
                    if not self.execute_step("点击livephoto文件夹", 'input tap 604 1372', 0.5): break
                    if not self.execute_step("长按第一张照片", 'input swipe 562 829 562 829 1000', 0.5): break
                    if not self.execute_step("全选", 'input tap 1149 269', 0.2): break
                    if not self.execute_step("删除", 'input tap 892 2488', 0.2): break
                    # 删除确认截图
                    if not self.execute_step("确认删除", 'input tap 939 2444', 0.2, need_screenshot=True): break
                    self.comm.log_signal.emit(f"✅ 第 {loop + 1} 次循环 ({test_name}) 完成")
                except Exception as e:
                    self.append_log(f'<font color="#FF0001">❌ 测试流程异常：{e}</font>')
        except Exception as e:
            self.append_log(f'<font color="#FF0000">❌ 主测试线程异常：{e}</font>')
        finally:
            self.comm.finished_signal.emit()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())
