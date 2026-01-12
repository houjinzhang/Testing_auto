import subprocess
import time

# 设备 ID（用 adb devices 查看）
DEVICE_ID = "AR2P015609000050"

# Appium 辅助应用包名
PACKAGES = [
    "io.appium.settings",
    "io.appium.uiautomator2.server",
    "io.appium.uiautomator2.server.test"
]

def run_cmd(cmd):
    """运行命令并返回输出"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def uninstall_packages():
    print("🔹 卸载旧的 Appium 辅助 APK...")
    for pkg in PACKAGES:
        run_cmd(f"adb -s {DEVICE_ID} uninstall {pkg}")
    print("✅ 卸载完成")

def reinstall_packages():
    print("🔹 重新安装 Appium 辅助 APK（通过启动一次 Appium 会话自动安装）...")
    print("   请在卸载后重新运行你的测试脚本，Appium 会自动安装最新版本。")
    time.sleep(2)

def set_ignore_battery_optimization():
    print("🔹 设置忽略电池优化...")
    for pkg in PACKAGES:
        run_cmd(f"adb -s {DEVICE_ID} shell dumpsys deviceidle whitelist +{pkg}")
    print("✅ 已加入电池优化白名单")

def main():
    print("=== Appium Server 自动修复工具 ===")
    uninstall_packages()
    set_ignore_battery_optimization()
    reinstall_packages()
    print("🎯 修复完成，请重新运行测试")

if __name__ == "__main__":
    main()
