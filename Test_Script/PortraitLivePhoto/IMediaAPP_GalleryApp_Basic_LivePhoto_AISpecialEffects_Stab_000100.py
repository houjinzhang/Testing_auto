import time
import subprocess
import pytest
import allure
import os
import sys

from allure_commons.types import AttachmentType
from appium import webdriver
from appium.options.common.base import AppiumOptions

DEVICE_SERIAL = 'AF2Q015811000014'
REPORT_DIR = "report"
os.makedirs(REPORT_DIR, exist_ok=True)
sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')

def adb_tap(x, y):
    cmd = f'adb -s {DEVICE_SERIAL} shell input tap {x} {y}'
    subprocess.run(cmd, shell=True, capture_output=True)

@pytest.fixture(scope="function")
def driver():
    options = AppiumOptions()
    options.load_capabilities({
        "platformName": "Android",
        "platformVersion": "16",
        "deviceName": "DNP_AN00",
        "appPackage": "com.hihonor.photos",
        "appActivity": "com.hihonor.gallery.app.GalleryMain",
        "newCommandTimeout": 1800,
        "noReset": True,
        "disableWindowAnimation": True
    })
    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    print(f"✅ Appium 会话已启动，Session ID: {driver.session_id}", flush=True)
    yield driver
    driver.quit()
    print("🔚 Appium 会话已关闭", flush=True)

def log_step(message):
    print(message, flush=True)
    allure.attach(message, name="步骤信息", attachment_type=AttachmentType.TEXT)

def safe_screenshot(driver, name):
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

@allure.feature("AI 编辑功能")
@allure.story("AI风格化稳定性循环测试")
def test_000100(driver):
    # # 步骤0：进入图库app
    # log_step("步骤0：进入图库app (坐标 767,1688)")
    # adb_tap(767, 1688)
    # time.sleep(1.5)

    # 步骤0.1：进入图库后点击指定区域
    log_step("步骤0.1：进入图库后点击指定区域（照片页面） (坐标 158,2530)")
    adb_tap(158, 2530)
    time.sleep(1)