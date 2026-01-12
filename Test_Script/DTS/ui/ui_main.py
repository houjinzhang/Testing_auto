import sys
import os
import json
import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit,
    QListWidget, QListWidgetItem, QLabel, QProgressBar, QMessageBox,
    QComboBox
)
from PyQt6.QtCore import QProcess, QPropertyAnimation, QEasingCurve


# -----------------------------------------------------
# 动效按钮：Hover 放大，点击缩小
# -----------------------------------------------------
class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.hover_anim = QPropertyAnimation(self, b"maximumWidth")
        self.hover_anim.setDuration(180)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.base_width = None

    def enterEvent(self, event):
        if self.base_width is None:
            self.base_width = self.width()

        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.width())
        self.hover_anim.setEndValue(self.base_width + 8)
        self.hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self.width())
        self.hover_anim.setEndValue(self.base_width)
        self.hover_anim.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self.setStyleSheet("transform: scale(0.95);")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.setStyleSheet("transform: scale(1);")
        super().mouseReleaseEvent(event)


# 你的模块
from Test_Script import Bridge
from tag_scanner import scan_pytest_markers


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # DTS/ui/
ROOT_DIR = os.path.dirname(CURRENT_DIR)                   # DTS/
HISTORY_FILE = os.path.join(ROOT_DIR, "execution_history.json")

ALLURE_PATH = r"D:\allure-2.18.1\bin\allure.bat"    # 固定你的 Allure 绝对路径


