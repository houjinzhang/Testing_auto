import time
import subprocess
import pytest
import allure
import os
import sys
from PIL import Image
from allure_commons.types import AttachmentType
from appium import webdriver
from appium.options.common.base import AppiumOptions

DEVICE_SERIAL = 'A6RV015322000050'
REPORT_DIR = "../report"
os.makedirs(REPORT_DIR, exist_ok=True)
sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')


def adb_tap(x, y):
    """使用 ADB 执行点击命令"""
    cmd = f'adb -s {DEVICE_SERIAL} shell input tap {x} {y}'
    subprocess.run(cmd, shell=True, capture_output=True)


def adb_swipe(x1, y1, x2, y2, duration=1000):
    """使用 ADB 执行滑动命令"""
    cmd = f'adb -s {DEVICE_SERIAL} shell input swipe {x1} {y1} {x2} {y2} {duration}'
    subprocess.run(cmd, shell=True, capture_output=True)


@pytest.fixture(scope="function")
def driver():
    """初始化 Appium driver"""
    options = AppiumOptions()
    options.load_capabilities({
        "platformName": "Android",
        "platformVersion": "16",
        "deviceName": "DNP_AN00",
        "appPackage": "com.hihonor.photos",
        "appActivity": "com.hihonor.gallery.app.GalleryMain",
        "newCommandTimeout": 3600,
        "noReset": True
    })
    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    print(f"✅ Appium 会话已启动，Session ID: {driver.session_id}", flush=True)
    yield driver
    driver.quit()
    print("🔚 Appium 会话已关闭", flush=True)


def log_step(message):
    """双输出：控制台 + Allure 报告"""
    print(message, flush=True)
    allure.attach(message, name="步骤信息", attachment_type=AttachmentType.TEXT)


def safe_screenshot(driver, name):
    """安全截图"""
    try:
        if driver.session_id:
            png_data = driver.get_screenshot_as_png()
            allure.attach(png_data, name=name, attachment_type=AttachmentType.PNG)
            print(f"📸 截图完成：{name}", flush=True)
        else:
            msg = "⚠️ 会话已失效，无法截图"
            print(msg, flush=True)
            allure.attach(msg, name=f"{name}-截图失败", attachment_type=AttachmentType.TEXT)
    except Exception as e:
        print(f"⚠️ 截图失败：{e}", flush=True)
        allure.attach(str(e), name=f"{name}-截图异常", attachment_type=AttachmentType.TEXT)


def save_adb_log(filename="adb_log.txt"):
    """抓取当前设备的 ADB 日志"""
    log_path = os.path.join(REPORT_DIR, filename)
    cmd = f"adb -s {DEVICE_SERIAL} logcat -d > {log_path}"
    subprocess.run(cmd, shell=True)
    print(f"📄 ADB 日志已保存：{log_path}", flush=True)

    # 附加到 Allure 报告
    try:
        with open(log_path, "rb") as f:
            allure.attach(f.read(), name="ADB日志", attachment_type=AttachmentType.TEXT)
    except Exception as e:
        print(f"⚠️ 附加ADB日志失败：{e}", flush=True)


def test_4(driver):
    log_step("点击进入相册")
    adb_tap(155, 2470)
    time.sleep(0.8)

    log_step("点击第一张照片")
    adb_tap(194, 1180)
    time.sleep(0.8)

    target_package = "com.hihonor.photos"  # 只检测这个包名
    total_loops = 500

    for i in range(total_loops):
        log_step(f"第 {i + 1} 次循环：进入编辑并退出")
        adb_tap(611, 2510)  # 进入编辑
        time.sleep(0.5)
        adb_tap(107, 208)   # 退出编辑
        time.sleep(0.5)

        # 每 100 次循环时，截图 + 检测
        if (i + 1) % 100 == 0:
            log_step(f"⏳ 第 {i + 1} 次循环：等待 3 秒后截图并检测当前页面")
            time.sleep(3)

            # 截图
            safe_screenshot(driver, f"loop_{i+1}_current_page")

            # 获取当前前台 App 包名
            current_package = driver.current_package
            log_step(f"当前前台包名：{current_package}")

            # 只在目标 App 内检测
            if current_package == target_package:
                page_xml = driver.page_source
                if "笔记" in page_xml:
                    # 抓取 ADB 日志
                    save_adb_log(f"adb_log_loop_{i+1}.txt")
                    pytest.fail(f"❌ 流程错误：第 {i + 1} 次检测到‘笔记’字样", pytrace=False)
                else:
                    log_step("✅ 当前页面未检测到‘笔记’，继续执行")
            else:
                log_step("⚠️ 当前不在目标 App，跳过检测")

