import sys
import os
import subprocess
import threading
import shutil
import tempfile
import locale
from typing import List

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QLineEdit, QFileDialog, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# ================= 隐藏 Windows subprocess CMD 黑框 =================
if os.name == "nt":
    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    _STARTUPINFO = None
    _CREATE_NO_WINDOW = 0


# 系统默认编码（Windows 上一般是 GBK）
DEFAULT_ENCODING = locale.getpreferredencoding(False)

# ========= 全局设备信息 =========
DEVICE_SERIAL = None
DEVICE_INFO = ""

# 默认手机相册目录、默认电脑保存目录
DEFAULT_PHONE_ALBUM_DIR = "/sdcard/DCIM/Camera"
DEFAULT_PC_SAVE_DIR = os.path.join(os.path.expanduser("~"), "PhonePhotos")

# 图标文件名（放在程序同级目录）
ICON_FILE = "logtool.ico"

# 常用手机媒体目录，用于下拉框初始化和刷新，会尝试列出这些目录下的子目录
COMMON_PHONE_MEDIA_ROOTS = [
    "/sdcard/DCIM",
    "/sdcard/Pictures",
    "/sdcard/Download",
    "/sdcard"
]

# ======== 简单样式（可自行美化）=======
APP_QSS = ("""
            QWidget {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 240),
                    stop:1 rgba(235, 240, 245, 240)
                );
                color: #333333;
                font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI";
                font-size: 10pt;
            }
            QLabel {
                color: #333333;
            }
            QTextEdit, QLineEdit {
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid rgba(0, 0, 0, 40);
                border-radius: 6px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid rgba(0, 0, 0, 40);
                border-radius: 6px;
                padding: 4px 10px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 255);
            }
            QPushButton:pressed {
                background-color: rgba(220, 230, 240, 255);
            }
        """)


