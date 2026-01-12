# conftest.py
import os, sys, time, subprocess, math, datetime
import pytest, allure
from contextlib import contextmanager
from allure_commons.types import AttachmentType
from appium import webdriver
from appium.options.common.base import AppiumOptions
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from adb_utils import run_adb_shell_base, auto_detect_device_base, ocr_detect_keyword

# ================= 基准分辨率 =================
BASE_WIDTH, BASE_HEIGHT = 2736, 1264
DEVICE_SERIAL, DEVICE_INFO = None, ""


# ================= 环境 =================
@pytest.fixture(scope="session", autouse=True)
def env_config():
    global DEVICE_SERIAL, DEVICE_INFO
    serial, msg, ok = auto_detect_device_base()
    if not ok:
        pytest.exit(msg, 1)

    DEVICE_SERIAL = serial
    _, ver, _ = run_adb_shell_base(serial, "getprop ro.build.version.release")
    _, model, _ = run_adb_shell_base(serial, "getprop ro.product.model")
    DEVICE_INFO = f"model={model}"

    os.makedirs("./report", exist_ok=True)
    sys.stdout.reconfigure(line_buffering=True, encoding="utf-8")
    print(f"[env] {serial} Android={ver} {model}", flush=True)

    return dict(
        DEVICE_SERIAL=serial,
        PLATFORM_VERSION=ver,
        DEVICE_NAME=model,
        REPORT_DIR="./report"
    )


# ================= 工具 =================
@pytest.fixture(scope="session")
def log_step():
    return lambda m, n="步骤": (
        print(m, flush=True),
        allure.attach(m, name=n, attachment_type=AttachmentType.TEXT)
    )


def adapt_xy(x, y, rw, rh):
    return int(x * rw / BASE_WIDTH), int(y * rh / BASE_HEIGHT)


@pytest.fixture(scope="session")
def screen_size(adb_shell_command):
    w, h = adb_shell_command("wm size").split()[-1].split("x")
    return int(w), int(h)


@pytest.fixture(scope="session")
def adb_shell_command(env_config, log_step):
    sn = env_config["DEVICE_SERIAL"]

    def run(cmd, desc="ADB", sleep=0.8):
        log_step(f"{desc}: {cmd}")
        c, o, e = run_adb_shell_base(sn, cmd)
        if c:
            pytest.fail(e)
        time.sleep(sleep)
        return o

    return run


# ================= NEW：动作耗时统计 =================
@contextmanager
def action_timer(name: str):
    start = time.time()
    yield
    cost = round(time.time() - start, 2)
    print(f"[PERF] {name:<20} {cost}s")
    try:
        allure.attach(
            f"{name} 耗时 {cost}s",
            name=f"PERF - {name}",
            attachment_type=AttachmentType.TEXT
        )
    except Exception:
        pass


# ================= NEW：智能等待 =================
def _wait_text_disappear(keyword, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        if not ocr_detect_keyword(keyword):
            return
        time.sleep(1)
    pytest.fail(f"等待「{keyword}」消失超时")


def smart_wait_by_desc(desc: str):
    d = desc.replace(" ", "")
    if any(k in d for k in ("AI", "智能", "抠图", "生成")):
        _wait_text_disappear("处理中", 40)
    elif any(k in d for k in ("保存", "完成")):
        _wait_text_disappear("保存", 20)
    else:
        time.sleep(0.8)


# ================= ADB 操作（增强但不破坏） =================
@pytest.fixture(scope="session")
def adb_tap(adb_shell_command, screen_size):
    rw, rh = screen_size

    def tap(x, y, d="点击", s=None, retry=2):
        ax, ay = adapt_xy(x, y, rw, rh)
        cmd = f"input tap {ax} {ay}"
        for _ in range(retry + 1):
            try:
                with action_timer(d):
                    adb_shell_command(cmd, f"{d} ({x},{y})", sleep=0)
                    if s is not None:
                        time.sleep(s)
                    else:
                        smart_wait_by_desc(d)
                return
            except Exception:
                time.sleep(0.5)
        pytest.fail(f"{d} 失败")

    return tap


@pytest.fixture(scope="session")
def adb_long_press(adb_shell_command, screen_size):
    rw, rh = screen_size

    def run(x, y, t=600, d="长按", s=None):
        ax, ay = adapt_xy(x, y, rw, rh)
        cmd = f"input swipe {ax} {ay} {ax} {ay} {t}"
        with action_timer(d):
            adb_shell_command(cmd, d, sleep=0)
            if s is not None:
                time.sleep(s)
            else:
                smart_wait_by_desc(d)

    return run


# ================= W3C 通用（原样保留） =================
def w3c_fingers(driver, count):
    act = ActionBuilder(driver)
    return act, [act.add_pointer_input("touch", f"finger{i}") for i in range(count)]


# ================= W3C 画圈（增强） =================
@pytest.fixture(scope="session")
def w3c_draw_circle(screen_size):
    rw, rh = screen_size

    def run(driver, cx, cy, r=120, steps=12, dur=600, retry=1):
        with action_timer("画圈选区"):
            for _ in range(retry + 1):
                act, (f,) = w3c_fingers(driver, 1)
                f.create_pointer_move(0, *adapt_xy(cx + r, cy, rw, rh))
                f.create_pointer_down(0)
                for i in range(1, steps + 1):
                    x = cx + r * math.cos(2 * math.pi * i / steps)
                    y = cy + r * math.sin(2 * math.pi * i / steps)
                    f.create_pointer_move(dur // steps, *adapt_xy(x, y, rw, rh))
                f.create_pointer_up(0)
                act.perform()

                if ocr_detect_keyword("已选中"):
                    return
                time.sleep(0.6)

        pytest.fail("画圈后未识别成功")

    return run

# ================= NEW：页面前置恢复 =================
def _force_back_home(sn):
    for _ in range(5):
        run_adb_shell_base(sn, "input keyevent 4")
        time.sleep(0.2)
    run_adb_shell_base(sn, "input keyevent 3")
    time.sleep(0.5)


def ensure_gallery_home(sn):
    _force_back_home(sn)
    run_adb_shell_base(
        sn, "am start -n com.hihonor.photos/.GalleryMain"
    )
    time.sleep(2)


@pytest.fixture(scope="function", autouse=True)
def ensure_clean_state(env_config):
    sn = env_config["DEVICE_SERIAL"]
    ensure_gallery_home(sn)
    yield
    _force_back_home(sn)


# ================= Appium Driver（原样保留） =================
@pytest.fixture(scope="session")
def driver(env_config):
    options = AppiumOptions()
    options.set_capability("platformName", "Android")
    options.set_capability("deviceName", env_config["DEVICE_NAME"])
    options.set_capability("udid", env_config["DEVICE_SERIAL"])
    options.set_capability("automationName", "UiAutomator2")
    options.set_capability("noReset", True)

    driver = webdriver.Remote(
        command_executor="http://127.0.0.1:4723/wd/hub",
        options=options
    )
    yield driver
    driver.quit()
