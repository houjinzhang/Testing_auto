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
DEVICE_SERIAL = 'AX2C015322000135'

sys.stdout.reconfigure(line_buffering=True)

def adb_tap(x, y):
    """使用 ADB 执行点击命令，速度远快于 Appium"""
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
        "newCommandTimeout": 600,
        "noReset": True
    })
    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    yield driver
    driver.quit()


@allure.epic("相册模块测试")
@allure.feature("图片浏览")
@allure.story("进入相册并查看所有图片")
@allure.severity(allure.severity_level.NORMAL)
@allure.title("测试：点击相册图标 & 点击“所有图片”")
def test_2(driver):
    with allure.step("点击照片"):
        adb_tap(155, 2470)
        time.sleep(1)

    total_loops = 500
    for outer_index in range(total_loops):
        percent = ((outer_index + 1) / total_loops) * 100
        print(f"▶ 正在执行第 {outer_index + 1}/{total_loops} 次循环 ({percent:.1f}%)", flush=True)

        with allure.step(f"第 {outer_index + 1} 次执行删除与恢复流程"):
            # 删除60张照片
            os.system("adb shell input swipe 213 1186 213 1186 800")
            adb_tap(863, 2473)
            adb_tap(1160, 248)
            time.sleep(0.5)
            adb_tap(873, 2418)
            time.sleep(1.5)

            # 进入回收站恢复 60 张（12 张 × 5 次）
            adb_tap(496, 2494)  # 打开相册
            time.sleep(0.5)
            adb_tap(690, 857)  # 打开回收站
            time.sleep(0.5)

            for restore_index in range(5):
                percent_restore = ((restore_index + 1) / 5) * 100
                print(f"▶ 正在执行第 {restore_index + 1}/5 次恢复流程 ({percent_restore:.1f}%)", flush=True)

                with allure.step(f"第 {restore_index + 1} 次恢复 12 张照片"):
                    coords = [
                        (198, 795), (628, 828), (1033, 798),
                        (203, 1181), (693, 1242), (1010, 1277),
                        (170, 1586), (665, 1692), (1026, 1612),
                        (257, 1998), (695, 2042), (1014, 2112)
                    ]

                    for idx, (x, y) in enumerate(coords):
                        if idx == 0:
                            os.system(f"adb shell input swipe {x} {y} {x} {y} 1500")
                        else:
                            adb_tap(x, y)
                        time.sleep(0.3)

                    adb_tap(243, 2542)  # 点击恢复按钮

                    try:
                        WebDriverWait(driver, 1.5).until(
                            EC.presence_of_element_located((By.XPATH, "//*[contains(@text, '无响应')]"))
                        )
                        assert False, "**检测到无响应，测试中断**"
                    except TimeoutException:
                        pass

            # 恢复完 120 张照片后退出回收站并回到照片页（外层循环末尾）
            adb_tap(104, 241)  # 退出回收站
            time.sleep(0.5)
            adb_tap(155, 2470)  # 回到照片页
            time.sleep(1)

            # 检测是否能在 1.5 秒内找到“照片”二字
            try:
                WebDriverWait(driver, 1.5).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(@text, '照片')]"))
                )
                print("✅ 检测到 '照片' 二字，返回照片页成功", flush=True)
            except TimeoutException:
                print("❌ 未检测到 '照片' 二字，返回照片页失败", flush=True)
                assert False, "未检测到 '照片' 二字，测试中断"

        print(f"✅ 第 {outer_index + 1}/{total_loops} 次循环完成 ({percent:.1f}%)\n", flush=True)
def pytest_sessionfinish(session, exitstatus):
    """pytest 运行结束后自动生成并打开 Allure 报告"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    report_dir = os.path.join(base_dir, "report")
    html_dir = os.path.join(base_dir, "report_html")

    if os.path.exists(report_dir) and os.listdir(report_dir):
        os.system(f"allure generate {report_dir} -o {html_dir} --clean")
        print(f"📊 Allure 报告已生成：{html_dir}")
        os.system(f"allure open {html_dir}")  # 自动打开浏览器
    else:
        print("⚠ 没有找到 Allure 原始数据，报告未生成")



    #  pytest -s test_DTS2025091616889.py --alluredir=./report
    #  allure generate ./report -o ./report_html --clean
