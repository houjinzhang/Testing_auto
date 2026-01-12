import sys
import time
import os
import threading
import subprocess
import datetime
import random
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout
from PyQt6.QtCore import QObject, pyqtSignal
from appium import webdriver
from appium.options.common.base import AppiumOptions
from selenium.webdriver.common.actions.action_builder import ActionBuilder

# ===== 基础配置 =====
DEVICE_SERIAL = 'AF2Q015811000014'
REPORT_DIR = "report_ai_enhance"
os.makedirs(REPORT_DIR, exist_ok=True)


# ===== Appium 初始化 =====
def init_driver():
    options = AppiumOptions()
    options.load_capabilities({
        "platformName": "Android",
        "platformVersion": "16",
        "deviceName": "DNP_AN00",
        "appPackage": "com.hihonor.photos",
        "appActivity": "com.hihonor.gallery.app.GalleryMain",
        "newCommandTimeout": 7200,
        "noReset": True,
        # "disableWindowAnimation": True
    })
    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    print(f"✅ Appium 会话已启动，Session ID: {driver.session_id}", flush=True)
    return driver


# ===== 手势封装 =====
def w3c_pinch_zoom(driver, start1, end1, start2, end2, duration=500):
    actions = ActionBuilder(driver)
    finger1 = actions.add_pointer_input("touch", "finger1")
    finger2 = actions.add_pointer_input("touch", "finger2")
    finger1.create_pointer_move(duration=0, x=start1[0], y=start1[1])
    finger1.create_pointer_down(button=0)
    finger1.create_pointer_move(duration=duration, x=end1[0], y=end1[1])
    finger1.create_pointer_up(button=0)
    finger2.create_pointer_move(duration=0, x=start2[0], y=start2[1])
    finger2.create_pointer_down(button=0)
    finger2.create_pointer_move(duration=duration, x=end2[0], y=end2[1])
    finger2.create_pointer_up(button=0)
    actions.perform()


def w3c_swipe(driver, start, end, duration=500):
    actions = ActionBuilder(driver)
    finger = actions.add_pointer_input("touch", "finger1")
    finger.create_pointer_move(duration=0, x=start[0], y=start[1])
    finger.create_pointer_down(button=0)
    finger.create_pointer_move(duration=duration, x=end[0], y=end[1])
    finger.create_pointer_up(button=0)
    actions.perform()


def w3c_long_press(driver, point, hold_time=1000):
    actions = ActionBuilder(driver)
    finger = actions.add_pointer_input("touch", "finger1")
    finger.create_pointer_move(duration=0, x=point[0], y=point[1])
    finger.create_pointer_down(button=0)
    finger.create_pause(hold_time / 1000)
    finger.create_pointer_up(button=0)
    actions.perform()


# ===== 信号类 =====
class Communicate(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()


# ===== 主窗口类 =====
class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("抠图恢复压测100次 - Appium版")
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
        self.driver = None

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
        t = threading.Thread(target=self.run_test, daemon=True)
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
        if self.driver:
            try:
                self.driver.quit()
                self.append_log("🔚 Appium 会话已关闭")
            except Exception as e:
                self.append_log(f"⚠️ driver.quit() 失败: {e}")

    def safe_screenshot(self, name):
        try:
            if self.driver and self.driver.session_id:
                png_data = self.driver.get_screenshot_as_png()
                path = os.path.join(REPORT_DIR, f"{name}.png")
                with open(path, "wb") as f:
                    f.write(png_data)
                self.comm.log_signal.emit(f'📸 **截图成功**: 已保存至 `{path}`')
        except Exception as e:
            self.comm.log_signal.emit(f'<font color="#FF8C00">⚠️ 截图失败: {e}</font>')

    def run_test(self):
        try:
            self.driver = init_driver()


            self.log_step("点击照片页")
            self.driver.tap([(131, 2508)])
            time.sleep(1.0)

            self.log_step("长按第一张1秒")
            w3c_long_press(self.driver, (244, 1235), hold_time=1000)
            time.sleep(1.0)

            self.driver.tap([(620, 1199)])
            self.log_step("选中第二张")
            time.sleep(0.5)

            self.driver.tap([(1063, 1210)])
            self.log_step("选中第三张")
            time.sleep(0.5)

            self.driver.tap([(233, 1649)])
            self.log_step("选中第四张")
            time.sleep(0.5)

            self.driver.tap([(627, 2489)])
            self.log_step("点击创作")
            time.sleep(1.0)

            self.driver.tap([(742, 2245)])
            self.log_step("点击拼图")
            time.sleep(1.0)

            self.driver.tap([(959, 2131)])
            self.log_step("选择四方格")
            time.sleep(1.0)

            # 循环 100 次
            for i in range(100):
                if not self.is_running:
                    break
                self.comm.log_signal.emit(f"--- 第 {i + 1}/100 次循环 ---")

                # 选第一张
                self.driver.tap([(245, 807)])
                self.log_step("循环-选第一张")
                time.sleep(2.0)

                # 点击扣他
                self.driver.tap([(181, 1642)])
                self.log_step("循环-点击扣他")
                time.sleep(15.0)

                if not self.is_running:
                    break

                # 选第一张
                self.driver.tap([(245, 807)])
                self.log_step("循环-选第一张")
                time.sleep(2.0)

                # 点击替换素材
                self.driver.tap([(796, 1216)])
                self.log_step("循环-点击替换素材")
                self.safe_screenshot(f"第{i + 1}次-替换素材后截图")
                time.sleep(0.5)

                # ===== 随机滑动 =====
                start_y = random.randint(1600, 1900)  # 起点随机
                end_y = random.randint(600, 900)  # 终点随机
                w3c_swipe(self.driver, start=(500, start_y), end=(500, end_y), duration=800)
                self.log_step(f"循环-替换素材后随机滑动 (start_y={start_y}, end_y={end_y})")
                time.sleep(5.0)


                # 点击选第一张
                self.driver.tap([(245, 807)])
                self.log_step("循环-选一张")
                self.safe_screenshot(f"第{i + 1}次-恢复后截图")
                time.sleep(1.0)

                # 点击确定
                self.driver.tap([(1136, 249)])
                self.log_step("循环-点击确定")
                self.safe_screenshot(f"第{i + 1}次-恢复后截图")
                time.sleep(1.0)


        except Exception as e:
            self.append_log(f'<font color="#FF0000">❌ 测试流程异常：{e}</font>')
        finally:
            self.comm.finished_signal.emit()

    def log_step(self, step_name):
        self.comm.log_signal.emit(f"  - {step_name}")

    def click_to_collect_logs(self):
        t = threading.Thread(target=self.collect_device_logs, daemon=True)
        t.start()

    def collect_device_logs(self, ver_str=""):
        folder = get_timestamp_folder(ver_str)
        full_path = os.path.join(os.getcwd(), folder)
        self.append_log(f"#### 开始采集日志到 ({full_path})...")
        os.makedirs(full_path, exist_ok=True)
        self.append_log(f"日志采集完成，全部保存在: {full_path}")


def get_timestamp_folder(ver_str=""):
    now = datetime.datetime.now()
    date_part = now.strftime("%Y%m%d_%H%M%S")
    return f"Logs_{ver_str}_{date_part}" if ver_str else f"Logs__{date_part}"


# ===== 程序入口 =====
if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())