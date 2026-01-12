import sys
import time
import os
import threading
import subprocess
import datetime
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import QObject, pyqtSignal, QPropertyAnimation, QEasingCurve

DEVICE_SERIAL = 'AN5U015925000136'
REPORT_DIR = "report_ai_enhance"
os.makedirs(REPORT_DIR, exist_ok=True)

# 渐变背景 QSS
APP_QSS = """
QWidget {
    background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #1e3c72, stop:1 #2a5298);
    color: #FFFFFF;
    font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
    font-size: 14px;
}

QPushButton {
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #4facfe, stop:1 #00f2fe);
    border: none;
    border-radius: 10px;
    padding: 10px 15px;
    color: white;
    font-weight: bold;
}
QPushButton:hover {
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #43e97b, stop:1 #38f9d7);
}
QPushButton:pressed {
    background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 #fa709a, stop:1 #fee140);
}

QTextEdit {
    background-color: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255,255,255,0.3);
    border-radius: 12px;
    padding: 8px;
    color: #FFFFFF;
    font-family: Consolas, monospace;
}
"""

class Communicate(QObject):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        # 提前应用样式，避免闪白
        self.setStyleSheet(APP_QSS)

        self.setWindowTitle("📷 Live Photo 测试工具")
        self.setGeometry(200, 200, 600, 600)

        # 窗口淡入效果
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(800)
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.start()

        layout = QVBoxLayout()
        self.startButton = QPushButton("▶ 开始测试")
        self.stopButton = QPushButton("⏹ 停止测试")
        self.clearButton = QPushButton("🧹 清空日志")
        self.collectLogButton = QPushButton("📂 采集设备日志")

        # 日志区域，直接设置初始样式避免闪白
        self.logEdit = QTextEdit()
        self.logEdit.setReadOnly(True)
        self.logEdit.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.15);
            border: 1px solid rgba(255,255,255,0.3);
            border-radius: 12px;
            padding: 8px;
            color: #FFFFFF;
            font-family: Consolas, monospace;
        """)

        # 按钮点击动效
        for btn in [self.startButton, self.stopButton, self.clearButton, self.collectLogButton]:
            btn.clicked.connect(lambda _, b=btn: self.animate_button(b))

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

    def animate_button(self, button):
        """按钮点击缩放动效"""
        anim = QPropertyAnimation(button, b"geometry")
        anim.setDuration(150)
        anim.setStartValue(button.geometry())
        anim.setEndValue(button.geometry().adjusted(2, 2, -2, -2))
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(lambda: button.setGeometry(button.geometry().adjusted(-2, -2, 2, 2)))
        anim.start()

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

    # 这里你可以把原来的 execute_step / check_app_crash / run_test / collect_device_logs 方法加回来

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_QSS)
    main_window = MainApp()
    main_window.show()
    sys.exit(app.exec())
