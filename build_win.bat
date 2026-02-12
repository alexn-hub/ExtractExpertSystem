@echo off
echo [1/3] Установка библиотек...
pip install PyQt5 pandas pyqtgraph openpyxl pyinstaller

echo [2/3] Очистка старых данных...
if exist build rd /s /q build
if exist dist rd /s /q dist

echo [3/3] Компиляция в EXE...
:: --onedir: создает папку с EXE и библиотеками (стабильнее для больших проектов)
:: --windowed: отключает черное окно консоли при запуске программы
:: --add-data "app;app": копирует твою папку с кодом ВНУТРЬ приложения
pyinstaller --noconfirm --onedir --windowed --name "ExtractExpertSystem" ^
 --add-data "app;app" ^
 main.py

echo ===========================================
echo ГОТОВО! Программа лежит в папке dist\ExtractExpertSystem
pause