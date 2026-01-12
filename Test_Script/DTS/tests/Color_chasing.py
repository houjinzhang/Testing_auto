import time
import subprocess
import pytest
import allure
import os

DEVICE_SERIAL = 'A2WU015624000112'
APP_PACKAGE = "com.hihonor.photos"
APP_ACTIVITY = "com.hihonor.gallery.app.GalleryMain"

MAX_CRASH_RESTARTS = 5  # 闪退重启次数上限

def adb_tap(x, y, step_name=None, loop_idx=None, wait=1, repeat=1, interval=0.5):
    """ADB 点击并在控制台 + Allure 输出"""
    for r in range(repeat):
        msg = f"[Round {loop_idx}] {step_name} -> tap({x}, {y}) [第{r+1}次]" \
              if loop_idx is not None else f"{step_name} -> tap({x}, {y}) [第{r+1}次]"
        if step_name:
            print(msg, flush=True)
            allure.attach(msg, name=f"{step_name} (Round {loop_idx}) 第{r+1}次",
                          attachment_type=allure.attachment_type.TEXT)
        command = f'adb -s {DEVICE_SERIAL} shell input tap {x} {y}'
        subprocess.run(command, shell=True, capture_output=True)
        if r < repeat - 1:
            time.sleep(interval)
    time.sleep(wait)

def is_app_running():
    """检测 App 是否在前台运行（增加二次确认避免误判）"""
    def check():
        result = subprocess.run(
            f"adb -s {DEVICE_SERIAL} shell pidof {APP_PACKAGE}",
            shell=True, capture_output=True, text=True
        )
        return bool(result.stdout.strip())

    if check():
        return True
    time.sleep(2)  # 等待 2 秒再确认
    return check()

def take_screenshot(filename="crash_screenshot.png"):
    """闪退时截图保存到本地并添加到 Allure 报告"""
    filepath = os.path.join(os.getcwd(), filename)
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell screencap -p /sdcard/{filename}", shell=True)
    subprocess.run(f"adb -s {DEVICE_SERIAL} pull /sdcard/{filename} {filepath}", shell=True)
    if os.path.exists(filepath):
        allure.attach.file(filepath, name="Crash Screenshot", attachment_type=allure.attachment_type.PNG)
        print(f"[截图] 已保存闪退截图到 {filepath}", flush=True)

def close_app():
    """彻底关闭 App"""
    print("[关闭] 正在关闭 App...", flush=True)
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell am force-stop {APP_PACKAGE}", shell=True)
    time.sleep(2)

def restart_app_full():
    """关闭并重启 App"""
    close_app()
    print("[重启] 正在重新启动 App...", flush=True)
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell am start -n {APP_PACKAGE}/{APP_ACTIVITY}", shell=True)
    time.sleep(3)
    print("[恢复] App 已重新启动", flush=True)

def optimize_device():
    """优化设备设置以减少耗电"""
    print("[优化] 降低亮度、关闭动画、清理后台应用...", flush=True)
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell settings put system screen_brightness 20", shell=True)
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell settings put global window_animation_scale 0", shell=True)
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell settings put global transition_animation_scale 0", shell=True)
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell settings put global animator_duration_scale 0", shell=True)
    subprocess.run(f"adb -s {DEVICE_SERIAL} shell am kill-all", shell=True)

@pytest.fixture(scope="function")
def driver():
    from appium import webdriver
    from appium.options.common.base import AppiumOptions

    optimize_device()  # 启动前优化设备

    with allure.step("启动 Appium 会话"):
        options = AppiumOptions()
        options.load_capabilities({
            "appium:platformName": "Android",
            "appium:automationName": "UiAutomator2",
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

def run_steps(steps, round_idx):
    """按步骤执行点击，并检测闪退"""
    for step in steps:
        if not is_app_running():
            take_screenshot(f"crash_round_{round_idx}.png")
            raise RuntimeError(f"App 闪退（双检测确认） - Round {round_idx}")
        adb_tap(
            step["x"], step["y"],
            step_name=step["name"],
            loop_idx=round_idx,
            wait=step.get("wait", 1),
            repeat=step.get("repeat", 1),
            interval=step.get("interval", 0.5)
        )

def test_1(driver):
    # 只执行一次的前置步骤
    first_step = [
        {"name": "点击第一张照片", "x": 204, "y": 1184}
    ]

    # 循环步骤（从点击AI编辑开始）
    def get_loop_steps(round_idx):
        warm_x, warm_y = 731, 2086  # 暖调夕阳固定坐标
        return [
            {"name": "点击AI编辑", "x": 620, "y": 2636},
            {"name": "点击AI色彩", "x": 801, "y": 2604},
            {"name": "点击暖调夕阳", "x": warm_x, "y": warm_y},
            {"name": "点击设置", "x": 1155, "y": 230, "repeat": 2, "interval": 0.5, "wait": 10},
            {"name": "选择金色秋日", "x": 391, "y": 2086},
            {"name": "再次点击设置", "x": 1141, "y": 259, "repeat": 2, "interval": 0.5, "wait": 10},
            {"name": "点击编辑", "x": 91, "y": 253, "wait": 2},
            {"name": "点击放弃", "x": 856, "y": 2490, "wait": 2}
        ]

    total_rounds = 150
    restart_count = 0

    current_round = 1
    while current_round <= total_rounds:
        try:
            print(f"\n===== 开始第 {current_round} 轮测试（目标总轮次 {total_rounds}） =====", flush=True)
            allure.attach(f"开始第 {current_round} 轮测试", name=f"Round {current_round}",
                          attachment_type=allure.attachment_type.TEXT)

            # 第一次执行前置步骤
            run_steps(first_step, round_idx=0)

            # 循环步骤
            while current_round <= total_rounds:
                loop_steps = get_loop_steps(current_round)
                run_steps(loop_steps, current_round)
                current_round += 1

        except RuntimeError as e:
            restart_count += 1
            print(f"[错误] {e}，重新启动 App 并从第一个步骤重新执行...（已重跑 {restart_count} 次）", flush=True)
            allure.attach(f"闪退重跑次数: {restart_count}", name="Crash Restart Count",
                          attachment_type=allure.attachment_type.TEXT)

            if restart_count > MAX_CRASH_RESTARTS:
                print("[终止] 闪退次数超过上限，停止测试！", flush=True)
                allure.attach("闪退次数超过上限，测试终止", name="Test Abort", attachment_type=allure.attachment_type.TEXT)
                break

            restart_app_full()
            current_round = 1  # 从第一轮重新开始
