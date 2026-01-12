chcp 65001
@echo off
setlocal enabledelayedexpansion

set count=500

for /l %%i in (1,1,%count%) do (
    adb shell input keyevent 24
    echo 已拍照：%%i 张
    powershell -command "Start-Sleep -Milliseconds 500"
)

echo 拍照完成！
pause