class MainApp(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("houpress")
        self.resize(900, 750)

        # -------------------------------
        # 窗口淡入动画
        # -------------------------------
        self.fadeAnim = QPropertyAnimation(self, b"windowOpacity")
        self.fadeAnim.setDuration(350)
        self.fadeAnim.setStartValue(0.0)
        self.fadeAnim.setEndValue(1.0)
        self.fadeAnim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fadeAnim.start()

        self.bridge = Bridge()
        self.process = None
        self.total_cases = 0
        self.finished_cases = 0
        self.targets = []

        layout = QVBoxLayout()
        layout.addWidget(QLabel("测试用例（可多选，可扫描整个 DTS）："))

        self.caseList = QListWidget()
        self.caseList.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.caseList)

        layout.addWidget(QLabel("按标签执行（可选择 / 可输入）："))

        self.tagBox = QComboBox()
        self.tagBox.setEditable(True)
        self.tagBox.setPlaceholderText("选择或输入标签...")
        layout.addWidget(self.tagBox)

        self.progressBar = QProgressBar()
        self.progressBar.setValue(0)
        layout.addWidget(self.progressBar)

        # -------------------------------
        # 动效按钮
        # -------------------------------
        self.runButton = AnimatedButton("开始执行")
        self.runButton.setObjectName("runButton")

        self.stopButton = AnimatedButton("停止执行")
        self.stopButton.setObjectName("stopButton")
        self.stopButton.setEnabled(False)

        layout.addWidget(self.runButton)
        layout.addWidget(self.stopButton)

        layout.addWidget(QLabel("实时日志："))
        self.logEdit = QTextEdit()
        self.logEdit.setReadOnly(True)
        layout.addWidget(self.logEdit)

        self.setLayout(layout)

        self.bridge.log_signal.connect(self.append_log)
        self.bridge.progress_signal.connect(self.progressBar.setValue)
        self.bridge.case_count_signal.connect(self.on_case_count)

        self.runButton.clicked.connect(self.start_pytest)
        self.stopButton.clicked.connect(self.stop_pytest)

        self.load_test_cases()
        self.load_markers()

    # ----------------------------------------------------------------------
    # 扫描 DTS 下所有 test 文件
    # ----------------------------------------------------------------------
    def load_test_cases(self):
        items = []

        for root, _, files in os.walk(ROOT_DIR):
            for f in files:
                if f.endswith(".py") and f != "conftest.py":
                    file_path = os.path.join(root, f)

                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        class_name = None

                        for line in fp:
                            line = line.strip()

                            if line.startswith("class ") and "Test" in line:
                                class_name = line.split("(")[0].replace("class ", "").replace(":", "")

                            if line.startswith("def test_"):
                                func_name = line.split("(")[0].replace("def ", "")
                                rel = os.path.relpath(file_path, ROOT_DIR).replace("\\", "/")

                                if class_name:
                                    items.append(f"{rel}::{class_name}::{func_name}")
                                else:
                                    items.append(f"{rel}::{func_name}")

        for it in sorted(items):
            self.caseList.addItem(QListWidgetItem(it))

    # ----------------------------------------------------------------------
    def load_markers(self):
        markers = scan_pytest_markers(ROOT_DIR)
        for m in markers:
            self.tagBox.addItem(m)

    # ----------------------------------------------------------------------
    def append_log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.logEdit.append(f"[{ts}] {msg}")
        self.logEdit.ensureCursorVisible()

    def on_case_count(self, count):
        self.total_cases = count
        self.finished_cases = 0
        self.progressBar.setValue(0)

    # ----------------------------------------------------------------------
    def start_pytest(self):
        selected_items = self.caseList.selectedItems()
        tag = self.tagBox.currentText().strip()

        if not selected_items and not tag:
            QMessageBox.warning(self, "提示", "请至少选择一个测试用例或填写标签！")
            return

        self.targets = [item.text() for item in selected_items]

        cmd = ["pytest"]

        if self.targets:
            cmd.extend(self.targets)
        else:
            cmd.append(".")

        cmd.extend(["-q", "-s", "--capture=no"])
        cmd.extend(["--alluredir", "report_ai_enhance"])

        if tag:
            cmd.extend(["-m", tag])

        self.process = QProcess(self)
        self.process.setWorkingDirectory(ROOT_DIR)

        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(self.read_output)
        self.process.finished.connect(self.on_process_finished)

        self.runButton.setEnabled(False)
        self.stopButton.setEnabled(True)

        self.bridge.log_signal.emit("开始执行 pytest ...")
        self.save_history(cmd)

        self.process.start("pytest", cmd[1:])

    # ----------------------------------------------------------------------
    def read_output(self):
        output = ""
        if self.process:
            output = self.process.readAllStandardOutput().data().decode("utf-8", "ignore")
            output += self.process.readAllStandardError().data().decode("utf-8", "ignore")

        if not output:
            return

        for line in output.splitlines():
            line = line.strip()

            if line.startswith("collected "):
                try:
                    count = int(line.split()[1])
                    self.bridge.case_count_signal.emit(count)
                except:
                    pass

            if line.startswith(("PASSED", "FAILED", "ERROR")):
                self.finished_cases += 1
                if self.total_cases > 0:
                    percent = int(self.finished_cases / self.total_cases * 100)
                    self.bridge.progress_signal.emit(percent)

            self.bridge.log_signal.emit(line)

    # ----------------------------------------------------------------------
    def on_process_finished(self):
        self.bridge.log_signal.emit("pytest 已结束")

        self.runButton.setEnabled(True)
        self.stopButton.setEnabled(False)

        self.bridge.log_signal.emit("正在打开 Allure 执行报告...")
        QProcess.startDetached(ALLURE_PATH, ["serve", "report_ai_enhance"], ROOT_DIR)

    # ----------------------------------------------------------------------
    def stop_pytest(self):
        if self.process:
            self.process.kill()
            self.bridge.log_signal.emit("⚠ pytest 已被强制终止")
        self.stopButton.setEnabled(False)

    # ----------------------------------------------------------------------
    def save_history(self, cmd):
        history = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as fp:
                history = json.load(fp)

        history.append({
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "command": " ".join(cmd),
            "targets": self.targets
        })

        with open(HISTORY_FILE, "w", encoding="utf-8") as fp:
            json.dump(history, fp, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    qss_path = os.path.join(CURRENT_DIR, "theme.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    win = MainApp()
    win.show()
    sys.exit(app.exec())
