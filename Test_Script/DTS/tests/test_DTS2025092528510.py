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
DEVICE_SERIAL = 'AYAT015313000099'

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
        "deviceName": "DNN_AN00",
        "appPackage": "com.hihonor.photos",
        "appActivity": "com.hihonor.gallery.app.GalleryMain",
        "newCommandTimeout": 600,
        "noReset": True
    })
    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    yield driver
    driver.quit()


def open_data_sync_fast(driver):
    adb_tap(155, 2470)  # 点击照片
    time.sleep(1)
    adb_tap(1181, 162)  # 进入设置
    time.sleep(1)
    adb_tap(932, 773)   # 点击设置按钮
    time.sleep(0.5)
    adb_tap(609, 779)   # 点击图库数据同步
    time.sleep(0.5)
    adb_tap(1097, 1159) # 打开数据同步开关
    time.sleep(0.5)
    adb_tap(906, 2404)  # 确认数据同步
    adb_tap(630, 2678)  # 退出设置
    time.sleep(1)
    adb_tap(770, 1690)  # 返回图库
    time.sleep(1)
    adb_tap(100, 277)   # 等待相册同步
    time.sleep(1)


def select_and_download_albums_fast(driver):
    """执行下载动作，然后等待下载完成"""
    adb_tap(477, 2450)  # 点击相册
    time.sleep(0.5)
    adb_swipe(281, 1985, 213, 1186, 1000)  # 滑动屏幕
    time.sleep(2)
    adb_swipe(300, 874, 300, 874, 700)  # 长按第一个相册
    adb_tap(915, 918)   # 选择第二个相册
    adb_tap(311, 1711)  # 选择第三个相册
    adb_tap(915, 1642)  # 选择第四个相册
    adb_tap(1130, 2500) # 点击下载按钮
    time.sleep(0.5)
    adb_tap(1157, 246)  # 打开菜单
    time.sleep(0.5)
    adb_tap(893, 941)   # 查看下载列表

    # 循环检测下载完成（只观察屏幕，不做动作）
    while True:
        if check_download_complete_with_screenshot(driver):
            print("✅ 检测到 '没有下载任务'，下载完成", flush=True)
            break
        else:
            print("⏳ 下载中，继续等待...", flush=True)
            time.sleep(5)  # 每隔5秒检测一次


def check_download_complete_with_screenshot(driver):
    """只在检测时截图"""
    try:
        WebDriverWait(driver, 1.5).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(@text, '没有下载任务')]"))
        )
        allure.attach(driver.get_screenshot_as_png(), name="下载完成", attachment_type=AttachmentType.PNG)
        return True
    except TimeoutException:
        allure.attach(driver.get_screenshot_as_png(), name="下载未完成", attachment_type=AttachmentType.PNG)
        return False


def enable_data_sync_fast(driver):
    adb_tap(118, 246)  # 返回图库
    time.sleep(1)
    adb_tap(155, 2470)  # 点击照片
    time.sleep(0.5)
    adb_tap(1181, 162)  # 进入设置
    time.sleep(0.5)
    adb_tap(932, 773)   # 点击设置按钮
    time.sleep(0.5)
    adb_tap(609, 779)   # 取消图库数据同步
    time.sleep(0.5)
    adb_tap(1097, 1159) # 关闭数据同步开关
    adb_tap(906, 2404)  # 确认关闭
    time.sleep(0.5)
    adb_tap(100, 218)   # 返回
    time.sleep(0.5)
    adb_tap(769, 1673)  # 打开图库app
    time.sleep(0.5)
    adb_tap(100, 218)   # 返回
    time.sleep(0.5)
    adb_tap(455, 2500)  # 进入相册页面
    time.sleep(0.5)


def delete_all_photos_fast(driver):
    adb_tap(502,2489)
    time.sleep(0.5)
    os.system("adb shell input swipe 213 1186 281 1985 500")
    time.sleep(1.5)
    adb_tap(639,1157)
    time.sleep(1)
    os.system("adb shell input swipe 138 496 138 496 800")
    time.sleep(0.5)
    adb_tap(1163,249)
    time.sleep(0.5)
    adb_tap(895,2540)
    time.sleep(0.5)
    adb_tap(907,2413)
    time.sleep(1)




def test_3(driver):
    total_loops = 500
    for loop_index in range(total_loops):
        percent = ((loop_index + 1) / total_loops) * 100
        print(f"▶ 正在执行第 {loop_index + 1}/{total_loops} 次完整流程 ({percent:.1f}%)", flush=True)

        # 第一步：打开数据同步
        open_data_sync_fast(driver)

        # 第二步：选择并下载相册 + 等待下载完成
        select_and_download_albums_fast(driver)

        # 第四步：关闭数据同步
        enable_data_sync_fast(driver)

        # 第五步：删除所有照片
        delete_all_photos_fast(driver)
        time.sleep(2)

        print(f"✅ 第 {loop_index + 1}/{total_loops} 次完整流程执行完成 ({percent:.1f}%)\n", flush=True)
