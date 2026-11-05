@echo off
chcp 65001 > nul
echo =======================================================
echo  Сборка ППО "ExtractExpertSystem" под Windows
echo =======================================================

echo [1/3] Установка всех необходимых зависимостей...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller pymodbus opcua pyyaml

echo [2/3] Очистка предыдущих сборок...
if exist build rd /s /q build
if exist dist rd /s /q dist

echo [3/3] Компиляция приложения в папку dist...
pyinstaller --noconfirm --onedir --windowed --name "ExtractExpertSystem" ^
  --add-data "config.yaml;." ^
  --add-data "app/gui/styles.qss;app/gui" ^
  --add-data "data;data" ^
  --hidden-import "sklearn.ensemble._forest" ^
  --hidden-import "sklearn.ensemble._gb" ^
  --hidden-import "sklearn.linear_model._ridge" ^
  --hidden-import "pymodbus" ^
  --hidden-import "opcua" ^
  main.py

echo =======================================================
echo ГОТОВО! Программа собрана в: dist\ExtractExpertSystem\ExtractExpertSystem.exe
echo =======================================================
pause