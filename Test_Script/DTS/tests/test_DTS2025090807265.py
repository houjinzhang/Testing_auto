import pytest
import time
import allure

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from Test_Script import adb_swipe

DEVICE_SERIAL = 'AX2C015322000135'


@pytest.mark.ai_edit     # ⭐ 添加标签，支持“按标签执行”
@allure.feature("照片处理")
@allure.story("AI 编辑—贴纸循环测试")
@allure.title("循环打开/关闭贴纸编辑 1000 次，检测无响应弹窗")

def test_1(driver):
    with allure.step("1. 点击进入第一张图片"):
        adb_tap(212, 1204)
        time.sleep(0.5)

    with allure.step("2. 打开 AI 编辑"):
        adb_tap(646, 2500)
        time.sleep(1)

    with allure.step("3. 滑动到贴纸并点击"):
        adb_swipe(900, 2450, 173, 2430, 100)
        time.sleep(1)
        adb_tap(490, 2474)
        time.sleep(0.5)

    with allure.step("4. 退出贴纸编辑页"):
        adb_tap(130, 1640)
        time.sleep(0.5)

    with allure.step("5. 循环 1000 次：进入/退出贴纸编辑 + **无响应**检测"):
        for i in range(1000):
            with allure.step(f"第 {i + 1} 次循环"):
                adb_tap(612, 2471)  # 进入贴纸编辑
                time.sleep(0.5)
                adb_tap(130, 1640)  # 退出贴纸编辑
                time.sleep(0.5)

    with allure.step("检查是否出现**无响应**弹窗"):
        try:
            # 最多等待 1.5 秒检测弹窗
            WebDriverWait(driver, 1.5).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(@text, '无响应')]"))
            )
            png = driver.get_screenshot_as_png()
            allure.attach(png, name="无响应截图", attachment_type=allure.attachment_type.PNG)
            assert False, "**检测到无响应，测试中断**"
        except TimeoutException:
            # 超过 1.5 秒未检测到弹窗，继续执行
            pass

    with allure.step("附加最终屏幕截图"):
        final_png = driver.get_screenshot_as_png()
        allure.attach(final_png, name="最终截图", attachment_type=allure.attachment_type.PNG)
