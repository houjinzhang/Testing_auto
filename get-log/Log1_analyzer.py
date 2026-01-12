import os
import re
import html
import gzip
import shutil
import subprocess
import chardet
import threading
import sys
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout,
    QFileDialog, QLabel, QLineEdit, QHBoxLayout
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QTextCursor, QIcon

MAX_FILE_SIZE = 50 * 1024 * 1024

# 统一图标路径（支持脚本运行 & PyInstaller 打包）
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后的临时目录
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ICON_PATH = os.path.join(BASE_DIR, "logtool.ico")


# ==================== 子进程封装：隐藏 Windows 下的 cmd 黑框 ====================

if os.name == "nt":
    _STARTUPINFO = subprocess.STARTUPINFO()
    _STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    _CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW
else:
    _STARTUPINFO = None
    _CREATE_NO_WINDOW = 0


def run_cmd(cmd, **kwargs):
    """
    通用封装：
    - Windows：隐藏 cmd 黑框
    - 其他平台：正常调用
    """
    if os.name == "nt":
        kwargs.setdefault("startupinfo", _STARTUPINFO)
        kwargs.setdefault("creationflags", _CREATE_NO_WINDOW)
    return subprocess.run(cmd, **kwargs)


def popen_cmd(cmd, **kwargs):
    """
    通用封装（Popen 版本）：
    - Windows：隐藏 cmd 黑框
    - 其他平台：正常调用
    """
    if os.name == "nt":
        kwargs.setdefault("startupinfo", _STARTUPINFO)
        kwargs.setdefault("creationflags", _CREATE_NO_WINDOW)
    return subprocess.Popen(cmd, **kwargs)


def detect_encoding(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read(4096)
        result = chardet.detect(data)
        return result["encoding"] or "utf-8"
    except:
        return "utf-8"


TS_PATTERNS = [
    re.compile(r'^(\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d{3})'),
    re.compile(r'^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2}(?:\.\d{3})?)'),
]


def extract_timestamp(line: str):
    s = line.lstrip()
    now_year = datetime.now().year

    for pat in TS_PATTERNS:
        m = pat.match(s)
        if not m:
            continue
        date_part, time_part = m.groups()
        try:
            if len(date_part) == 5:  # MM-DD
                dt_str = f"{now_year}-{date_part} {time_part}"
                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
            else:
                dt_str = f"{date_part} {time_part}"
                if "." in time_part:
                    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S.%f")
                else:
                    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue

    return None


def search_and_generate_html(keyword, file_list, output="log_report.html",
                             stop_event=None, log_cb=None):
    results = []

    keyword = keyword.strip()
    pattern = None    # 支持“留空 = 所有行”
    if keyword:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)

    for path in file_list:
        if stop_event and stop_event.is_set():
            if log_cb:
                log_cb("⏹ 分析被用户中断（文件循环阶段）")
            break

        enc = detect_encoding(path)
        try:
            with open(path, "r", encoding=enc, errors="ignore") as f:
                lines = f.readlines()
        except:
            continue

        for i, line in enumerate(lines, 1):
            if stop_event and stop_event.is_set():
                if log_cb:
                    log_cb(f"⏹ 分析被用户中断（读取 {path} 时）")
                break

            if (pattern is None) or pattern.search(line):
                ts = extract_timestamp(line)
                results.append({
                    "file": path,
                    "line": i,
                    "content": line.rstrip("\n"),
                    "ts": ts,
                    "idx": len(results),
                })

    if stop_event and stop_event.is_set():
        return None

    # 排序：有时间的按时间降序；无时间的排最后并保持原始顺序
    def sort_key(r):
        if r["ts"] is None:
            return (1, r["idx"])
        return (0, -r["ts"].timestamp())

    results.sort(key=sort_key)

    # 生成“记事本风格”的 HTML：单列、按时间降序、一行一条
    html_parts = [
        "<html><meta charset='utf-8'><body>",
        f"<h2>Log 扫描报告（共 {len(results)} 条）</h2>",
        f"<p>生成时间：{datetime.now()}</p>",
        "<p>排序规则：按时间降序排列（无时间戳的行排在最后，保持原始顺序）。</p>"
    ]

    if not results:
        html_parts.append("<p>未找到匹配内容</p>")
    else:
        html_parts.append("<pre>")
        for r in results:
            if r["ts"] is not None:
                ts_str = r["ts"].strftime("%m-%d %H:%M:%S.%f")[:-3]  # 保留到毫秒
            else:
                ts_str = ""

            # 一行：时间  文件:行号: 原始日志
            line_text = f"{ts_str}  {r['file']}:{r['line']}: {r['content']}"
            html_parts.append(html.escape(line_text))
        html_parts.append("</pre>")

    html_parts.append("</body></html>")

    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(html_parts))

    return output


