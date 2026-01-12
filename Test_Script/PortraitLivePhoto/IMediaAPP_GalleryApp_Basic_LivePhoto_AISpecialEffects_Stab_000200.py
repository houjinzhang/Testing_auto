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
def test_ai_edit_stability(driver):
    # # 步骤0：进入图库app
    # log_step("步骤0：进入图库app (坐标 767,1688)")
    # adb_tap(767, 1688)
    # time.sleep(1.5)

    # 步骤0.1：进入图库后点击指定区域
    log_step("步骤0.1：进入图库后点击指定区域（照片页面） (坐标 158,2530)")
    adb_tap(158, 2530)
    time.sleep(1)

    # 步骤1：选择第一张照片
    log_step("步骤1：选择第一张照片 (坐标 212,1185)")
    adb_tap(212, 1185)
    time.sleep(1.5)

    # 步骤2：点击 AI 编辑按钮
    log_step("步骤2：点击 AI 编辑按钮 (坐标 613,2500)")
    adb_tap(613, 2500)
    time.sleep(1.0)

    # 步骤3-循环：依次点击各AI编辑功能按钮，共循环25次
    for i in range(25):
        log_step(f"--- 第 {i+1}/25 次循环 ---")
        adb_tap(130, 2476)   # 魔法修图
        time.sleep(1)
        adb_tap(344, 2434)   # 取消
        time.sleep(1)
        adb_tap(596, 2480)   # 裁剪
        time.sleep(1)
        adb_tap(815, 2473)   # 调节
        time.sleep(1)
        adb_tap(866, 2452)   # AI色彩
        time.sleep(1)
        adb_tap(196, 2479)   # 滑动到最前面（起点）
        adb_tap(859, 2550)   # 滑动到最前面（终点）
        time.sleep(1)

    # 步骤4：截图
    log_step("步骤4：循环完成后截图")
    safe_screenshot(driver, "AI风格化循环25次后截图")
