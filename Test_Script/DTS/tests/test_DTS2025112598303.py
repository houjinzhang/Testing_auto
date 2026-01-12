import pytest
import time
import allure
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from allure_commons.types import AttachmentType

from conftest import adb_tap

@pytest.mark.haha
@allure.feature("DTS2025112598303.py")
@allure.story("裁剪压测")
@allure.title("裁剪功能循环压测 100 次")
def test_1(driver):

    adb_tap(180, 1229)
    time.sleep(1)

    adb_tap(639, 2539)
    time.sleep(1)

    adb_tap(347, 2492)
    time.sleep(0.8)

    for i in range(100):

        with allure.step(f"第 {i+1} 次裁剪循环"):

            adb_tap(623, 1992)
            time.sleep(0.5)

            adb_tap(863, 1976)
            time.sleep(0.5)

            adb_tap(114, 2280)
            time.sleep(0.5)

            adb_tap(1136, 2273)
            time.sleep(0.5)

    # 无响应检测
    try:
        WebDriverWait(driver, 1.5).until(
            EC.presence_of_element_located(
                (By.XPATH, "//*[contains(@text,'无响应')]")
            )
        )
        png = driver.get_screenshot_as_png()
        allure.attach(png, name="无响应截图", attachment_type=AttachmentType.PNG)
        assert False, "检测到无响应"
    except TimeoutException:
        pass

    png = driver.get_screenshot_as_png()
    allure.attach(png, name="最终截图", attachment_type=AttachmentType.PNG)
