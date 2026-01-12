import time
import subprocess
import pytest
import allure
import os
import sys

from allure_commons.types import AttachmentType
from appium import webdriver
from appium.options.common.base import AppiumOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# 配置设备序列号
DEVICE_SERIAL = 'A6RV015322000050'

# 自动创建 allure 报告目录
REPORT_DIR = "../report"
os.makedirs(REPORT_DIR, exist_ok=True)

sys.stdout.reconfigure(line_buffering=True)


def adb_tap(x, y):
    """使用 ADB 执行点击命令，速度远快于 Appium"""
    cmd = f'adb -s {DEVICE_SERIAL} shell input tap {x} {y}'
    subprocess.run(cmd, shell=True, capture_output=True)


def adb_swipe(x1, y1, x2, y2, duration=1000):
    """使用 ADB 执行滑动命令"""
    cmd = f'adb -s {DEVICE_SERIAL} shell input swipe {x1} {y1} {x2} {y2} {duration}'
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
        "newCommandTimeout": 600,
        "noReset": True
    })
    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    yield driver
    driver.quit()

def check_text_exists(text):
    """
    检查当前界面是否包含指定文字
    """
    # 导出当前界面布局到 /sdcard
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell uiautomator dump /sdcard/view.xml", shell=True, capture_output=True)
    # 拉取到本地
    subprocess.run(f"adb -s {DEVICE_SERIAL} pull /sdcard/view.xml ./view.xml", shell=True, capture_output=True)

    # 读取 XML 文件并查找文字
    try:
        with open("../view.xml", "r", encoding="utf-8") as f:
            xml_content = f.read()
        return text in xml_content
    except FileNotFoundError:
        return False
def step_1_add_modified_image():
    """
    在笔记中添加照片，然后进入照片大图进行保存或分享
    """
    print("📌 Step 1: 开始在笔记中添加照片并进入大图模式...")

    # 回到首页
    adb_tap(594, 2687)
    time.sleep(1.5)

    # 打开笔记（笔记要放在图库正下面）
    adb_tap(751, 2015)
    time.sleep(1.5)

    # 点击新建笔记
    adb_tap(617, 2438)
    time.sleep(3)

    # 点击添加
    adb_tap(895, 1579)
    time.sleep(1.5)

    # 从图库中选择
    adb_tap(197, 1717)
    time.sleep(1.5)

    # 选择第一张照片
    adb_tap(241, 711)
    time.sleep(2)

    # 点击添加到笔记
    adb_tap(1060, 2157)
    time.sleep(3)

    # 点击中间进入图库大图模式
    adb_tap(588, 1081)
    time.sleep(1.5)

    # 选中主题（长按）
    os.system("adb shell input swipe 733 1343 733 1343 800")
    time.sleep(1.5)

    # 保存
    adb_tap(568, 1817)
    time.sleep(1.5)

    # 分享
    adb_tap(749, 1828)
    time.sleep(2.5)
    #点4次返回3262685
    for _ in range(4):
        adb_tap(326, 2685)
        time.sleep(1)  # 如果需要点击之间有间隔

    # 回到首页
    adb_tap(652, 2684)
    time.sleep(1.5)

    print("✅ Step 1 完成：已在笔记中添加照片并进入大图模式进行保存或分享")


def step_2_delete_saved_photo(driver, first_time=True):
    """
    第二步：进入图库并删除第一张已保存的照片
    first_time=True 表示第一次循环，需要进入相册页并选中抠图相册
    """
    print("📌 Step 2: 开始删除已保存的照片...")

    # 回到首页
    adb_tap(652, 2684)
    time.sleep(1.5)

    # 进入图库
    adb_tap(772, 1706)
    time.sleep(1.5)

    if first_time:
        # 点击相册页
        adb_tap(915, 1937)
        time.sleep(1.5)

        # 选中抠图相册
        adb_tap(914, 1930)
        time.sleep(1.5)

    # 选中第一张照片（长按）
    os.system("adb shell input swipe 217 683 217 683 800")
    time.sleep(1.5)

    # 点击删除按钮
    adb_tap(873, 2490)
    time.sleep(1.5)

    # 确认删除
    adb_tap(902, 2404)
    time.sleep(1.5)

    print("✅ Step 2 完成：已删除第一张已保存的照片")


def test_5(driver):
    loops = 200
    for i in range(loops):
        print(f"\n🔄 循环 {i + 1}/{loops} 开始")

        # 第一步：添加照片并保存/分享
        step_1_add_modified_image()

        # 第二步：第一次循环需要进入相册页，后面直接删除
        step_2_delete_saved_photo(driver, first_time=(i == 0))

        print(f"✅ 循环 {i + 1}/{loops} 完成")
        time.sleep(1)