class HilogTool(QWidget):
    log_signal = pyqtSignal(str)
    device_info_signal = pyqtSignal(str, str)
    analysis_root_signal = pyqtSignal(str)
    analysis_finished_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("多目录日志分析工具")
        self.setGeometry(600, 150, 900, 650)
        self.setWindowIcon(QIcon(ICON_PATH))  # 使用统一绝对路径图标

        # 浅色“磨砂玻璃风格”QSS
        self.setStyleSheet("""
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

        self.save_dir = ""
        self.media_dir = ""          # 截图/录屏单独目录
        self.analysis_root = ""
        self.session_dir = ""
        self.stop_event = threading.Event()
        self.selected_gz_files = []

        # 录屏状态（只用于防止并发录屏）
        self.is_recording = False

        # ==== 顶部设备信息 ====
        self.device_label = QLabel("设备：未连接")
        self.version_label = QLabel("版本：未知")
        self.device_info_btn = QPushButton("获取设备信息")
        self.device_info_btn.clicked.connect(self.refresh_device_info)

        device_layout = QHBoxLayout()
        device_layout.addWidget(self.device_label)
        device_layout.addWidget(self.version_label)
        device_layout.addStretch()
        device_layout.addWidget(self.device_info_btn)

        # ==== 日志保存目录 ====
        self.path_label = QLabel("日志保存目录：未选择")
        self.choose_save_btn = QPushButton("设置日志目录")
        self.choose_save_btn.clicked.connect(self.choose_save_dir)
        self.open_save_btn = QPushButton("打开日志目录")
        self.open_save_btn.clicked.connect(self.open_save_dir)

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_label, 1)
        path_layout.addWidget(self.choose_save_btn)
        path_layout.addWidget(self.open_save_btn)

        # ==== 截图/录屏保存目录 ====
        self.media_path_label = QLabel("截图/录屏目录：未设置（默认使用 日志目录/Media）")
        self.choose_media_btn = QPushButton("设置截图/录屏目录")
        self.choose_media_btn.clicked.connect(self.choose_media_dir)
        self.open_media_btn = QPushButton("打开截图/录屏目录")
        self.open_media_btn.clicked.connect(self.open_media_dir)

        media_layout = QHBoxLayout()
        media_layout.addWidget(self.media_path_label, 1)
        media_layout.addWidget(self.choose_media_btn)
        media_layout.addWidget(self.open_media_btn)

        # ==== ADB 操作按钮：正常 / 抠图 / 清空 ====
        self.pull_normal_btn = QPushButton("正常抓日志（含数据库 & 截图）")
        self.pull_normal_btn.clicked.connect(self.pull_logs_normal)

        self.pull_cutout_btn = QPushButton("抠图抓日志（CutOut 素材）")
        self.pull_cutout_btn.clicked.connect(self.pull_logs_cutout)

        self.clear_adb_btn = QPushButton("清空 adb 日志 (logcat + 设备目录)")
        self.clear_adb_btn.clicked.connect(self.clear_adb_logs)

        adb_btn_layout = QHBoxLayout()
        adb_btn_layout.addWidget(self.pull_normal_btn)
        adb_btn_layout.addWidget(self.pull_cutout_btn)
        adb_btn_layout.addWidget(self.clear_adb_btn)
        adb_btn_layout.addStretch()

        # ==== 截图 / 录屏操作 ====
        self.screenshot_btn = QPushButton("截图并保存")
        self.screenshot_btn.clicked.connect(self.take_screenshot)

        # === 定时录屏按钮 ===
        self.record_15s_btn = QPushButton("录屏15s")
        self.record_15s_btn.clicked.connect(lambda: self.record_fixed_duration(15))

        self.record_20s_btn = QPushButton("录屏20s")
        self.record_20s_btn.clicked.connect(lambda: self.record_fixed_duration(20))

        self.record_30s_btn = QPushButton("录屏30s")
        self.record_30s_btn.clicked.connect(lambda: self.record_fixed_duration(30))

        self.record_60s_btn = QPushButton("录屏1分钟")
        self.record_60s_btn.clicked.connect(lambda: self.record_fixed_duration(60))

        self.record_120s_btn = QPushButton("录屏2分钟")
        self.record_120s_btn.clicked.connect(lambda: self.record_fixed_duration(120))

        capture_layout = QHBoxLayout()
        capture_layout.addWidget(self.screenshot_btn)
        capture_layout.addSpacing(20)
        capture_layout.addWidget(self.record_15s_btn)
        capture_layout.addWidget(self.record_20s_btn)
        capture_layout.addWidget(self.record_30s_btn)
        capture_layout.addWidget(self.record_60s_btn)
        capture_layout.addWidget(self.record_120s_btn)
        capture_layout.addStretch()

        # ==== 选择分析文件 ====
        self.choose_analysis_btn = QPushButton("选择需要分析的 .gz 日志文件")
        self.choose_analysis_btn.clicked.connect(self.choose_gz_files)
        self.analysis_root_label = QLabel("当前分析文件：未选择")

        analysis_layout = QHBoxLayout()
        analysis_layout.addWidget(self.choose_analysis_btn)
        analysis_layout.addWidget(self.analysis_root_label, 1)

        # ==== 关键字搜索 ====
        self.keyword_input = QLineEdit()
        keyword_label = QLabel("关键字搜索（留空 = 分析所有行）：")

        keyword_layout = QHBoxLayout()
        keyword_layout.addWidget(keyword_label)
        keyword_layout.addWidget(self.keyword_input)

        # ==== 分析控制按钮 ====
        self.run_btn = QPushButton("开始分析并生成报告")
        self.run_btn.clicked.connect(self.run_analysis)
        self.stop_btn = QPushButton("停止分析")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_analysis)

        run_layout = QHBoxLayout()
        run_layout.addWidget(self.run_btn)
        run_layout.addWidget(self.stop_btn)
        run_layout.addStretch()

        # ==== 工具运行日志 ====
        log_label = QLabel("工具运行日志：")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(220)

        # ==== 主布局 ====
        main_layout = QVBoxLayout()
        main_layout.addLayout(device_layout)
        main_layout.addLayout(path_layout)
        main_layout.addLayout(media_layout)
        main_layout.addSpacing(8)
        main_layout.addLayout(adb_btn_layout)
        main_layout.addLayout(capture_layout)
        main_layout.addSpacing(10)
        main_layout.addLayout(analysis_layout)
        main_layout.addLayout(keyword_layout)
        main_layout.addLayout(run_layout)
        main_layout.addWidget(log_label)
        main_layout.addWidget(self.log)

        self.setLayout(main_layout)

        # 信号连接
        self.log_signal.connect(self._append_log)
        self.device_info_signal.connect(self._update_device_info)
        self.analysis_root_signal.connect(self._update_analysis_root_ui)
        self.analysis_finished_signal.connect(self._on_analysis_finished)

    # ==================== 公共小工具 ====================

    def _append_log(self, msg: str):
        max_blocks = 2000  # 工具日志最多保留 2000 行

        self.log.append(msg)

        doc = self.log.document()
        block_count = doc.blockCount()
        if block_count > max_blocks:
            extra = block_count - max_blocks
            cursor = self.log.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(
                QTextCursor.MoveOperation.Down,
                QTextCursor.MoveMode.KeepAnchor,
                extra
            )
            cursor.removeSelectedText()
            cursor.deleteChar()

    def _update_device_info(self, serial: str, version: str):
        self.device_label.setText(f"设备：{serial}")
        self.version_label.setText(f"版本：{version}")

    def _update_analysis_root_ui(self, path: str):
        self.analysis_root_label.setText(f"当前分析目录：{path}")

    def _on_analysis_finished(self):
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.stop_event.clear()
        # 清理解压文件
        tmp_gz_dir = "tmp_gz"
        try:
            for f in os.listdir(tmp_gz_dir):
                os.remove(os.path.join(tmp_gz_dir, f))
        except Exception:
            pass

    def log_print(self, msg):
        try:
            self.log_signal.emit(msg)
        except RuntimeError:
            pass

    def _set_record_buttons_enabled(self, enabled: bool):
        """
        统一控制录屏相关按钮启用/禁用
        """
        for btn in [
            getattr(self, "record_15s_btn", None),
            getattr(self, "record_20s_btn", None),
            getattr(self, "record_30s_btn", None),
            getattr(self, "record_60s_btn", None),
            getattr(self, "record_120s_btn", None),
        ]:
            if btn is not None:
                btn.setEnabled(enabled)

    # 统一获取 / 创建截图录屏根目录
    def _get_media_root(self):
        if self.media_dir:
            root = self.media_dir
        elif self.save_dir:
            root = os.path.join(self.save_dir, "Media")
        else:
            root = os.path.join(os.getcwd(), "Media")
        os.makedirs(root, exist_ok=True)
        return root

    def open_save_dir(self):
        if not self.save_dir:
            self.log_print("❌ 还未选择日志保存目录")
            return

        try:
            if os.name == "nt":
                os.startfile(self.save_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.save_dir])
            else:
                subprocess.run(["xdg-open", self.save_dir])
            self.log_print(f"打开保存目录：{self.save_dir}")
        except Exception as e:
            self.log_print(f"打开保存目录失败：{e}")

    def choose_media_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择截图/录屏保存目录")
        if d:
            self.media_dir = d
            self.media_path_label.setText(f"截图/录屏目录：{d}")
            self.log_print(f"设置截图/录屏目录：{d}")

    def open_media_dir(self):
        root = self._get_media_root()
        try:
            if os.name == "nt":
                os.startfile(root)
            elif sys.platform == "darwin":
                subprocess.run(["open", root])
            else:
                subprocess.run(["xdg-open", root])
            self.log_print(f"打开截图/录屏目录：{root}")
        except Exception as e:
            self.log_print(f"打开截图/录屏目录失败：{e}")

    def refresh_device_info(self):
        def worker():
            serial = "未知"
            version = "未知"
            try:
                p = run_cmd(
                    ["adb", "get-serialno"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                if p.returncode == 0:
                    s = p.stdout.strip()
                    if s and s != "unknown":
                        serial = s
            except Exception as e:
                self.log_print(f"获取设备序列号异常：{e}")

            try:
                p = run_cmd(
                    ["adb", "shell", "getprop", "ro.build.display.id"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                if p.returncode == 0 and p.stdout.strip():
                    version = p.stdout.strip()
                else:
                    p2 = run_cmd(
                        ["adb", "shell", "getprop", "ro.build.version.release"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=5
                    )
                    if p2.returncode == 0 and p2.stdout.strip():
                        version = p2.stdout.strip()
            except Exception as e:
                self.log_print(f"获取版本信息异常：{e}")

            self.device_info_signal.emit(serial, version)
            self.log_print(f"设备序列号：{serial}")
            self.log_print(f"版本信息：{version}")

        threading.Thread(target=worker, daemon=True).start()

    def choose_save_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if d:
            self.save_dir = d
            self.path_label.setText(f"日志保存目录：{d}")
            self.log_print(f"选择保存目录：{d}")

    def choose_gz_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择要分析的 .gz 文件",
            "",
            "GZ 日志文件 (*.gz)"
        )
        if files:
            self.selected_gz_files = files
            self.analysis_root_label.setText(f"已选 {len(files)} 个 .gz 日志文件")
            self.log_print(f"选择分析的 .gz 包：{files}")
        else:
            self.selected_gz_files = []
            self.analysis_root_label.setText("当前分析文件：未选择")
            self.log_print("未选择 .gz 文件")

    # ==================== 正常抓日志（对应第一个 bat） ====================

    def pull_logs_normal(self):
        if not self.save_dir:
            self.log_print("❌ 请先选择保存目录")
            return

        def worker():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_dir = os.path.join(self.save_dir, f"Logs_normal_{ts}")
            os.makedirs(self.session_dir, exist_ok=True)
            self.log_print(f"开始正常抓日志… 本次目录：{self.session_dir}")

            # adb remount
            try:
                self.log_print("执行 adb remount …")
                run_cmd(
                    ["adb", "remount"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
            except Exception as e:
                self.log_print(f"adb remount 异常：{e}")

            # 对应 bat 中 mkdir 的结构
            subdirs = [
                "dropbox", "tombstones", "corefile", "apanic", "diaglogs",
                "LogService", "archive", "database", "databases",
                "Screenshots", "android_logs", "hilogs"
            ]
            for d in subdirs:
                os.makedirs(os.path.join(self.session_dir, d), exist_ok=True)

            # 基础日志拉取
            base_pulls = [
                ("/data/log/android_logs", os.path.join("android_logs", "")),
                ("/data/tombstones", "tombstones"),
                ("/data/system/dropbox", "dropbox"),
                ("/data/log/hilogs", os.path.join("hilogs", "")),
            ]
            for src, dst in base_pulls:
                dst_path = os.path.join(self.session_dir, dst)
                self.log_print(f"[正常] 拉取 {src} → {dst_path}...")
                try:
                    run_cmd(
                        ["adb", "pull", src, dst_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                except Exception as e:
                    self.log_print(str(e))

            # adb remount 再执行一次
            try:
                self.log_print("再次执行 adb remount …")
                run_cmd(
                    ["adb", "remount"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
            except Exception as e:
                self.log_print(f"adb remount 异常：{e}")

            # 数据库 + 截图
            db_subdirs = [
                os.path.join("databases", "gallery"),
                os.path.join("databases", "media"),
                os.path.join("databases", "modulemedia"),
                os.path.join("databases", "medialibrary"),
            ]
            for d in db_subdirs:
                os.makedirs(os.path.join(self.session_dir, d), exist_ok=True)
            os.makedirs(os.path.join(self.session_dir, "Screenshots"), exist_ok=True)

            material_pulls = [
                ("/data/data/com.hihonor.photos/databases",           os.path.join("databases", "gallery")),
                ("/data/data/com.android.providers.media/databases",  os.path.join("databases", "media")),
                ("/data/data/com.android.providers.media.module/databases", os.path.join("databases", "modulemedia")),
                ("/data/data/com.hihonor.medialibrary/databases",     os.path.join("databases", "medialibrary")),
                ("/sdcard/Pictures/Screenshots",                      "Screenshots"),
            ]
            for src, dst in material_pulls:
                dst_path = os.path.join(self.session_dir, dst)
                self.log_print(f"[正常-素材] 拉取 {src} → {dst_path}...")
                try:
                    run_cmd(
                        ["adb", "pull", src, dst_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                except Exception as e:
                    self.log_print(str(e))

            self.log_print("✔ 正常抓日志完成")
            # 默认设置为当前分析目录
            self.analysis_root = self.session_dir
            self.analysis_root_signal.emit(self.analysis_root)

        threading.Thread(target=worker, daemon=True).start()

    # ==================== 抠图抓日志（对应第二个 bat） ====================

    def pull_logs_cutout(self):
        if not self.save_dir:
            self.log_print("❌ 请先选择保存目录")
            return

        def worker():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.session_dir = os.path.join(self.save_dir, f"Logs_cutout_{ts}")
            os.makedirs(self.session_dir, exist_ok=True)
            self.log_print(f"开始抠图抓日志… 本次目录：{self.session_dir}")

            # 创建目录结构（按 bat 逻辑）
            subdirs = [
                "android_logs", "hilogs", "dropbox",
                "media", "mediaModule",
                os.path.join("library", "databases"),
                os.path.join("library", "shared_prefs"),
                os.path.join("gallery", "databases"),
                os.path.join("gallery", "shared_prefs"),
                "CutOutVideo",
            ]
            for d in subdirs:
                os.makedirs(os.path.join(self.session_dir, d), exist_ok=True)

            # 基础日志
            base_pulls = [
                ("/data/log/android_logs", "android_logs"),
                ("/data/log/hilogs", "hilogs"),
                ("/data/system/dropbox", "dropbox"),
            ]
            for src, dst in base_pulls:
                dst_path = os.path.join(self.session_dir, dst)
                self.log_print(f"[抠图-基础] 拉取 {src} → {dst_path}...")
                try:
                    run_cmd(
                        ["adb", "pull", src, dst_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                except Exception as e:
                    self.log_print(str(e))

            # 数据库 + 配置 + CutOut 素材
            material_pulls = [
                # /data/user/0/... 路径
                ("/data/user/0/com.android.providers.media.module/databases",
                 "media"),
                ("/data/user/0/com.google.android.providers.media.module/databases",
                 "mediaModule"),

                # library
                ("/data/data/com.hihonor.medialibrary/databases",
                 os.path.join("library", "databases")),
                ("/data/data/com.hihonor.medialibrary/shared_prefs",
                 os.path.join("library", "shared_prefs")),

                # gallery - honor
                ("/data/data/com.hihonor.photos/databases",
                 os.path.join("gallery", "databases")),
                ("/data/data/com.hihonor.photos/shared_prefs",
                 os.path.join("gallery", "shared_prefs")),

                # gallery - huawei
                ("/data/data/com.huawei.photos/databases",
                 os.path.join("gallery", "databases")),
                ("/data/data/com.huawei.photos/shared_prefs",
                 os.path.join("gallery", "shared_prefs")),

                # CutOut 视频素材
                ("/data/data/com.hihonor.videoeditor/files/LivePhotoCache",
                 "CutOutVideo"),
            ]
            for src, dst in material_pulls:
                dst_path = os.path.join(self.session_dir, dst)
                self.log_print(f"[抠图-素材] 拉取 {src} → {dst_path}...")
                try:
                    run_cmd(
                        ["adb", "pull", src, dst_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                except Exception as e:
                    self.log_print(str(e))

            self.log_print("✔ 抠图抓日志完成")
            self.analysis_root = self.session_dir
            self.analysis_root_signal.emit(self.analysis_root)

        threading.Thread(target=worker, daemon=True).start()

    # ==================== ADB 截图并保存到“截图/录屏目录” ====================

    def take_screenshot(self):
        def worker():
            root = self._get_media_root()
            screenshots_dir = os.path.join(root, "Screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            remote_path = f"/sdcard/hilogtool_screenshot_{ts}.png"
            local_path = os.path.join(screenshots_dir, f"screenshot_{ts}.png")

            self.log_print(f"开始通过 adb 截图：{remote_path}")
            try:
                # 1. 在设备上截图
                p1 = run_cmd(
                    ["adb", "shell", "screencap", "-p", remote_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=15
                )
                if p1.returncode != 0:
                    err = p1.stderr.strip() or p1.stdout.strip()
                    self.log_print(f"❌ 截图失败：{err}")
                    return

                # 2. 把截图拉到本地目录
                self.log_print(f"拉取截图到本地：{local_path}")
                p2 = run_cmd(
                    ["adb", "pull", remote_path, local_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30
                )
                if p2.returncode != 0:
                    err = p2.stderr.strip() or p2.stdout.strip()
                    self.log_print(f"❌ 拉取截图失败：{err}")
                    return

                # 3. 删除设备上的临时截图文件（不强依赖成功）
                run_cmd(
                    ["adb", "shell", "rm", "-f", remote_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )

                self.log_print(f"✔ 截图已保存到：{local_path}")
                # 自动打开目录
                try:
                    if os.name == "nt":
                        os.startfile(screenshots_dir)
                    elif sys.platform == "darwin":
                        subprocess.run(["open", screenshots_dir])
                    else:
                        subprocess.run(["xdg-open", screenshots_dir])
                except Exception as e:
                    self.log_print(f"打开截图目录失败：{e}")
            except Exception as e:
                self.log_print(f"截图流程异常：{e}")

        threading.Thread(target=worker, daemon=True).start()

    # ==================== 定时录屏（15 / 20 / 30 / 60 / 120 秒） ====================

    def record_fixed_duration(self, seconds: int):
        """
        定时录屏：录屏指定秒数（15 / 20 / 30 / 60 / 120 等），录完自动保存并拉取到本地。
        内部会比设定值多录 2 秒，用来补偿 screenrecord 启停和封装损耗。
        """
        if self.is_recording:
            self.log_print("⚠ 当前已有录屏任务进行中，请稍后再试。")
            return

        def worker():
            self.is_recording = True
            self._set_record_buttons_enabled(False)

            root = self._get_media_root()
            record_dir = os.path.join(root, "ScreenRecords")
            os.makedirs(record_dir, exist_ok=True)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            remote_path = f"/sdcard/hilogtool_screenrecord_{seconds}s_{ts}.mp4"
            local_path = os.path.join(record_dir, f"screenrecord_{seconds}s_{ts}.mp4")

            # 实际给 screenrecord 的时间略大一点
            real_seconds = seconds + 2

            self.log_print(f"开始定时录屏 {seconds} 秒（实际 {real_seconds} 秒）：{remote_path}")
            try:
                # 使用 time-limit 参数，让设备端在指定时间后自动结束录屏
                p = run_cmd(
                    ["adb", "shell", "screenrecord", "--time-limit", str(real_seconds), remote_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=real_seconds + 30   # 留一点余量
                )

                if p.returncode != 0:
                    err = p.stderr.strip() or p.stdout.strip()
                    self.log_print(f"❌ 定时录屏失败：{err}")
                    return

                self.log_print("录屏结束，开始拉取录屏文件到本地...")
                p2 = run_cmd(
                    ["adb", "pull", remote_path, local_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=real_seconds + 120
                )
                if p2.returncode != 0:
                    err = p2.stderr.strip() or p2.stdout.strip()
                    self.log_print(f"❌ 拉取定时录屏失败：{err}")
                else:
                    self.log_print(f"✔ 定时录屏已保存到：{local_path}")
                    # 自动打开目录
                    try:
                        if os.name == "nt":
                            os.startfile(record_dir)
                        elif sys.platform == "darwin":
                            subprocess.run(["open", record_dir])
                        else:
                            subprocess.run(["xdg-open", record_dir])
                    except Exception as e:
                        self.log_print(f"打开录屏目录失败：{e}")

                # 删除设备上的临时录屏文件（不强依赖成功）
                run_cmd(
                    ["adb", "shell", "rm", "-f", remote_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
            except subprocess.TimeoutExpired:
                self.log_print("❌ 定时录屏命令超时")
            except Exception as e:
                self.log_print(f"定时录屏流程异常：{e}")
            finally:
                self.is_recording = False
                self._set_record_buttons_enabled(True)

        threading.Thread(target=worker, daemon=True).start()

    # ==================== 其他公共功能 ====================

    def clear_adb_logs(self):
        def worker():
            # 1. 清 logcat 缓冲
            self.log_print("开始清空 adb logcat...")
            try:
                p = run_cmd(
                    ["adb", "logcat", "-c"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                if p.returncode == 0:
                    self.log_print("✔ adb logcat 已清空")
                else:
                    err = p.stderr.strip() or p.stdout.strip()
                    self.log_print(f"⚠ 清空 adb 日志失败：{err}")
            except Exception as e:
                self.log_print(f"清空 adb 日志异常：{e}")
                # logcat 清空失败就不继续删文件了
                return

            # 2. 清设备上的日志文件目录内容
            self.log_print("开始清空设备日志目录内容...")

            device_dirs = {
                "android_logs": "/data/log/android_logs",
                "tombstones": "/data/tombstones",
                "dropbox": "/data/system/dropbox",
                "corefile": "/data/log/corefile",
                "apanic": "/data/log/apanic",
                "diaglogs": "/data/log/diaglogs",
                "LogService": "/data/log/LogService",
                "archive": "/data/log/archive",
                "database": "/data/log/database",
                "databases": "/data/log/databases",
                "hilogs": "/data/log/hilogs",
                # 如需清空截图，请谨慎取消注释（会删用户截图）
                # "Screenshots": "/sdcard/Pictures/Screenshots",
            }

            for name, path in device_dirs.items():
                rm_target = f"{path}/*"
                cmd = ["adb", "shell", "rm", "-rf", rm_target]
                try:
                    self.log_print(f"清空 {name} ({rm_target}) ...")
                    p = run_cmd(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        timeout=10
                    )
                    if p.returncode == 0:
                        self.log_print(f"✔ 已清空 {name}: {rm_target}")
                    else:
                        err = p.stderr.strip() or p.stdout.strip()
                        self.log_print(f"⚠ 清空 {name} 失败：{err}")
                except Exception as e:
                    self.log_print(f"清空 {name} 异常：{e}")

            self.log_print("✅ 日志缓冲 + 设备日志目录内容 已清理完成，可以重新复现问题后抓日志。")

        threading.Thread(target=worker, daemon=True).start()

    def run_analysis(self):
        if not self.selected_gz_files:
            self.log_print("❌ 请先选择要分析的 .gz 文件")
            return

        self.stop_event.clear()
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        keyword = self.keyword_input.text().strip()

        def worker():
            try:
                self.log_print(f"共选择 {len(self.selected_gz_files)} 个 .gz 文件分析")
                tmp_gz_dir = "tmp_gz"
                os.makedirs(tmp_gz_dir, exist_ok=True)
                file_list = []
                for gzfile in self.selected_gz_files:
                    out_file = os.path.join(
                        tmp_gz_dir,
                        os.path.basename(gzfile[:-3]) + f"_{abs(hash(gzfile))}.log"
                    )
                    try:
                        with gzip.open(gzfile, 'rb') as gz, open(out_file, 'wb') as out:
                            shutil.copyfileobj(gz, out)
                        file_list.append(out_file)
                        self.log_print(f"已解压 {gzfile} → {out_file}")
                    except Exception as e:
                        self.log_print(f"解压失败: {gzfile} - {e}")

                self.log_print(f"共准备 {len(file_list)} 个日志进行分析")
                output_dir = os.path.dirname(self.selected_gz_files[0]) if self.selected_gz_files else "."
                output = os.path.join(output_dir, "log_report.html")
                report = search_and_generate_html(
                    keyword,
                    file_list,
                    output,
                    stop_event=self.stop_event,
                    log_cb=self.log_print
                )

                if self.stop_event.is_set():
                    self.log_print("⏹ 分析已中断，未生成完整报告")
                    return

                if report:
                    self.log_print(f"✔ 报告已生成：{report}")
                    try:
                        os.startfile(report)
                    except Exception as e:
                        self.log_print(f"打开报告失败：{e}")
                else:
                    self.log_print("⚠ 未生成报告（没有匹配内容或被中断）")
            finally:
                self.analysis_finished_signal.emit()

        threading.Thread(target=worker, daemon=True).start()

    def stop_analysis(self):
        self.log_print("⏹ 正在请求停止分析…")
        self.stop_event.set()

    def closeEvent(self, event):
        try:
            self.stop_event.set()
        except Exception:
            pass
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication([])
    # 应用级图标（任务栏等）
    app.setWindowIcon(QIcon(ICON_PATH))

    gui = HilogTool()
    gui.show()
    app.exec()
