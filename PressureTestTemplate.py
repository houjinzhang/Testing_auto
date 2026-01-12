# =========================================================
# PressureTestTemplate.py
# 基于 GUI 的 ADB 压测模板
#
# 规则：
#   只允许修改 `run_test()`
#   其他任何位置禁止修改
# =========================================================

import sys
import time
import threading

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit,
    QVBoxLayout, QHBoxLayout, QLabel, QLineEdit
)
from PyQt6.QtCore import QObject, pyqtSignal

# conftest 提供的能力（adb / 设备 / 环境）
import conftest


# ================== 信号定义 ==================
class Communicate(QObject):
    log_signal = pyqtSignal(str)      # 日志信号
    finished_signal = pyqtSignal()    # 测试结束信号


# ================== 主窗口 ==================
class MainApp(QWidget):
    """
    压测 GUI 模板
    只允许修改：
        - run_test()
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("压测模板")
        self.setGeometry(200, 200, 650, 600)

        self.is_running = False        # 是否正在运行
        self.loop_count = 100          # 循环次数

        # ---------- UI ----------
        self._init_ui()

        # ---------- 信号 ----------
        self.comm = Communicate()
        self.comm.log_signal.connect(self._append_log)
        self.comm.finished_signal.connect(self._on_finished)

        self.stop_btn.setEnabled(False)

        # ---------- conftest 能力 ----------
        self.env = None
        self.adb_shell = None
        self.adb_tap = None

        self._init_env()

    # ==================================================
    # UI 初始化（禁止修改）
    # ==================================================
    def _init_ui(self):
        main = QVBoxLayout()

        top = QHBoxLayout()
        self.device_label = QLabel("设备：未就绪")
        self.refresh_btn = QPushButton("重新初始化设备")
        self.refresh_btn.clicked.connect(self._init_env)
        top.addWidget(self.device_label)
        top.addStretch()
        top.addWidget(self.refresh_btn)
        main.addLayout(top)

        loop_l = QHBoxLayout()
        loop_l.addWidget(QLabel("循环次数："))
        self.loop_input = QLineEdit("100")
        self.loop_input.setFixedWidth(80)
        loop_l.addWidget(self.loop_input)
        loop_l.addStretch()
        main.addLayout(loop_l)

        self.start_btn = QPushButton("开始测试")
        self.stop_btn = QPushButton("停止测试")
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)

        main.addWidget(self.start_btn)
        main.addWidget(self.stop_btn)
        main.addWidget(self.log)
        self.setLayout(main)

    # ==================================================
    # 环境初始化（禁止修改）
    # ==================================================
    def _init_env(self):
        try:
            self.env = conftest.env_config()
            self.adb_shell = conftest.adb_shell_command(self.env, self._log_step)
            self.adb_tap = conftest.adb_tap(
                self.adb_shell,
                conftest.screen_size(self.adb_shell)
            )
            sn = self.env["DEVICE_SERIAL"]
            self.device_label.setText(f"设备：{sn}")
            self._append_log(f"设备初始化完成：{sn}")
            self.start_btn.setEnabled(True)
        except Exception as e:
            self._append_log(f"<font color='red'>初始化失败：{e}</font>")
            self.start_btn.setEnabled(False)

    # ==================================================
    # 测试控制（禁止修改）
    # ==================================================
    def start(self):
        try:
            self.loop_count = int(self.loop_input.text())
            assert self.loop_count > 0
        except Exception:
            self._append_log("<font color='red'>循环次数输入非法</font>")
            return

        self.is_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._append_log(f"\n开始压测，共 {self.loop_count} 次循环")
        threading.Thread(target=self.run_test, daemon=True).start()

    def stop(self):
        self.is_running = False
        self._append_log("已请求停止测试…")

    def _on_finished(self):
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._append_log("\n测试结束")

    # ==================================================
    # 日志相关（禁止修改）
    # ==================================================
    def _log_step(self, msg, *_):
        self.comm.log_signal.emit(msg)

    def _append_log(self, msg):
        ts = time.strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {msg}")
        self.log.ensureCursorVisible()

    # ==================================================
    # ⭐ 压测逻辑（唯一允许修改的区域）
    # ==================================================
    def run_test(self):
        """
        只允许在这个函数中编写 / 修改压测逻辑
        """
        pass


# ================== 程序入口 ==================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainApp()
    w.show()
    sys.exit(app.exec())
