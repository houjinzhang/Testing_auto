import time
import subprocess
import pytest
import allure
import sys

DEVICE_SERIAL = 'BBBM01251M000272'
APP_PACKAGE = "com.hihonor.photos"
APP_ACTIVITY = "com.hihonor.gallery.app.GalleryMain"

def adb_tap(x, y, step_name=None, loop_idx=None):
    """ADB 点击并在控制台 + Allure 输出"""
    msg = f"[Loop {loop_idx}] {step_name} -> tap({x}, {y})" if loop_idx is not None else f"{step_name} -> tap({x}, {y})"
    if step_name:
        print(msg, flush=True)
        allure.attach(msg, name=f"{step_name} (Loop {loop_idx})", attachment_type=allure.attachment_type.TEXT)
    command = f'adb -s {DEVICE_SERIAL} shell input tap {x} {y}'
    subprocess.run(command, shell=True, capture_output=True)
    time.sleep(1)

def is_app_running():
    """检测 App 是否在前台运行"""
    result = subprocess.run(
        f"adb -s {DEVICE_SERIAL} shell pidof {APP_PACKAGE}",
        shell=True, capture_output=True, text=True
    )
    return bool(result.stdout.strip())

def restart_app():
    """重新启动 App"""
    print("[警告] 检测到 App 闪退，正在重新启动...", flush=True)
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell am start -n {APP_PACKAGE}/{APP_ACTIVITY}", shell=True)
    time.sleep(3)  # 等待 App 启动完成
    print("[恢复] App 已重新启动", flush=True)

@pytest.fixture(scope="function")
def driver():
    from appium import webdriver
    from appium.options.common.base import AppiumOptions

    with allure.step("启动 Appium 会话"):
        options = AppiumOptions()
        options.load_capabilities({
            "appium:platformName": "Android",
            "appium:platformVersion": "16",
            "appium:deviceName": "MBH-AN10",
            "appium:appPackage": APP_PACKAGE,
            "appium:appActivity": APP_ACTIVITY,
            "appium:newCommandTimeout": 600,
            "appium:noReset": True
        })
        driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    yield driver
    with allure.step("关闭 Appium 会话"):
        driver.quit()

def test_1(driver):
    total_loops = 2000
    for i in range(1, total_loops + 1):
        sys.stdout.write(f"\n===== 开始第 {i}/{total_loops} 次循环 =====\n")
        sys.stdout.flush()

        try:
            # 如果 App 闪退，自动重启
            if not is_app_running():
                restart_app()

            adb_tap(409, 2190, "进入相册页面", i)
            adb_tap(844, 212, "新建相册加号", i)
            adb_tap(741, 1280, "点击确定", i)
            adb_tap(183, 570, "选择第一张照片", i)
            adb_tap(889, 1858, "点击添加", i)
            adb_tap(465, 1783, "点击复制", i)
            adb_tap(104, 200, "点击返回", i)

        except Exception as e:
            print(f"[错误] 循环 {i} 出现异常: {e}", flush=True)
            restart_app()

        sys.stdout.write(f"===== 第 {i}/{total_loops} 次循环结束 =====\n")
        sys.stdout.flush()