def resource_path(relative_path: str) -> str:
    """
    获取资源文件的真实路径，兼容 PyInstaller 打包后环境
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def auto_detect_device():
    """
    自动检测第一个处于 device 状态的设备：
    - 设置全局 DEVICE_SERIAL
    - 设置全局 DEVICE_INFO（product/model）
    """
    global DEVICE_SERIAL, DEVICE_INFO
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            shell=False,
            capture_output=True,
            text=True,
            encoding=DEFAULT_ENCODING,
            errors="ignore",
            check=False
        )
    except FileNotFoundError:
        DEVICE_SERIAL = None
        DEVICE_INFO = "错误: 未找到 adb，请确认已安装并加入环境变量"
        return
    except Exception as e:
        DEVICE_SERIAL = None
        DEVICE_INFO = f"错误: 执行 adb 失败: {e}"
        return

    lines = result.stdout.strip().splitlines()
    if not lines:
        DEVICE_SERIAL = None
        DEVICE_INFO = "错误: adb 无输出，请检查 adb 状态"
        return

    # 跳过第一行 "List of devices attached"
    serial = None
    info = ""
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        state = parts[1]
        if state != "device":
            continue
        serial = parts[0]

        model = ""
        product = ""
        for p in parts[2:]:
            if p.startswith("model:"):
                model = p[len("model:"):]
            elif p.startswith("product:"):
                product = p[len("product:"):]
        if model or product:
            info_list = []
            if model:
                info_list.append(f"model={model}")
            if product:
                info_list.append(f"product={product}")
            info = ", ".join(info_list)
        break

    DEVICE_SERIAL = serial
    if serial is None:
        DEVICE_INFO = "错误: 未检测到处于 device 状态的设备，请检查连接/授权"
    else:
        DEVICE_INFO = info if info else "设备信息未知"


def run_adb(args: List[str]):
    """
    执行一个 adb 命令（不带 adb 前缀），基于全局 DEVICE_SERIAL。
    例如: run_adb(["pull", "/sdcard/DCIM/Camera", "C:/Users/A/PhonePhotos"])
    返回: (returncode, stdout+stderr_str)
    """
    if not DEVICE_SERIAL:
        return -1, "错误: 未检测到设备序列号，请先连接设备并确认 adb devices 可识别"

    full_cmd = ["adb", "-s", DEVICE_SERIAL] + args
    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            encoding=DEFAULT_ENCODING,
            errors="ignore",
            check=False
        )
        out = (result.stdout or "") + (("\n" + result.stderr) if result.stderr else "")
        return result.returncode, out.strip()
    except FileNotFoundError:
        return -1, "错误: 未找到 adb，请确认已安装并加入环境变量"
    except Exception as e:
        return -1, f"未知错误: {e}"


def _get_phone_subdirs(parent_path: str) -> List[str]:
    """
    通过 adb 获取指定路径下的子目录列表。
    返回绝对路径列表，例如 /sdcard/DCIM/Camera
    """
    if not DEVICE_SERIAL:
        return []

    cmd = ["shell", "ls", "-F", parent_path]
    code, output = run_adb(cmd)

    subdirs = []
    if code == 0 and output:
        for line in output.splitlines():
            line = line.strip()
            if line.endswith('/') and line not in ('.', '..'):
                full_path = os.path.join(parent_path, line).rstrip('/')
                subdirs.append(full_path)
    return subdirs


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("相册推送工具（手机 ↔ 电脑）")

        # 设置窗口图标
        icon_path = resource_path(ICON_FILE)
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setMinimumSize(700, 430)
        self.setStyleSheet(APP_QSS)

        self._build_ui()

        # 自动检测设备
        auto_detect_device()
        self._after_detect_device()

    def _build_ui(self):
        layout = QVBoxLayout()

        # ===== 顶部：设备信息 & 重新检测按钮 =====
        top_bar = QHBoxLayout()
        self.device_label = QLabel("设备: 未检测")
        top_bar.addWidget(self.device_label)

        self.btn_refresh_device = QPushButton("重新检测设备")
        self.btn_refresh_device.clicked.connect(self.on_refresh_device_clicked)
        top_bar.addWidget(self.btn_refresh_device)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        # ===== 一、手机 → 电脑 =====
        phone_to_pc_box = QVBoxLayout()
        phone_to_pc_box.addWidget(QLabel("一、从手机相册拉取到电脑"))

        # 手机相册目录 (下拉框 + 刷新按钮)
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("手机相册目录:"))
        self.phone_pull_dir_combo = QComboBox()
        self.phone_pull_dir_combo.setEditable(True)
        self.phone_pull_dir_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.phone_pull_dir_combo.setMinimumWidth(350)
        self.phone_pull_dir_combo.addItem(DEFAULT_PHONE_ALBUM_DIR)
        h1.addWidget(self.phone_pull_dir_combo)

        self.btn_refresh_phone_dirs = QPushButton("刷新手机目录")
        self.btn_refresh_phone_dirs.clicked.connect(self.on_refresh_phone_dirs_clicked)
        h1.addWidget(self.btn_refresh_phone_dirs)

        phone_to_pc_box.addLayout(h1)

        # 电脑保存目录 + 打开目录按钮
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("电脑保存目录:"))
        self.pc_save_dir_edit = QLineEdit(DEFAULT_PC_SAVE_DIR)
        h2.addWidget(self.pc_save_dir_edit)
        self.btn_choose_pc_dir = QPushButton("选择目录")
        self.btn_choose_pc_dir.clicked.connect(self.choose_pc_dir)
        h2.addWidget(self.btn_choose_pc_dir)

        self.btn_open_pc_dir = QPushButton("打开目录")
        self.btn_open_pc_dir.clicked.connect(self.on_open_pc_dir_clicked)
        h2.addWidget(self.btn_open_pc_dir)

        phone_to_pc_box.addLayout(h2)

        # 按钮
        self.btn_pull_photos = QPushButton("从手机相册拉取到电脑")
        self.btn_pull_photos.clicked.connect(self.on_pull_photos_clicked)
        phone_to_pc_box.addWidget(self.btn_pull_photos)

        layout.addLayout(phone_to_pc_box)
        layout.addSpacing(10)

        # ===== 二、电脑 → 手机（文件夹 = 相册） =====
        pc_folder_to_phone_box = QVBoxLayout()
        pc_folder_to_phone_box.addWidget(QLabel("二、从电脑推送整个文件夹到手机（作为一个相册）"))

        # 手机相册根目录 (下拉框)
        h5_root = QHBoxLayout()
        h5_root.addWidget(QLabel("手机相册根目录:"))
        self.phone_target_root_combo = QComboBox()
        self.phone_target_root_combo.setEditable(True)
        self.phone_target_root_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.phone_target_root_combo.setMinimumWidth(350)
        self.phone_target_root_combo.addItem(DEFAULT_PHONE_ALBUM_DIR)
        h5_root.addWidget(self.phone_target_root_combo)
        pc_folder_to_phone_box.addLayout(h5_root)

        # 电脑相册文件夹 + 按钮
        h5 = QHBoxLayout()
        self.pc_album_dir_edit = QLineEdit()
        self.pc_album_dir_edit.setPlaceholderText("选择电脑上的相册文件夹，例如 D:/Pictures/Trip2025")
        h5.addWidget(self.pc_album_dir_edit)

        self.btn_choose_album_dir = QPushButton("选择文件夹")
        self.btn_choose_album_dir.clicked.connect(self.choose_pc_album_dir)
        h5.addWidget(self.btn_choose_album_dir)

        self.btn_push_album_dir = QPushButton("推送文件夹到手机相册")
        self.btn_push_album_dir.clicked.connect(self.on_push_album_dir_clicked)
        h5.addWidget(self.btn_push_album_dir)

        pc_folder_to_phone_box.addLayout(h5)

        layout.addLayout(pc_folder_to_phone_box)
        layout.addSpacing(10)

        # ===== 日志区域 =====
        layout.addWidget(QLabel("日志输出:"))
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        layout.addWidget(self.log_edit)

        self.setLayout(layout)

    # ========== UI 辅助 ==========
    def log(self, msg: str):
        self.log_edit.append(msg)
        self.log_edit.ensureCursorVisible()

    def _after_detect_device(self):
        """
        根据当前 DEVICE_SERIAL / DEVICE_INFO 更新：
        - 顶部设备信息标签
        - 按钮启用/禁用状态
        - 如有设备则刷新一次手机目录
        """
        global DEVICE_SERIAL, DEVICE_INFO

        if DEVICE_SERIAL:
            self.device_label.setText(f"设备: {DEVICE_SERIAL} ({DEVICE_INFO})")
            self.log("[INFO] 已检测到设备。")
            self.log(f"- SN: {DEVICE_SERIAL}")
            self.log(f"- 信息: {DEVICE_INFO}")

            # 启用与设备相关的按钮
            self.btn_pull_photos.setEnabled(True)
            self.btn_push_album_dir.setEnabled(True)
            self.btn_refresh_phone_dirs.setEnabled(True)

            # 自动刷新一次手机目录
            self._populate_phone_dir_combos()
        else:
            self.device_label.setText("设备: 未检测到，请检查连接/授权")
            self.log(f"<font color='#FF0000'>- {DEVICE_INFO}</font>")

            # 禁用与设备相关的按钮
            self.btn_pull_photos.setEnabled(False)
            self.btn_push_album_dir.setEnabled(False)
            self.btn_refresh_phone_dirs.setEnabled(False)

    # 重新检测设备按钮事件
    def on_refresh_device_clicked(self):
        self.log("[REFRESH] 正在重新检测设备...")
        auto_detect_device()
        self._after_detect_device()

    # ========== 打开电脑目录 ==========
    def _open_pc_dir(self, path: str):
        """
        在系统文件管理器中打开指定目录（跨平台）。
        """
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            self.log(f"<font color='#FF0000'>错误: 目录不存在: {path}</font>")
            return

        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
            self.log(f"[OPEN] 已打开电脑目录: {path}")
        except Exception as e:
            self.log(f"<font color='#FF0000'>[ERR] 打开目录失败: {e}</font>")

    def on_open_pc_dir_clicked(self):
        dir_path = self.pc_save_dir_edit.text().strip()
        if not dir_path:
            self.log("<font color='#FF0000'>错误: 电脑保存目录为空</font>")
            return
        self._open_pc_dir(dir_path)

    # ========== 获取并填充手机目录到下拉框 ==========
    def _collect_phone_dirs(self) -> List[str]:
        all_dirs = set()
        all_dirs.add(DEFAULT_PHONE_ALBUM_DIR)

        for root in COMMON_PHONE_MEDIA_ROOTS:
            all_dirs.add(root)
            subdirs = _get_phone_subdirs(root)
            for d in subdirs:
                all_dirs.add(d)

        return sorted(all_dirs)

    def _populate_phone_dir_combos(self):
        if not DEVICE_SERIAL:
            return

        self.log("[REFRESH] 正在从手机获取目录列表，请稍候...")
        dirs = self._collect_phone_dirs()

        if not dirs:
            self.log("<font color='#FF0000'>[WARN] 未获取到任何目录，请检查手机存储访问权限</font>")
            return

        # 更新“手机相册目录”
        self.phone_pull_dir_combo.blockSignals(True)
        self.phone_pull_dir_combo.clear()
        self.phone_pull_dir_combo.addItems(dirs)
        if DEFAULT_PHONE_ALBUM_DIR in dirs:
            self.phone_pull_dir_combo.setCurrentText(DEFAULT_PHONE_ALBUM_DIR)
        self.phone_pull_dir_combo.blockSignals(False)

        # 更新“手机相册根目录”
        self.phone_target_root_combo.blockSignals(True)
        self.phone_target_root_combo.clear()
        self.phone_target_root_combo.addItems(dirs)
        if DEFAULT_PHONE_ALBUM_DIR in dirs:
            self.phone_target_root_combo.setCurrentText(DEFAULT_PHONE_ALBUM_DIR)
        self.phone_target_root_combo.blockSignals(False)

        self.log(f"[OK] 手机目录刷新完成，共 {len(dirs)} 条")

    def on_refresh_phone_dirs_clicked(self):
        if not DEVICE_SERIAL:
            self.log("<font color='#FF0000'>错误: 未检测到设备，无法刷新目录</font>")
            return
        self._populate_phone_dir_combos()

    # ========== 选择电脑目录 ==========
    def choose_pc_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "选择电脑保存目录", self.pc_save_dir_edit.text() or os.getcwd()
        )
        if directory:
            self.pc_save_dir_edit.setText(directory)

    def choose_pc_album_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self, "选择要作为相册推送的文件夹", os.getcwd()
        )
        if directory:
            self.pc_album_dir_edit.setText(directory)

    # ========== 按钮事件：手机 → 电脑 ==========
    def on_pull_photos_clicked(self):
        phone_dir = self.phone_pull_dir_combo.currentText().strip()
        pc_dir = self.pc_save_dir_edit.text().strip()

        if not DEVICE_SERIAL:
            self.log("<font color='#FF0000'>错误: 未检测到设备，无法拉取相册</font>")
            return
        if not phone_dir:
            self.log("<font color='#FF0000'>错误: 手机相册目录不能为空</font>")
            return
        if not pc_dir:
            self.log("<font color='#FF0000'>错误: 电脑保存目录不能为空</font>")
            return

        os.makedirs(pc_dir, exist_ok=True)

        t = threading.Thread(
            target=self._pull_photos_thread,
            args=(phone_dir, pc_dir),
            daemon=True
        )
        t.start()

    def _pull_photos_thread(self, phone_dir: str, pc_dir: str):
        self.log(f"[PULL] 开始从手机目录 {phone_dir} 拉取到电脑目录 {pc_dir}")
        cmd = ["pull", phone_dir, pc_dir]
        code, out = run_adb(cmd)
        if code == 0:
            self.log("[OK] 相册拉取完成，正在打开电脑保存目录...")
            self._open_pc_dir(pc_dir)
        else:
            self.log(f"<font color='#FF0000'>[ERR] 拉取失败(返回码 {code}): {out}</font>")

    # ========== 按钮事件：电脑 → 手机（文件夹 = 相册） ==========
    def on_push_album_dir_clicked(self):
        if not DEVICE_SERIAL:
            self.log("<font color='#FF0000'>错误: 未检测到设备，无法推送文件夹</font>")
            return

        phone_target_root = self.phone_target_root_combo.currentText().strip()
        if not phone_target_root:
            self.log("<font color='#FF0000'>错误: 手机目标目录不能为空</font>")
            return

        pc_album_dir = self.pc_album_dir_edit.text().strip()
        if not pc_album_dir:
            self.log("<font color='#FF0000'>错误: 还未选择要推送的文件夹</font>")
            return

        if not os.path.isdir(pc_album_dir):
            self.log(f"<font color='#FF0000'>错误: 文件夹不存在: {pc_album_dir}</font>")
            return

        t = threading.Thread(
            target=self._push_album_dir_thread,
            args=(pc_album_dir, phone_target_root),
            daemon=True
        )
        t.start()

    def _push_album_dir_thread(self, pc_album_dir, phone_target_root):
        album_name = os.path.basename(os.path.normpath(pc_album_dir))
        phone_target_root = phone_target_root.rstrip("/")
        phone_album_parent = phone_target_root
        phone_album_dir = f"{phone_album_parent}/{album_name}"

        self.log(f"[PUSH] 开始推送文件夹 '{pc_album_dir}' 到手机 '{phone_album_parent}'")
        self.log(f"--> 手机上将生成相册目录: {phone_album_dir}")

        # 先确保父目录存在
        adb_mkdir_cmd = ["shell", "mkdir", "-p", phone_album_parent]
        run_adb(adb_mkdir_cmd)

        # 处理本地路径包含中文/特殊字符的情况：复制到临时英文目录再推送
        pc_src_dir = pc_album_dir
        temp_root = None

        # 如果本地路径中包含非 ASCII 字符，则复制到临时目录
        if not all(ord(c) < 128 for c in pc_album_dir):
            try:
                temp_root = tempfile.mkdtemp(prefix="adb_album_")
                pc_src_dir = os.path.join(temp_root, album_name)
                shutil.copytree(pc_album_dir, pc_src_dir)
                self.log(f"[WARN] 检测到本地路径包含中文/特殊字符，已复制到临时目录: {pc_src_dir}")
            except Exception as e:
                self.log(f"<font color='#FF0000'>[ERR] 创建临时目录或拷贝文件失败: {e}</font>")
                return

        # 正式执行 adb push
        cmd = ["push", pc_src_dir, phone_album_parent + "/"]
        code, out = run_adb(cmd)

        # 清理临时目录
        if temp_root:
            try:
                shutil.rmtree(temp_root, ignore_errors=True)
            except Exception:
                pass

        if code == 0:
            self.log(f"[OK] 文件夹推送完成，相册 '{album_name}' 已同步到手机")
        else:
            self.log(f"<font color='#FF0000'>[ERR] 文件夹推送失败(返回码 {code}): {out}</font>")


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 设置应用图标（任务栏等）
    icon_path = resource_path(ICON_FILE)
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    w = MainWindow()
    w.show()
    sys.exit(app.exec())
