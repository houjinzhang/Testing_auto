@echo off
echo Pulling logs...
set date=%date:~0,10%
set date=%date:/=%
if "%time:~0,2%" lss "10" (set hh=0%time:~1,1%) else (set hh=%time:~0,2%)
set time=%hh%%time:~3,5%
::set time=%time:~0,8%
set time=%time::=%
::echo %time%
set dirName=%date%-%time%
::echo %dirName%
mkdir %dirName%
adb pull /data/log/android_logs %dirName%/android_logs
adb pull /data/log/hilogs %dirName%/hilogs
adb pull /data/system/dropbox %dirName%/dropbox
echo Pulling databases
adb pull /data/user/0/com.android.providers.media.module/databases %dirName%/media
adb pull /data/user/0/com.google.android.providers.media.module/databases %dirName%/mediaModule
mkdir %cd%\%dirName%\library
adb pull /data/data/com.hihonor.medialibrary/databases %dirName%/library/databases
adb pull /data/data/com.hihonor.medialibrary/shared_prefs %dirName%/library/shared_prefs
mkdir %cd%\%dirName%\gallery
adb pull /data/data/com.hihonor.photos/databases %dirName%/gallery/databases
adb pull /data/data/com.hihonor.photos/shared_prefs %dirName%/gallery/shared_prefs
adb pull /data/data/com.huawei.photos/databases %dirName%/gallery/databases
adb pull /data/data/com.huawei.photos/shared_prefs %dirName%/gallery/shared_prefs
mkdir %cd%\%dirName%\CutOutVideo
adb pull  /data/data/com.hihonor.videoeditor/files/LivePhotoCache %dirName%/CutOutVideo
pause