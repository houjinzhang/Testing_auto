# adb_utils.py
"""
ADB 相关的通用工具函数（完全静默版）：
- 设备自动检测
- adb shell / exec-out
- 截屏 & OCR
"""

import subprocess
import io
from typing import Optional, Tuple

from PIL import Image
import pytesseract

# -------------------------------------------------
# Windows 下隐藏 adb 控制台窗口（关键）
# -------------------------------------------------
CREATE_NO_WINDOW = 0x08000000

def _run_hidden(cmd, shell=False):
    return subprocess.run(
        cmd,
        shell=shell,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        creationflags=CREATE_NO_WINDOW
    )

# -------------------------------------------------
# Tesseract 路径
# -------------------------------------------------
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# -------------------------------------------------
# 全局设备 SN
# -------------------------------------------------
DEVICE_SERIAL: Optional[str] = None


# ==============================
# DEVICE_SERIAL 管理
# ==============================

def set_device_serial(serial: Optional[str]) -> None:
    global DEVICE_SERIAL
    DEVICE_SERIAL = serial


def get_device_serial() -> Optional[str]:
    return DEVICE_SERIAL


# ==============================
# 设备自动检测（静默）
# ==============================

def auto_detect_device_base() -> Tuple[Optional[str], str, bool]:
    try:
        result = _run_hidden(
            "adb devices -l",
            shell=True
        )
    except FileNotFoundError:
        set_device_serial(None)
        return None, "未找到 adb，可执行文件不存在或未加入环境变量", False
    except Exception as e:
        set_device_serial(None)
        return None, f"执行 adb 失败: {e}", False

    lines = result.stdout.strip().splitlines()
    if not lines:
        set_device_serial(None)
        return None, "adb 无输出，请检查 adb 是否可以正常执行", False

    serial: Optional[str] = None

    for line in lines[1:]:
        parts = line.strip().split()
        if len(parts) >= 2 and parts[1] == "device":
            serial = parts[0]
            break

    if not serial:
        set_device_serial(None)
        return None, "未检测到处于 device 状态的设备，请检查连接/授权", False

    set_device_serial(serial)
    return serial, f"已检测到设备: {serial}", True


# ==============================
# ADB shell（静默）
# ==============================

def run_adb_shell_base(serial: str, command: str) -> Tuple[int, str, str]:
    result = _run_hidden(
        ["adb", "-s", serial, "shell", command]
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run_adb_shell_global(command: str) -> Tuple[int, str, str]:
    serial = get_device_serial()
    if not serial:
        return -1, "", "未检测到可用设备（DEVICE_SERIAL 未设置）"
    return run_adb_shell_base(serial, command)


# ==============================
# 截屏（exec-out，无黑框）
# ==============================

def adb_screencap_png(
    serial: Optional[str] = None
) -> Tuple[bool, Optional[bytes], str]:

    if serial is None:
        serial = get_device_serial()
    if not serial:
        return False, None, "未检测到可用设备（serial 为空）"

    try:
        proc = subprocess.run(
            ["adb", "-s", serial, "exec-out", "screencap", "-p"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
            check=False
        )
    except FileNotFoundError:
        return False, None, "未找到 adb，请确认已安装并加入环境变量"
    except Exception as e:
        return False, None, f"screencap 执行异常: {e}"

    if proc.returncode != 0 or not proc.stdout:
        err = proc.stderr.decode(errors="ignore") if proc.stderr else ""
        return False, None, f"screencap 失败: {err}"

    return True, proc.stdout, ""


# ==============================
# OCR
# ==============================

def ocr_image_bytes(
    img_bytes: bytes,
    lang: str = "chi_sim"
) -> Tuple[bool, str, str]:

    try:
        img = Image.open(io.BytesIO(img_bytes))

        if img.width > img.height:
            img = img.rotate(90, expand=True)

        text = pytesseract.image_to_string(img, lang=lang)
        return True, text, ""

    except Exception as e:
        return False, "", f"OCR 识别异常: {e}"


def ocr_detect_keyword(
    keyword: str,
    serial: Optional[str] = None,
    lang: str = "chi_sim"
) -> Optional[bool]:

    ok, png_data, err1 = adb_screencap_png(serial)
    if not ok or not png_data:
        print(f"[OCR] screencap 失败: {err1}")
        return None

    ok2, text, err2 = ocr_image_bytes(png_data, lang=lang)
    if not ok2:
        print(f"[OCR] OCR 失败: {err2}")
        return None

    clean = text.replace(" ", "").replace("\n", "")
    key_clean = keyword.replace(" ", "").replace("\n", "")
    return key_clean in clean
