import pytest
import subprocess
import time

from appium import webdriver
from appium.options.common.base import AppiumOptions


DEVICE_SERIAL = "BDTL01255G001220"


def adb_tap(x, y):
    cmd = f"adb -s {DEVICE_SERIAL} shell input tap {x} {y}"
    subprocess.run(cmd, shell=True)


def adb_swipe(sx, sy, ex, ey, duration=150):
    cmd = f"adb -s {DEVICE_SERIAL} shell input swipe {sx} {sy} {ex} {ey} {duration}"
    subprocess.run(cmd, shell=True)


@pytest.fixture(scope="function")
def driver():
    options = AppiumOptions()
    options.load_capabilities({
        "appium:platformName": "Android",
        "appium:platformVersion": "16",
        "appium:deviceName": "DNP_AN00",
        "appium:appPackage": "com.hihonor.photos",
        "appium:appActivity": "com.hihonor.gallery.app.GalleryMain",
        "appium:newCommandTimeout": 600,
        "appium:noReset": True
    })

    driver = webdriver.Remote("http://127.0.0.1:4723/wd/hub", options=options)
    yield driver

    try:
        driver.quit()
    except:
        pass
